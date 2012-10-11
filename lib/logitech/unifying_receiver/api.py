#
# Logitech Unifying Receiver API.
#

from logging import getLogger as _Logger
from struct import pack as _pack
from struct import unpack as _unpack
from binascii import hexlify as _hexlify

from .common import FirmwareInfo
from .common import AttachedDeviceInfo
from .common import ReprogrammableKeyInfo
from . import constants as C
from . import exceptions as E
from . import base as _base


_LOG_LEVEL = 5
_l = _Logger('lur.api')

#
#
#

"""Opens the first Logitech Unifying Receiver found attached to the machine.

:returns: An open file handle for the found receiver, or ``None``.
"""
open = _base.open


"""Closes a HID device handle."""
close = _base.close


def request(handle, devnumber, feature, function=b'\x00', params=b'', features=None):
	"""Makes a feature call to the device, and returns the reply data.

	Basically a write() followed by (possibly multiple) reads, until a reply
	matching the called feature is received. In theory the UR will always reply
	to feature call; otherwise this function will wait indefinitely.

	Incoming data packets not matching the feature and function will be
	delivered to the unhandled hook (if any), and ignored.

	:param function: the function to call on that feature, may be an byte value
	or a bytes string of length 1.
	:param params: optional bytes string to send as function parameters to the
	feature; may also be an integer if the function only takes a single byte as
	parameter.

	The optional ``features`` parameter is a cached result of the
	get_device_features function for this device, necessary to find the feature
	index. If the ``features_arrary`` is not provided, one will be obtained by
	manually calling get_device_features before making the request call proper.

	:raises FeatureNotSupported: if the device does not support the feature.
	"""

	feature_index = None
	if feature == C.FEATURE.ROOT:
		feature_index = b'\x00'
	else:
		if features is None:
			features = get_device_features(handle, devnumber)
			if features is None:
				_l.log(_LOG_LEVEL, "(%d) no features array available", devnumber)
				return None
		if feature in features:
			feature_index = _pack('!B', features.index(feature))

	if feature_index is None:
		_l.warn("(%d) feature <%s:%s> not supported", devnumber, _hexlify(feature), C.FEATURE_NAME[feature])
		raise E.FeatureNotSupported(devnumber, feature)

	if type(function) == int:
		function = _pack('!B', function)
	if type(params) == int:
		params = _pack('!B', params)

	return _base.request(handle, devnumber, feature_index + function, params)


def ping(handle, devnumber):
	"""Pings a device to check if it is attached to the UR.

	:returns: True if the device is connected to the UR, False if the device is
	not attached, None if no conclusive reply is received.
	"""
	reply = _base.request(handle, devnumber, b'\x00\x10', b'\x00\x00\xAA')
	return reply is not None and reply[2:3] == b'\xAA'


def get_device_protocol(handle, devnumber):
	reply = _base.request(handle, devnumber, b'\x00\x10', b'\x00\x00\xAA')
	if reply is not None and len(reply) > 2 and reply[2:3] == b'\xAA':
		return 'HID %d.%d' % (ord(reply[0:1]), ord(reply[1:2]))


def find_device_by_name(handle, name):
	"""Searches for an attached device by name.

	:returns: an AttachedDeviceInfo tuple, or ``None``.
	"""
	_l.log(_LOG_LEVEL, "searching for device '%s'", name)

	for devnumber in range(1, 1 + C.MAX_ATTACHED_DEVICES):
		features = get_device_features(handle, devnumber)
		if features:
			d_name = get_device_name(handle, devnumber, features)
			if d_name == name:
				return get_device_info(handle, devnumber, name=d_name, features=features)


def list_devices(handle):
	"""List all devices attached to the UR.

	:returns: a list of AttachedDeviceInfo tuples.
	"""
	_l.log(_LOG_LEVEL, "listing all devices")

	devices = []

	for device in range(1, 1 + C.MAX_ATTACHED_DEVICES):
		features = get_device_features(handle, device)
		if features:
			devices.append(get_device_info(handle, device, features=features))

	return devices


