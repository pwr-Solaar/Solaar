## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Base low-level functions as API for upper layers."""

from __future__ import annotations

import dataclasses
import logging
import platform
import struct
import threading
import typing

from contextlib import contextmanager
from random import getrandbits
from time import time
from typing import Any
from typing import Callable

from . import base_usb
from . import common
from . import descriptors
from . import exceptions
from .common import LOGITECH_VENDOR_ID
from .common import BusID
from .hidpp10_constants import ErrorCode as Hidpp10ErrorCode
from .hidpp20_constants import ErrorCode as Hidpp20ErrorCode

if typing.TYPE_CHECKING:
    import gi

    from hidapi.common import DeviceInfo

    gi.require_version("Gdk", "3.0")
    from gi.repository import GLib  # NOQA: E402

if platform.system() == "Linux":
    import hidapi.udev_impl as hidapi
else:
    import hidapi.hidapi_impl as hidapi

logger = logging.getLogger(__name__)


class HIDProtocol(typing.Protocol):
    def find_paired_node_wpid(self, receiver_path: str, index: int):
        ...

    def find_paired_node(self, receiver_path: str, index: int, timeout: int):
        ...

    def open(self, vendor_id, product_id, serial=None):
        ...

    def open_path(self, path) -> int:
        ...

    def enumerate(self, filter_func: Callable[[int, int, int, bool, bool], dict[str, typing.Any]]) -> DeviceInfo:
        ...

    def monitor_glib(
        self, glib: GLib, callback: Callable, filter_func: Callable[[int, int, int, bool, bool], dict[str, typing.Any]]
    ) -> None:
        ...

    def read(self, device_handle, bytes_count, timeout_ms):
        ...

    def write(self, device_handle: int, data: bytes) -> int:
        ...

    def close(self, device_handle) -> None:
        ...


SHORT_MESSAGE_SIZE = 7
_LONG_MESSAGE_SIZE = 20
_MEDIUM_MESSAGE_SIZE = 15
_MAX_READ_SIZE = 32

HIDPP_SHORT_MESSAGE_ID = 0x10
HIDPP_LONG_MESSAGE_ID = 0x11
DJ_MESSAGE_ID = 0x20


"""Default timeout on read (in seconds)."""
DEFAULT_TIMEOUT = 4
# the receiver itself should reply very fast, within 500ms
_RECEIVER_REQUEST_TIMEOUT = 0.9
# devices may reply a lot slower, as the call has to go wireless to them and come back
_DEVICE_REQUEST_TIMEOUT = DEFAULT_TIMEOUT
# when pinging, be extra patient (no longer)
_PING_TIMEOUT = DEFAULT_TIMEOUT

hidapi = typing.cast(HIDProtocol, hidapi)

request_lock = threading.Lock()  # serialize all requests
handles_lock = {}


@dataclasses.dataclass
class HIDPPNotification:
    report_id: int
    devnumber: int
    sub_id: int
    address: int
    data: bytes

    def __str__(self):
        text_as_hex = common.strhex(self.data)
        return f"Notification({self.report_id:02x},{self.devnumber},{self.sub_id:02X},{self.address:02X},{text_as_hex})"


def _usb_device(product_id: int, usb_interface: int) -> dict[str, Any]:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "bus_id": BusID.USB,
        "usb_interface": usb_interface,
        "isDevice": True,
    }


def _bluetooth_device(product_id: int) -> dict[str, Any]:
    return {"vendor_id": LOGITECH_VENDOR_ID, "product_id": product_id, "bus_id": BusID.BLUETOOTH, "isDevice": True}


KNOWN_DEVICE_IDS = []

for _ignore, d in descriptors.DEVICES.items():
    if d.usbid:
        usb_interface = d.interface if d.interface else 2
        KNOWN_DEVICE_IDS.append(_usb_device(d.usbid, usb_interface))
    if d.btid:
        KNOWN_DEVICE_IDS.append(_bluetooth_device(d.btid))


