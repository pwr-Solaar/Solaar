"""Generic Human Interface Device API.

It is little more than a thin ctypes layer over a native hidapi implementation.
The docstrings are mostly copied from the hidapi API header, with changes where
necessary.

The native HID API implemenation is available at
https://github.com/signal11/hidapi.

The native implementation comes in two flavors, hidraw (``libhidapi-hidraw.so``)
and libusb (``libhidapi-libusb.so``). For this API to work, at least one of them
must be in ``LD_LIBRARY_PATH``; otherwise an ImportError will be raised.

Using the native hidraw implementation is recommended.
Currently the native libusb implementation (temporarily) detaches the device's
USB driver from the kernel, and it may cause the device to become unresponsive.
"""

#
# LEGACY, no longer supported
#

__version__ = '0.3-hidapi-0.7.0'


import ctypes as _C
from struct import pack as _pack


#
# look for a native implementation in the same directory as this file
#

# The CDLL native library object.
_native = None

for native_implementation in ('hidraw', 'libusb'):
	try:
		_native = _C.cdll.LoadLibrary('libhidapi-' + native_implementation + '.so')
		break
	except OSError:
		pass

if _native is None:
	raise ImportError('hidapi: failed to load any HID API native implementation')


#
# Structures used by this API.
#


# used by the native implementation when enumerating, no need to expose it
class _NativeDeviceInfo(_C.Structure):
	pass
_NativeDeviceInfo._fields_ = [
				('path', _C.c_char_p),
				('vendor_id', _C.c_ushort),
				('product_id', _C.c_ushort),
				('serial', _C.c_wchar_p),
				('release', _C.c_ushort),
				('manufacturer', _C.c_wchar_p),
				('product', _C.c_wchar_p),
				('usage_page', _C.c_ushort),
				('usage', _C.c_ushort),
				('interface', _C.c_int),
				('next_device', _C.POINTER(_NativeDeviceInfo))
]


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


# create a DeviceInfo tuple from a hid_device object
def _makeDeviceInfo(native_device_info):
	return DeviceInfo(
				path=native_device_info.path.decode('ascii'),
				vendor_id=hex(native_device_info.vendor_id)[2:].zfill(4),
				product_id=hex(native_device_info.product_id)[2:].zfill(4),
				serial=native_device_info.serial if native_device_info.serial else None,
				release=hex(native_device_info.release)[2:],
				manufacturer=native_device_info.manufacturer,
				product=native_device_info.product,
				interface=native_device_info.interface,
				driver=None)


#
# set-up arguments and return types for each hidapi function
#

_native.hid_init.argtypes = None
_native.hid_init.restype = _C.c_int

_native.hid_exit.argtypes = None
_native.hid_exit.restype = _C.c_int

_native.hid_enumerate.argtypes = [_C.c_ushort, _C.c_ushort]
_native.hid_enumerate.restype = _C.POINTER(_NativeDeviceInfo)

_native.hid_free_enumeration.argtypes = [_C.POINTER(_NativeDeviceInfo)]
_native.hid_free_enumeration.restype = None

_native.hid_open.argtypes = [_C.c_ushort, _C.c_ushort, _C.c_wchar_p]
_native.hid_open.restype = _C.c_void_p

_native.hid_open_path.argtypes = [_C.c_char_p]
_native.hid_open_path.restype = _C.c_void_p

_native.hid_close.argtypes = [_C.c_void_p]
_native.hid_close.restype = None

_native.hid_write.argtypes = [_C.c_void_p, _C.c_char_p, _C.c_size_t]
_native.hid_write.restype = _C.c_int

_native.hid_read.argtypes = [_C.c_void_p, _C.c_char_p, _C.c_size_t]
_native.hid_read.restype = _C.c_int

_native.hid_read_timeout.argtypes = [_C.c_void_p, _C.c_char_p, _C.c_size_t, _C.c_int]
_native.hid_read_timeout.restype = _C.c_int

_native.hid_set_nonblocking.argtypes = [_C.c_void_p, _C.c_int]
_native.hid_set_nonblocking.restype = _C.c_int

_native.hid_send_feature_report.argtypes = [_C.c_void_p, _C.c_char_p, _C.c_size_t]
_native.hid_send_feature_report.restype = _C.c_int

_native.hid_get_feature_report.argtypes = [_C.c_void_p, _C.c_char_p, _C.c_size_t]
_native.hid_get_feature_report.restype = _C.c_int

_native.hid_get_manufacturer_string.argtypes = [_C.c_void_p, _C.c_wchar_p, _C.c_size_t]
_native.hid_get_manufacturer_string.restype = _C.c_int

_native.hid_get_product_string.argtypes = [_C.c_void_p, _C.c_wchar_p, _C.c_size_t]
_native.hid_get_product_string.restype = _C.c_int

_native.hid_get_serial_number_string.argtypes = [_C.c_void_p, _C.c_wchar_p, _C.c_size_t]
_native.hid_get_serial_number_string.restype = _C.c_int

