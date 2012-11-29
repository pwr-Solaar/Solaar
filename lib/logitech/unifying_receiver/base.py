#
# Base low-level functions used by the API proper.
# Unlikely to be used directly unless you're expanding the API.
#

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

	# apparently there are TWO product ids possible for the UR
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

	The first two (required) bytes of data must be the feature index for the
	device, and a function code for that feature.

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	# the data is padded to either 5 or 18 bytes
	if len(data) > _SHORT_MESSAGE_SIZE - 2:
		wdata = _pack('!BB18s', 0x11, devnumber, data)
	else:
		wdata = _pack('!BB5s', 0x10, devnumber, data)
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

	If any data was read in the given timeout, returns a tuple of
	(code, devnumber, message data).

	:raises NoReceiver: if the receiver is no longer available, i.e. has
	been physically removed from the machine, or the kernel driver has been
	unloaded. The handle will be closed automatically.
	"""
	reply = _read(handle, timeout)
	if reply:
		return reply[1:]


def _read(handle, timeout):
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
	"""Read anything already in the input buffer."""
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

"""The function that may be called on incoming events.

The hook must be a callable accepting one tuple parameter, with the format
``(<int> devnumber, <bytes[2]> request_id, <bytes> data)``.

This hook will only be called by the request()/ping() functions, when received
replies do not match the expected request_id. As such, it is not suitable for
intercepting broadcast events from the device (e.g. special keys being pressed,
battery charge events, etc), at least not in a timely manner.
"""
events_hook = None

def _unhandled(report_id, devnumber, data):
	"""Deliver a possible event to the unhandled_hook (if any)."""
	if events_hook:
		event = make_event(devnumber, data)
		if event:
			events_hook(event)


from collections import namedtuple
_Event = namedtuple('_Event', ['devnumber', 'sub_id', 'address', 'data'])
_Event.__str__ = lambda self: 'Event(%d,%02X,%02X,%s)' % (self.devnumber, self.sub_id, self.address, _strhex(self.data))
del namedtuple

def make_event(devnumber, data):
	sub_id = ord(data[:1])
	if devnumber == 0xFF:
		if sub_id == 0x4A:  # receiver lock event
			return _Event(devnumber, sub_id, ord(data[1:2]), data[2:])
	else:
		address = ord(data[1:2])
		if sub_id > 0x00 and sub_id < 0x80 and (address & 0x01) == 0:
			return _Event(devnumber, sub_id, address, data[2:])


def request(handle, devnumber, request_id, *params):
	"""Makes a feature call to a device and waits for a matching reply.

	This function will skip all incoming messages and events not related to the
	device we're  requesting for, or the feature specified in the initial
	request; it will also wait for a matching reply indefinitely.

	:param handle: an open UR handle.
	:param devnumber: attached device number.
	:param request_id: a 16-bit integer.
	:param params: parameters for the feature call, 3 to 16 bytes.
	:returns: the reply data, or ``None`` if some error occured.
	"""
	assert type(request_id) == int
	if devnumber != 0xFF and request_id < 0x8000:
		timeout = _DEVICE_REQUEST_TIMEOUT
		# for HID++ 2.0 feature request, randomize the swid to make it easier to
		# recognize the reply for this request. also, always set the last bit
		# (0) in swid, to make events easier to identify
		request_id = (request_id & 0xFFF0) | _random_bits(4) | 0x01
	else:
		timeout = _RECEIVER_REQUEST_TIMEOUT
	request_str = _pack('!H', request_id)

	params = b''.join(_pack('B', p) if type(p) == int else p for p in params)
	# if _log.isEnabledFor(_DEBUG):
	# 	_log.debug("(%s) device %d request_id {%04X} params [%s]", handle, devnumber, request_id, _strhex(params))

	_skip_incoming(handle)
	ihandle = int(handle)
	write(ihandle, devnumber, request_str + params)

	while True:
		now = _timestamp()
		reply = _read(handle, timeout)
		delta = _timestamp() - now

		if reply:
			report_id, reply_devnumber, reply_data = reply
			if reply_devnumber == devnumber:
				if report_id == 0x10 and reply_data[:1] == b'\x8F' and reply_data[1:3] == request_str:
					error = ord(reply_data[3:4])

					# if error == _hidpp10.ERROR.resource_error: # device unreachable
					# 	_log.warn("(%s) device %d error on request {%04X}: unknown device", handle, devnumber, request_id)
					# 	raise DeviceUnreachable(number=devnumber, request=request_id)

					# if error == _hidpp10.ERROR.unknown_device: # unknown device
					# 	_log.error("(%s) device %d error on request {%04X}: unknown device", handle, devnumber, request_id)
					# 	raise NoSuchDevice(number=devnumber, request=request_id)

					_log.debug("(%s) device %d error on request {%04X}: %d = %s",
									handle, devnumber, request_id, error, _hidpp10.ERROR[error])
					break

				if reply_data[:1] == b'\xFF' and reply_data[1:3] == request_str:
					# a HID++ 2.0 feature call returned with an error
					error = ord(reply_data[3:4])
					_log.error("(%s) device %d error on feature request {%04X}: %d = %s",
									handle, devnumber, request_id, error, _hidpp20.ERROR[error])
					raise _hidpp20.FeatureCallError(number=devnumber, request=request_id, error=error, params=params)

				if reply_data[:2] == request_str:
					if devnumber == 0xFF:
						if request_id == 0x83B5 or request_id == 0x81F1:
							# these replies have to match the first parameter as well
							if reply_data[2:3] == params[:1]:
								return reply_data[2:]
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

	_skip_incoming(handle)
	ihandle = int(handle)

	# randomize the swid and mark byte to positively identify the ping reply,
	# and set the last (0) bit in swid to make it easier to distinguish requests
	# from events
	request_id = 0x0010 | _random_bits(4) | 0x01
	request_str = _pack('!H', request_id)
	ping_mark = _pack('B', _random_bits(8))
	write(ihandle, devnumber, request_str + b'\x00\x00' + ping_mark)

	while True:
		now = _timestamp()
		reply = _read(ihandle, _PING_TIMEOUT)
		delta = _timestamp() - now

		if reply:
			report_id, number, data = reply
			if number == devnumber:
				if data[:2] == request_str and data[4:5] == ping_mark:
					# HID++ 2.0+ device, currently connected
					return ord(data[2:3]) + ord(data[3:4]) / 10.0

				if report_id == 0x10 and data[:1] == b'\x8F' and data[1:3] == request_str:
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
