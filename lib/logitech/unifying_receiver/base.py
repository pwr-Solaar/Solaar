#
# Base low-level functions used by the API proper.
# Unlikely to be used directly unless you're expanding the API.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from time import time as _timestamp
from struct import pack as _pack
from random import getrandbits as _random_bits

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR.base')
del getLogger

from .common import strhex as _strhex, KwException as _KwException
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
import hidapi as _hid

#
#
#

_SHORT_MESSAGE_SIZE = 7
_LONG_MESSAGE_SIZE = 20
_MEDIUM_MESSAGE_SIZE = 15
_MAX_READ_SIZE = 32

"""Default timeout on read (in ms)."""
DEFAULT_TIMEOUT = 3000
_RECEIVER_REQUEST_TIMEOUT = 500
_DEVICE_REQUEST_TIMEOUT = DEFAULT_TIMEOUT
_PING_TIMEOUT = 5000

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

def receivers():
	"""List all the Linux devices exposed by the UR attached to the machine."""
	# (Vendor ID, Product ID) = ('Logitech', 'Unifying Receiver')
	# interface 2 if the actual receiver interface

	for d in _hid.enumerate(0x046d, 0xc52b, 2):
		if d.driver == 'logitech-djreceiver':
			yield d

	# apparently there are TWO product ids possible for the UR?
	for d in _hid.enumerate(0x046d, 0xc532, 2):
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
	for rawdevice in receivers():
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
	if len(data) > _SHORT_MESSAGE_SIZE - 2 or data[:1] == b'\x82':
		wdata = _pack(b'!BB18s', 0x11, devnumber, data)
	else:
		wdata = _pack(b'!BB5s', 0x10, devnumber, data)
	if _log.isEnabledFor(_DEBUG):
		_log.debug("(%s) <= w[%02X %02X %s %s]", handle, ord(wdata[:1]), devnumber, _strhex(wdata[2:4]), _strhex(wdata[4:]))

	try:
		_hid.write(int(handle), wdata)
	except Exception as reason:
		_log.error("write failed, assuming handle %s no longer available", repr(handle))
		close(handle)
		raise NoReceiver(reason=reason)


def read(handle, timeout=DEFAULT_TIMEOUT):
	"""Read some data from the receiver. Usually called after a write (feature
	call), to get the reply.

	:returns: a tuple of (devnumber, message data), or `None`

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	reply = _read(handle, timeout)
	if reply:
		return reply[1:]


def _read(handle, timeout):
	"""Read an incoming packet from the receiver.

	:returns: a tuple of (report_id, devnumber, data), or `None`.

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	try:
		data = _hid.read(int(handle), _MAX_READ_SIZE, timeout)
	except Exception as reason:
		_log.error("read failed, assuming handle %s no longer available", repr(handle))
		close(handle)
		raise NoReceiver(reason=reason)

	if data:
		report_id = ord(data[:1])
		assert (report_id == 0x10 and len(data) == _SHORT_MESSAGE_SIZE or
				report_id == 0x11 and len(data) == _LONG_MESSAGE_SIZE or
				report_id == 0x20 and len(data) == _MEDIUM_MESSAGE_SIZE)
		devnumber = ord(data[1:2])

		if _log.isEnabledFor(_DEBUG):
			_log.debug("(%s) => r[%02X %02X %s %s]", handle, report_id, devnumber, _strhex(data[2:4]), _strhex(data[4:]))

		return report_id, devnumber, data[2:]


def _skip_incoming(handle):
	"""Read anything already in the input buffer.

	Used by request() and ping() before their write.
	"""
	ihandle = int(handle)

	while True:
		try:
			data = _hid.read(ihandle, _MAX_READ_SIZE, 0)
		except Exception as reason:
			_log.error("read failed, assuming receiver %s no longer available", handle)
			close(handle)
			raise NoReceiver(reason=reason)

		if data:
			report_id = ord(data[:1])
			assert (report_id == 0x10 and len(data) == _SHORT_MESSAGE_SIZE or
					report_id == 0x11 and len(data) == _LONG_MESSAGE_SIZE or
					report_id == 0x20 and len(data) == _MEDIUM_MESSAGE_SIZE)
			_unhandled(report_id, ord(data[1:2]), data[2:])
		else:
			return

