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
"""Generic Human Interface Device API.

This provides a python interface to libusb's hidapi library which,
unlike udev, is available for non-linux platforms.
See https://github.com/libusb/hidapi for how to obtain binaries.

Parts of this code are adapted from https://github.com/apmorton/pyhidapi
which is MIT licensed.
"""

from __future__ import annotations

import atexit
import ctypes
import logging
import platform
import typing

from threading import Thread
from time import sleep
from typing import Any
from typing import Callable

from hidapi.common import DeviceInfo

if typing.TYPE_CHECKING:
    import gi

    gi.require_version("Gdk", "3.0")
    from gi.repository import GLib  # NOQA: E402

logger = logging.getLogger(__name__)

ACTION_ADD = "add"
ACTION_REMOVE = "remove"

# Global handle to hidapi
_hidapi = None

# hidapi binary names for various platforms
_library_paths = (
    "libhidapi-hidraw.so",
    "libhidapi-hidraw.so.0",
    "libhidapi-libusb.so",
    "libhidapi-libusb.so.0",
    "libhidapi-iohidmanager.so",
    "libhidapi-iohidmanager.so.0",
    "libhidapi.dylib",
    "hidapi.dll",
    "libhidapi-0.dll",
)

for lib in _library_paths:
    try:
        _hidapi = ctypes.cdll.LoadLibrary(lib)
        break
    except OSError:
        pass
else:
    raise ImportError(f"Unable to load hidapi library, tried: {' '.join(_library_paths)}")


# Retrieve version of hdiapi library
class _cHidApiVersion(ctypes.Structure):
    _fields_ = [
        ("major", ctypes.c_int),
        ("minor", ctypes.c_int),
        ("patch", ctypes.c_int),
    ]


_hidapi.hid_version.argtypes = []
_hidapi.hid_version.restype = ctypes.POINTER(_cHidApiVersion)
_hid_version = _hidapi.hid_version()


# Construct device info struct based on API version
class _cDeviceInfo(ctypes.Structure):
    def as_dict(self):
        return {name: getattr(self, name) for name, _t in self._fields_ if name != "next"}


# Low level hdiapi device info struct
# See https://github.com/libusb/hidapi/blob/master/hidapi/hidapi.h#L143
_cDeviceInfo_fields = [
    ("path", ctypes.c_char_p),
    ("vendor_id", ctypes.c_ushort),
    ("product_id", ctypes.c_ushort),
    ("serial_number", ctypes.c_wchar_p),
    ("release_number", ctypes.c_ushort),
    ("manufacturer_string", ctypes.c_wchar_p),
    ("product_string", ctypes.c_wchar_p),
    ("usage_page", ctypes.c_ushort),
    ("usage", ctypes.c_ushort),
    ("interface_number", ctypes.c_int),
    ("next", ctypes.POINTER(_cDeviceInfo)),
]
if _hid_version.contents.major >= 0 and _hid_version.contents.minor >= 13:
    _cDeviceInfo_fields.append(("bus_type", ctypes.c_int))
_cDeviceInfo._fields_ = _cDeviceInfo_fields

