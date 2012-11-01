#
# Logitech Unifying Receiver API.
#

from struct import pack as _pack
from struct import unpack as _unpack


from . import base as _base
from .common import (FirmwareInfo as _FirmwareInfo,
					ReprogrammableKeyInfo as _ReprogrammableKeyInfo)
from .constants import (FEATURE, FEATURE_NAME, FEATURE_FLAGS,
						FIRMWARE_KIND, DEVICE_KIND,
						BATTERY_STATUS, KEY_NAME,
						MAX_ATTACHED_DEVICES)
from .exceptions import FeatureNotSupported as _FeatureNotSupported


_hex = _base._hex

from logging import getLogger
_log = getLogger('LUR').getChild('api')
del getLogger

#
#
#

class PairedDevice(object):
	def __init__(self, handle, number):
		self.handle = handle
		self.number = number

		self._name = None
		self._kind = None
		self._firmware = None
		self.features = [FEATURE.ROOT]

	@property
	def name(self):
		if self._name is None:
			self._name = get_device_name(self.handle, self.number, self.features)
		return self._name or '?'

	@property
	def kind(self):
		if self._kind is None:
			self._kind = get_device_kind(self.handle, self.number, self.features)
		return self._kind or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			self._firmware = get_device_firmware(self.handle, self.number, self.features)
		return self._firmware or ()

	def ping(self):
		reply = _base.request(self.handle, self.number, b'\x00\x10', b'\x00\x00\xAA')
		return reply is not None and reply[2:3] == b'\xAA'

	def __str__(self):
		return '<PairedDevice(%X,%d,%s)>' % (self.handle, self.number, self._name or '?')

	def __hash__(self):
		return self.number


class Receiver(object):
	name = 'Unifying Receiver'
	max_devices = MAX_ATTACHED_DEVICES

	def __init__(self, handle, path=None):
		self.handle = handle
		self.path = path

		self._serial = None
		self._firmware = None

	def close(self):
		handle = self.handle
		self.handle = 0
		return (handle and _base.close(handle))

	@property
	def serial(self):
		if self._serial is None and self.handle:
			serial = _base.request(self.handle, 0xFF, b'\x83\xB5', b'\x03')
			if serial:
				self._serial = _hex(serial[1:5])
		return self._serial

	@property
	def firmware(self):
		if self._firmware is None and self.handle:
			firmware = []

			reply = _base.request(self.handle, 0xFF, b'\x83\xB5', b'\x02')
			if reply and reply[0:1] == b'\x02':
				fw_version = _hex(reply[1:5])
				fw_version = '%s.%s.%s' % (fw_version[0:2], fw_version[2:4], fw_version[4:8])
				firmware.append(_FirmwareInfo(0, FIRMWARE_KIND[0], '', fw_version, None))

			reply = _base.request(self.handle, 0xFF, b'\x81\xF1', b'\x04')
			if reply and reply[0:1] == b'\x04':
				bl_version = _hex(reply[1:3])
				bl_version = '%s.%s' % (bl_version[0:2], bl_version[2:4])
				firmware.append(_FirmwareInfo(1, FIRMWARE_KIND[1], '', bl_version, None))

			self._firmware = tuple(firmware)

		return self._firmware

	def __iter__(self):
		if self.handle == 0:
			return

		for number in range(1, MAX_ATTACHED_DEVICES):
			dev = get_device(self.handle, number)
			if dev is not None:
				yield dev

	def __getitem__(self, key):
		if type(key) != int:
			raise TypeError('key must be an integer')
		if self.handle == 0 or key < 0 or key > MAX_ATTACHED_DEVICES:
			raise IndexError(key)
		return get_device(self.handle, key) if key > 0 else None

	def __delitem__(self, key):
		if type(key) != int:
			raise TypeError('key must be an integer')
		if self.handle == 0 or key < 0 or key > MAX_ATTACHED_DEVICES:
			raise IndexError(key)
		if key > 0:
			_log.debug("unpairing device %d", key)
			reply = _base.request(self.handle, 0xFF, b'\x80\xB2', _pack('!BB', 0x03, key))
			if reply is None or reply[1:2] == b'\x8F':
				raise IndexError(key)

	def __len__(self):
		if self.handle == 0:
			return 0
		# not really sure about this one...
		count = _base.request(self.handle, 0xFF, b'\x81\x00')
		return 0 if count is None else ord(count[1:2])

	def __contains__(self, dev):
		if self.handle == 0:
			return False
		if type(dev) == int:
			return (dev < 1 or dev > MAX_ATTACHED_DEVICES) and ping(self.handle, dev)
		return ping(self.handle, dev.number)

	def __str__(self):
		return '<Receiver(%X,%s)>' % (self.handle, self.path)

	def __hash__(self):
		return self.handle

	__bool__ = __nonzero__ = lambda self: self.handle != 0

	@classmethod
	def open(self):
		"""Opens the first Logitech Unifying Receiver found attached to the machine.

		:returns: An open file handle for the found receiver, or ``None``.
		"""
		for rawdevice in _base.list_receiver_devices():
			handle = _base.try_open(rawdevice.path)
			if handle:
				return Receiver(handle, rawdevice.path)