def product_information(usb_id: int) -> dict[str, Any]:
    """Returns hardcoded information from USB receiver."""
    return base_usb.get_receiver_info(usb_id)


def receivers():
    """Enumerate all the receivers attached to the machine."""
    yield from hidapi.enumerate(get_known_receiver_info)


def filter_products_of_interest(
    bus_id: int, vendor_id: int, product_id: int, hidpp_short: bool = False, hidpp_long: bool = False
) -> dict[str, Any] | None:
    """Check that this product is of interest and if so return the device record for further checking"""

    recv = get_known_receiver_info(bus_id, vendor_id, product_id, hidpp_short, hidpp_long)
    if recv:  # known or unknown receiver
        return recv

    device = get_known_device_info(bus_id, vendor_id, product_id)
    if device:
        return device

    if hidpp_short or hidpp_long:
        return get_unknown_hid_device_info(bus_id, vendor_id, product_id)

    if hidpp_short is None and hidpp_long is None:
        return get_unknown_logitech_device_info(bus_id, vendor_id, product_id)
    return None


def get_known_device_info(bus_id: int, vendor_id: int, product_id: int) -> dict[str, Any]:
    for recv in KNOWN_DEVICE_IDS:
        if _match_device(recv, bus_id, vendor_id, product_id):
            return recv


def get_unknown_hid_device_info(bus_id: int, vendor_id: int, product_id: int) -> dict[str, Any]:
    return {"vendor_id": vendor_id, "product_id": product_id, "bus_id": bus_id, "isDevice": True}


def get_unknown_logitech_device_info(bus_id: int, vendor_id: int, product_id: int) -> dict[str, Any] | None:
    """Get info from unknown device in Logitech product range.

    Check whether product is a Logitech USB-connected or Bluetooth
    device based on bus, vendor, and product ID. This allows Solaar to
    support receiverless HID++ 2.0 devices that it knows nothing about.
    """
    if vendor_id != LOGITECH_VENDOR_ID:
        return None

    if bus_id == BusID.USB.value and (0xC07D <= product_id <= 0xC094 or 0xC32B <= product_id <= 0xC344):
        device_info = _usb_device(product_id, 2)
        return device_info
    elif bus_id == BusID.BLUETOOTH.value and (0xB012 <= product_id <= 0xB0FF or 0xB317 <= product_id <= 0xB3FF):
        device_info = _bluetooth_device(product_id)
        return device_info

    return None


def _match_device(record: dict[str, Any], bus_id: int, vendor_id: int, product_id: int):
    return (
        (record.get("bus_id") is None or record.get("bus_id") == bus_id)
        and (record.get("vendor_id") is None or record.get("vendor_id") == vendor_id)
        and (record.get("product_id") is None or record.get("product_id") == product_id)
    )


def get_known_receiver_info(
    bus_id: int, vendor_id: int, product_id: int, _hidpp_short: bool = False, _hidpp_long: bool = False
) -> dict[str, Any]:
    """Check that this product is a Logitech receiver and return it.

    Filters based on bus_id, vendor_id and product_id.

    If so return the receiver record for further checking.
    """
    try:
        record = base_usb.get_receiver_info(product_id)
        if _match_device(record, bus_id, vendor_id, product_id):
            return record
    except ValueError:
        pass

    if vendor_id == LOGITECH_VENDOR_ID and 0xC500 <= product_id <= 0xC5FF:  # unknown receiver
        return {"vendor_id": vendor_id, "product_id": product_id, "bus_id": bus_id, "isDevice": False}
    return None


def receivers_and_devices():
    """Enumerate all the receivers and devices directly attached to the machine."""
    yield from hidapi.enumerate(filter_products_of_interest)


def notify_on_receivers_glib(glib: GLib, callback: Callable):
    """Watch for matching devices and notifies the callback on the GLib thread.

    Parameters
    ----------
    glib
        GLib instance.
    """
    return hidapi.monitor_glib(glib, callback, filter_products_of_interest)