# Set up hidapi functions
_hidapi.hid_init.argtypes = []
_hidapi.hid_init.restype = ctypes.c_int
_hidapi.hid_exit.argtypes = []
_hidapi.hid_exit.restype = ctypes.c_int
_hidapi.hid_enumerate.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
_hidapi.hid_enumerate.restype = ctypes.POINTER(_cDeviceInfo)
_hidapi.hid_free_enumeration.argtypes = [ctypes.POINTER(_cDeviceInfo)]
_hidapi.hid_free_enumeration.restype = None
_hidapi.hid_open.argtypes = [ctypes.c_ushort, ctypes.c_ushort, ctypes.c_wchar_p]
_hidapi.hid_open.restype = ctypes.c_void_p
_hidapi.hid_open_path.argtypes = [ctypes.c_char_p]
_hidapi.hid_open_path.restype = ctypes.c_void_p
_hidapi.hid_write.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
_hidapi.hid_write.restype = ctypes.c_int
_hidapi.hid_read_timeout.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
_hidapi.hid_read_timeout.restype = ctypes.c_int
_hidapi.hid_read.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
_hidapi.hid_read.restype = ctypes.c_int
_hidapi.hid_get_input_report.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
_hidapi.hid_get_input_report.restype = ctypes.c_int
_hidapi.hid_set_nonblocking.argtypes = [ctypes.c_void_p, ctypes.c_int]
_hidapi.hid_set_nonblocking.restype = ctypes.c_int
_hidapi.hid_send_feature_report.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
_hidapi.hid_send_feature_report.restype = ctypes.c_int
_hidapi.hid_get_feature_report.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
_hidapi.hid_get_feature_report.restype = ctypes.c_int
_hidapi.hid_close.argtypes = [ctypes.c_void_p]
_hidapi.hid_close.restype = None
_hidapi.hid_get_manufacturer_string.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_size_t]
_hidapi.hid_get_manufacturer_string.restype = ctypes.c_int
_hidapi.hid_get_product_string.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_size_t]
_hidapi.hid_get_product_string.restype = ctypes.c_int
_hidapi.hid_get_serial_number_string.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_size_t]
_hidapi.hid_get_serial_number_string.restype = ctypes.c_int
_hidapi.hid_get_indexed_string.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_size_t]
_hidapi.hid_get_indexed_string.restype = ctypes.c_int
_hidapi.hid_error.argtypes = [ctypes.c_void_p]
_hidapi.hid_error.restype = ctypes.c_wchar_p

# Initialize hidapi
_hidapi.hid_init()
atexit.register(_hidapi.hid_exit)

# Solaar opens the same device more than once which will fail unless we
# allow non-exclusive opening. On windows opening with shared access is
# the default, for macOS we need to set it explicitly.
if platform.system() == "Darwin":
    _hidapi.hid_darwin_set_open_exclusive.argtypes = [ctypes.c_int]
    _hidapi.hid_darwin_set_open_exclusive.restype = None
    _hidapi.hid_darwin_set_open_exclusive(0)


class HIDError(Exception):
    pass


def _enumerate_devices():
    """Returns all HID devices which are potentially useful to us"""
    devices = []
    c_devices = _hidapi.hid_enumerate(0, 0)
    p = c_devices
    while p:
        devices.append(p.contents.as_dict())
        p = p.contents.next
    _hidapi.hid_free_enumeration(c_devices)

    unique_devices = {}
    for device in devices:
        # hidapi returns separate entries for each usage page of a device.
        # Deduplicate by path to only keep one device entry.
        if device["path"] not in unique_devices:
            unique_devices[device["path"]] = device

    unique_devices = unique_devices.values()
    # print("Unique devices:\n" + '\n'.join([f"{dev}" for dev in unique_devices]))
    return unique_devices


# Use a separate thread to check if devices have been removed or connected
class _DeviceMonitor(Thread):
    def __init__(self, device_callback, polling_delay=5.0):
        self.device_callback = device_callback
        self.polling_delay = polling_delay
        self.prev_devices = None
        # daemon threads are automatically killed when main thread exits
        super().__init__(daemon=True)

    def run(self):
        # Populate initial set of devices so startup doesn't cause any callbacks
        self.prev_devices = {tuple(dev.items()): dev for dev in _enumerate_devices()}

        # Continously enumerate devices and raise callback for changes
        while True:
            current_devices = {tuple(dev.items()): dev for dev in _enumerate_devices()}
            for key, device in self.prev_devices.items():
                if key not in current_devices:
                    self.device_callback(ACTION_REMOVE, device)
            for key, device in current_devices.items():
                if key not in self.prev_devices:
                    self.device_callback(ACTION_ADD, device)
            self.prev_devices = current_devices
            sleep(self.polling_delay)


