# -*- python-mode -*-
# -*- coding: UTF-8 -*-

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

# Base low-level functions used by the API proper.
# Unlikely to be used directly unless you're expanding the API.

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import DEBUG as _DEBUG
from logging import getLogger
from random import getrandbits as _random_bits
from time import time as _timestamp

import hidapi as _hid

from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .base_usb import ALL as _RECEIVER_USB_IDS
from .base_usb import DEVICES as _DEVICE_IDS
from .base_usb import other_device_check as _other_device_check
from .common import KwException as _KwException
from .common import pack as _pack
from .common import strhex as _strhex

_log = getLogger(__name__)
del getLogger

#
#
#

_SHORT_MESSAGE_SIZE = 7
_LONG_MESSAGE_SIZE = 20
_MEDIUM_MESSAGE_SIZE = 15
_MAX_READ_SIZE = 32

HIDPP_SHORT_MESSAGE_ID = 0x10
HIDPP_LONG_MESSAGE_ID = 0x11
DJ_MESSAGE_ID = 0x20

# mapping from report_id to message length
report_lengths = {
    HIDPP_SHORT_MESSAGE_ID: _SHORT_MESSAGE_SIZE,
    HIDPP_LONG_MESSAGE_ID: _LONG_MESSAGE_SIZE,
    DJ_MESSAGE_ID: _MEDIUM_MESSAGE_SIZE,
    0x21: _MAX_READ_SIZE
}
"""Default timeout on read (in seconds)."""
DEFAULT_TIMEOUT = 4
# the receiver itself should reply very fast, within 500ms
_RECEIVER_REQUEST_TIMEOUT = 0.9
# devices may reply a lot slower, as the call has to go wireless to them and come back
_DEVICE_REQUEST_TIMEOUT = DEFAULT_TIMEOUT
# when pinging, be extra patient
_PING_TIMEOUT = DEFAULT_TIMEOUT * 2

#
# Exceptions that may be raised by this API.
#


class NoReceiver(_KwException):
    """Raised when trying to talk through a previously open handle, when the
    receiver is no longer available. Should only happen if the receiver is
    physically disconnected from the machine, or its kernel driver module is
    unloaded."""
    pass


class NoSuchDevice(_KwException):
    """Raised when trying to reach a device number not paired to the receiver."""
    pass


class DeviceUnreachable(_KwException):
    """Raised when a request is made to an unreachable (turned off) device."""
    pass


#
#
#


def match(record, bus_id, vendor_id, product_id):
    return ((record.get('bus_id') is None or record.get('bus_id') == bus_id)
            and (record.get('vendor_id') is None or record.get('vendor_id') == vendor_id)
            and (record.get('product_id') is None or record.get('product_id') == product_id))


def filter_receivers(bus_id, vendor_id, product_id):
    """Check that this product is a Logitech receiver and if so return the receiver record for further checking"""
    for record in _RECEIVER_USB_IDS:  # known receivers
        if match(record, bus_id, vendor_id, product_id):
            return record


def receivers():
    """Enumerate all the receivers attached to the machine."""
    for dev in _hid.enumerate(filter_receivers):
        yield dev


def filter_devices(bus_id, vendor_id, product_id):
    """Check that this product is of interest and if so return the device record for further checking"""
    for record in _DEVICE_IDS:  # known devices
        if match(record, bus_id, vendor_id, product_id):
            return record
    return _other_device_check(bus_id, vendor_id, product_id)  # USB and BT devices unknown to Solaar


def wired_devices():
    """Enumerate all the USB-connected and Bluetooth devices attached to the machine."""
    for dev in _hid.enumerate(filter_devices):
        yield dev


def filter_either(bus_id, vendor_id, product_id):
    return filter_receivers(bus_id, vendor_id, product_id) or filter_devices(bus_id, vendor_id, product_id)


def notify_on_receivers_glib(callback):
    """Watch for matching devices and notifies the callback on the GLib thread."""
    return _hid.monitor_glib(callback, filter_either)


#
#
#


