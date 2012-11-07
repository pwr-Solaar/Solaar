#
# Base low-level functions used by the API proper.
# Unlikely to be used directly unless you're expanding the API.
#

from struct import pack as _pack
from binascii import hexlify as _hexlify
_hex = lambda d: _hexlify(d).decode('ascii').upper()

from .constants import ERROR_NAME
from .exceptions import (NoReceiver as _NoReceiver,
						FeatureCallError as _FeatureCallError)

from logging import getLogger
_log = getLogger('LUR').getChild('base')
del getLogger

import hidapi as _hid


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
DEFAULT_TIMEOUT = 1500

#
#
#

def _logdebug_hook(reply_code, devnumber, data):
	"""Default unhandled hook, logs the reply as DEBUG."""
	_log.warn("UNHANDLED [%02X %02X %s %s] (%s)", reply_code, devnumber, _hex(data[:2]), _hex(data[2:]), repr(data))


"""The function that will be called on unhandled incoming events.

The hook must be a function with the signature: ``_(int, int, str)``, where
the parameters are: (reply_code, devnumber, data).

This hook will only be called by the request() function, when it receives
replies that do not match the requested feature call. As such, it is not
suitable for intercepting broadcast events from the device (e.g. special
keys being pressed, battery charge events, etc), at least not in a timely
manner. However, these events *may* be delivered here if they happen while
doing a feature call to the device.

The default implementation logs the unhandled reply as DEBUG.
"""
unhandled_hook = _logdebug_hook

#
#
#

def list_receiver_devices():
	"""List all the Linux devices exposed by the UR attached to the machine."""
	# (Vendor ID, Product ID) = ('Logitech', 'Unifying Receiver')
	# interface 2 if the actual receiver interface
	for d in _hid.enumerate(0x046d, 0xc52b, 2):
		if d.driver is None or d.driver == 'logitech-djreceiver':
			yield d


_COUNT_DEVICES_REQUEST = b'\x10\xFF\x81\x00\x00\x00\x00'

def try_open(path):
	"""Checks if the given Linux device path points to the right UR device.

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
		_log.debug("[%s] open failed", path)
		return None

	_hid.write(receiver_handle, _COUNT_DEVICES_REQUEST)

	# if this is the right hidraw device, we'll receive a 'bad device' from the UR
	# otherwise, the read should produce nothing
	reply = _hid.read(receiver_handle, _MAX_REPLY_SIZE, DEFAULT_TIMEOUT / 2)
	if reply:
		if reply[:5] == _COUNT_DEVICES_REQUEST[:5]:
			# 'device 0 unreachable' is the expected reply from a valid receiver handle
			_log.info("[%s] success: handle %X", path, receiver_handle)
			return receiver_handle
		_log.debug("[%s] %X ignored reply %s", path, receiver_handle, _hex(reply))
	else:
		_log.debug("[%s] %X no reply", path, receiver_handle)

	close(receiver_handle)


def open():
	"""Opens the first Logitech Unifying Receiver found attached to the machine.

	:returns: An open file handle for the found receiver, or ``None``.
	"""
	for rawdevice in list_receiver_devices():
		_log.info("checking %s", rawdevice)
		handle = try_open(rawdevice.path)
		if handle:
			return handle


def close(handle):
	"""Closes a HID device handle."""
	if handle:
		try:
			_hid.close(handle)
			# _log.info("closed receiver handle %X", handle)
			return True
		except:
			_log.exception("closing receiver handle %X", handle)

	return False


def write(handle, devnumber, data):
	"""Writes some data to a certain device.

	:param handle: an open UR handle.
	:param devnumber: attached device number.
	:param data: data to send, up to 5 bytes.

	The first two (required) bytes of data must be the feature index for the
	device, and a function code for that feature.

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	assert _MIN_CALL_SIZE == 7
	assert _MAX_CALL_SIZE == 20
	# the data is padded to either 5 or 18 bytes
	wdata = _pack('!BB18s' if len(data) > 5 else '!BB5s', 0x10, devnumber, data)
	_log.debug("<= w[10 %02X %s %s]", devnumber, _hex(wdata[2:4]), _hex(wdata[4:]))
	if not _hid.write(handle, wdata):
		_log.warn("write failed, assuming receiver %X no longer available", handle)
		close(handle)
		raise _NoReceiver


