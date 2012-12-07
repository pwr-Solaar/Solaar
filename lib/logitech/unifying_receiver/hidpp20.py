#
# Logitech Unifying Receiver API.
#

from __future__ import absolute_import, division, print_function, unicode_literals

from struct import pack as _pack, unpack as _unpack
from weakref import proxy as _proxy

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR').getChild('hidpp20')
del getLogger

from . import settings as _settings
from .common import (FirmwareInfo as _FirmwareInfo,
					ReprogrammableKeyInfo as _ReprogrammableKeyInfo,
					KwException as _KwException,
					NamedInts as _NamedInts)

#
#
#

"""Possible features available on a Logitech device.

A particular device might not support all these features, and may support other
unknown features as well.
"""
FEATURE = _NamedInts(
				ROOT=0x0000,
				FEATURE_SET=0x0001,
				FIRMWARE=0x0003,
				NAME=0x0005,
				BATTERY=0x1000,
				REPROGRAMMABLE_KEYS=0x1B00,
				WIRELESS=0x1D4B,
				FN_STATUS=0x40A0,
				SOLAR_CHARGE=0x4301,
				TOUCH_MOUSE=0x6110)
FEATURE._fallback = lambda x: 'unknown:%04X' % x

FEATURE_FLAG = _NamedInts(
				internal=0x20,
				hidden=0x40,
				obsolete=0x80)

DEVICE_KIND = _NamedInts(
				keyboard=0x00,
				remote_control=0x01,
				numpad=0x02,
				mouse=0x03,
				touchpad=0x04,
				trackball=0x05,
				presenter=0x06,
				receiver=0x07)

FIRMWARE_KIND = _NamedInts(
				Firmware=0x00,
				Bootloader=0x01,
				Hardware=0x02,
				Other=0x03)

BATTERY_OK = lambda status: status < 5

BATTERY_STATUS = _NamedInts(
				discharging=0x00,
				recharging=0x01,
				almost_full=0x02,
				full=0x03,
				slow_recharge=0x04,
				invalid_battery=0x05,
				thermal_error=0x06)

KEY = _NamedInts(
				Volume_Up=0x0001,
				Volume_Down=0x0002,
				Mute=0x0003,
				Play__Pause=0x0004,
				Next=0x0005,
				Previous=0x0006,
				Stop=0x0007,
				Application_Switcher=0x0008,
				Calculator=0x000A,
				Mail=0x000E,
				Home=0x001A,
				Music=0x001D,
				Search=0x0029,
				Sleep=0x002F)
KEY._fallback = lambda x: 'unknown:%04X' % x

KEY_FLAG = _NamedInts(
				reprogrammable=0x10,
				FN_sensitive=0x08,
				nonstandard=0x04,
				is_FN=0x02,
				mse=0x01)

ERROR = _NamedInts(
				unknown=0x01,
				invalid_argument=0x02,
				out_of_range=0x03,
				hardware_error=0x04,
				logitech_internal=0x05,
				invalid_feature_index=0x06,
				invalid_function=0x07,
				busy=0x08,
				unsupported=0x09)

#
#
#

class FeatureNotSupported(_KwException):
	"""Raised when trying to request a feature not supported by the device."""
	pass

class FeatureCallError(_KwException):
	"""Raised if the device replied to a feature call with an error."""
	pass

#
#
#