def open_path(path):
    """Checks if the given Linux device path points to the right UR device.

    :param path: the Linux device path.

    The UR physical device may expose multiple linux devices with the same
    interface, so we have to check for the right one. At this moment the only
    way to distinguish betheen them is to do a test ping on an invalid
    (attached) device number (i.e., 0), expecting a 'ping failed' reply.

    :returns: an open receiver handle if this is the right Linux device, or
    ``None``.
    """
    return _hid.open_path(path)


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
                _hid.close(handle)
            else:
                handle.close()
            # _log.info("closed receiver handle %r", handle)
            return True
        except Exception:
            # _log.exception("closing receiver handle %r", handle)
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

    if long_message or len(data) > _SHORT_MESSAGE_SIZE - 2 or data[:1] == b'\x82':
        wdata = _pack('!BB18s', HIDPP_LONG_MESSAGE_ID, devnumber, data)
    else:
        wdata = _pack('!BB5s', HIDPP_SHORT_MESSAGE_ID, devnumber, data)
    if _log.isEnabledFor(_DEBUG):
        _log.debug('(%s) <= w[%02X %02X %s %s]', handle, ord(wdata[:1]), devnumber, _strhex(wdata[2:4]), _strhex(wdata[4:]))

    try:
        _hid.write(int(handle), wdata)
    except Exception as reason:
        _log.error('write failed, assuming handle %r no longer available', handle)
        close(handle)
        raise NoReceiver(reason=reason)


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


# sanity checks on  message report id and size
def check_message(data):
    assert isinstance(data, bytes), (repr(data), type(data))
    report_id = ord(data[:1])
    if report_id in report_lengths:  # is this an HID++ or DJ message?
        if report_lengths.get(report_id) == len(data):
            return True
        else:
            _log.warn('unexpected message size: report_id %02X message %s' % (report_id, _strhex(data)))
    return False


def _read(handle, timeout):
    """Read an incoming packet from the receiver.

    :returns: a tuple of (report_id, devnumber, data), or `None`.

    :raises NoReceiver: if the receiver is no longer available, i.e. has
    been physically removed from the machine, or the kernel driver has been
    unloaded. The handle will be closed automatically.
    """
    try:
        # convert timeout to milliseconds, the hidapi expects it
        timeout = int(timeout * 1000)
        data = _hid.read(int(handle), _MAX_READ_SIZE, timeout)
    except Exception as reason:
        _log.warn('read failed, assuming handle %r no longer available', handle)
        close(handle)
        raise NoReceiver(reason=reason)

    if data and check_message(data):  # ignore messages that fail check
        report_id = ord(data[:1])
        devnumber = ord(data[1:2])

        if _log.isEnabledFor(_DEBUG):
            _log.debug('(%s) => r[%02X %02X %s %s]', handle, report_id, devnumber, _strhex(data[2:4]), _strhex(data[4:]))

        return report_id, devnumber, data[2:]


#
#
#


def _skip_incoming(handle, ihandle, notifications_hook):
    """Read anything already in the input buffer.

    Used by request() and ping() before their write.
    """

    while True:
        try:
            # read whatever is already in the buffer, if any
            data = _hid.read(ihandle, _MAX_READ_SIZE, 0)
        except Exception as reason:
            _log.error('read failed, assuming receiver %s no longer available', handle)
            close(handle)
            raise NoReceiver(reason=reason)

        if data:
            if check_message(data):  # only process messages that pass check
                # report_id = ord(data[:1])
                if notifications_hook:
                    n = make_notification(ord(data[:1]), ord(data[1:2]), data[2:])
                    if n:
                        notifications_hook(n)
        else:
            # nothing in the input buffer, we're done
            return


def make_notification(report_id, devnumber, data):
    """Guess if this is a notification (and not just a request reply), and
    return a Notification tuple if it is."""

    sub_id = ord(data[:1])
    if sub_id & 0x80 == 0x80:
        # this is either a HID++1.0 register r/w, or an error reply
        return

    # DJ input records are not notifications
    if report_id == DJ_MESSAGE_ID and (sub_id < 0x10):
        return

    address = ord(data[1:2])
    if (
        # standard HID++ 1.0 notification, SubId may be 0x40 - 0x7F
        (sub_id >= 0x40) or  # noqa: E131
        # custom HID++1.0 battery events, where SubId is 0x07/0x0D
        (sub_id in (0x07, 0x0D) and len(data) == 5 and data[4:5] == b'\x00') or
        # custom HID++1.0 illumination event, where SubId is 0x17
        (sub_id == 0x17 and len(data) == 5) or
        # HID++ 2.0 feature notifications have the SoftwareID 0
        (address & 0x0F == 0x00)
    ):  # noqa: E129
        return _HIDPP_Notification(report_id, devnumber, sub_id, address, data[2:])


