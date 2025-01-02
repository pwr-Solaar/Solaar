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

from __future__ import annotations

import errno
import logging
import os
import typing
import warnings


# the tuple object we'll expose when enumerating devices
from select import select
from time import sleep
from time import time
from typing import Callable

import pyudev

from hidapi.common import DeviceInfo

if typing.TYPE_CHECKING:
    import gi

    gi.require_version("Gdk", "3.0")
    from gi.repository import GLib  # NOQA: E402

logger = logging.getLogger(__name__)

fileopen = open

ACTION_ADD = "add"
ACTION_REMOVE = "remove"

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


def _match(action: str, device, filter_func: typing.Callable[[int, int, int, bool, bool], dict[str, typing.Any]]):
    """

    The filter_func is used to determine whether this is a device of
    interest to Solaar. It is given the bus id, vendor id, and product
    id and returns a dictionary with the required hid_driver and
    usb_interface and whether this is a receiver or device."""
    logger.debug(f"Dbus event {action} {device}")
    hid_device = device.find_parent("hid")
    if hid_device is None:  # only HID devices are of interest to Solaar
        return
    hid_id = hid_device.properties.get("HID_ID")
    if not hid_id:
        return  # there are reports that sometimes the id isn't set up right so be defensive
    bid, vid, pid = hid_id.split(":")
    hid_hid_device = hid_device.find_parent("hid")
    if hid_hid_device is not None:
        return  # these are devices connected through a receiver so don't pick them up here

    try:  # if report descriptor does not indicate HID++ capabilities then this device is not of interest to Solaar
        from hid_parser import ReportDescriptor

        hidpp_short = hidpp_long = False
        devfile = "/sys" + hid_device.properties.get("DEVPATH") + "/report_descriptor"
        with fileopen(devfile, "rb") as fd:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                rd = ReportDescriptor(fd.read())
            hidpp_short = 0x10 in rd.input_report_ids and 6 * 8 == int(rd.get_input_report_size(0x10))
            # and _Usage(0xFF00, 0x0001) in rd.get_input_items(0x10)[0].usages  # be more permissive
            hidpp_long = 0x11 in rd.input_report_ids and 19 * 8 == int(rd.get_input_report_size(0x11))
            # and _Usage(0xFF00, 0x0002) in rd.get_input_items(0x11)[0].usages  # be more permissive
        if not hidpp_short and not hidpp_long:
            return
    except Exception as e:  # if can't process report descriptor fall back to old scheme
        hidpp_short = None
        hidpp_long = None
        logger.info(
            "Report Descriptor not processed for DEVICE %s BID %s VID %s PID %s: %s",
            device.device_node,
            bid,
            vid,
            pid,
            e,
        )

    filtered_result = filter_func(int(bid, 16), int(vid, 16), int(pid, 16), hidpp_short, hidpp_long)
    if not filtered_result:
        return
    interface_number = filtered_result.get("usb_interface")
    isDevice = filtered_result.get("isDevice")

    if action == ACTION_ADD:
        hid_driver_name = hid_device.properties.get("DRIVER")
        intf_device = device.find_parent("usb", "usb_interface")
        usb_interface = None if intf_device is None else intf_device.attributes.asint("bInterfaceNumber")
        # print('*** usb interface', action, device, 'usb_interface:', intf_device, usb_interface, interface_number)
        logger.info(
            "Found device %s BID %s VID %s PID %s HID++ %s %s USB %s %s",
            device.device_node,
            bid,
            vid,
            pid,
            hidpp_short,
            hidpp_long,
            usb_interface,
            interface_number,
        )
        if not (hidpp_short or hidpp_long or interface_number is None or interface_number == usb_interface):
            return
        attrs = intf_device.attributes if intf_device is not None else None

        d_info = DeviceInfo(
            path=device.device_node,
            bus_id=int(bid, 16),
            vendor_id=vid[-4:],
            product_id=pid[-4:],
            interface=usb_interface,
            driver=hid_driver_name,
            manufacturer=attrs.get("manufacturer") if attrs else None,
            product=attrs.get("product") if attrs else None,
            serial=hid_device.properties.get("HID_UNIQ"),
            release=attrs.get("bcdDevice") if attrs else None,
            isDevice=isDevice,
            hidpp_short=hidpp_short,
            hidpp_long=hidpp_long,
        )
        return d_info

    elif action == ACTION_REMOVE:
        d_info = DeviceInfo(
            path=device.device_node,
            bus_id=None,
            vendor_id=vid[-4:],
            product_id=pid[-4:],
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


def find_paired_node(receiver_path: str, index: int, timeout: int):
    """Find the node of a device paired with a receiver"""
    context = pyudev.Context()
    receiver_phys = pyudev.Devices.from_device_file(context, receiver_path).find_parent("hid").get("HID_PHYS")

    if not receiver_phys:
        return None

    phys = f"{receiver_phys}:{index}"  # noqa: E231
    timeout += time()
    delta = time()
    while delta < timeout:
        for dev in context.list_devices(subsystem="hidraw"):
            dev_phys = dev.find_parent("hid").get("HID_PHYS")
            if dev_phys and dev_phys == phys:
                return dev.device_node
        delta = time()

    return None


def find_paired_node_wpid(receiver_path: str, index: int):
    """Find the node of a device paired with a receiver, get wpid from udev"""
    context = pyudev.Context()
    receiver_phys = pyudev.Devices.from_device_file(context, receiver_path).find_parent("hid").get("HID_PHYS")

    if not receiver_phys:
        return None

    phys = f"{receiver_phys}:{index}"  # noqa: E231
    for dev in context.list_devices(subsystem="hidraw"):
        dev_phys = dev.find_parent("hid").get("HID_PHYS")
        if dev_phys and dev_phys == phys:
            # get hid id like 0003:0000046D:00000065
            hid_id = dev.find_parent("hid").get("HID_ID")
            # get wpid - last 4 symbols
            udev_wpid = hid_id[-4:]
            return udev_wpid

    return None


def monitor_glib(glib: GLib, callback: Callable, filter_func: Callable):
    """Monitor GLib.

    Parameters
    ----------
    glib
        GLib instance.
    """
    c = pyudev.Context()
    m = pyudev.Monitor.from_netlink(c)
    m.filter_by(subsystem="hidraw")

    def _process_udev_event(monitor, condition, cb, filter_func):
        if condition == glib.IO_IN:
            event = monitor.receive_device()
            if event:
                action, device = event
                # print ("***", action, device)
                if action == ACTION_ADD:
                    d_info = _match(action, device, filter_func)
                    if d_info:
                        glib.idle_add(cb, action, d_info)
                elif action == ACTION_REMOVE:
                    # the GLib notification does _not_ match!
                    pass
        return True

    try:
        # io_add_watch_full may not be available...
        glib.io_add_watch_full(m, glib.PRIORITY_LOW, glib.IO_IN, _process_udev_event, callback, filter_func)
    except AttributeError:
        try:
            # and the priority parameter appeared later in the API
            glib.io_add_watch(m, glib.PRIORITY_LOW, glib.IO_IN, _process_udev_event, callback, filter_func)
        except Exception:
            glib.io_add_watch(m, glib.IO_IN, _process_udev_event, callback, filter_func)

    logger.debug("Starting dbus monitoring")
    m.start()


def enumerate(filter_func: typing.Callable[[int, int, int, bool, bool], dict[str, typing.Any]]):
    """Enumerate the HID Devices.

    List all the HID devices attached to the system, optionally filtering by
    vendor_id, product_id, and/or interface_number.

    :returns: a list of matching ``DeviceInfo`` tuples.
    """

    logger.debug("Starting dbus enumeration")
    for dev in pyudev.Context().list_devices(subsystem="hidraw"):
        dev_info = _match(ACTION_ADD, dev, filter_func)
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


def open_path(device_path):
    """Open a HID device by its path name.

    :param device_path: the path of a ``DeviceInfo`` tuple returned by enumerate().

    :returns: an opaque device handle, or ``None``.
    """
    assert device_path
    assert device_path.startswith("/dev/hidraw")

    logger.info("OPEN PATH %s", device_path)
    retrycount = 0
    while retrycount < 3:
        retrycount += 1
        try:
            return os.open(device_path, os.O_RDWR | os.O_SYNC)
        except OSError as e:
            logger.info("OPEN PATH FAILED %s ERROR %s %s", device_path, e.errno, e)
            if e.errno == errno.EACCES:
                sleep(0.1)
            else:
                raise


def close(device_handle) -> None:
    """Close a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    assert device_handle
    os.close(device_handle)


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
    while retrycount < 3:
        try:
            retrycount += 1
            bytes_written = os.write(device_handle, data)
        except OSError as e:
            if e.errno == errno.EPIPE:
                sleep(0.1)
        else:
            break
    if bytes_written != len(data):
        raise OSError(errno.EIO, f"written {int(bytes_written)} bytes out of expected {len(data)}")


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
    timeout = None if timeout_ms < 0 else timeout_ms / 1000.0
    rlist, wlist, xlist = select([device_handle], [], [device_handle], timeout)

    if xlist:
        assert xlist == [device_handle]
        raise OSError(errno.EIO, f"exception on file descriptor {int(device_handle)}")

    if rlist:
        assert rlist == [device_handle]
        data = os.read(device_handle, bytes_count)
        assert data is not None
        assert isinstance(data, bytes), (repr(data), type(data))
        return data
    else:
        return b""


_DEVICE_STRINGS = {
    0: "manufacturer",
    1: "product",
    2: "serial",
}


def get_manufacturer(device_handle):
    """Get the Manufacturer String from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return get_indexed_string(device_handle, 0)


def get_product(device_handle):
    """Get the Product String from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    return get_indexed_string(device_handle, 1)


def get_serial(device_handle):
    """Get the serial number from a HID device.

    :param device_handle: a device handle returned by open() or open_path().
    """
    serial = get_indexed_string(device_handle, 2)
    return serial


def get_indexed_string(device_handle, index):
    """Get a string from a HID device, based on its string index.

    Note: currently not working in the ``hidraw`` native implementation.

    :param device_handle: a device handle returned by open() or open_path().
    :param index: the index of the string to get.
    :returns: the value corresponding to index, or None if no value found
    :rtype: bytes or NoneType
    """
    try:
        key = _DEVICE_STRINGS[index]
    except KeyError:
        return None

    assert device_handle
    stat = os.fstat(device_handle)
    try:
        dev = pyudev.Devices.from_device_number(pyudev.Context(), "char", stat.st_rdev)
    except (pyudev.DeviceNotFoundError, ValueError):
        return None

    hid_dev = dev.find_parent("hid")
    if hid_dev:
        assert "HID_ID" in hid_dev
        bus, _ignore, _ignore = hid_dev["HID_ID"].split(":")

        if bus == "0003":  # USB
            usb_dev = dev.find_parent("usb", "usb_device")
            assert usb_dev
            return usb_dev.attributes.get(key)

        elif bus == "0005":  # BLUETOOTH
            # TODO
            pass
