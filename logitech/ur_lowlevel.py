"""Low-level interface for devices connected through a Logitech Universal
Receiver (UR).

Uses the HID api exposed through hidapi.py.
Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

Strongly recommended to use these functions from a single thread; calling
multiple functions from different threads has a high chance of mixing the
replies and causing failures.

In the context of this API, 'handle' is the open handle of UR attached to
the machine, and 'device' is the number (1..6 according to the documentation)
of the device attached to the UR.

References:
http://julien.danjou.info/blog/2012/logitech-k750-linux-support
http://6xq.net/git/lars/lshidpp.git/plain/doc/
"""


#
# Logging set-up.
# Add a new logging level for tracing low-level writes and reads.
#

import logging

LOG_LEVEL = 1

def _urll_trace(self, msg, *args):
	if self.isEnabledFor(LOG_LEVEL):
		args = (None if x is None
				else x.encode('hex') if type(x) == str and any(c < '\x20' or c > '\x7E' for c in x)
				else x
				for x in args)
		self.log(LOG_LEVEL, msg, *args)

logging.addLevelName(LOG_LEVEL, 'trace1')
logging.Logger.trace1 = _urll_trace
_log = logging.getLogger('logitech.ur_lowlevel')
_log.setLevel(LOG_LEVEL)


#
#
#


"""Possible features available on a Logitech device.

A particular device might not support all these features, and may support other
unknown features as well.
"""
FEATURE = type('FEATURE', (),
				dict(
					ROOT=b'\x00\x00',
					FEATURE_SET=b'\x00\x01',
					FIRMWARE=b'\x00\x03',
					NAME=b'\x00\x05',
					BATTERY=b'\x10\x00',
					REPROGRAMMABLE_KEYS=b'\x1B\x00',
					WIRELESS_STATUS=b'\x1D\x4B',
					# UNKNOWN_1=b'\x1D\xF3',
					# UNKNOWN_2=b'\x40\xA0',
					# UNKNOWN_3=b'\x41\x00',
					SOLAR_CHARGE=b'\x43\x01',
					# UNKNOWN_4=b'\x45\x20',
				))


"""Possible types of devices connected to an UR."""
DEVICE_TYPES = ("Keyboard", "Remote Control", "NUMPAD", "Mouse",
				"Touchpad", "Trackball", "Presenter", "Receiver")


"""Default timeout on read (in ms)."""
DEFAULT_TIMEOUT = 1000


"""Minimum size of a reply data packet."""
_MIN_REPLY_SIZE = 7


"""Maximum size of a reply data packet."""
_MAX_REPLY_SIZE = 64

class NoReceiver(Exception):
	"""May be raised when trying to talk through a previously connected
	receiver that is no longer available."""
	pass


def _default_event_hook(reply_code, device, data):
	_log.trace1("EVENT_HOOK |:%d| code %d status [%s]", device, reply_code, data)


"""A function that will be called on incoming events.

It must be a function with the signature: ``_(int, int, str)``, where the
parameters are: (reply code, device number, data).
"""
event_hook = _default_event_hook


#
# Low-level functions.
#


from . import hidapi


def open():
	"""Opens the first Logitech UR found attached to the machine.

	:returns: An open file handle for the found receiver, or ``None``.
	"""
	# USB ids for (Logitech, Unifying Receiver)
	# interface 2 if the actual receiver interface
	for rawdevice in hidapi.enumerate(0x046d, 0xc52b, 2):

		_log.trace1("checking %s", rawdevice)
		receiver = hidapi.open_path(rawdevice.path)
		if not receiver:
			# could be a file permissions issue
			# in any case, unreachable
			_log.trace1("[%s] open failed", rawdevice.path)
			continue

		_log.trace1("[%s] receiver handle |%d:|", rawdevice.path, receiver)
		# ping on device id 0 (always an error)
		hidapi.write(receiver, b'\x10\x00\x00\x10\x00\x00\xAA')

		# if this is the right hidraw device, we'll receive a 'bad subdevice'
		# otherwise, the read should produce nothing
		reply = hidapi.read(receiver, _MAX_REPLY_SIZE, DEFAULT_TIMEOUT)
		if reply:
			_log.trace1("[%s] |%d:| exploratory ping reply [%s]", rawdevice.path, receiver, reply)

			if reply[:4] == b'\x10\x00\x8F\x00':
				# 'device 0 unreachable' is the expected reply from a valid receiver handle
				_log.trace1("[%s] success: found receiver with handle |%d:|", rawdevice.path, receiver)
				return receiver

			if reply == b'\x01\x00\x00\x00\x00\x00\x00\x00':
				# no idea what this is, but it comes up occasionally
				_log.trace1("[%s] |%d:| mistery reply", rawdevice.path, receiver)
			else:
				_log.trace1("[%s] |%d:| unknown reply", rawdevice.path, receiver)
		else:
			_log.trace1("[%s] |%d:| no reply", rawdevice.path, receiver)
			pass

		# ignore
		hidapi.close(receiver)

	return (None, None)