def open_path(path) -> int:
    """Checks if the given Linux device path points to the right UR device.

    :param path: the Linux device path.

    The UR physical device may expose multiple linux devices with the same
    interface, so we have to check for the right one. At this moment the only
    way to distinguish betheen them is to do a test ping on an invalid
    (attached) device number (i.e., 0), expecting a 'ping failed' reply.

    :returns: an open receiver handle if this is the right Linux device, or
    ``None``.
    """
    return hidapi.open_path(path)


def open():
    """Opens the first Logitech Unifying Receiver found attached to the machine.

    :returns: An open file handle for the found receiver, or ``None``.
    """
    for rawdevice in receivers():
        handle = open_path(rawdevice.path)
        if handle:
            return handle


def close(handle):
    """Closes a HID device handle."""
    if handle:
        try:
            if isinstance(handle, int):
                hidapi.close(handle)
            else:
                handle.close()
            return True
        except Exception:
            pass

    return False


def write(handle, devnumber, data, long_message=False):
    """Writes some data to the receiver, addressed to a certain device.

    :param handle: an open UR handle.
    :param devnumber: attached device number.
    :param data: data to send, up to 5 bytes.

    The first two (required) bytes of data must be the SubId and address.

    :raises NoReceiver: if the receiver is no longer available, i.e. has
    been physically removed from the machine, or the kernel driver has been
    unloaded. The handle will be closed automatically.
    """
    # the data is padded to either 5 or 18 bytes
    assert data is not None
    assert isinstance(data, bytes), (repr(data), type(data))

    if long_message or len(data) > SHORT_MESSAGE_SIZE - 2 or data[:1] == b"\x82":
        wdata = struct.pack("!BB18s", HIDPP_LONG_MESSAGE_ID, devnumber, data)
    else:
        wdata = struct.pack("!BB5s", HIDPP_SHORT_MESSAGE_ID, devnumber, data)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "(%s) <= w[%02X %02X %s %s]",
            handle,
            ord(wdata[:1]),
            devnumber,
            common.strhex(wdata[2:4]),
            common.strhex(wdata[4:]),
        )

    try:
        hidapi.write(int(handle), wdata)
    except Exception as reason:
        logger.error("write failed, assuming handle %r no longer available", handle)
        close(handle)
        raise exceptions.NoReceiver(reason=reason) from reason


def read(handle, timeout=DEFAULT_TIMEOUT):
    """Read some data from the receiver. Usually called after a write (feature
    call), to get the reply.

    :param: handle open handle to the receiver
    :param: timeout how long to wait for a reply, in seconds

    :returns: a tuple of (devnumber, message data), or `None`

    :raises NoReceiver: if the receiver is no longer available, i.e. has
    been physically removed from the machine, or the kernel driver has been
    unloaded. The handle will be closed automatically.
    """
    reply = _read(handle, timeout)
    if reply:
        return reply


def _is_relevant_message(data: bytes) -> bool:
    """Checks if given id is a HID++ or DJ message.

    Applies sanity checks on message report ID and message size.
    """
    assert isinstance(data, bytes), (repr(data), type(data))

    # mapping from report_id to message length
    report_lengths = {
        HIDPP_SHORT_MESSAGE_ID: SHORT_MESSAGE_SIZE,
        HIDPP_LONG_MESSAGE_ID: _LONG_MESSAGE_SIZE,
        DJ_MESSAGE_ID: _MEDIUM_MESSAGE_SIZE,
        0x21: _MAX_READ_SIZE,
    }

    report_id = ord(data[:1])
    if report_id in report_lengths:
        if report_lengths.get(report_id) == len(data):
            return True
        else:
            logger.warning(f"unexpected message size: report_id {report_id:02X} message {common.strhex(data)}")
    return False