_native.hid_get_indexed_string.argtypes = [_C.c_void_p, _C.c_int, _C.c_wchar_p, _C.c_size_t]
_native.hid_get_indexed_string.restype = _C.c_int

_native.hid_error.argtypes = [_C.c_void_p]
_native.hid_error.restype = _C.c_wchar_p


#
# exposed API
# docstrings mostly copied from hidapi.h
#


def init():
	"""Initialize the HIDAPI library.

	This function initializes the HIDAPI library. Calling it is not strictly
	necessary, as it will be called automatically by enumerate() and any of the
	open_*() functions if it is needed.  This function should be called at the
	beginning of execution however, if there is a chance of HIDAPI handles
	being opened by different threads simultaneously.

	:returns: ``True`` if successful.
	"""
	return _native.hid_init() == 0


def exit():
	"""Finalize the HIDAPI library.

	This function frees all of the static data associated with HIDAPI. It should
	be called at the end of execution to avoid memory leaks.

	:returns: ``True`` if successful.
	"""
	return _native.hid_exit() == 0


def enumerate(vendor_id=None, product_id=None, interface_number=None):
	"""Enumerate the HID Devices.

	List all the HID devices attached to the system, optionally filtering by
	vendor_id, product_id, and/or interface_number.

	:returns: an iterable of matching ``DeviceInfo`` tuples.
	"""

	devices = _native.hid_enumerate(vendor_id, product_id)
	d = devices
	while d:
		if interface_number is None or interface_number == d.contents.interface:
			yield _makeDeviceInfo(d.contents)
		d = d.contents.next_device

	if devices:
		_native.hid_free_enumeration(devices)


def open(vendor_id, product_id, serial=None):
	"""Open a HID device by its Vendor ID, Product ID and optional serial number.

	If no serial is provided, the first device with the specified IDs is opened.

	:returns: an opaque device handle, or ``None``.
	"""
	return _native.hid_open(vendor_id, product_id, serial) or None


def open_path(device_path):
	"""Open a HID device by its path name.

	:param device_path: the path of a ``DeviceInfo`` tuple returned by
	enumerate().

	:returns: an opaque device handle, or ``None``.
	"""
	if type(device_path) == str:
		device_path = device_path.encode('ascii')
	return _native.hid_open_path(device_path) or None


def close(device_handle):
	"""Close a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	_native.hid_close(device_handle)


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

	:returns: ``True`` if the write was successful.
	"""
	bytes_written = _native.hid_write(device_handle, _C.c_char_p(data), len(data))
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

	:returns: the data packet read, an empty bytes string if a timeout was
	reached, or None if there was an error while reading.
	"""
	out_buffer = _C.create_string_buffer(b'\x00' * (bytes_count + 1))
	bytes_read = _native.hid_read_timeout(device_handle, out_buffer, bytes_count, timeout_ms)
	if bytes_read == -1:
		return None
	if bytes_read == 0:
		return b''
	return out_buffer[:bytes_read]


def send_feature_report(device_handle, data, report_number=None):
	"""Send a Feature report to the device.

	:param device_handle: a device handle returned by open() or open_path().
	:param data: the data bytes to send including the report number as the
	first byte.
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

	:returns: ``True`` if the report was successfully written to the device.
	"""
	if report_number is not None:
		data = _pack(b'!B', report_number) + data
	bytes_written = _native.hid_send_feature_report(device_handle, _C.c_char_p(data), len(data))
	return bytes_written > -1


def get_feature_report(device_handle, bytes_count, report_number=None):
	"""Get a feature report from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	:param bytes_count: how many bytes to read.
	:param report_number: if set, it is sent as the report number.

	:returns: the feature report data.
	"""
	out_buffer = _C.create_string_buffer('\x00' * (bytes_count + 2))
	if report_number is not None:
		out_buffer[0] = _pack(b'!B', report_number)
	bytes_read = _native.hid_get_feature_report(device_handle, out_buffer, bytes_count)
	if bytes_read > -1:
		return out_buffer[:bytes_read]


def _read_wchar(func, device_handle, index=None):
	_BUFFER_SIZE = 64
	buf = _C.create_unicode_buffer('\x00' * _BUFFER_SIZE)
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
	return _read_wchar(_native.hid_get_manufacturer_string, device_handle)


def get_product(device_handle):
	"""Get the Product String from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	return _read_wchar(_native.hid_get_product_string, device_handle)


def get_serial(device_handle):
	"""Get the serial number from a HID device.

	:param device_handle: a device handle returned by open() or open_path().
	"""
	serial = _read_wchar(_native.hid_get_serial_number_string, device_handle)
	if serial is not None:
		return ''.join(hex(ord(c)) for c in serial)


def get_indexed_string(device_handle, index):
	"""Get a string from a HID device, based on its string index.

	Note: currently not working in the ``hidraw`` native implementation.

	:param device_handle: a device handle returned by open() or open_path().
	:param index: the index of the string to get.
	"""
	return _read_wchar(_native.hid_get_indexed_string, device_handle, index)
