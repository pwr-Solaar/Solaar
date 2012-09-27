"""Low-level interface for devices connected through a Logitech Universal
Receiver (UR).

Uses the HID api exposed through hidapi.py.
Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

Strongly recommended to use these functions from a single thread; calling
multiple functions from different threads has a high chance of mixing the
replies and causing apparent failures.

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

logging.addLevelName(LOG_LEVEL, 'TRACE1')
logging.Logger.trace1 = _urll_trace
_l = logging.getLogger('ur_lowlevel')
_l.setLevel(LOG_LEVEL)


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
FEATURE_NAMES = { FEATURE.ROOT: 'ROOT',
					FEATURE.FEATURE_SET: 'FEATURE_SET',
					FEATURE.FIRMWARE: 'FIRMWARE',
					FEATURE.NAME: 'NAME',
					FEATURE.BATTERY: 'BATTERY',
					FEATURE.REPROGRAMMABLE_KEYS: 'REPROGRAMMABLE_KEYS',
					FEATURE.WIRELESS_STATUS: 'WIRELESS_STATUS',
					FEATURE.SOLAR_CHARGE: 'SOLAR_CHARGE',
				}


"""Possible types of devices connected to an UR."""
DEVICE_TYPES = ("Keyboard", "Remote Control", "NUMPAD", "Mouse",
				"Touchpad", "Trackball", "Presenter", "Receiver")


FIRMWARE_TYPES = ("Main (HID)", "Bootloader", "Hardware", "Other")

BATTERY_STATUSES = ("Discharging (in use)", "Recharging", "Almost full", "Full",
					"Slow recharge", "Invalid battery", "Thermal error",
					"Charging error")

ERROR_CODES = ("Ok", "Unknown", "Invalid argument", "Out of range",
				"Hardware error", "Logitech internal", "Invalid feature index",
				"Invalid function", "Busy", "Usupported")

"""Default timeout on read (in ms)."""
DEFAULT_TIMEOUT = 1000


"""Minimum size of a reply data packet."""
_MIN_REPLY_SIZE = 7


"""Maximum size of a reply data packet."""
_MAX_REPLY_SIZE = 32


#
# Exceptions that may be raised by this API.
#

class NoReceiver(Exception):
	"""May be raised when trying to talk through a previously connected
	receiver that is no longer available."""
	pass

class FeatureNotSupported(Exception):
	"""Raised when trying to request a feature not supported by the device."""
	def __init__(self, device, feature):
		super(FeatureNotSupported, self).__init__(device, feature, FEATURE_NAMES[feature])
		self.device = device
		self.feature = feature
		self.feature_name = FEATURE_NAMES[feature]


#
#
#


def _default_event_hook(reply_code, device, data):
	_l.trace1("EVENT_HOOK (,%d) code %d status [%s]", device, reply_code, data)


"""A function that will be called on incoming events.

It must be a function with the signature: ``_(int, int, str)``, where the
parameters are: (reply code, device number, data).