def _read(handle, timeout) -> tuple[int, int, bytes]:
    """Read an incoming packet from the receiver.

    :returns: a tuple of (report_id, devnumber, data), or `None`.

    :raises NoReceiver: if the receiver is no longer available, i.e. has
    been physically removed from the machine, or the kernel driver has been
    unloaded. The handle will be closed automatically.
    """
    try:
        # convert timeout to milliseconds, the hidapi expects it
        timeout = int(timeout * 1000)
        data = hidapi.read(int(handle), _MAX_READ_SIZE, timeout)
    except Exception as reason:
        logger.warning("read failed, assuming handle %r no longer available", handle)
        close(handle)
        raise exceptions.NoReceiver(reason=reason) from reason

    if data and _is_relevant_message(data):  # ignore messages that fail check
        report_id = ord(data[:1])
        devnumber = ord(data[1:2])

        if logger.isEnabledFor(logging.DEBUG) and (
            report_id != DJ_MESSAGE_ID or ord(data[2:3]) > 0x10
        ):  # ignore DJ input messages
            logger.debug(
                "(%s) => r[%02X %02X %s %s]",
                handle,
                report_id,
                devnumber,
                common.strhex(data[2:4]),
                common.strhex(data[4:]),
            )

        return report_id, devnumber, data[2:]


def make_notification(report_id: int, devnumber: int, data: bytes) -> HIDPPNotification | None:
    """Guess if this is a notification (and not just a request reply), and
    return a Notification if it is."""

    sub_id = ord(data[:1])
    if sub_id & 0x80 == 0x80:
        # this is either a HID++1.0 register r/w, or an error reply
        return None

    # DJ input records are not notifications
    if report_id == DJ_MESSAGE_ID and (sub_id < 0x10):
        return None

    address = ord(data[1:2])
    if sub_id == 0x00 and (address & 0x0F == 0x00):
        # this is a no-op notification - don't do anything with it
        return None

    if (
        # standard HID++ 1.0 notification, SubId may be 0x40 - 0x7F
        (sub_id >= 0x40)  # noqa: E131
        or
        # custom HID++1.0 battery events, where SubId is 0x07/0x0D
        (sub_id in (0x07, 0x0D) and len(data) == 5 and data[4:5] == b"\x00")
        or
        # custom HID++1.0 illumination event, where SubId is 0x17
        (sub_id == 0x17 and len(data) == 5)
        or
        # HID++ 2.0 feature notifications have the SoftwareID 0
        (address & 0x0F == 0x00)
    ):  # noqa: E129
        return HIDPPNotification(report_id, devnumber, sub_id, address, data[2:])
    return None


def handle_lock(handle):
    with request_lock:
        if handles_lock.get(handle) is None:
            if logger.isEnabledFor(logging.INFO):
                logger.info("New lock %s", repr(handle))
            handles_lock[handle] = threading.Lock()  # Serialize requests on the handle
    return handles_lock[handle]


# context manager for locks with a timeout
@contextmanager
def acquire_timeout(lock, handle, timeout):
    result = lock.acquire(timeout=timeout)
    try:
        if not result:
            logger.error("lock on handle %d not acquired, probably due to timeout", int(handle))
        yield result
    finally:
        if result:
            lock.release()


def find_paired_node(receiver_path: str, index: int, timeout: int):
    """Find the node of a device paired with a receiver."""
    return hidapi.find_paired_node(receiver_path, index, timeout)


def find_paired_node_wpid(receiver_path: str, index: int):
    """Find the node of a device paired with a receiver.

    Get wpid from udev.
    """
    return hidapi.find_paired_node_wpid(receiver_path, index)