def _match(
    action: str,
    device: dict[str, Any],
    filter_func: Callable[[int, int, int, bool, bool], dict[str, Any]],
):
    """
    The filter_func is used to determine whether this is a device of
    interest to Solaar. It is given the bus id, vendor id, and product
    id and returns a dictionary with the required hid_driver and
    usb_interface and whether this is a receiver or device.
    """

    vid = device["vendor_id"]
    pid = device["product_id"]
    hid_bus_type = device["bus_type"]

    # Translate hidapi bus_type to the bus_id values Solaar expects
    if device.get("bus_type") == 0x01:
        bus_id = 0x03  # USB
    elif device.get("bus_type") == 0x02:
        bus_id = 0x05  # Bluetooth
    else:
        bus_id = None
        logger.info(f"Device {device['path']} has an unsupported bus type {hid_bus_type:02X}")
        return None

    # Skip unlikely devices with all-zero VID PID or unsupported bus IDs
    if vid == 0 and pid == 0:
        logger.info(f"Device {device['path']} has all-zero VID and PID")
        logger.info(f"Skipping unlikely device {device['path']} ({bus_id}/{vid:04X}/{pid:04X})")
        return None

    # Check for hidpp support
    device["hidpp_short"] = False
    device["hidpp_long"] = False
    device_handle = None
    try:
        device_handle = open_path(device["path"])
        try:
            report = _get_input_report(device_handle, 0x10, 32)
            if len(report) == 1 + 6 and report[0] == 0x10:
                device["hidpp_short"] = True
        except HIDError as e:
            logger.info(f"Error opening device {device['path']} ({bus_id}/{vid:04X}/{pid:04X}) for hidpp check: {e}")
        try:
            report = _get_input_report(device_handle, 0x11, 32)
            if len(report) == 1 + 19 and report[0] == 0x11:
                device["hidpp_long"] = True
        except HIDError as e:
            logger.info(f"Error opening device {device['path']} ({bus_id}/{vid:04X}/{pid:04X}) for hidpp check: {e}")
    finally:
        if device_handle:
            close(device_handle)

    logger.info(
        "Found device BID %s VID %04X PID %04X HID++ SHORT %s LONG %s",
        bus_id,
        vid,
        pid,
        device["hidpp_short"],
        device["hidpp_long"],
    )

    if not device["hidpp_short"] and not device["hidpp_long"]:
        return None

    filtered_result = filter_func(bus_id, vid, pid, device["hidpp_short"], device["hidpp_long"])
    if not filtered_result:
        return
    is_device = filtered_result.get("isDevice")

    if action == ACTION_ADD:
        d_info = DeviceInfo(
            path=device["path"].decode(),
            bus_id=bus_id,
            vendor_id=f"{vid:04X}",  # noqa
            product_id=f"{pid:04X}",  # noqa
            interface=None,
            driver=None,
            manufacturer=device["manufacturer_string"],
            product=device["product_string"],
            serial=device["serial_number"],
            release=device["release_number"],
            isDevice=is_device,
            hidpp_short=device["hidpp_short"],
            hidpp_long=device["hidpp_long"],
        )
        return d_info

    elif action == ACTION_REMOVE:
        d_info = DeviceInfo(
            path=device["path"].decode(),
            bus_id=None,
            vendor_id=f"{vid:04X}",  # noqa
            product_id=f"{pid:04X}",  # noqa
            interface=None,
            driver=None,
            manufacturer=None,
            product=None,
            serial=None,
            release=None,
            isDevice=is_device,
            hidpp_short=None,
            hidpp_long=None,
        )
        return d_info

    logger.info(f"Finished checking HIDPP support for device {device['path']} ({bus_id}/{vid:04X}/{pid:04X})")


def find_paired_node(receiver_path: str, index: int, timeout: int):
    """Find the node of a device paired with a receiver"""
    return None


def find_paired_node_wpid(receiver_path: str, index: int):
    """Find the node of a device paired with a receiver, get wpid from udev"""
    return None


def monitor_glib(
    glib: GLib,
    callback: Callable,
    filter_func: Callable[[int, int, int, bool, bool], dict[str, Any]],
) -> None:
    """Monitor GLib.

    Parameters
    ----------
    glib
        GLib instance.
    callback
        Called when device found.
    filter_func
        Filter devices callback.
    """

    def device_callback(action: str, device):
        if action == ACTION_ADD:
            d_info = _match(action, device, filter_func)
            if d_info:
                glib.idle_add(callback, action, d_info)
        elif action == ACTION_REMOVE:
            # Removed devices will be detected by Solaar directly
            pass

    monitor = _DeviceMonitor(device_callback=device_callback)
    monitor.start()


def enumerate(filter_func) -> DeviceInfo:
    """Enumerate the HID Devices.

    List all the HID devices attached to the system, optionally filtering by
    vendor_id, product_id, and/or interface_number.

    :returns: a list of matching ``DeviceInfo`` tuples.
    """
    for device in _enumerate_devices():
        d_info = _match(ACTION_ADD, device, filter_func)
        if d_info:
            yield d_info