_HIDPP_Notification = namedtuple('_HIDPP_Notification', ('report_id', 'devnumber', 'sub_id', 'address', 'data'))
_HIDPP_Notification.__str__ = lambda self: 'Notification(%02x,%d,%02X,%02X,%s)' % (
    self.report_id, self.devnumber, self.sub_id, self.address, _strhex(self.data)
)
_HIDPP_Notification.__unicode__ = _HIDPP_Notification.__str__
del namedtuple

#
#
#


# a very few requests (e.g., host switching) do not expect a reply, but use no_reply=True with extreme caution
def request(handle, devnumber, request_id, *params, no_reply=False, return_error=False, long_message=False):
    """Makes a feature call to a device and waits for a matching reply.
    :param handle: an open UR handle.
    :param devnumber: attached device number.
    :param request_id: a 16-bit integer.
    :param params: parameters for the feature call, 3 to 16 bytes.
    :returns: the reply data, or ``None`` if some error occurred. or no reply expected
    """

    # import inspect as _inspect
    # print ('\n  '.join(str(s) for s in _inspect.stack()))

    assert isinstance(request_id, int)
    if devnumber != 0xFF and request_id < 0x8000:
        # For HID++ 2.0 feature requests, randomize the SoftwareId to make it
        # easier to recognize the reply for this request. also, always set the
        # most significant bit (8) in SoftwareId, to make notifications easier
        # to distinguish from request replies.
        # This only applies to peripheral requests, ofc.
        request_id = (request_id & 0xFFF0) | 0x08 | _random_bits(3)

    timeout = _RECEIVER_REQUEST_TIMEOUT if devnumber == 0xFF else _DEVICE_REQUEST_TIMEOUT
    # be extra patient on long register read
    if request_id & 0xFF00 == 0x8300:
        timeout *= 2

    if params:
        params = b''.join(_pack('B', p) if isinstance(p, int) else p for p in params)
    else:
        params = b''
    # if _log.isEnabledFor(_DEBUG):
    #     _log.debug("(%s) device %d request_id {%04X} params [%s]", handle, devnumber, request_id, _strhex(params))
    request_data = _pack('!H', request_id) + params

    ihandle = int(handle)
    notifications_hook = getattr(handle, 'notifications_hook', None)
    try:
        _skip_incoming(handle, ihandle, notifications_hook)
    except NoReceiver:
        _log.warn('device or receiver disconnected')
        return None
    write(ihandle, devnumber, request_data, long_message)

    if no_reply:
        return None

    # we consider timeout from this point
    request_started = _timestamp()
    delta = 0

    while delta < timeout:
        reply = _read(handle, timeout)

        if reply:
            report_id, reply_devnumber, reply_data = reply
            if reply_devnumber == devnumber:
                if report_id == HIDPP_SHORT_MESSAGE_ID and reply_data[:1] == b'\x8F' and reply_data[1:3] == request_data[:2]:
                    error = ord(reply_data[3:4])

                    # if error == _hidpp10.ERROR.resource_error: # device unreachable
                    #     _log.warn("(%s) device %d error on request {%04X}: unknown device", handle, devnumber, request_id)
                    #     raise DeviceUnreachable(number=devnumber, request=request_id)

                    # if error == _hidpp10.ERROR.unknown_device: # unknown device
                    #     _log.error("(%s) device %d error on request {%04X}: unknown device", handle, devnumber, request_id)
                    #     raise NoSuchDevice(number=devnumber, request=request_id)

                    if _log.isEnabledFor(_DEBUG):
                        _log.debug(
                            '(%s) device 0x%02X error on request {%04X}: %d = %s', handle, devnumber, request_id, error,
                            _hidpp10.ERROR[error]
                        )
                    return _hidpp10.ERROR[error] if return_error else None
                if reply_data[:1] == b'\xFF' and reply_data[1:3] == request_data[:2]:
                    # a HID++ 2.0 feature call returned with an error
                    error = ord(reply_data[3:4])
                    _log.error(
                        '(%s) device %d error on feature request {%04X}: %d = %s', handle, devnumber, request_id, error,
                        _hidpp20.ERROR[error]
                    )
                    raise _hidpp20.FeatureCallError(number=devnumber, request=request_id, error=error, params=params)

                if reply_data[:2] == request_data[:2]:
                    if request_id & 0xFE00 == 0x8200:
                        # long registry r/w should return a long reply
                        assert report_id == HIDPP_LONG_MESSAGE_ID
                    elif request_id & 0xFE00 == 0x8000:
                        # short registry r/w should return a short reply
                        assert report_id == HIDPP_SHORT_MESSAGE_ID

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
                request_started = _timestamp()

            if notifications_hook:
                n = make_notification(report_id, reply_devnumber, reply_data)
                if n:
                    notifications_hook(n)
                # elif _log.isEnabledFor(_DEBUG):
                #     _log.debug("(%s) ignoring reply %02X [%s]", handle, reply_devnumber, _strhex(reply_data))
            # elif _log.isEnabledFor(_DEBUG):
            #     _log.debug("(%s) ignoring reply %02X [%s]", handle, reply_devnumber, _strhex(reply_data))

        delta = _timestamp() - request_started
        # if _log.isEnabledFor(_DEBUG):
        #     _log.debug("(%s) still waiting for reply, delta %f", handle, delta)

    _log.warn(
        'timeout (%0.2f/%0.2f) on device %d request {%04X} params [%s]', delta, timeout, devnumber, request_id,
        _strhex(params)
    )
    # raise DeviceUnreachable(number=devnumber, request=request_id)