#
#
#

"""The function that may be called on incoming notifications.

The hook must be a callable accepting one tuple parameter, with the format
``(<int> devnumber, <bytes[2]> request_id, <bytes> data)``.

This hook will only be called by the request()/ping() functions, when received
replies do not match the expected request_id. As such, it is not suitable for
intercepting broadcast notifications from the device (e.g. special keys being
pressed, battery charge notifications, etc), at least not in a timely manner.
"""
notifications_hook = None

def _unhandled(report_id, devnumber, data):
	"""Deliver a possible notification to the notifications_hook (if any)."""
	if notifications_hook:
		n = make_notification(devnumber, data)
		if n:
			notifications_hook(n)

def make_notification(devnumber, data):
	"""Guess if this is a notification (and not just a request reply), and
	return a Notification tuple if it is."""
	sub_id = ord(data[:1])
	if sub_id & 0x80 != 0x80:
		# HID++ 1.0 standard notifications are 0x40 - 0x7F
		# HID++ 2.0 feature notifications have the SoftwareID 0
		address = ord(data[1:2])
		if sub_id >= 0x40 or address & 0x0F == 0x00:
			return _HIDPP_Notification(devnumber, sub_id, address, data[2:])

from collections import namedtuple
_HIDPP_Notification = namedtuple('_HIDPP_Notification', ['devnumber', 'sub_id', 'address', 'data'])
_HIDPP_Notification.__str__ = lambda self: 'Notification(%d,%02X,%02X,%s)' % (self.devnumber, self.sub_id, self.address, _strhex(self.data))
_HIDPP_Notification.__unicode__ = _HIDPP_Notification.__str__
del namedtuple


def request(handle, devnumber, request_id, *params):
	"""Makes a feature call to a device and waits for a matching reply.

	This function will wait for a matching reply indefinitely.

	:param handle: an open UR handle.
	:param devnumber: attached device number.
	:param request_id: a 16-bit integer.
	:param params: parameters for the feature call, 3 to 16 bytes.
	:returns: the reply data, or ``None`` if some error occured.
	"""
	assert isinstance(request_id, int)
	if devnumber != 0xFF and request_id < 0x8000:
		timeout = _DEVICE_REQUEST_TIMEOUT
		# for HID++ 2.0 feature requests, randomize the SoftwareId to make it
		# easier to recognize the reply for this request. also, always set the
		# most significant bit (8) in SoftwareId, to make notifications easier
		# to distinguish from request replies
		request_id = (request_id & 0xFFF0) | 0x08 | _random_bits(3)
	else:
		timeout = _RECEIVER_REQUEST_TIMEOUT

	params = b''.join(_pack(b'B', p) if isinstance(p, int) else p for p in params)
	# if _log.isEnabledFor(_DEBUG):
	# 	_log.debug("(%s) device %d request_id {%04X} params [%s]", handle, devnumber, request_id, _strhex(params))
	request_data = _pack(b'!H', request_id) + params

	_skip_incoming(handle)
	ihandle = int(handle)
	write(ihandle, devnumber, request_data)

	while True:
		now = _timestamp()
		reply = _read(handle, timeout)
		delta = _timestamp() - now

		if reply:
			report_id, reply_devnumber, reply_data = reply
			if reply_devnumber == devnumber:
				if report_id == 0x10 and reply_data[:1] == b'\x8F' and reply_data[1:3] == request_data[:2]:
					error = ord(reply_data[3:4])

					# if error == _hidpp10.ERROR.resource_error: # device unreachable
					# 	_log.warn("(%s) device %d error on request {%04X}: unknown device", handle, devnumber, request_id)
					# 	raise DeviceUnreachable(number=devnumber, request=request_id)

					# if error == _hidpp10.ERROR.unknown_device: # unknown device
					# 	_log.error("(%s) device %d error on request {%04X}: unknown device", handle, devnumber, request_id)
					# 	raise NoSuchDevice(number=devnumber, request=request_id)

					_log.debug("(%s) device 0x%02X error on request {%04X}: %d = %s",
									handle, devnumber, request_id, error, _hidpp10.ERROR[error])
					break

				if reply_data[:1] == b'\xFF' and reply_data[1:3] == request_data[:2]:
					# a HID++ 2.0 feature call returned with an error
					error = ord(reply_data[3:4])
					_log.error("(%s) device %d error on feature request {%04X}: %d = %s",
									handle, devnumber, request_id, error, _hidpp20.ERROR[error])
					raise _hidpp20.FeatureCallError(number=devnumber, request=request_id, error=error, params=params)

				if reply_data[:2] == request_data[:2]:
					if request_id & 0xFF00 == 0x8300:
						# long registry r/w should return a long reply
						assert report_id == 0x11
					elif request_id & 0xF000 == 0x8000:
						# short registry r/w should return a short reply
						assert report_id == 0x10

					if devnumber == 0xFF:
						if request_id == 0x83B5 or request_id == 0x81F1:
							# these replies have to match the first parameter as well
							if reply_data[2:3] == params[:1]:
								return reply_data[2:]
							else:
								# hm, not mathing my request, and certainly not a notification
								continue
						else:
							return reply_data[2:]
					else:
						return reply_data[2:]

			_unhandled(report_id, reply_devnumber, reply_data)

		if delta >= timeout:
			_log.warn("timeout on device %d request {%04X} params[%s]", devnumber, request_id, _strhex(params))
			break
			# raise DeviceUnreachable(number=devnumber, request=request_id)