def open(vendor_id, product_id, serial=None):
    """Open a HID device by its Vendor ID, Product ID and optional serial number.

    If no serial is provided, the first device with the specified IDs is opened.

    :returns: an opaque device handle, or ``None``.
    """
    if serial is not None:
        serial = ctypes.create_unicode_buffer(serial)

    device_handle = _hidapi.hid_open(vendor_id, product_id, serial)
    if device_handle is None:
        raise HIDError(_hidapi.hid_error(None))
    return device_handle


def open_path(device_path: str) -> int:
    """Open a HID device by its path name.

    :param device_path: the path of a ``DeviceInfo`` tuple returned by enumerate().

    :returns: an opaque device handle, or ``None``.
    """
    if not isinstance(device_path, bytes):
        device_path = device_path.encode()

    device_handle = _hidapi.hid_open_path(device_path)
    if device_handle is None:
        raise HIDError(_hidapi.hid_error(None))
    return device_handle


def close(device_handle) -> None:
    """Close a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    assert device_handle
    _hidapi.hid_close(device_handle)


def write(device_handle: int, data: bytes) -> int:
    """Write an Output report to a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    :param data: the data bytes to send including the report number as the
    first byte.

    The first byte of data[] must contain the Report ID. For
    devices which only support a single report, this must be set
    to 0x0. The remaining bytes contain the report data. Since
    the Report ID is mandatory, calls to hid_write() will always
    contain one more byte than the report contains. For example,
    if a hid report is 16 bytes long, 17 bytes must be passed to
    hid_write(), the Report ID (or 0x0, for devices with a
    single report), followed by the report data (16 bytes). In
    this example, the length passed in would be 17.

    write() will send the data on the first OUT endpoint, if
    one exists. If it does not, it will send the data through
    the Control Endpoint (Endpoint 0).
    """
    assert device_handle
    assert data
    assert isinstance(data, bytes), (repr(data), type(data))

    bytes_written = _hidapi.hid_write(device_handle, data, len(data))
    if bytes_written < 0:
        raise HIDError(_hidapi.hid_error(device_handle))
    return bytes_written


def read(device_handle, bytes_count, timeout_ms=None):
    """Read an Input report from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    :param bytes_count: maximum number of bytes to read.
    :param timeout_ms: can be -1 (default) to wait for data indefinitely, 0 to
    read whatever is in the device's input buffer, or a positive integer to
    wait that many milliseconds.

    Input reports are returned to the host through the INTERRUPT IN endpoint.
    The first byte will contain the Report number if the device uses numbered
    reports.

    :returns: the data packet read, an empty bytes string if a timeout was
    reached, or None if there was an error while reading.
    """
    assert device_handle

    data = ctypes.create_string_buffer(bytes_count)
    if timeout_ms is None or timeout_ms < 0:
        bytes_read = _hidapi.hid_read(device_handle, data, bytes_count)
    else:
        bytes_read = _hidapi.hid_read_timeout(device_handle, data, bytes_count, timeout_ms)

    if bytes_read < 0:
        raise HIDError(_hidapi.hid_error(device_handle))

    return data.raw[:bytes_read]


def _get_input_report(device_handle, report_id, size):
    assert device_handle
    data = ctypes.create_string_buffer(size)
    data[0] = bytearray((report_id,))
    size = _hidapi.hid_get_input_report(device_handle, data, size)
    if size < 0:
        raise HIDError(_hidapi.hid_error(device_handle))
    return data.raw[:size]


def _readstring(device_handle, func, max_length=255):
    assert device_handle
    buf = ctypes.create_unicode_buffer(max_length)
    ret = func(device_handle, buf, max_length)
    if ret < 0:
        raise HIDError("Error reading device property")
    return buf.value


def get_manufacturer(device_handle):
    """Get the Manufacturer String from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return _readstring(device_handle, _hidapi.get_manufacturer_string)


def get_product(device_handle):
    """Get the Product String from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return _readstring(device_handle, _hidapi.get_product_string)


def get_serial(device_handle):
    """Get the serial number from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return _readstring(device_handle, _hidapi.get_serial_number_string)
