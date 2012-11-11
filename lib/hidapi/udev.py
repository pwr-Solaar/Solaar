"""Generic Human Interface Device API.

It is currently a partial pure-Python implementation of the native HID API
implemented by signal11 (https://github.com/signal11/hidapi), and requires
``pyudev``.
The docstrings are mostly copied from the hidapi API header, with changes where
necessary.
"""

import os as _os
import errno as _errno
from select import select as _select
from pyudev import (Context as _Context,
					Device as _Device)


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


def enumerate(vendor_id=None, product_id=None, interface_number=None):
	"""Enumerate the HID Devices.

	List all the HID devices attached to the system, optionally filtering by
	vendor_id, product_id, and/or interface_number.

	:returns: a list of matching ``DeviceInfo`` tuples.
	"""
	for dev in _Context().list_devices(subsystem='hidraw'):
		hid_dev = dev.find_parent('hid')
		if not hid_dev:
			continue

		assert 'HID_ID' in hid_dev
		bus, vid, pid = hid_dev['HID_ID'].split(':')
		if vendor_id is not None and vendor_id != int(vid, 16):
			continue
		if product_id is not None and product_id != int(pid, 16):
			continue

		if bus == '0003':  # USB
			intf_dev = dev.find_parent('usb', 'usb_interface')
			if not intf_dev:
				continue

			interface = intf_dev.attributes.asint('bInterfaceNumber')
			if interface_number is not None and interface_number != interface:
				continue

			serial = hid_dev['HID_UNIQ'] if 'HID_UNIQ' in hid_dev else None

			usb_dev = dev.find_parent('usb', 'usb_device')
			assert usb_dev
			attrs = usb_dev.attributes
			d_info = DeviceInfo(path=dev.device_node,
								vendor_id=vid[-4:],
								product_id=pid[-4:],
								serial=serial,
								release=attrs['bcdDevice'],
								manufacturer=attrs['manufacturer'],
								product=attrs['product'],
								interface=interface,
								driver=hid_dev['DRIVER'])
			yield d_info

		elif bus == '0005':  # BLUETOOTH
			# TODO
			pass


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
	assert '/dev/hidraw' in device_path
	return _os.open(device_path, _os.O_RDWR | _os.O_SYNC)


def close(device_handle):
	"""Close a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
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
	bytes_written = _os.write(device_handle, data)

	if bytes_written != len(data):
		raise OSError(errno=_errno.EIO, strerror='written %d bytes out of expected %d' % (bytes_written, len(data)))


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
	timeout = None if timeout_ms < 0 else timeout_ms / 1000.0
	rlist, wlist, xlist = _select([device_handle], [], [device_handle], timeout)

	if xlist:
		assert xlist == [device_handle]
		raise OSError(errno=_errno.EIO, strerror='exception on file descriptor %d' % device_handle)

	if rlist:
		assert rlist == [device_handle]
		data = _os.read(device_handle, bytes_count)
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
	"""
	if index not in _DEVICE_STRINGS:
		return None

	stat = _os.fstat(device_handle)
	dev = _Device.from_device_number(_Context(), 'char', stat.st_rdev)
	if dev:
		hid_dev = dev.find_parent('hid')
		if hid_dev:
			assert 'HID_ID' in hid_dev
			bus, _, _ = hid_dev['HID_ID'].split(':')

			if bus == '0003':  # USB
				usb_dev = dev.find_parent('usb', 'usb_device')
				assert usb_dev
				key = _DEVICE_STRINGS[index]
				attrs = usb_dev.attributes
				if key in attrs:
					return attrs[key]

			elif bus == '0005':  # BLUETOOTH
				# TODO
				pass