# a very few requests (e.g., host switching) do not expect a reply, but use no_reply=True with extreme caution
def request(
    handle,
    devnumber,
    request_id: int,
    *params,
    no_reply: bool = False,
    return_error: bool = False,
    long_message: bool = False,
    protocol: float = 1.0,
):
    """Makes a feature call to a device and waits for a matching reply.
    :param handle: an open UR handle.
    :param devnumber: attached device number.
    :param request_id: a 16-bit integer.
    :param params: parameters for the feature call, 3 to 16 bytes.
    :returns: the reply data, or ``None`` if some error occurred. or no reply expected
    """
    with acquire_timeout(handle_lock(handle), handle, 10.0):
        assert isinstance(request_id, int)
        if (devnumber != 0xFF or protocol >= 2.0) and request_id < 0x8000:
            # Always set the most significant bit (8) in SoftwareId,
            # to make notifications easier to distinguish from request replies.
            # This only applies to peripheral requests, ofc.
            sw_id = _get_next_sw_id()
            request_id = (request_id & 0xFFF0) | sw_id  # was 0x08 | getrandbits(3)

        timeout = _RECEIVER_REQUEST_TIMEOUT if devnumber == 0xFF else _DEVICE_REQUEST_TIMEOUT
        # be extra patient on long register read
        if request_id & 0xFF00 == 0x8300:
            timeout *= 2

        if params:
            params = b"".join(struct.pack("B", p) if isinstance(p, int) else p for p in params)
        else:
            params = b""
        request_data = struct.pack("!H", request_id) + params

        ihandle = int(handle)
        notifications_hook = getattr(handle, "notifications_hook", None)
        try:
            _read_input_buffer(handle, ihandle, notifications_hook)
        except exceptions.NoReceiver:
            logger.warning("device or receiver disconnected")
            return None
        write(ihandle, devnumber, request_data, long_message)

        if no_reply:
            return None

        # we consider timeout from this point
        request_started = time()
        delta = 0

        while delta < timeout:
            reply = _read(handle, timeout)
            if reply:
                report_id, reply_devnumber, reply_data = reply
                if reply_devnumber == devnumber or reply_devnumber == devnumber ^ 0xFF:  # BT device returning 0x00
                    if (
                        report_id == HIDPP_SHORT_MESSAGE_ID
                        and reply_data[:1] == b"\x8f"
                        and reply_data[1:3] == request_data[:2]
                    ):
                        error = ord(reply_data[3:4])

                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(
                                "(%s) device 0x%02X error on request {%04X}: %d = %s",
                                handle,
                                devnumber,
                                request_id,
                                error,
                                Hidpp10ErrorCode(error),
                            )
                        return Hidpp10ErrorCode(error) if return_error else None
                    if reply_data[:1] == b"\xff" and reply_data[1:3] == request_data[:2]:
                        # a HID++ 2.0 feature call returned with an error
                        error = ord(reply_data[3:4])
                        logger.error(
                            "(%s) device %d error on feature request {%04X}: %d = %s",
                            handle,
                            devnumber,
                            request_id,
                            error,
                            Hidpp20ErrorCode(error),
                        )
                        raise exceptions.FeatureCallError(
                            number=devnumber,
                            request=request_id,
                            error=error,
                            params=params,
                        )

                    if reply_data[:2] == request_data[:2]:
                        if devnumber == 0xFF:
                            if request_id == 0x83B5 or request_id == 0x81F1:
                                # these replies have to match the first parameter as well
                                if reply_data[2:3] == params[:1]:
                                    return reply_data[2:]
                                else:
                                    # hm, not matching my request, and certainly not a notification
                                    continue
                            else:
                                return reply_data[2:]
                        else:
                            return reply_data[2:]
                else:
                    # a reply was received, but did not match our request in any way
                    # reset the timeout starting point
                    request_started = time()

                if notifications_hook:
                    n = make_notification(report_id, reply_devnumber, reply_data)
                    if n:
                        notifications_hook(n)
            delta = time() - request_started

        logger.warning(
            "timeout (%0.2f/%0.2f) on device %d request {%04X} params [%s]",
            delta,
            timeout,
            devnumber,
            request_id,
            common.strhex(params),
        )
        # raise DeviceUnreachable(number=devnumber, request=request_id)