This function will be called by the request() function, when it receives replies
that do not match the write ca
"""
event_hook = _default_event_hook

def _publish_event(reply_code, device, data):
	if event_hook is not None:
		event_hook.__call__(reply_code, device, data)


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

		_l.trace1("checking %s", rawdevice)
		receiver = hidapi.open_path(rawdevice.path)
		if not receiver:
			# could be a file permissions issue
			# in any case, unreachable
			_l.trace1("[%s] open failed", rawdevice.path)
			continue

		_l.trace1("[%s] receiver handle (%d,)", rawdevice.path, receiver)
		# ping on device id 0 (always an error)
		hidapi.write(receiver, b'\x10\x00\x00\x10\x00\x00\xAA')

		# if this is the right hidraw device, we'll receive a 'bad subdevice'
		# otherwise, the read should produce nothing
		reply = hidapi.read(receiver, _MAX_REPLY_SIZE, DEFAULT_TIMEOUT)
		if reply:
			if reply[:4] == b'\x10\x00\x8F\x00':
				# 'device 0 unreachable' is the expected reply from a valid receiver handle
				_l.trace1("[%s] success: handle (%d,)", rawdevice.path, receiver)
				return receiver

			if reply == b'\x01\x00\x00\x00\x00\x00\x00\x00':
				# no idea what this is, but it comes up occasionally
				_l.trace1("[%s] (%d,) mistery reply [%s]", rawdevice.path, receiver, reply)
			else:
				_l.trace1("[%s] (%d,) unknown reply [%s]", rawdevice.path, receiver, reply)
		else:
			_l.trace1("[%s] (%d,) no reply", rawdevice.path, receiver)

		# ignore
		close(receiver)
		# hidapi.close(receiver)

	return None


def close(handle):
	"""Closes a HID device handle."""
	if handle:
		try:
			hidapi.close(handle)
			_l.trace1("(%d,) closed", handle)
			return True
		except Exception as e:
			_l.debug("(%d,) closing: %s", handle, e)

	return False


def write(handle, device, feature_index, function=b'\x00', param1=b'\x00', param2=b'\x00', param3=b'\x00'):
	"""Write a feature call to the receiver.

	:param handle: UR handle obtained with open().
	:param device: attached device number
	:param feature_index: index in the
	"""
	if type(feature_index) == int:
		feature_index = chr(feature_index)
	data = feature_index + function + param1 + param2 + param3
	return _write(handle, device, data)


def _write(handle, device, data):
	"""Writes some data to a certain device.

	The first two (required) bytes of data must be the feature index for the
	device, and a function code for that feature.

	If the receiver is no longer available (e.g. has been physically removed
	from the machine), raises NoReceiver.
	"""
	wdata = b'\x10' + chr(device) + data + b'\x00' * (5 - len(data))
	_l.trace1("(%d,%d) <= w[%s]", handle, device, wdata)
	# return hidapi.write(handle, wdata)
	if not hidapi.write(handle, wdata):
		_l.trace1("(%d,%d) write failed, assuming receiver has been removed", handle, device)
		raise NoReceiver()


def read(handle, timeout=DEFAULT_TIMEOUT):
	"""Read some data from the receiver. Usually called after a write (feature
	call), to get the reply.

	If any data was read in the given timeout, returns a tuple of
	(reply_code, device, message data). The reply code should be ``0x11`` for a
	successful feature call, or ``0x10`` to indicate some error, e.g. the device
	is no longer available.
	"""
	data = hidapi.read(handle, _MAX_REPLY_SIZE, timeout)
	if data:
		_l.trace1("(%d,*) => r[%s]", handle, data)
		if len(data) < _MIN_REPLY_SIZE:
			_l.trace1("(%d,*) => r[%s] read short reply", handle, data)
		if len(data) > _MAX_REPLY_SIZE:
			_l.trace1("(%d,*) => r[%s] read long reply", handle, data)
		return ord(data[0]), ord(data[1]), data[2:]
	else:
		_l.trace1("(%d,*) => r[]", handle)


def request(handle, device, feature, function=b'\x00', data=b'', features_array=None):
	"""Makes a feature call to the device, and returns the reply data.

	Basically a write() followed by (possibly multiple) reads, until a reply
	matching the called feature is received. In theory the UR will always reply
	to feature call; otherwise this function will wait indefinetly.

	Incoming data packets not matching the feature and function will be
	delivered to the event_hook (if any), and then ignored.

	The optional ``features_array`` parameter is a cached result of the
	get_device_features function for this device, necessary to find the feature
	index. If the ``features_arrary`` is not provided, one will be obtained by
	calling get_device_features.

	If the feature is not supported, returns None.
	"""
	if features_array is None:
		features_array = get_device_features(handle, device)
		if features_array is None:
			_l.trace1("(%d,%d) no features array available", handle, device)
			return None

	if feature in features_array:
		feature_index = chr(features_array.index(feature))
		return _request(handle, device, feature_index + function, data)
	else:
		_l.warn("(%d,%d) feature <%s:%s> not supported", handle, device, feature.encode('hex'), FEATURE_NAMES[feature])
		raise FeatureNotSupported(device, feature)



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
	_l.trace1("(%d,%d) request feature %s data %s", handle, device, feature_function, data)
	_write(handle, device, feature_function + data)
	while True:
		reply = read(handle)

		if not reply:
			# keep waiting...
			continue

		if reply[1] != device:
			# this message not for the device we're interested in
			_l.trace1("(%d,%d) request reply for unexpected device %s", handle, device, reply)
			_publish_event(*reply)
			continue

		if reply[0] == 0x10 and reply[2][0] == b'\x8F':
			# device not present
			_l.trace1("(%d,%d) request ping failed %s", handle, device, reply)
			return None

		if reply[0] == 0x11 and reply[2][0] == b'\xFF' and reply[2][1:3] == feature_function:
			# an error returned from the device
			error = ord(reply[2][3])
			_l.trace1("(%d,%d) request feature call error %d = %s: %s", handle, device, error, ERROR_CODES[error], reply)
			return None

		if reply[0] == 0x11 and reply[2][:2] == feature_function:
			# a matching reply
			_l.trace1("(%d,%d) matched reply with data [%s]", handle, device, reply[2][2:])
			return reply[2][2:]

		_l.trace1("(%d,%d) unmatched reply %s (expected %s)", handle, device, reply[2][:2], feature_function)
		_publish_event(*reply)


def ping(handle, device):
	"""Pings a device to check if it is attached to the UR.

	:returns: True if the device is connected to the UR, False if the device is
	not attached, None if no conclusive reply is received.
	"""
	def _status(reply):
		if not reply:
			return None

		if reply[1] != device:
			# oops
			_l.trace1("(%d,%d) ping: reply for another device: %s", handle, device, reply)
			_publish_event(*reply)
			return _status(read(handle))

		if (reply[0] == 0x11 and reply[2][:2] == b'\x00\x10' and reply[2][4] == b'\xAA'):
			# ping ok
			_l.trace1("(%d,%d) ping: ok %s", handle, device, reply[2])
			return True

		if (reply[0] == 0x10 and reply[2][:2] == b'\x8F\x00'):
			# ping failed
			_l.trace1("(%d,%d) ping: device not present", handle, device)
			return False

		if (reply[0] == 0x11 and reply[2][:2] == b'\x09\x00' and reply[2][7:11] == b'GOOD'):
			# some devices may reply with a SOLAR_STATUS packet before the
			# ping_ok reply, especially right after the device connected to the
			# receiver
			_l.trace1("(%d,%d) ping: solar status %s", handle, device, reply[2])
			_publish_event(*reply)
			return _status(read(handle))

		# ugh
		_l.trace1("(%d,%d) ping: unknown reply for this device", handle, device, reply)
		_publish_event(*reply)
		return None

	_l.trace1("(%d,%d) pinging", handle, device)
	_write(handle, device, b'\x00\x10\x00\x00\xAA')
	return _status(read(handle, DEFAULT_TIMEOUT * 3))


def get_feature_index(handle, device, feature):
	"""Reads the index of a device's feature.

	:returns: An int, or ``None`` if the feature is not available.
	"""
	_l.trace1("(%d,%d) get feature index <%s>", handle, device, feature.encode('hex'))
	feature_index = _request(handle, device, FEATURE.ROOT, feature)
	if feature_index:
		# only consider active and supported features
		if ord(feature_index[0]) and ord(feature_index[1]) & 0xA0 == 0:
			_l.trace1("(%d,%d) feature <%s> index %s", handle, device, feature.encode('hex'), feature_index[0])
			return ord(feature_index[0])

		_l.warn("(%d,%d) feature <%s:%s> not supported", handle, device, feature.encode('hex'), FEATURE_NAMES[feature])
		raise FeatureNotSupported(device, feature)


def get_device_features(handle, device):
	"""Returns an array of feature ids.

	Their position in the array is the index to be used when accessing that
	feature on the device.

	Only call this function in the initial set-up of the device, because
	other messages and events not related to querying the feature set
	will be ignored.
	"""
	_l.trace1("(%d,%d) get device features", handle, device)

	# get the index of the FEATURE_SET
	fs_index = _request(handle, device, FEATURE.ROOT, FEATURE.FEATURE_SET)
	if not fs_index:
		_l.trace1("(%d,%d) FEATURE_SET not available", handle, device)
		return None
	fs_index = fs_index[0]

	# For debugging purposes, query all the available features on the device,
	# even if unknown.

	# get the number of active features the device has
	features_count = _request(handle, device, fs_index + b'\x00')
	if not features_count:
		# this can happen if the device disappeard since the fs_index call
		_l.trace1("(%d,%d) no features available?!", handle, device)
		return None
	features_count = ord(features_count[0])

	# a device may have a maximum of 15 features
	features = [None] * 0x10
	_l.trace1("(%d,%d) found %d features", handle, device, features_count)

	for index in range(1, 1 + features_count):
		# for each index, get the feature residing at that index
		feature = _request(handle, device, fs_index + b'\x10', chr(index))
		if feature:
			features[index] = feature[0:2].upper()
			_l.trace1("(%d,%d) feature <%s> at index %d", handle, device, features[index].encode('hex'), index)

	return None if all(c == None for c in features) else features


def get_device_firmware(handle, device, features_array=None):
	"""Reads a device's firmware info.

	Returns an list of tuples [ (firmware_type, firmware_version, ...), ... ],
	ordered by firmware layer.
	"""
	fw_count = request(handle, device, FEATURE.FIRMWARE, features_array=features_array)
	if fw_count:
		fw_count = ord(fw_count[0])

		fw = []
		for index in range(0, fw_count):
			fw_info = request(handle, device, FEATURE.FIRMWARE, function=b'\x10', data=chr(index), features_array=features_array)
			if fw_info:
				fw_type = ord(fw_info[0]) & 0x0F
				if fw_type == 0 or fw_type == 1:
					prefix = str(fw_info[1:4])
					version = ( str((ord(fw_info[4]) & 0xF0) >> 4) +
								str(ord(fw_info[4]) & 0x0F) +
								'.' +
								str((ord(fw_info[5]) & 0xF0) >> 4) +
								str(ord(fw_info[5]) & 0x0F))
					name = prefix + ' ' + version
					build = 256 * ord(fw_info[6]) + ord(fw_info[7])
					if build:
						name += ' b' + str(build)
					extras = fw_info[9:].rstrip('\x00')
					_l.trace1("(%d:%d) firmware %d = %s %s extras=%s", handle, device, fw_type, FIRMWARE_TYPES[fw_type], name, extras.encode('hex'))
					fw.append((fw_type, name, build, extras))
				elif fw_type == 2:
					version = ord(fw_info[1])
					_l.trace1("(%d:%d) firmware 2 = Hardware v%x", handle, device, version)
					fw.append((2, version))
				else:
					_l.trace1("(%d:%d) firmware other", handle, device)
					fw.append((fw_type, ))
		return fw


def get_device_type(handle, device, features_array=None):
	"""Reads a device's type.

	:see DEVICE_TYPES:
	:returns: a string describing the device type, or ``None`` if the device is
	not available or does not support the ``NAME`` feature.
	"""
	d_type = request(handle, device, FEATURE.NAME, function=b'\x20', features_array=features_array)
	if d_type:
		d_type = ord(d_type[0])
		_l.trace1("(%d,%d) device type %d = %s", handle, device, d_type, DEVICE_TYPES[d_type])
		return DEVICE_TYPES[d_type]


def get_device_name(handle, device, features_array=None):
	"""Reads a device's name.

	:returns: a string with the device name, or ``None`` if the device is not
	available or does not support the ``NAME`` feature.
	"""
	name_length = request(handle, device, FEATURE.NAME, features_array=features_array)
	if name_length:
		name_length = ord(name_length[0])

		d_name = ''
		while len(d_name) < name_length:
			name_index = len(d_name)
			name_fragment = request(handle, device, FEATURE.NAME, function=b'\x10', data=chr(name_index), features_array=features_array)
			name_fragment = name_fragment[:name_length - len(d_name)]
			d_name += name_fragment

		_l.trace1("(%d,%d) device name %s", handle, device, d_name)
		return d_name

def get_device_battery_level(handle, device, features_array=None):
	"""Reads a device's battery level.
	"""
	battery = request(handle, device, FEATURE.BATTERY, features_array=features_array)
	if battery:
		discharge = ord(battery[0])
		dischargeNext = ord(battery[1])
		status = ord(battery[2])
		_l.trace1("(%d:%d) battery %d%% charged, next level %d%% charge, status %d = %s", discharge, dischargeNext, status, BATTERY_STATUSES[status])
		return (discharge, dischargeNext, status)
