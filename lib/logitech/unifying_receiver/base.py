#
# Base low-level functions used by the API proper.
# Unlikely to be used directly unless you're expanding the API.
#

import logging
import struct
from binascii import hexlify

from .constants import *
from .exceptions import *

from . import unhandled as _unhandled
import hidapi as _hid


_LOG_LEVEL = 4
_l = logging.getLogger('logitech.unifying_receiver.base')

#
# These values are defined by the Logitech documentation.
# Overstepping these boundaries will only produce log warnings.
#

"""Minimim lenght of a feature call packet."""
_MIN_CALL_SIZE = 7


"""Maximum lenght of a feature call packet."""
_MAX_CALL_SIZE = 20


"""Minimum size of a feature reply packet."""
_MIN_REPLY_SIZE = _MIN_CALL_SIZE


"""Maximum size of a feature reply packet."""
_MAX_REPLY_SIZE = _MAX_CALL_SIZE


"""Default timeout on read (in ms)."""
DEFAULT_TIMEOUT = 1000


"""Maximum number of devices attached to a UR."""
MAX_ATTACHED_DEVICES = 6

#
#
#

def list_receiver_devices():
	"""List all the Linux devices exposed by the UR attached to the machine."""
	# (Vendor ID, Product ID) = ('Logitech', 'Unifying Receiver')
	# interface 2 if the actual receiver interface
	return _hid.enumerate(0x046d, 0xc52b, 2)


def try_open(path):
	"""Checks if the given device path points to the right UR device.

	:param path: the Linux device path.

	The UR physical device may expose multiple linux devices with the same
	interface, so we have to check for the right one. At this moment the only
	way to distinguish betheen them is to do a test ping on an invalid
	(attached) device number (i.e., 0), expecting a 'ping failed' reply.

	:returns: an open receiver handle if this is the right Linux device, or
	``None``.
	"""
	receiver_handle = _hid.open_path(path)
	if receiver_handle is None:
		# could be a file permissions issue (did you add the udev rules?)
		# in any case, unreachable
		_l.log(_LOG_LEVEL, "[%s] open failed", path)
		return None

	_l.log(_LOG_LEVEL, "[%s] receiver handle (%d,)", path, receiver_handle)
	# ping on device id 0 (always an error)
	_hid.write(receiver_handle, b'\x10\x00\x00\x10\x00\x00\xAA')

	# if this is the right hidraw device, we'll receive a 'bad device' from the UR
	# otherwise, the read should produce nothing
	reply = _hid.read(receiver_handle, _MAX_REPLY_SIZE, DEFAULT_TIMEOUT)
	if reply:
		if reply[:4] == b'\x10\x00\x8F\x00':
			# 'device 0 unreachable' is the expected reply from a valid receiver handle
			_l.log(_LOG_LEVEL, "[%s] success: handle (%d,)", path, receiver_handle)
			return receiver_handle

		# any other replies are ignored, and will assume this is the wrong receiver device
		if reply == b'\x01\x00\x00\x00\x00\x00\x00\x00':
			# no idea what this is, but it comes up occasionally
			_l.log(_LOG_LEVEL, "[%s] (%d,) mistery reply [%s]", path, receiver_handle, hexlify(reply))
		else:
			_l.log(_LOG_LEVEL, "[%s] (%d,) unknown reply [%s]", path, receiver_handle, hexlify(reply))
	else:
		_l.log(_LOG_LEVEL, "[%s] (%d,) no reply", path, receiver_handle)

	close(receiver_handle)
	return None


def close(handle):
	"""Closes a HID device handle."""
	if handle:
		try:
			_hid.close(handle)
			_l.log(_LOG_LEVEL, "(%d,) closed", handle)
			return True
		except:
			_l.exception("(%d,) closing", handle)

	return False


# def write(handle, device, feature_index, function=b'\x00', param1=b'\x00', param2=b'\x00', param3=b'\x00'):
# 	"""Write a feature call to the receiver.
#
# 	:param handle: UR handle obtained with open().
# 	:param device: attached device number.
# 	:param feature_index: index in the device's feature array.
# 	"""
# 	if type(feature_index) == int:
# 		feature_index = chr(feature_index)
# 	data = feature_index + function + param1 + param2 + param3
# 	return _write(handle, device, data)