#
#
#

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
	if feature == FEATURE.ROOT:
		feature_index = b'\x00'
	else:
		feature_index = _get_feature_index(handle, devnumber, feature, features)
		if feature_index is None:
			# i/o read error
			return None

		feature_index = _pack('!B', feature_index)

	if type(function) == int:
		function = _pack('!B', function)
	if type(params) == int:
		params = _pack('!B', params)

	return _base.request(handle, devnumber, feature_index + function, params)


def ping(handle, devnumber):
	"""
	:returns: True if the device is connected to the UR.
	"""
	reply = _base.request(handle, devnumber, b'\x00\x10', b'\x00\x00\xAA')
	return reply is not None and reply[2:3] == b'\xAA'


def get_device(handle, devnumber, features=None):
	"""Gets the complete info for a device (type, features).

	:returns: a PairedDevice or ``None``.
	"""
	if ping(handle, devnumber):
		devinfo = PairedDevice(handle, devnumber)
		# _log.debug("found device %s", devinfo)
		return devinfo


def get_feature_index(handle, devnumber, feature):
	"""Reads the index of a device's feature.

	:returns: An int, or ``None`` if the feature is not available.
	"""
	# _log.debug("device %d get feature index <%s:%s>", devnumber, _hex(feature), FEATURE_NAME[feature])
	if len(feature) != 2:
		raise ValueError("invalid feature <%s>: it must be a two-byte string" % feature)

	# FEATURE.ROOT should always be available for any attached devices
	reply = _base.request(handle, devnumber, FEATURE.ROOT, feature)
	if reply:
		feature_index = ord(reply[0:1])
		if feature_index:
			# feature_flags = ord(reply[1:2]) & 0xE0
			# if feature_flags:
			# 	_log.debug("device %d feature <%s:%s> has index %d: %s",
			# 				devnumber, _hex(feature), FEATURE_NAME[feature], feature_index,
			# 				','.join([FEATURE_FLAGS[k] for k in FEATURE_FLAGS if feature_flags & k]))
			# else:
			# 	_log.debug("device %d feature <%s:%s> has index %d", devnumber, _hex(feature), FEATURE_NAME[feature], feature_index)

			# only consider active and supported features?
			# if feature_flags:
			# 	raise E.FeatureNotSupported(devnumber, feature)

			return feature_index

		_log.warn("device %d feature <%s:%s> not supported by the device", devnumber, _hex(feature), FEATURE_NAME[feature])
		raise _FeatureNotSupported(devnumber, feature)


def _get_feature_index(handle, devnumber, feature, features=None):
	if features is None:
		return get_feature_index(handle, devnumber, feature)

	if feature in features:
		return features.index(feature)

	index = get_feature_index(handle, devnumber, feature)
	if index is not None:
		if len(features) <= index:
			features += [None] * (index + 1 - len(features))
		features[index] = feature
		return index


def get_device_features(handle, devnumber):
	"""Returns an array of feature ids.

	Their position in the array is the index to be used when requesting that
	feature on the device.
	"""
	# _log.debug("device %d get device features", devnumber)

	# get the index of the FEATURE_SET
	# FEATURE.ROOT should always be available for all devices
	fs_index = _base.request(handle, devnumber, FEATURE.ROOT, FEATURE.FEATURE_SET)
	if fs_index is None:
		_log.warn("device %d FEATURE_SET not available", devnumber)
		return None
	fs_index = fs_index[:1]

	# For debugging purposes, query all the available features on the device,
	# even if unknown.

	# get the number of active features the device has
	features_count = _base.request(handle, devnumber, fs_index + b'\x00')
	if not features_count:
		# this can happen if the device disappeard since the fs_index request
		# otherwise we should get at least a count of 1 (the FEATURE_SET we've just used above)
		_log.debug("device %d no features available?!", devnumber)
		return None

	features_count = ord(features_count[:1])
	# _log.debug("device %d found %d features", devnumber, features_count)

	features = [None] * 0x20
	for index in range(1, 1 + features_count):
		# for each index, get the feature residing at that index
		feature = _base.request(handle, devnumber, fs_index + b'\x10', _pack('!B', index))
		if feature:
			# feature_flags = ord(feature[2:3]) & 0xE0
			feature = feature[0:2].upper()
			features[index] = feature

			# if feature_flags:
			# 	_log.debug("device %d feature <%s:%s> at index %d: %s",
			# 				devnumber, _hex(feature), FEATURE_NAME[feature], index,
			# 				','.join([FEATURE_FLAGS[k] for k in FEATURE_FLAGS if feature_flags & k]))
			# else:
			# 	_log.debug("device %d feature <%s:%s> at index %d", devnumber, _hex(feature), FEATURE_NAME[feature], index)

	features[0] = FEATURE.ROOT
	while features[-1] is None:
		del features[-1]
	return tuple(features)