class FeaturesArray(object):
	"""A sequence of features supported by a HID++ 2.0 device."""
	__slots__ = ('supported', 'device', 'features')

	def __init__(self, device):
		assert device is not None
		self.device = _proxy(device)
		self.supported = True
		self.features = None

	def __del__(self):
		self.supported = False

	def _check(self):
		# print ("%s check" % self.device)
		if self.supported:
			assert self.device
			if self.features is not None:
				return True

			protocol = self.device.protocol
			if protocol == 0:
				# device is not connected right now, will have to try later
				return False

			# I _think_ this is universally true
			if protocol < 2.0:
				self.supported = False
				# self.device.features = None
				self.device = None
				return False

			reply = self.device.request(int(FEATURE.ROOT), _pack(b'!H', FEATURE.FEATURE_SET))
			if reply is None:
				self.supported = False
			else:
				fs_index = ord(reply[0:1])
				if fs_index:
					count = self.device.request(fs_index << 8)
					if count is None:
						_log.warn("FEATURE_SET found, but failed to read features count")
						# most likely the device is unavailable
						return False
					else:
						count = ord(count[:1])
						assert count >= fs_index
						self.features = [None] * (1 + count)
						self.features[0] = FEATURE.ROOT
						self.features[fs_index] = FEATURE.FEATURE_SET
						return True
				else:
					self.supported = False

		return False

	__bool__ = __nonzero__ = _check

	def __getitem__(self, index):
		if self._check():
			assert type(index) == int
			if index < 0 or index >= len(self.features):
				raise IndexError(index)

			if self.features[index] is None:
				feature = self.device.feature_request(FEATURE.FEATURE_SET, 0x10, index)
				if feature:
					feature, = _unpack(b'!H', feature[:2])
					self.features[index] = FEATURE[feature]

			return self.features[index]

	def __contains__(self, value):
		if self._check():
			may_have = False
			for f in self.features:
				if f is None:
					may_have = True
				elif int(value) == int(f):
					return True
				elif int(value) < int(f):
					break

			if may_have:
				reply = self.device.request(int(FEATURE.ROOT), _pack(b'!H', value))
				if reply:
					index = ord(reply[0:1])
					if index:
						self.features[index] = FEATURE[int(value)]
						return True

	def index(self, value):
		if self._check():
			may_have = False
			for index, f in enumerate(self.features):
				if f is None:
					may_have = True
				elif int(value) == int(f):
					return index
				elif int(value) < int(f):
					raise ValueError("%s not in list" % repr(value))

			if may_have:
				reply = self.device.request(int(FEATURE.ROOT), _pack(b'!H', value))
				if reply:
					index = ord(reply[0:1])
					self.features[index] = FEATURE[int(value)]
					return index

		raise ValueError("%s not in list" % repr(value))

	def __iter__(self):
		if self._check():
			yield FEATURE.ROOT
			index = 1
			last_index = len(self.features)
			while index < last_index:
				yield self.__getitem__(index)
				index += 1

	def __len__(self):
		return len(self.features) if self._check() else 0

#
#
#

class KeysArray(object):
	"""A sequence of key mappings supported by a HID++ 2.0 device."""
	__slots__ = ('device', 'keys')

	def __init__(self, device, count):
		assert device is not None
		self.device = _proxy(device)
		self.keys = [None] * count

	def __getitem__(self, index):
		assert type(index) == int
		if index < 0 or index >= len(self.keys):
			raise IndexError(index)

		if self.keys[index] is None:
			keydata = feature_request(self.device, FEATURE.REPROGRAMMABLE_KEYS, 0x10, index)
			if keydata:
				key, key_task, flags = _unpack(b'!HHB', keydata[:5])
				self.keys[index] = _ReprogrammableKeyInfo(index, KEY[key], KEY[key_task], flags)

		return self.keys[index]

	def index(self, value):
		for index, k in enumerate(self.keys):
			if k is not None and int(value) == int(k.key):
				return index

		for index, k in enumerate(self.keys):
			if k is None:
				k = self.__getitem__(index)
				if k is not None:
					return index

	def __iter__(self):
		for k in range(0, len(self.keys)):
			yield self.__getitem__(k)

	def __len__(self):
		return len(self.keys)


#
#
#

