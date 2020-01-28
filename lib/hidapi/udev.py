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

"""Generic Human Interface Device API.

It is currently a partial pure-Python implementation of the native HID API
implemented by signal11 (https://github.com/signal11/hidapi), and requires
``pyudev``.
The docstrings are mostly copied from the hidapi API header, with changes where
necessary.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import os as _os
import errno as _errno
from time import sleep
from select import select as _select
from pyudev import Context as _Context, Monitor as _Monitor, Device as _Device
from pyudev import DeviceNotFoundError


native_implementation = 'udev'


# the tuple object we'll expose when enumerating devices
from collections import namedtuple
DeviceInfo = namedtuple('DeviceInfo', [
				'path',
				'vendor_id',
				'product_id',
				'serial',
				'release',
				'manufacturer',
				'product',
				'interface',
				'driver',
				])
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


# The filter is used to determine whether this is a device of interest to Solaar
def _match(action, device, filter):
	vendor_id=filter.get('vendor_id')
	product_id=filter.get('product_id')
	interface_number=filter.get('usb_interface')
	hid_driver=filter.get('hid_driver')

	usb_device = device.find_parent('usb', 'usb_device')
	# print ("* parent", action, device, "usb:", usb_device)
	if not usb_device:
		return

	vid = usb_device.get('ID_VENDOR_ID')
	pid = usb_device.get('ID_MODEL_ID')
	if vid is None or pid is None:
		return # there are reports that sometimes the usb_device isn't set up right so be defensive
	if not ((vendor_id is None or vendor_id == int(vid, 16)) and
			(product_id is None or product_id == int(pid, 16))):
		return

	if action == 'add':
		hid_device = device.find_parent('hid')
		if not hid_device:
			return
		hid_driver_name = hid_device.get('DRIVER')
		# print ("** found hid", action, device, "hid:", hid_device, hid_driver_name)
		if hid_driver:
			if isinstance(hid_driver, tuple):
				if hid_driver_name not in hid_driver:
					return
			elif hid_driver_name != hid_driver:
				return

		intf_device = device.find_parent('usb', 'usb_interface')
		# print ("*** usb interface", action, device, "usb_interface:", intf_device)
		if interface_number is None:
			usb_interface = None if intf_device is None else intf_device.attributes.asint('bInterfaceNumber')
		else:
			usb_interface = None if intf_device is None else intf_device.attributes.asint('bInterfaceNumber')
			if usb_interface is None or interface_number != usb_interface:
				return

		attrs = usb_device.attributes
		d_info = DeviceInfo(path=device.device_node,
							vendor_id=vid[-4:],
							product_id=pid[-4:],
							serial=hid_device.get('HID_UNIQ'),
							release=attrs.get('bcdDevice'),
							manufacturer=attrs.get('manufacturer'),
							product=attrs.get('product'),
							interface=usb_interface,
							driver=hid_driver_name)
		return d_info

	elif action == 'remove':
		# print (dict(device), dict(usb_device))

		d_info = DeviceInfo(path=device.device_node,
							vendor_id=vid[-4:],
							product_id=pid[-4:],
							serial=None,
							release=None,
							manufacturer=None,
							product=None,
							interface=None,
							driver=None)
		return d_info


def monitor_glib(callback, *device_filters):
	from gi.repository import GLib

	c = _Context()

	# already existing devices
	# for device in c.list_devices(subsystem='hidraw'):
	# 	# print (device, dict(device), dict(device.attributes))
	# 	for filter in device_filters:
	# 		d_info = _match('add', device, *filter)
	# 		if d_info:
	# 			GLib.idle_add(callback, 'add', d_info)
	# 			break

	m = _Monitor.from_netlink(c)
	m.filter_by(subsystem='hidraw')

	def _process_udev_event(monitor, condition, cb, filters):
		if condition == GLib.IO_IN:
			event = monitor.receive_device()
			if event:
				action, device = event
				# print ("***", action, device)
				if action == 'add':
					for filter in filters:
						d_info = _match(action, device, filter)
						if d_info:
							GLib.idle_add(cb, action, d_info)
							break
				elif action == 'remove':
					# the GLib notification does _not_ match!
					pass
		return True

	try:
		# io_add_watch_full may not be available...
		GLib.io_add_watch_full(m, GLib.PRIORITY_LOW, GLib.IO_IN, _process_udev_event, callback, device_filters)
		# print ("did io_add_watch_full")
	except AttributeError:
		try:
			# and the priority parameter appeared later in the API
			GLib.io_add_watch(m, GLib.PRIORITY_LOW, GLib.IO_IN, _process_udev_event, callback, device_filters)
			# print ("did io_add_watch with priority")
		except:
			GLib.io_add_watch(m, GLib.IO_IN, _process_udev_event, callback, device_filters)
			# print ("did io_add_watch")

	m.start()


def enumerate(usb_id):
	"""Enumerate the HID Devices.

	List all the HID devices attached to the system, optionally filtering by
	vendor_id, product_id, and/or interface_number.

	:returns: a list of matching ``DeviceInfo`` tuples.
	"""

	for dev in _Context().list_devices(subsystem='hidraw'):
		dev_info = _match('add', dev, usb_id)
		if dev_info:
			yield dev_info


def open(vendor_id, product_id, serial=None):
	"""Open a HID device by its Vendor ID, Product ID and optional serial number.

	If no serial is provided, the first device with the specified IDs is opened.

	:returns: an opaque device handle, or ``None``.
	"""
	for device in enumerate(vendor_id, product_id):
		if serial is None or serial == device.serial:
			return open_path(device.path)


def open_path(device_path):
	"""Open a HID device by its path name.

	:param device_path: the path of a ``DeviceInfo`` tuple returned by
	enumerate().

	:returns: an opaque device handle, or ``None``.
	"""
	assert device_path
	assert device_path.startswith('/dev/hidraw')
	return _os.open(device_path, _os.O_RDWR | _os.O_SYNC)


def close(device_handle):
	"""Close a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	assert device_handle
	_os.close(device_handle)


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
	while(retrycount < 3):
		try:
			bytes_written = _os.write(device_handle, data)
			retrycount += 1
		except IOError as e:
			if e.errno == _errno.EPIPE:
				sleep(0.1)
		else:
			break
	if bytes_written != len(data):
		raise IOError(_errno.EIO, 'written %d bytes out of expected %d' % (bytes_written, len(data)))


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
	rlist, wlist, xlist = _select([device_handle], [], [device_handle], timeout)

	if xlist:
		assert xlist == [device_handle]
		raise IOError(_errno.EIO, 'exception on file descriptor %d' % device_handle)

	if rlist:
		assert rlist == [device_handle]
		data = _os.read(device_handle, bytes_count)
		assert data is not None
		assert isinstance(data, bytes), (repr(data), type(data))
		return data
	else:
		return b''


_DEVICE_STRINGS = {
			0: 'manufacturer',
			1: 'product',
			2: 'serial',
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
	if serial is not None:
		return ''.join(hex(ord(c)) for c in serial)


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
	stat = _os.fstat(device_handle)
	try:
		dev = _Device.from_device_number(_Context(), 'char', stat.st_rdev)
	except (DeviceNotFoundError, ValueError):
		return None

	hid_dev = dev.find_parent('hid')
	if hid_dev:
		assert 'HID_ID' in hid_dev
		bus, _ignore, _ignore = hid_dev['HID_ID'].split(':')

		if bus == '0003':  # USB
			usb_dev = dev.find_parent('usb', 'usb_device')
			assert usb_dev
			return usb_dev.attributes.get(key)

		elif bus == '0005':  # BLUETOOTH
			# TODO
			pass