def get_device_info(handle, devnumber, name=None, features=None):
	"""Gets the complete info for a device (type, name, firmware versions, features).

	:returns: an AttachedDeviceInfo tuple, or ``None``.
	"""
	if features is None:
		features = get_device_features(handle, devnumber)
		if features is None:
			return None

	d_type = get_device_type(handle, devnumber, features)
	d_name = get_device_name(handle, devnumber, features) if name is None else name
	d_firmware = get_device_firmware(handle, devnumber, features)
	devinfo = AttachedDeviceInfo(handle, devnumber, d_type, d_name, d_firmware, features)
	_l.log(_LOG_LEVEL, "(%d) found device %s", devnumber, devinfo)
	return devinfo


def get_feature_index(handle, devnumber, feature):
	"""Reads the index of a device's feature.

	:returns: An int, or ``None`` if the feature is not available.
	"""
	_l.log(_LOG_LEVEL, "(%d) get feature index <%s:%s>", devnumber, _hexlify(feature), C.FEATURE_NAME[feature])
	if len(feature) != 2:
		raise ValueError("invalid feature <%s>: it must be a two-byte string" % feature)

	# FEATURE.ROOT should always be available for any attached devices
	reply = _base.request(handle, devnumber, C.FEATURE.ROOT, feature)
	if reply:
		# only consider active and supported features
		feature_index = ord(reply[0:1])
		if feature_index:
			feature_flags = ord(reply[1:2]) & 0xE0
			if _l.isEnabledFor(_LOG_LEVEL):
				if feature_flags:
					_l.log(_LOG_LEVEL, "(%d) feature <%s:%s> has index %d: %s",
							devnumber, _hexlify(feature), C.FEATURE_NAME[feature], feature_index,
							','.join([C.FEATURE_FLAGS[k] for k in C.FEATURE_FLAGS if feature_flags & k]))
				else:
					_l.log(_LOG_LEVEL, "(%d) feature <%s:%s> has index %d", devnumber, _hexlify(feature), C.FEATURE_NAME[feature], feature_index)

			# if feature_flags:
			# 	raise E.FeatureNotSupported(devnumber, feature)

			return feature_index

		_l.warn("(%d) feature <%s:%s> not supported by the device", devnumber, _hexlify(feature), C.FEATURE_NAME[feature])
		raise E.FeatureNotSupported(devnumber, feature)


def get_device_features(handle, devnumber):
	"""Returns an array of feature ids.

	Their position in the array is the index to be used when requesting that
	feature on the device.
	"""
	_l.log(_LOG_LEVEL, "(%d) get device features", devnumber)

	# get the index of the FEATURE_SET
	# FEATURE.ROOT should always be available for all devices
	fs_index = _base.request(handle, devnumber, C.FEATURE.ROOT, C.FEATURE.FEATURE_SET)
	if fs_index is None:
		# _l.warn("(%d) FEATURE_SET not available", device)
		return None
	fs_index = fs_index[:1]

	# For debugging purposes, query all the available features on the device,
	# even if unknown.

	# get the number of active features the device has
	features_count = _base.request(handle, devnumber, fs_index + b'\x00')
	if not features_count:
		# this can happen if the device disappeard since the fs_index request
		# otherwise we should get at least a count of 1 (the FEATURE_SET we've just used above)
		_l.log(_LOG_LEVEL, "(%d) no features available?!", devnumber)
		return None

	features_count = ord(features_count[:1])
	_l.log(_LOG_LEVEL, "(%d) found %d features", devnumber, features_count)

	features = [None] * 0x20
	for index in range(1, 1 + features_count):
		# for each index, get the feature residing at that index
		feature = _base.request(handle, devnumber, fs_index + b'\x10', _pack('!B', index))
		if feature:
			feature_flags = ord(feature[2:3]) & 0xE0
			feature = feature[0:2].upper()
			features[index] = feature

			if _l.isEnabledFor(_LOG_LEVEL):
				if feature_flags:
					_l.log(_LOG_LEVEL, "(%d) feature <%s:%s> at index %d: %s",
							devnumber, _hexlify(feature), C.FEATURE_NAME[feature], index,
							','.join([C.FEATURE_FLAGS[k] for k in C.FEATURE_FLAGS if feature_flags & k]))
				else:
					_l.log(_LOG_LEVEL, "(%d) feature <%s:%s> at index %d", devnumber, _hexlify(feature), C.FEATURE_NAME[feature], index)

	features[0] = C.FEATURE.ROOT
	while features[-1] is None:
		del features[-1]
	return features