class ToggleFN_Setting(_settings.Setting):
	def __init__(self):
		super(ToggleFN_Setting, self).__init__('fn-swap', _settings.KIND.toggle, 'Swap Fx function',
					'When set, the F1..F12 keys will activate their special function,\n'
					'and you must hold the FN key to activate their standard function.\n'
					'\n'
					'When unset, the F1..F12 keys will activate their standard function,\n'
					'and you must hold the FN key to activate their special function.')

	def read(self):
		if self._value is None and self._device:
			fn = self._device.feature_request(FEATURE.FN_STATUS)
			if fn:
				self._value = (fn[:1] == b'\x01')
		return self._value

	def write(self, value):
		if self._device:
			reply = self._device.feature_request(FEATURE.FN_STATUS, 0x10, 0x01 if value else 0x00)
			self._value = (reply[:1] == b'\x01') if reply else None
			return self._value

#
#
#

def feature_request(device, feature, function=0x00, *params):
	if device.features:
		if feature in device.features:
			feature_index = device.features.index(int(feature))
			return device.request((feature_index << 8) + (function & 0xFF), *params)


def get_firmware(device):
	"""Reads a device's firmware info.

	:returns: a list of FirmwareInfo tuples, ordered by firmware layer.
	"""
	count = feature_request(device, FEATURE.FIRMWARE)
	if count:
		count = ord(count[:1])

		fw = []
		for index in range(0, count):
			fw_info = feature_request(device, FEATURE.FIRMWARE, 0x10, index)
			if fw_info:
				level = ord(fw_info[:1]) & 0x0F
				if level == 0 or level == 1:
					name, version_major, version_minor, build = _unpack(b'!3sBBH', fw_info[1:8])
					version = '%02X.%02X' % (version_major, version_minor)
					if build:
						version += '.B%04X' % build
					extras = fw_info[9:].rstrip(b'\x00') or None
					fw_info = _FirmwareInfo(FIRMWARE_KIND[level], name.decode('ascii'), version, extras)
				elif level == FIRMWARE_KIND.Hardware:
					fw_info = _FirmwareInfo(FIRMWARE_KIND.Hardware, '', ord(fw_info[1:2]), None)
				else:
					fw_info = _FirmwareInfo(FIRMWARE_KIND.Other, '', '', None)

				fw.append(fw_info)
				# _log.debug("device %d firmware %s", devnumber, fw_info)
		return tuple(fw)


def get_kind(device):
	"""Reads a device's type.

	:see DEVICE_KIND:
	:returns: a string describing the device type, or ``None`` if the device is
	not available or does not support the ``NAME`` feature.
	"""
	kind = feature_request(device, FEATURE.NAME, 0x20)
	if kind:
		kind = ord(kind[:1])
		# _log.debug("device %d type %d = %s", devnumber, kind, DEVICE_KIND[kind])
		return DEVICE_KIND[kind]


def get_name(device):
	"""Reads a device's name.

	:returns: a string with the device name, or ``None`` if the device is not
	available or does not support the ``NAME`` feature.
	"""
	name_length = feature_request(device, FEATURE.NAME)
	if name_length:
		name_length = ord(name_length[:1])

		name = b''
		while len(name) < name_length:
			fragment = feature_request(device, FEATURE.NAME, 0x10, len(name))
			if fragment:
				name += fragment[:name_length - len(name)]
			else:
				_log.error("failed to read whole name of %s (expected %d chars)", device, name_length)
				return None

		return name.decode('ascii')


def get_battery(device):
	"""Reads a device's battery level.

	:raises FeatureNotSupported: if the device does not support this feature.
	"""
	battery = feature_request(device, FEATURE.BATTERY)
	if battery:
		discharge, dischargeNext, status = _unpack(b'!BBB', battery[:3])
		if _log.isEnabledFor(_DEBUG):
			_log.debug("device %d battery %d%% charged, next level %d%% charge, status %d = %s",
						device.number, discharge, dischargeNext, status, BATTERY_STATUS[status])
		return discharge, BATTERY_STATUS[status]


def get_keys(device):
	count = feature_request(device, FEATURE.REPROGRAMMABLE_KEYS)
	if count:
		return KeysArray(device, ord(count[:1]))
