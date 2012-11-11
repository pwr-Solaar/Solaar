#
# Base low-level functions used by the API proper.
# Unlikely to be used directly unless you're expanding the API.
#

import os as _os
from time import time as _timestamp
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
DEFAULT_TIMEOUT = 2000

#
#
#

def list_receiver_devices():
	"""List all the Linux devices exposed by the UR attached to the machine."""
	# (Vendor ID, Product ID) = ('Logitech', 'Unifying Receiver')
	# interface 2 if the actual receiver interface
	for d in _hid.enumerate(0x046d, 0xc52b, 2):
		if d.driver == 'logitech-djreceiver':
			yield d

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
	for rawdevice in list_receiver_devices():
		handle = open_path(rawdevice.path)
		if handle:
			return handle


def close(handle):
	"""Closes a HID device handle."""
	if handle:
		try:
			if type(handle) == int:
				_hid.close(handle)
			else:
				handle.close()
			# _log.info("closed receiver handle %s", repr(handle))
			return True
		except:
			# _log.exception("closing receiver handle %s", repr(handle))
			pass

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
	_log.debug("(%s) <= w[10 %02X %s %s]", handle, devnumber, _hex(wdata[2:4]), _hex(wdata[4:]))

	try:
		_hid.write(int(handle), wdata)
	except Exception as reason:
		_log.error("write failed, assuming handle %s no longer available", repr(handle))
		close(handle)
		raise _NoReceiver(reason)


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
	try:
		data = _hid.read(int(handle), _MAX_REPLY_SIZE, timeout)
	except Exception as reason:
		_log.error("read failed, assuming handle %s no longer available", repr(handle))
		close(handle)
		raise _NoReceiver(reason)

	if data:
		if len(data) < _MIN_REPLY_SIZE:
			_log.warn("(%s) => r[%s] read packet too short: %d bytes", handle, _hex(data), len(data))
			data += b'\x00' * (_MIN_REPLY_SIZE - len(data))
		if len(data) > _MAX_REPLY_SIZE:
			_log.warn("(%s) => r[%s] read packet too long: %d bytes", handle, _hex(data), len(data))
		code = ord(data[:1])
		devnumber = ord(data[1:2])
		_log.debug("(%s) => r[%02X %02X %s %s]", handle, code, devnumber, _hex(data[2:4]), _hex(data[4:]))
		return code, devnumber, data[2:]

	# _l.log(_LOG_LEVEL, "(-) => r[]")

def _skip_incoming(handle):
	ihandle = int(handle)

	while True:
		try:
			data = _hid.read(ihandle, _MAX_REPLY_SIZE, 0)
		except Exception as reason:
			_log.error("read failed, assuming receiver %s no longer available", handle)
			close(handle)
			raise _NoReceiver(reason)

		if data:
			if unhandled_hook:
				unhandled_hook(ord(data[:1]), ord(data[1:2]), data[2:])
		else:
			return

#
#
#

"""The function that will be called on unhandled incoming events.

The hook must be a function with the signature: ``_(int, int, str)``, where
the parameters are: (reply_code, devnumber, data).

This hook will only be called by the request() function, when it receives
replies that do not match the requested feature call. As such, it is not
suitable for intercepting broadcast events from the device (e.g. special
keys being pressed, battery charge events, etc), at least not in a timely
manner. However, these events *may* be delivered here if they happen while
doing a feature call to the device.
"""
unhandled_hook = None


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

	# _log.debug("%s device %d request {%s} params [%s]", handle, devnumber, _hex(feature_index_function), _hex(params))
	if len(feature_index_function) != 2:
		raise ValueError('invalid feature_index_function {%s}: it must be a two-byte string' % _hex(feature_index_function))

	_skip_incoming(handle)
	ihandle = int(handle)
	write(ihandle, devnumber, feature_index_function + params)

	while True:
		now = _timestamp()
		reply = read(ihandle, DEFAULT_TIMEOUT)
		delta = _timestamp() - now

		if reply:
			reply_code, reply_devnumber, reply_data = reply
			if reply_devnumber == devnumber:
				if reply_code == 0x10 and reply_data[:1] == b'\x8F' and reply_data[1:3] == feature_index_function:
					# device not present
					_log.debug("device %d request failed on {%s} call: [%s]", devnumber, _hex(feature_index_function), _hex(reply_data))
					return None

				if reply_code == 0x10 and reply_data[:1] == b'\x8F':
					# device not present
					_log.debug("device %d request failed: [%s]", devnumber, _hex(reply_data))
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

			if unhandled_hook:
				unhandled_hook(reply_code, reply_devnumber, reply_data)

		if delta >= DEFAULT_TIMEOUT:
			_log.warn("timeout on device %d request {%s} params[%s]", devnumber, _hex(feature_index_function), _hex(params))
			return None


def ping(handle, devnumber):
	"""Check if a device is connected to the UR.

	:returns: The HID protocol supported by the device, as a floating point number, if the device is active.
	"""
	_log.debug("%s pinging device %d", handle, devnumber)

	_skip_incoming(handle)
	ihandle = int(handle)
	write(ihandle, devnumber, b'\x00\x11\x00\x00\xAA')

	while True:
		now = _timestamp()
		reply = read(ihandle, DEFAULT_TIMEOUT)
		delta = _timestamp() - now

		if reply:
			reply_code, reply_devnumber, reply_data = reply
			if reply_devnumber == devnumber:
				if reply_code == 0x11 and reply_data[:2] == b'\x00\x11' and reply_data[4:5] == b'\xAA':
					# HID 2.0+ device, currently connected
					return ord(reply_data[2:3]) + ord(reply_data[3:4]) / 10.0

				if reply_code == 0x10 and reply_data == b'\x8F\x00\x11\x01\x00':
					# HID 1.0 device, currently connected
					return 1.0

				if reply_code == 0x10 and reply_data[:3] == b'\x8F\x00\x11':
					# a disconnected device
					return None

			if unhandled_hook:
				unhandled_hook(reply_code, reply_devnumber, reply_data)

		if delta >= DEFAULT_TIMEOUT:
			_log.warn("timeout on device %d ping", devnumber)
			return None