def get_device_firmware(handle, devnumber, features=None):
	"""Reads a device's firmware info.

	:returns: a list of FirmwareInfo tuples, ordered by firmware layer.
	"""
	def _makeFirmwareInfo(level, type, name=None, version=None, build=None, extras=None):
		return FirmwareInfo(level, type, name, version, build, extras)

	fw_count = request(handle, devnumber, C.FEATURE.FIRMWARE, features=features)
	if fw_count:
		fw_count = ord(fw_count[:1])

		fw = []
		for index in range(0, fw_count):
			fw_info = request(handle, devnumber, C.FEATURE.FIRMWARE, function=b'\x10', params=index, features=features)
			if fw_info:
				fw_level = ord(fw_info[:1]) & 0x0F
				if fw_level == 0 or fw_level == 1:
					fw_type = C.FIRMWARE_TYPE[fw_level]
					name, = _unpack('!3s', fw_info[1:4])
					name = name.decode('ascii')
					version = _hexlify(fw_info[4:6])
					version = '%s.%s' % (version[0:2], version[2:4])
					build, = _unpack('!H', fw_info[6:8])
					extras = fw_info[9:].rstrip(b'\x00')
					if extras:
						fw_info = _makeFirmwareInfo(level=fw_level, type=fw_type, name=name, version=version, build=build, extras=extras)
					else:
						fw_info = _makeFirmwareInfo(level=fw_level, type=fw_type, name=name, version=version, build=build)
				elif fw_level == 2:
					fw_info = _makeFirmwareInfo(level=2, type=C.FIRMWARE_TYPE[2], version=ord(fw_info[1:2]))
				else:
					fw_info = _makeFirmwareInfo(level=fw_level, type=C.FIRMWARE_TYPE[-1])

				fw.append(fw_info)
				_l.log(_LOG_LEVEL, "(%d) firmware %s", devnumber, fw_info)
		return fw


def get_device_type(handle, devnumber, features=None):
	"""Reads a device's type.

	:see DEVICE_TYPE:
	:returns: a string describing the device type, or ``None`` if the device is
	not available or does not support the ``NAME`` feature.
	"""
	d_type = request(handle, devnumber, C.FEATURE.NAME, function=b'\x20', features=features)
	if d_type:
		d_type = ord(d_type[:1])
		_l.log(_LOG_LEVEL, "(%d) device type %d = %s", devnumber, d_type, C.DEVICE_TYPE[d_type])
		return C.DEVICE_TYPE[d_type]


def get_device_name(handle, devnumber, features=None):
	"""Reads a device's name.

	:returns: a string with the device name, or ``None`` if the device is not
	available or does not support the ``NAME`` feature.
	"""
	name_length = request(handle, devnumber, C.FEATURE.NAME, features=features)
	if name_length:
		name_length = ord(name_length[:1])

		d_name = b''
		while len(d_name) < name_length:
			name_fragment = request(handle, devnumber, C.FEATURE.NAME, function=b'\x10', params=len(d_name), features=features)
			if name_fragment:
				name_fragment = name_fragment[:name_length - len(d_name)]
				d_name += name_fragment
			else:
				break

		d_name = d_name.decode('ascii')
		_l.log(_LOG_LEVEL, "(%d) device name %s", devnumber, d_name)
		return d_name


def get_device_battery_level(handle, devnumber, features=None):
	"""Reads a device's battery level.

	:raises FeatureNotSupported: if the device does not support this feature.
	"""
	battery = request(handle, devnumber, C.FEATURE.BATTERY, features=features)
	if battery:
		discharge, dischargeNext, status = _unpack('!BBB', battery[:3])
		_l.log(_LOG_LEVEL, "(%d) battery %d%% charged, next level %d%% charge, status %d = %s",
						devnumber, discharge, dischargeNext, status, C.BATTERY_STATUSE[status])
		return (discharge, dischargeNext, C.BATTERY_STATUS[status])


def get_device_keys(handle, devnumber, features=None):
	count = request(handle, devnumber, C.FEATURE.REPROGRAMMABLE_KEYS, features=features)
	if count:
		keys = []

		count = ord(count[:1])
		for index in range(0, count):
			keydata = request(handle, devnumber, C.FEATURE.REPROGRAMMABLE_KEYS, function=b'\x10', params=index, features=features)
			if keydata:
				key, key_task, flags = _unpack('!HHB', keydata[:5])
				keys.append(ReprogrammableKeyInfo(index, key, C.KEY_NAME[key], key_task, C.KEY_NAME[key_task], flags))

		return keys