def read(handle, timeout=DEFAULT_TIMEOUT):
	"""Read some data from the receiver. Usually called after a write (feature
	call), to get the reply.

	:param handle: an open UR handle.
	:param timeout: read timeout on the UR handle.

	If any data was read in the given timeout, returns a tuple of
	(reply_code, devnumber, message data). The reply code is generally ``0x11``
	for a successful feature call, or ``0x10`` to indicate some error, e.g. the
	device is no longer available.

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	data = _hid.read(handle, _MAX_REPLY_SIZE, timeout)
	if data is None:
		_log.warn("read failed, assuming receiver %X no longer available", handle)
		close(handle)
		raise _NoReceiver

	if data:
		if len(data) < _MIN_REPLY_SIZE:
			_log.warn("=> r[%s] read packet too short: %d bytes", _hex(data), len(data))
			data += b'\x00' * (_MIN_REPLY_SIZE - len(data))
		if len(data) > _MAX_REPLY_SIZE:
			_log.warn("=> r[%s] read packet too long: %d bytes", _hex(data), len(data))
		code = ord(data[:1])
		devnumber = ord(data[1:2])
		_log.debug("=> r[%02X %02X %s %s]", code, devnumber, _hex(data[2:4]), _hex(data[4:]))
		return code, devnumber, data[2:]

	# _l.log(_LOG_LEVEL, "(-) => r[]")


_MAX_READ_TIMES = 3
request_context = None
from collections import namedtuple
_DEFAULT_REQUEST_CONTEXT_CLASS = namedtuple('_DEFAULT_REQUEST_CONTEXT_CLASS', ['write', 'read', 'unhandled_hook'])
_DEFAULT_REQUEST_CONTEXT = _DEFAULT_REQUEST_CONTEXT_CLASS(write=write, read=read, unhandled_hook=unhandled_hook)
del namedtuple

def request(handle, devnumber, feature_index_function, params=b'', features=None):
	"""Makes a feature call to a device and waits for a matching reply.

	This function will skip all incoming messages and events not related to the
	device we're  requesting for, or the feature specified in the initial
	request; it will also wait for a matching reply indefinitely.

	:param handle: an open UR handle.
	:param devnumber: attached device number.
	:param feature_index_function: a two-byte string of (feature_index, feature_function).
	:param params: parameters for the feature call, 3 to 16 bytes.
	:param features: optional features array for the device, only used to fill
	the FeatureCallError exception if one occurs.
	:returns: the reply data packet, or ``None`` if the device is no longer
	available.
	:raisees FeatureCallError: if the feature call replied with an error.
	"""
	if type(params) == int:
		params = _pack('!B', params)

	# _log.debug("device %d request {%s} params [%s]", devnumber, _hex(feature_index_function), _hex(params))
	if len(feature_index_function) != 2:
		raise ValueError('invalid feature_index_function {%s}: it must be a two-byte string' % _hex(feature_index_function))

	if request_context is None or handle != request_context.handle:
		context = _DEFAULT_REQUEST_CONTEXT
		_unhandled = unhandled_hook
	else:
		context = request_context
		_unhandled = getattr(context, 'unhandled_hook')

	context.write(handle, devnumber, feature_index_function + params)

	read_times = _MAX_READ_TIMES
	while read_times > 0:
		divisor = (1 + _MAX_READ_TIMES - read_times)
		reply = context.read(handle, int(DEFAULT_TIMEOUT * (divisor + 1) / 2 / divisor))
		read_times -= 1

		if not reply:
			# keep waiting...
			continue

		reply_code, reply_devnumber, reply_data = reply

		if reply_devnumber != devnumber:
			# this message not for the device we're interested in
			# _l.log(_LOG_LEVEL, "device %d request got reply for unexpected device %d: [%s]", devnumber, reply_devnumber, _hex(reply_data))
			# worst case scenario, this is a reply for a concurrent request
			# on this receiver
			if _unhandled:
				_unhandled(reply_code, reply_devnumber, reply_data)
			continue

		if reply_code == 0x10 and reply_data[:1] == b'\x8F' and reply_data[1:3] == feature_index_function:
			# device not present
			_log.debug("device %d request ping failed on {%s} call: [%s]", devnumber, _hex(feature_index_function), _hex(reply_data))
			return None

		if reply_code == 0x10 and reply_data[:1] == b'\x8F':
			# device not present
			_log.debug("device %d request ping failed: [%s]", devnumber, _hex(reply_data))
			return None

		if reply_code == 0x11 and reply_data[0] == b'\xFF' and reply_data[1:3] == feature_index_function:
			# the feature call returned with an error
			error_code = ord(reply_data[3])
			_log.warn("device %d request feature call error %d = %s: %s", devnumber, error_code, ERROR_NAME[error_code], _hex(reply_data))
			feature_index = ord(feature_index_function[:1])
			feature_function = feature_index_function[1:2]
			feature = None if features is None else features[feature_index] if feature_index < len(features) else None
			raise _FeatureCallError(devnumber, feature, feature_index, feature_function, error_code, reply_data)

		if reply_code == 0x11 and reply_data[:2] == feature_index_function:
			# a matching reply
			# _log.debug("device %d matched reply with feature-index-function [%s]", devnumber, _hex(reply_data[2:]))
			return reply_data[2:]

		if reply_code == 0x10 and devnumber == 0xFF and reply_data[:2] == feature_index_function:
			# direct calls to the receiver (device 0xFF) may also return successfully with reply code 0x10
			# _log.debug("device %d matched reply with feature-index-function [%s]", devnumber, _hex(reply_data[2:]))
			return reply_data[2:]

		# _log.debug("device %d unmatched reply {%s} (expected {%s})", devnumber, _hex(reply_data[:2]), _hex(feature_index_function))
		if _unhandled:
			_unhandled(reply_code, reply_devnumber, reply_data)
