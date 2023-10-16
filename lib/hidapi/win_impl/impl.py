# -*- python-mode -*-

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

It is currently a partial pure-Python implementation of the native HID API
implemented by signal11 (https://github.com/signal11/hidapi), and requires
``pyudev``.
The docstrings are mostly copied from the hidapi API header, with changes where
necessary.
"""

import errno as _errno
import os as _os
import warnings as _warnings

# the tuple object we'll expose when enumerating devices
from collections import namedtuple
from logging import INFO as _INFO
from logging import getLogger
from select import select as _select
from time import sleep
from time import time as _timestamp
from .device import DeviceManager, enumerate_devices
from typing import Dict
from functools import wraps
import hid

_log = getLogger(__name__)
del getLogger
native_implementation = 'udev'
fileopen = open

DeviceInfo = namedtuple(
    'DeviceInfo', [
        'path',
        'bus_id',
        'vendor_id',
        'product_id',
        'interface',
        'driver',
        'manufacturer',
        'product',
        'serial',
        'release',
        'isDevice',
        'hidpp_short',
        'hidpp_long',
    ]
)
del namedtuple

#
# exposed API
# docstrings mostly copied from hidapi.h
#


def init():
    """This function is a no-op, and exists only to match the native hidapi
    implementation.

    :returns: ``True``.
    """
    return True


def exit():
    """This function is a no-op, and exists only to match the native hidapi
    implementation.

    :returns: ``True``.
    """
    return True


# The filterfn is used to determine whether this is a device of interest to Solaar.
# It is given the bus id, vendor id, and product id and returns a dictionary
# with the required hid_driver and usb_interface and whether this is a receiver or device.
def _match(action, info, filterfn):
    try:
        hidpp_short = hidpp_long = False
        for path in info['path'].split(';'):
            device = hid.device()
            device.open_path(path.encode('utf-8'))
            if not hidpp_short:
                try:
                    hidpp_short = len(device.get_input_report(0x10, 32)) == 7
                    # and _Usage(0xFF00, 0x0001) in rd.get_input_items(0x10)[0].usages  # be more permissive
                except IOError:
                    pass
            if not hidpp_long:
                try:
                    hidpp_long = len(device.get_input_report(0x11, 32)) == 20
                    # and _Usage(0xFF00, 0x0002) in rd.get_input_items(0x11)[0].usages  # be more permissive
                except IOError:
                    pass
            device.close()
        if not hidpp_short and not hidpp_long:
            return
    except Exception as e:  # if can't process report descriptor fall back to old scheme
        hidpp_short = hidpp_long = None
        _log.warn('Report Descriptor not processed for BID %d VID %d PID %d: %s', info['bus_type'], info['vendor_id'], info['product_id'], e)

    filter = filterfn(info['bus_type'], info['vendor_id'], info['product_id'], hidpp_short, hidpp_long)
    if not filter:
        return
    #hid_driver = filter.get('hid_driver')
    interface_number = filter.get('usb_interface')
    isDevice = filter.get('isDevice')

    if action == 'add':
        """
        hid_driver_name = hid_device.get('DRIVER')
        # print ("** found hid", action, device, "hid:", hid_device, hid_driver_name)
        if hid_driver:
            if isinstance(hid_driver, tuple):
                if hid_driver_name not in hid_driver:
                    return
            elif hid_driver_name != hid_driver:
                return
        """

        usb_interface = info['interface_number']
        # print('*** usb interface', action, device, 'usb_interface:', intf_device, usb_interface, interface_number)
        if _log.isEnabledFor(_INFO):
            _log.info(
                'Found device BID %d VID %d PID %d HID++ %s %s USB %s %s', info['bus_type'], info['vendor_id'], info['product_id'], hidpp_short, hidpp_long,
                usb_interface, interface_number
            )
        if not (hidpp_short or hidpp_long or interface_number is None or interface_number == usb_interface):
            return

        d_info = DeviceInfo(
            path=info['path'],
            bus_id=info['bus_type'],
            vendor_id=info['vendor_id'],
            product_id=info['product_id'],
            interface=usb_interface,
            driver=None,
            manufacturer=info['manufacturer_string'],
            product=info['product_string'],
            serial=info['serial_number'],
            release=info['release_number'],
            isDevice=isDevice,
            hidpp_short=hidpp_short,
            hidpp_long=hidpp_long,
        )
        return d_info

    elif action == 'remove':
        # print (dict(device), dict(usb_device))

        d_info = DeviceInfo(
            path=info['path'],
            bus_id=None,
            vendor_id=info['vendor_id'],
            product_id=info['product_id'],
            interface=None,
            driver=None,
            manufacturer=None,
            product=None,
            serial=None,
            release=None,
            isDevice=isDevice,
            hidpp_short=None,
            hidpp_long=None,
        )
        return d_info


def find_paired_node(receiver_path, index, timeout):
    """Find the node of a device paired with a receiver"""
    return None

def find_paired_node_wpid(receiver_path, index):
    """Find the node of a device paired with a receiver, get wpid from udev"""
    return None

def monitor_glib(callback, filterfn):
    pass

def enumerate(filterfn):
    """Enumerate the HID Devices.

    List all the HID devices attached to the system, optionally filtering by
    vendor_id, product_id, and/or interface_number.

    :returns: a list of matching ``DeviceInfo`` tuples.
    """

    for dev in enumerate_devices():
        dev_info = _match('add', dev, filterfn)
        if dev_info:
            yield dev_info


def open(vendor_id, product_id, serial=None):
    """Open a HID device by its Vendor ID, Product ID and optional serial number.

    If no serial is provided, the first device with the specified IDs is opened.

    :returns: an opaque device handle, or ``None``.
    """

    def matchfn(bid, vid, pid):
        return vid == vendor_id and pid == product_id

    for device in enumerate(matchfn):
        if serial is None or serial == device.serial:
            return open_path(device.path)


def open_path(device_path: str):
    """Open a HID device by its path name.

    :param device_path: the path of a ``DeviceInfo`` tuple returned by enumerate().

    :returns: an opaque device handle, or ``None``.
    """
    assert device_path
    #assert device_path.startswith('/dev/hidraw')

    _log.info('OPEN PATH %s', device_path)
    retrycount = 0
    while (retrycount < 3):
        retrycount += 1
        try:
            return DeviceManager.get().open_path(device_path)
        except:
            pass
        """
        except OSError as e:
            _log.info('OPEN PATH FAILED %s ERROR %s %s', device_path, e.errno, e)
            if e.errno == _errno.EACCES:
                sleep(0.1)
            else:
                raise
        """


def close(device_handle):
    """Close a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    assert device_handle
    DeviceManager.get().close(device_handle)


def write(device_handle, data):
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
    retrycount = 0
    bytes_written = 0
    while (retrycount < 3):
        try:
            retrycount += 1
            bytes_written = DeviceManager.get().write(device_handle, data)
        except OSError as e:
            #if e.errno == _errno.EPIPE:
            sleep(0.1)
        else:
            break
    if bytes_written != len(data):
        raise OSError(_errno.EIO, 'written %d bytes out of expected %d' % (bytes_written, len(data)))


def read(device_handle, bytes_count, timeout_ms=-1):
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
    data = DeviceManager.get().read(device_handle, bytes_count, timeout_ms)
    assert data is not None
    assert isinstance(data, bytes), (repr(data), type(data))
    return data

def get_manufacturer(device_handle):
    """Get the Manufacturer String from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return DeviceManager.get().get_info(device_handle).manufacturer_string


def get_product(device_handle):
    """Get the Product String from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return DeviceManager.get().get_info(device_handle).product_string


def get_serial(device_handle):
    """Get the serial number from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return DeviceManager.get().get_info(device_handle).serial_number