def close(handle):
	"""Closes a HID device handle."""
	if handle:
		try:
			hidapi.close(handle)
			_log.trace1("|%d:| closed", handle)
			return True
		except Exception as e:
			_log.debug("|%d:| closing: %s", handle, e)

	return False


def write(handle, device, feature_index, function=b'\x00',
			param1=b'\x00', param2=b'\x00', param3=b'\x00'):
	"""Write a feature call to the receiver.

	:param handle: UR handle obtained with open().
	:param device: attached device number
	:param feature_index: index in the
	"""
	if type(feature_index) == int:
		feature_index = chr(feature_index)
	data = b''.join((feature_index, function, param1, param2, param3))
	return _write(handle, device, data)


def _write(handle, device, data):
	"""Writes some data to a certain device.

	:returns: True if the data was successfully written.
	"""
	wdata = b''.join((b'\x10', chr(device), data, b'\x00' * (5 - len(data))))
	_log.trace1("|%d:%d| <= w[%s]", handle, device, wdata)
	# return hidapi.write(handle, wdata)
	if not hidapi.write(handle, wdata):
		_log.trace1("|%d:%d| write failed", handle, device)
		raise NoReceiver()
	return True


def read(handle, timeout=DEFAULT_TIMEOUT):
	"""Read some data from the receiver.

	If any data was read in the given timeout, returns a tuple of
	(message key, device, message data).
	"""
	data = hidapi.read(handle, _MAX_REPLY_SIZE, timeout)
	if data:
		_log.trace1("|%d:*| => r[%s]", handle, data)
		if len(data) < _MIN_REPLY_SIZE:
			_log.trace1("|%d:*| => r[%s] short read", handle, data)
		if len(data) > _MAX_REPLY_SIZE:
			_log.trace1("|%d:*| => r[%s] long read", handle, data)
		return ord(data[0]), ord(data[1]), data[2:]
	else:
		_log.trace1("|%d:*| => r[]", handle)


def _publish_event(reply_code, device, data):
	if event_hook is not None:
		event_hook.__call__(reply_code, device, data)


def request(handle, device, feature, function=b'\x00', data=b'', features_array=None):
	if features_array is None:
		features_array = get_device_features(handle, device)
		if features_array is None:
			_log.trace1("|%d:%d| no features array available", handle, device)
			return None

	if feature not in features_array:
		_log.trace1("|%d:%d| feature <%s> not supported", handle, device, feature)
		return None

	index = chr(features_array.index(feature))
	return _request(handle, device, index + function, data)


def _request(handle, device, feature_function, data=b''):
	"""Makes a feature call device and waits for a matching reply.

	Only call this in the initial set-up of the device.

	This function will skip all incoming messages and events not related to the
	device we're  requesting for, or the feature specified in the initial
	request; it will also wait for a matching reply indefinetly.

	:param feature_function: a two-byte string of (feature_index, function).
	:param data: additional data to send, up to 5 bytes.
	:returns:
	"""
	_log.trace1("|%d:%d| request feature %s data %s", handle, device, feature_function, data)
	if _write(handle, device, feature_function + data):
		while True:
			reply = read(handle)

			if not reply:
				# keep waiting...
				continue

			if reply[1] != device:
				# this message not for the device we're interested in
				_log.trace1("request reply for unexpected device %s", reply)
				_publish_event(*reply)
				continue

			if reply[0] == 0x10 and reply[2][0] == b'\x8F':
				# device not present
				return None

			if reply[0] == 0x11 and reply[2][:2] == feature_function:
				# a matching reply
				_log.trace1("|%d:%d| matched reply with data [%s]", handle, device, reply[2][2:])
				return reply[2][2:]

			_log.trace1("unmatched reply %s (%s)", reply[2][:2], feature_function)
			_publish_event(*reply)


