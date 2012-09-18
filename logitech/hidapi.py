"""Human Interface Device API.

It is little more than a thin ctypes layer over a native hidapi implementation.
The docstrings are mostly copied from the hidapi API header, with changes where
necessary.

The native HID API implemenation is available at https://github.com/signal11/hidapi.

Using the native hidraw implementation is recommended.
Currently the native libusb implementation (temporarily) detaches the device's
USB driver from the kernel, and it may cause the device to become unresponsive.
"""

__version__ = '0.2-hidapi-0.7.0'


import os.path
from collections import namedtuple

from ctypes import (
				cdll, create_string_buffer, create_unicode_buffer,
				c_int, c_ushort, c_size_t, c_char_p, c_wchar_p, c_void_p, POINTER, Structure
)


_hidapi = None
native_path = os.path.dirname(__file__)
for native_implementation in ('hidraw', 'libusb'):
	try:
		native_lib = os.path.join(native_path, 'libhidapi-' + native_implementation + '.so')
		_hidapi = cdll.LoadLibrary(native_lib)
		break
	except OSError:
		pass
del native_path, native_lib, native_implementation
if _hidapi is None:
	raise ImportError(__file__, 'failed to load any HID API native implementation')


# internally used by native hidapi, no need to expose it
class _DeviceInfo(Structure):
	pass
_DeviceInfo._fields_ = [
				('path', c_char_p),
				('vendor_id', c_ushort),
				('product_id', c_ushort),
				('serial', c_wchar_p),
				('release', c_ushort),
				('manufacturer', c_wchar_p),
				('product', c_wchar_p),
				('usage_page', c_ushort),
				('usage', c_ushort),
				('interface', c_int),
				('next', POINTER(_DeviceInfo))
]


# the tuple object we'll expose when enumerating devices
DeviceInfo = namedtuple('DeviceInfo', [
				'path',
				'vendor_id',
				'product_id',
				'serial',
				'release',
				'manufacturer',
				'product',
				'interface'])


# create a DeviceInfo tuple from a hid_device object
def _DevInfoTuple(hid_device):
	return DeviceInfo(
				path=str(hid_device.path),
				vendor_id=hex(hid_device.vendor_id)[2:],
				product_id=hex(hid_device.product_id)[2:],
				serial=str(hid_device.serial) if hid_device.serial else None,
				release=hex(hid_device.release)[2:],
				manufacturer=str(hid_device.manufacturer),
				product=str(hid_device.product),
				interface=hid_device.interface)


#
# set-up arguments and return types for each hidapi function
#

_hidapi.hid_init.argtypes = None
_hidapi.hid_init.restype = c_int

_hidapi.hid_exit.argtypes = None
_hidapi.hid_exit.restype = c_int

_hidapi.hid_enumerate.argtypes = [ c_ushort, c_ushort ]
_hidapi.hid_enumerate.restype = POINTER(_DeviceInfo)

_hidapi.hid_free_enumeration.argtypes = [ POINTER(_DeviceInfo) ]
_hidapi.hid_free_enumeration.restype = None

_hidapi.hid_open.argtypes = [ c_ushort, c_ushort, c_wchar_p ]
_hidapi.hid_open.restype = c_void_p

_hidapi.hid_open_path.argtypes = [ c_char_p ]
_hidapi.hid_open_path.restype = c_void_p  # POINTER(_hid_device)

_hidapi.hid_close.argtypes = [ c_void_p ]
_hidapi.hid_close.restype = None

_hidapi.hid_write.argtypes = [ c_void_p, c_char_p, c_size_t ]
_hidapi.hid_write.restype = c_int

# _hidapi.hid_read.argtypes = [ c_void_p, c_char_p, c_size_t ]
# _hidapi.hid_read.restype = c_int

_hidapi.hid_read_timeout.argtypes = [ c_void_p, c_char_p, c_size_t, c_int ]
_hidapi.hid_read_timeout.restype = c_int

# _hidapi.hid_set_nonblocking.argtypes = [ c_void_p, c_int ]
# _hidapi.hid_set_nonblocking.restype = c_int

_hidapi.hid_send_feature_report.argtypes = [ c_void_p, c_char_p, c_size_t ]
_hidapi.hid_send_feature_report.restype = c_int

_hidapi.hid_get_feature_report.argtypes = [ c_void_p, c_char_p, c_size_t ]
_hidapi.hid_get_feature_report.restype = c_int

_hidapi.hid_get_manufacturer_string.argtypes = [ c_void_p, c_wchar_p, c_size_t ]
_hidapi.hid_get_manufacturer_string.restype = c_int

_hidapi.hid_get_product_string.argtypes = [ c_void_p, c_wchar_p, c_size_t ]
_hidapi.hid_get_product_string.restype = c_int

_hidapi.hid_get_serial_number_string.argtypes = [ c_void_p, c_wchar_p, c_size_t ]
_hidapi.hid_get_serial_number_string.restype = c_int

# _hidapi.hid_get_indexed_string.argtypes = [ c_void_p, c_int, c_wchar_p, c_size_t ]
# _hidapi.hid_get_indexed_string.restype = c_int

# _hidapi.hid_error.argtypes = [ c_void_p ]
# _hidapi.hid_error.restype = c_wchar_p


#
# exposed API
# docstrings mostly copied from hidapi.h
#