def write(handle, device, data):
	"""Writes some data to a certain device.

	:param handle: an open UR handle.
	:param device: attached device number.
	:param data: data to send, up to 5 bytes.

	The first two (required) bytes of data must be the feature index for the
	device, and a function code for that feature.

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	if len(data) < _MIN_CALL_SIZE - 2:
		data += b'\x00' * (_MIN_CALL_SIZE - 2 - len(data))
	elif len(data) > _MIN_CALL_SIZE - 2:
		data += b'\x00' * (_MAX_CALL_SIZE - 2 - len(data))
	wdata = struct.pack('!BB', 0x10, device) + data
	_l.log(_LOG_LEVEL, "(%d,%d) <= w[%s]", handle, device, hexlify(wdata))
	if len(wdata) < _MIN_CALL_SIZE:
		_l.warn("(%d:%d) <= w[%s] call packet too short: %d bytes", handle, device, hexlify(wdata), len(wdata))
	if len(wdata) > _MAX_CALL_SIZE:
		_l.warn("(%d:%d) <= w[%s] call packet too long: %d bytes", handle, device, hexlify(wdata), len(wdata))
	if not _hid.write(handle, wdata):
		_l.warn("(%d,%d) write failed, assuming receiver no longer available", handle, device)
		close(handle)
		raise NoReceiver()


def read(handle, timeout=DEFAULT_TIMEOUT):
	"""Read some data from the receiver. Usually called after a write (feature
	call), to get the reply.

	:param handle: an open UR handle.
	:param timeout: read timeout on the UR handle.

	If any data was read in the given timeout, returns a tuple of
	(reply_code, device, message data). The reply code should be ``0x11`` for a
	successful feature call, or ``0x10`` to indicate some error, e.g. the device
	is no longer available.

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	data = _hid.read(handle, _MAX_REPLY_SIZE * 2, timeout)
	if data is None:
		_l.warn("(%d,*) read failed, assuming receiver no longer available", handle)
		close(handle)
		raise NoReceiver

	if data:
		_l.log(_LOG_LEVEL, "(%d,*) => r[%s]", handle, hexlify(data))
		if len(data) < _MIN_REPLY_SIZE:
			_l.warn("(%d,*) => r[%s] read packet too short: %d bytes", handle, hexlify(data), len(data))
		if len(data) > _MAX_REPLY_SIZE:
			_l.warn("(%d,*) => r[%s] read packet too long: %d bytes", handle, hexlify(data), len(data))
		code = ord(data[:1])
		device = ord(data[1:2])
		return code, device, data[2:]
	_l.log(_LOG_LEVEL, "(%d,*) => r[]", handle)


def request(handle, device, feature_index_function, params=b'', features_array=None):
	"""Makes a feature call device and waits for a matching reply.

	This function will skip all incoming messages and events not related to the
	device we're  requesting for, or the feature specified in the initial
	request; it will also wait for a matching reply indefinitely.

	:param handle: an open UR handle.
	:param device: attached device number.
	:param feature_index_function: a two-byte string of (feature_index, feature_function).
	:param params: parameters for the feature call, 3 to 16 bytes.
	:param features_array: optional features array for the device, only used to
	fill the FeatureCallError exception if one occurs.
	:returns: the reply data packet, or ``None`` if the device is no longer
	available.
	:raisees FeatureCallError: if the feature call replied with an error.
	"""
	_l.log(_LOG_LEVEL, "(%d,%d) request {%s} params [%s]", handle, device, hexlify(feature_index_function), hexlify(params))
	if len(feature_index_function) != 2:
		raise ValueError('invalid feature_index_function {%s}: it must be a two-byte string' % hexlify(feature_index_function))

	write(handle, device, feature_index_function + params)
	while True:
		reply = read(handle)

		if not reply:
			# keep waiting...
			continue

		reply_code, reply_device, reply_data = reply

		if reply_device != device:
			# this message not for the device we're interested in
			_l.log(_LOG_LEVEL, "(%d,%d) request got reply for unexpected device %d: [%s]", handle, device, reply_device, hexlify(reply_data))
			# worst case scenario, this is a reply for a concurrent request
			# on this receiver
			_unhandled._publish(reply_code, reply_device, reply_data)
			continue

		if reply_code == 0x10 and reply_data[:1] == b'\x8F' and reply_data[1:2] == feature_index_function:
			# device not present
			_l.log(_LOG_LEVEL, "(%d,%d) request ping failed on {%s} call: [%s]", handle, device, hexlify(feature_index_function), hexlify(reply_data))
			return None

		if reply_code == 0x10 and reply_data[:1] == b'\x8F':
			# device not present
			_l.log(_LOG_LEVEL, "(%d,%d) request ping failed: [%s]", handle, device, hexlify(reply_data))
			return None

		if reply_code == 0x11 and reply_data[0] == b'\xFF' and reply_data[1:3] == feature_index_function:
			# an error returned from the device
			error_code = ord(reply_data[3])
			_l.warn("(%d,%d) request feature call error %d = %s: %s", handle, device, error_code, ERROR_NAME[error_code], hexlify(reply_data))
			feature_index = ord(feature_index_function[:1])
			feature_function = feature_index_function[1:2]
			feature = None if features_array is None else features_array[feature_index]
			raise FeatureCallError(device, feature, feature_index, feature_function, error_code, reply_data)

		if reply_code == 0x11 and reply_data[:2] == feature_index_function:
			# a matching reply
			_l.log(_LOG_LEVEL, "(%d,%d) matched reply with data [%s]", handle, device, hexlify(reply_data[2:]))
			return reply_data[2:]

		_l.log(_LOG_LEVEL, "(%d,%d) unmatched reply {%s} (expected {%s})", handle, device, hexlify(reply_data[:2]), hexlify(feature_index_function))
		_unhandled._publish(reply_code, reply_device, reply_data)