def ping(handle, devnumber, long_message: bool = False):
    """Check if a device is connected to the receiver.
    :returns: The HID protocol supported by the device, as a floating point number, if the device is active.
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("(%s) pinging device %d", handle, devnumber)
    with acquire_timeout(handle_lock(handle), handle, 10.0):
        notifications_hook = getattr(handle, "notifications_hook", None)
        try:
            _read_input_buffer(handle, int(handle), notifications_hook)
        except exceptions.NoReceiver:
            logger.warning("device or receiver disconnected")
            return

        # randomize the mark byte to be able to identify the ping reply
        sw_id = _get_next_sw_id()
        request_id = 0x0010 | sw_id  # was 0x0018 | getrandbits(3)
        request_data = struct.pack("!HBBB", request_id, 0, 0, getrandbits(8))
        write(int(handle), devnumber, request_data, long_message)

        request_started = time()  # we consider timeout from this point
        delta = 0
        while delta < _PING_TIMEOUT:
            reply = _read(handle, _PING_TIMEOUT)
            if reply:
                report_id, reply_devnumber, reply_data = reply
                if reply_devnumber == devnumber or reply_devnumber == devnumber ^ 0xFF:  # BT device returning 0x00
                    if reply_data[:2] == request_data[:2] and reply_data[4:5] == request_data[-1:]:
                        # HID++ 2.0+ device, currently connected
                        return ord(reply_data[2:3]) + ord(reply_data[3:4]) / 10.0

                    if (
                        report_id == HIDPP_SHORT_MESSAGE_ID
                        and reply_data[:1] == b"\x8f"
                        and reply_data[1:3] == request_data[:2]
                    ):  # error response
                        error = ord(reply_data[3:4])
                        if error == Hidpp10ErrorCode.INVALID_SUB_ID_COMMAND:
                            # a valid reply from a HID++ 1.0 device
                            return 1.0
                        if error in [Hidpp10ErrorCode.RESOURCE_ERROR, Hidpp10ErrorCode.CONNECTION_REQUEST_FAILED]:
                            return  # device unreachable
                        if error == Hidpp10ErrorCode.UNKNOWN_DEVICE:  # no paired device with that number
                            logger.error("(%s) device %d error on ping request: unknown device", handle, devnumber)
                            raise exceptions.NoSuchDevice(number=devnumber, request=request_id)

                if notifications_hook:
                    n = make_notification(report_id, reply_devnumber, reply_data)
                    if n:
                        notifications_hook(n)

            delta = time() - request_started

        logger.warning("(%s) timeout (%0.2f/%0.2f) on device %d ping", handle, delta, _PING_TIMEOUT, devnumber)


def _read_input_buffer(handle, ihandle, notifications_hook):
    """Consume anything already in the input buffer.

    Used by request() and ping() before their write.
    """

    while True:
        try:
            # read whatever is already in the buffer, if any
            data = hidapi.read(ihandle, _MAX_READ_SIZE, 0)
        except Exception as reason:
            logger.error("read failed, assuming receiver %s no longer available", handle)
            close(handle)
            raise exceptions.NoReceiver(reason=reason) from reason

        if data:
            if _is_relevant_message(data):  # only process messages that pass check
                # report_id = ord(data[:1])
                if notifications_hook:
                    n = make_notification(ord(data[:1]), ord(data[1:2]), data[2:])
                    if n:
                        notifications_hook(n)
        else:
            # nothing in the input buffer, we're done
            return


def _get_next_sw_id() -> int:
    """Returns 'random' software ID to separate replies from different devices.

    Cycle the HID++ 2.0 software ID from 0x2 to 0xF to separate
    results and notifications.
    """
    if not hasattr(_get_next_sw_id, "software_id"):
        _get_next_sw_id.software_id = 0xF

    if _get_next_sw_id.software_id < 0xF:
        _get_next_sw_id.software_id += 1
    else:
        _get_next_sw_id.software_id = 2
    return _get_next_sw_id.software_id