def init():
	"""Initialize the HIDAPI library.

	This function initializes the HIDAPI library. Calling it is not
	strictly necessary, as it will be called automatically by
	hid_enumerate() and any of the hid_open_*() functions if it is
	needed.  This function should be called at the beginning of
	execution however, if there is a chance of HIDAPI handles
	being opened by different threads simultaneously.

	:returns: True if successful.
	"""
	return _hidapi.hid_init() == 0


def exit():
	"""Finalize the HIDAPI library.

	This function frees all of the static data associated with
	HIDAPI. It should be called at the end of execution to avoid
	memory leaks.

	:returns: True if successful.
	"""
	return _hidapi.hid_exit() == 0


def enumerate(vendor_id=None, product_id=None, interface_number=None):
	"""Enumerate the HID Devices.

	List all the HID devices attached to the system, optionally filtering by
	vendor_id, product_id, and/or interface_number.

	:returns: a list of matching DeviceInfo tuples.
	"""
	results = []

	devices = _hidapi.hid_enumerate(vendor_id, product_id)
	d = devices
	while d:
		if interface_number is None or interface_number == d.contents.interface:
			results.append(_DevInfoTuple(d.contents))
		d = d.contents.next

	if devices:
		_hidapi.hid_free_enumeration(devices)

	return results


def open(vendor_id, product_id, serial=None):
	"""Open a HID device using a Vendor ID, Product ID and optionally a serial number.

	If no serial_number is provided, the first device with the specified ids is opened.

	:returns: an opaque device handle, or None.
	"""
	return _hidapi.hid_open(vendor_id, product_id, serial) or None


def open_path(device_path):
	"""Open a HID device by its path name.

	:param device_path: the path of a DeviceInfo tuple returned by enumerate().

	:returns: an opaque device handle, or None.
	"""
	return _hidapi.hid_open_path(device_path) or None


def close(device_handle):
	"""Close a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	_hidapi.hid_close(device_handle)


def write(device_handle, data):
	"""Write an Output report to a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	:param data: the data bytes to send including the report number as the first byte.

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

	:returns: True if the write was successful.
	"""
	bytes_written = _hidapi.hid_write(device_handle, c_char_p(data), len(data))
	return bytes_written > -1


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

	:returns: the bytes read, or None if a timeout was reached.
	"""
	out_buffer = create_string_buffer('\x00' * (bytes_count + 1))
	bytes_read = _hidapi.hid_read_timeout(device_handle, out_buffer, bytes_count, timeout_ms)
	if bytes_read > -1:
		return out_buffer[:bytes_read]


def send_feature_report(device_handle, data, report_number=None):
	"""Send a Feature report to the device.

	:param device_handle: a device handle returned by open() or open_path().
	:param data: the data bytes to send including the report number as the first byte.
	:param report_number: if set, it is sent as the first byte with the data.

	Feature reports are sent over the Control endpoint as a
	Set_Report transfer.  The first byte of data[] must
	contain the Report ID. For devices which only support a
	single report, this must be set to 0x0. The remaining bytes
	contain the report data. Since the Report ID is mandatory,
	calls to send_feature_report() will always contain one
	more byte than the report contains. For example, if a hid
	report is 16 bytes long, 17 bytes must be passed to
	send_feature_report(): the Report ID (or 0x0, for
	devices which do not use numbered reports), followed by the
	report data (16 bytes).

	:returns: True if the report was successfully written to the device.
	"""
	if report_number is not None:
		data = chr(report_number) + data
	bytes_written = _hidapi.hid_send_feature_report(device_handle, c_char_p(data), len(data))
	return bytes_written > -1


def get_feature_report(device_handle, bytes_count, report_number=None):
	"""Get a feature report from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	:param bytes_count: how many bytes to read.
	:param report_number: if set, it is sent as the report number.

	:returns: the feature report data.
	"""
	out_buffer = create_string_buffer('\x00' * (bytes_count + 2))
	if report_number is not None:
		out_buffer[0] = chr(report_number)
	bytes_read = _hidapi.hid_get_feature_report(device_handle, out_buffer, bytes_count)
	if bytes_read > -1:
		return out_buffer[:bytes_read]


def _read_wchar(func, device_handle, index=None):
	_BUFFER_SIZE = 64
	buf = create_unicode_buffer('\x00' * _BUFFER_SIZE)
	if index is None:
		ok = func(device_handle, buf, _BUFFER_SIZE)
	else:
		ok = func(device_handle, index, buf, _BUFFER_SIZE)
	if ok == 0:
		return buf.value


def get_manufacturer(device_handle):
	"""Get the Manufacturer String from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	return _read_wchar(_hidapi.hid_get_manufacturer_string, device_handle)


def get_product(device_handle):
	"""Get the Product String from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	return _read_wchar(_hidapi.hid_get_product_string, device_handle)


def get_serial(device_handle):
	"""Get the serial number from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	serial = _read_wchar(_hidapi.hid_get_serial_number_string, device_handle)
	if serial is not None:
		return ''.join(hex(ord(c)) for c in serial)


# def get_indexed_string(device_handle, index):
#   """
#   :param device_handle: a device handle returned by open() or open_path().
#   """
#   return _read_wchar(_hidapi.hid_get_indexed_string, device_handle, index)