def ping(handle, device):
	"""Pings a device to check if it is attached to the UR.

	:returns: True if the device is connected to the UR, False if the device is
	not attached, None if no conclusive reply is received.
	"""
	def _status(reply):
		if not reply:
			return None

		# ping ok
		if (reply[0] == 0x11 and reply[1] == device and
							reply[2][:2] == b'\x00\x10' and
							reply[2][4] == b'\xAA'):
			_log.trace1("|%d:%d| ping: ok %s", handle, device, reply[2])
			return True

		# ping failed
		if (reply[0] == 0x10 and reply[1] == device and
							reply[2][:2] == b'\x8F\x00'):
			_log.trace1("|%d:%d| ping: device not present", handle, device)
			return False

		# sometimes the first packet is a status packet
		if (reply[0] == 0x11 and reply[1] == device and
							reply[2][:2] == b'\x09\x00' and
							reply[2][7:11] == b'GOOD'):
			_log.trace1("|%d:%d| ping: status %s", handle, device, reply[2])
			_publish_event(*reply)
			return _status(read(handle))

		# ugh
		_log.trace1("|%d:%d| ping: unknown reply", handle, device, reply)
		_publish_event(*reply)
		return None

	_log.trace1("|%d:%d| pinging", handle, device)
	if _write(handle, device, b'\x00\x10\x00\x00\xAA'):
		return _status(read(handle, DEFAULT_TIMEOUT * 3))
	return None


def get_feature_index(handle, device, feature):
	"""Reads the index of a device's feature.

	:returns: An int, or None if the feature is not available.
	"""
	_log.trace1("|%d:%d| get feature index <%s>", handle, device, feature)
	feature_index = _request(handle, device, FEATURE.ROOT, feature)
	if feature_index:
		# only consider active and supported features
		if ord(feature_index[0]) and ord(feature_index[1]) & 0xA0 == 0:
			_log.trace1("|%d:%d| feature <%s> index %s", handle, device, feature, feature_index[0])
			return ord(feature_index[0])

		_log.trace1("|%d:%d| feature <%s> not available", handle, device, feature)


def get_device_features(handle, device):
	"""Returns an array of feature ids.

	Their position in the array is the index to be used when accessing that
	feature on the device.

	Only call this function in the initial set-up of the device, because
	other messages and events not related to querying the feature set
	will be ignored.
	"""
	_log.trace1("|%d:%d| get device features", handle, device)

	# get the index of the FEATURE_SET
	fs_index = _request(handle, device, FEATURE.ROOT, FEATURE.FEATURE_SET)
	if not fs_index:
		_log.trace1("|%d:%d| FEATURE_SET not available", handle, device)
		return None
	fs_index = fs_index[0]

	# For debugging purposes, query all the available features on the device,
	# even if unknown.

	# get the number of active features the device has
	features_count = _request(handle, device, fs_index + b'\x00')
	if not features_count:
		# theoretically this cannot happen, as we've already called FEATURE_SET
		_log.trace1("|%d:%d| no features available?!", handle, device)
		return None
	features_count = ord(features_count[0])

	# a device may have a maximum of 15 features
	features = [0] * 0x10
	_log.trace1("|%d:%d| found %d features", handle, device, features_count)

	for index in range(1, 1 + features_count):
		# for each index, get the feature residing at that index
		feature = _request(handle, device, fs_index + b'\x10', chr(index))
		if feature:
			features[index] = feature[0:2].upper()
			_log.trace1("|%d:%d| feature <%s> at index %d", handle, device, features[index], index)

	return None if all(c == 0 for c in features) else features