def ping(handle, devnumber, long_message=False):
    """Check if a device is connected to the receiver.

    :returns: The HID protocol supported by the device, as a floating point number, if the device is active.
    """
    if _log.isEnabledFor(_DEBUG):
        _log.debug('(%s) pinging device %d', handle, devnumber)

    # import inspect as _inspect
    # print ('\n  '.join(str(s) for s in _inspect.stack()))

    assert devnumber != 0xFF
    assert devnumber >= 0x00
    assert devnumber < 0x0F

    # randomize the SoftwareId and mark byte to be able to identify the ping
    # reply, and set most significant (0x8) bit in SoftwareId so that the reply
    # is always distinguishable from notifications
    request_id = 0x0018 | _random_bits(3)
    request_data = _pack('!HBBB', request_id, 0, 0, _random_bits(8))

    ihandle = int(handle)
    notifications_hook = getattr(handle, 'notifications_hook', None)
    try:
        _skip_incoming(handle, ihandle, notifications_hook)
    except NoReceiver:
        _log.warn('device or receiver disconnected')
        return

    write(ihandle, devnumber, request_data, long_message)

    # we consider timeout from this point
    request_started = _timestamp()
    delta = 0

    while delta < _PING_TIMEOUT:
        reply = _read(handle, _PING_TIMEOUT)

        if reply:
            report_id, reply_devnumber, reply_data = reply
            if reply_devnumber == devnumber:
                if reply_data[:2] == request_data[:2] and reply_data[4:5] == request_data[-1:]:
                    # HID++ 2.0+ device, currently connected
                    return ord(reply_data[2:3]) + ord(reply_data[3:4]) / 10.0

                if report_id == HIDPP_SHORT_MESSAGE_ID and reply_data[:1] == b'\x8F' and reply_data[1:3] == request_data[:2]:
                    assert reply_data[-1:] == b'\x00'
                    error = ord(reply_data[3:4])

                    if error == _hidpp10.ERROR.invalid_SubID__command:  # a valid reply from a HID++ 1.0 device
                        return 1.0

                    if error == _hidpp10.ERROR.resource_error:  # device unreachable
                        return

                    if error == _hidpp10.ERROR.unknown_device:  # no paired device with that number
                        _log.error('(%s) device %d error on ping request: unknown device', handle, devnumber)
                        raise NoSuchDevice(number=devnumber, request=request_id)

            if notifications_hook:
                n = make_notification(report_id, reply_devnumber, reply_data)
                if n:
                    notifications_hook(n)
                # elif _log.isEnabledFor(_DEBUG):
                #     _log.debug("(%s) ignoring reply %02X [%s]", handle, reply_devnumber, _strhex(reply_data))

        delta = _timestamp() - request_started

    _log.warn('(%s) timeout (%0.2f/%0.2f) on device %d ping', handle, delta, _PING_TIMEOUT, devnumber)
    # raise DeviceUnreachable(number=devnumber, request=request_id)