def get_device_firmware(handle, devnumber, features=None):
	"""Reads a device's firmware info.

	:returns: a list of FirmwareInfo tuples, ordered by firmware layer.
	"""
	fw_fi = _get_feature_index(handle, devnumber, FEATURE.FIRMWARE, features)
	if fw_fi is None:
		return None

	fw_count = _base.request(handle, devnumber, _pack('!BB', fw_fi, 0x00))
	if fw_count:
		fw_count = ord(fw_count[:1])

		fw = []
		for index in range(0, fw_count):
			fw_info = _base.request(handle, devnumber, _pack('!BB', fw_fi, 0x10), params=index)
			if fw_info:
				level = ord(fw_info[:1]) & 0x0F
				if level == 0 or level == 1:
					kind = FIRMWARE_KIND[level]
					name, = _unpack('!3s', fw_info[1:4])
					name = name.decode('ascii')
					version = _hex(fw_info[4:6])
					version = '%s.%s' % (version[0:2], version[2:4])
					build, = _unpack('!H', fw_info[6:8])
					if build:
						version += ' b%d' % build
					extras = fw_info[9:].rstrip(b'\x00') or None
					fw_info = _FirmwareInfo(level, kind, name, version, extras)
				elif level == 2:
					fw_info = _FirmwareInfo(2, FIRMWARE_KIND[2], '', ord(fw_info[1:2]), None)
				else:
					fw_info = _FirmwareInfo(level, FIRMWARE_KIND[-1], '', '', None)

				fw.append(fw_info)
				# _log.debug("device %d firmware %s", devnumber, fw_info)
		return tuple(fw)


def get_device_kind(handle, devnumber, features=None):
	"""Reads a device's type.

	:see DEVICE_KIND:
	:returns: a string describing the device type, or ``None`` if the device is
	not available or does not support the ``NAME`` feature.
	"""
	name_fi = _get_feature_index(handle, devnumber, FEATURE.NAME, features)
	if name_fi is None:
		return None

	d_kind = _base.request(handle, devnumber, _pack('!BB', name_fi, 0x20))
	if d_kind:
		d_kind = ord(d_kind[:1])
		# _log.debug("device %d type %d = %s", devnumber, d_kind, DEVICE_KIND[d_kind])
		return DEVICE_KIND[d_kind]


def get_device_name(handle, devnumber, features=None):
	"""Reads a device's name.

	:returns: a string with the device name, or ``None`` if the device is not
	available or does not support the ``NAME`` feature.
	"""
	name_fi = _get_feature_index(handle, devnumber, FEATURE.NAME, features)
	if name_fi is None:
		return None

	name_length = _base.request(handle, devnumber, _pack('!BB', name_fi, 0x00))
	if name_length:
		name_length = ord(name_length[:1])

		d_name = b''
		while len(d_name) < name_length:
			name_fragment = _base.request(handle, devnumber, _pack('!BB', name_fi, 0x10), len(d_name))
			if name_fragment:
				name_fragment = name_fragment[:name_length - len(d_name)]
				d_name += name_fragment
			else:
				break

		d_name = d_name.decode('ascii')
		# _log.debug("device %d name %s", devnumber, d_name)
		return d_name


def get_device_battery_level(handle, devnumber, features=None):
	"""Reads a device's battery level.

	:raises FeatureNotSupported: if the device does not support this feature.
	"""
	bat_fi = _get_feature_index(handle, devnumber, FEATURE.BATTERY, features)
	if bat_fi is not None:
		battery = _base.request(handle, devnumber, _pack('!BB', bat_fi, 0))
		if battery:
			discharge, dischargeNext, status = _unpack('!BBB', battery[:3])
			_log.debug("device %d battery %d%% charged, next level %d%% charge, status %d = %s",
						devnumber, discharge, dischargeNext, status, BATTERY_STATUS[status])
			return (discharge, dischargeNext, BATTERY_STATUS[status])


def get_device_keys(handle, devnumber, features=None):
	rk_fi = _get_feature_index(handle, devnumber, FEATURE.REPROGRAMMABLE_KEYS, features)
	if rk_fi is None:
		return None

	count = _base.request(handle, devnumber, _pack('!BB', rk_fi, 0))
	if count:
		keys = []

		count = ord(count[:1])
		for index in range(0, count):
			keydata = _base.request(handle, devnumber, _pack('!BB', rk_fi, 0x10), index)
			if keydata:
				key, key_task, flags = _unpack('!HHB', keydata[:5])
				rki = _ReprogrammableKeyInfo(index, key, KEY_NAME[key], key_task, KEY_NAME[key_task], flags)
				keys.append(rki)

		return keys