def ping(handle, devnumber):
	"""Check if a device is connected to the UR.

	:returns: The HID protocol supported by the device, as a floating point number, if the device is active.
	"""
	if _log.isEnabledFor(_DEBUG):
		_log.debug("(%s) pinging device %d", handle, devnumber)

	# randomize the SoftwareId and mark byte to be able to identify the ping
	# reply, and set most significant (0x8) bit in SoftwareId so that the reply
	# is always distinguishable from notifications
	request_id = 0x0018 | _random_bits(3)
	request_data = _pack(b'!HBBB', request_id, 0, 0, _random_bits(8))

	_skip_incoming(handle)
	ihandle = int(handle)
	write(ihandle, devnumber, request_data)

	while True:
		now = _timestamp()
		reply = _read(ihandle, _PING_TIMEOUT)
		delta = _timestamp() - now

		if reply:
			report_id, number, data = reply
			if number == devnumber:
				if data[:2] == request_data[:2] and data[4:5] == request_data[-1:]:
					# HID++ 2.0+ device, currently connected
					return ord(data[2:3]) + ord(data[3:4]) / 10.0

				if report_id == 0x10 and data[:1] == b'\x8F' and data[1:3] == request_data[:2]:
					assert data[-1:] == b'\x00'
					error = ord(data[3:4])

					if error == _hidpp10.ERROR.invalid_SubID__command: # a valid reply from a HID++ 1.0 device
						return 1.0

					if error == _hidpp10.ERROR.resource_error: # device unreachable
						# raise DeviceUnreachable(number=devnumber, request=request_id)
						break

					if error == _hidpp10.ERROR.unknown_device: # no paired device with that number
						_log.error("(%s) device %d error on ping request: unknown device", handle, devnumber)
						raise NoSuchDevice(number=devnumber, request=request_id)

			_unhandled(report_id, number, data)

		if delta >= _PING_TIMEOUT:
			_log.warn("(%s) timeout on device %d ping", handle, devnumber)
			# raise DeviceUnreachable(number=devnumber, request=request_id)
