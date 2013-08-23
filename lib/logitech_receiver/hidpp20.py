# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Logitech Unifying Receiver API.

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger


from .common import (FirmwareInfo as _FirmwareInfo,
					ReprogrammableKeyInfo as _ReprogrammableKeyInfo,
					KwException as _KwException,
					NamedInts as _NamedInts,
					pack as _pack,
					unpack as _unpack)
from . import special_keys

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
	FEATURE_INFO=0x0002,
	DEVICE_FW_VERSION=0x0003,
	DEVICE_NAME=0x0005,
	DEVICE_GROUPS=0x0006,
	DFUCONTROL=0x00C0,
	BATTERY_STATUS=0x1000,
	BACKLIGHT=0x1981,
	REPROG_CONTROLS=0x1B00,
	REPROG_CONTROLS_V2=0x1B01,
	REPROG_CONTROLS_V3=0x1B03,
	WIRELESS_DEVICE_STATUS=0x1D4B,
	LEFT_RIGHT_SWAP=0x2001,
	VERTICAL_SCROLLING=0x2100,
	HI_RES_SCROLLING=0x2120,
	MOUSE_POINTER=0x2200,
	FN_INVERSION=0x40A0,
	NEW_FN_INVERSION=0x40A2,
	ENCRYPTION=0x4100,
	SOLAR_DASHBOARD=0x4301,
	KEYBOARD_LAYOUT=0x4520,
	TOUCHPAD_FW_ITEMS=0x6010,
	TOUCHPAD_SW_ITEMS=0x6011,
	TOUCHPAD_WIN8_FW_ITEMS=0x6012,
	TOUCHPAD_RAW_XY=0x6100,
	TOUCHMOUSE_RAW_POINTS=0x6110,
)
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

BATTERY_OK = lambda status: status not in (BATTERY_STATUS.invalid_battery, BATTERY_STATUS.thermal_error)

BATTERY_STATUS = _NamedInts(
				discharging=0x00,
				recharging=0x01,
				almost_full=0x02,
				full=0x03,
				slow_recharge=0x04,
				invalid_battery=0x05,
				thermal_error=0x06)

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
	assert FEATURE.ROOT == 0x0000

	def __init__(self, device):
		assert device is not None
		self.device = device
		self.supported = True
		self.features = None

	def __del__(self):
		self.supported = False
		self.device = None
		self.features = None

	def _check(self):
		# print (self.device, "check", self.supported, self.features, self.device.protocol)
		if self.supported:
			assert self.device
			if self.features is not None:
				return True

			if not self.device.online:
				# device is not connected right now, will have to try later
				return False

			# I _think_ this is universally true
			if self.device.protocol and self.device.protocol < 2.0:
				self.supported = False
				self.device.features = None
				self.device = None
				return False

			reply = self.device.request(0x0000, _pack('!H', FEATURE.FEATURE_SET))
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
			if isinstance(index, int):
				if index < 0 or index >= len(self.features):
					raise IndexError(index)

				if self.features[index] is None:
					feature = self.device.feature_request(FEATURE.FEATURE_SET, 0x10, index)
					if feature:
						feature, = _unpack('!H', feature[:2])
						self.features[index] = FEATURE[feature]

				return self.features[index]

			elif isinstance(index, slice):
				indices = index.indices(len(self.features))
				return [self.__getitem__(i) for i in range(*indices)]

	def __contains__(self, featureId):
		"""Tests whether the list contains given Feature ID"""
		if self._check():
			ivalue = int(featureId)

			may_have = False
			for f in self.features:
				if f is None:
					may_have = True
				elif ivalue == int(f):
					return True

			if may_have:
				reply = self.device.request(0x0000, _pack('!H', ivalue))
				if reply:
					index = ord(reply[0:1])
					if index:
						self.features[index] = FEATURE[ivalue]
						return True

	def index(self, featureId):
		"""Gets the Feature Index for a given Feature ID"""
		if self._check():
			may_have = False
			ivalue = int(featureId)
			for index, f in enumerate(self.features):
				if f is None:
					may_have = True
				elif ivalue == int(f):
					return index

			if may_have:
				reply = self.device.request(0x0000, _pack('!H', ivalue))
				if reply:
					index = ord(reply[0:1])
					self.features[index] = FEATURE[ivalue]
					return index

		raise ValueError("%r not in list" % featureId)

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
		self.device = device
		self.keys = [None] * count

	def __getitem__(self, index):
		if isinstance(index, int):
			if index < 0 or index >= len(self.keys):
				raise IndexError(index)

			if self.keys[index] is None:
				keydata = feature_request(self.device, FEATURE.REPROG_CONTROLS, 0x10, index)
				if keydata:
					key, key_task, flags = _unpack('!HHB', keydata[:5])
					ctrl_id_text = special_keys.CONTROL[key]
					ctrl_task_text = special_keys.TASK[key_task]
					self.keys[index] = _ReprogrammableKeyInfo(index, ctrl_id_text, ctrl_task_text, flags)

			return self.keys[index]

		elif isinstance(index, slice):
			indices = index.indices(len(self.keys))
			return [self.__getitem__(i) for i in range(*indices)]

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

def feature_request(device, feature, function=0x00, *params):
	if device.online and device.features:
		if feature in device.features:
			feature_index = device.features.index(int(feature))
			return device.request((feature_index << 8) + (function & 0xFF), *params)


def get_firmware(device):
	"""Reads a device's firmware info.

	:returns: a list of FirmwareInfo tuples, ordered by firmware layer.
	"""
	count = feature_request(device, FEATURE.DEVICE_FW_VERSION)
	if count:
		count = ord(count[:1])

		fw = []
		for index in range(0, count):
			fw_info = feature_request(device, FEATURE.DEVICE_FW_VERSION, 0x10, index)
			if fw_info:
				level = ord(fw_info[:1]) & 0x0F
				if level == 0 or level == 1:
					name, version_major, version_minor, build = _unpack('!3sBBH', fw_info[1:8])
					version = '%02X.%02X' % (version_major, version_minor)
					if build:
						version += '.B%04X' % build
					extras = fw_info[9:].rstrip(b'\x00') or None
					fw_info = _FirmwareInfo(FIRMWARE_KIND[level], name.decode('ascii'), version, extras)
				elif level == FIRMWARE_KIND.Hardware:
					fw_info = _FirmwareInfo(FIRMWARE_KIND.Hardware, '', str(ord(fw_info[1:2])), None)
				else:
					fw_info = _FirmwareInfo(FIRMWARE_KIND.Other, '', '', None)

				fw.append(fw_info)
				# if _log.isEnabledFor(_DEBUG):
				# 	_log.debug("device %d firmware %s", devnumber, fw_info)
		return tuple(fw)


def get_kind(device):
	"""Reads a device's type.

	:see DEVICE_KIND:
	:returns: a string describing the device type, or ``None`` if the device is
	not available or does not support the ``DEVICE_NAME`` feature.
	"""
	kind = feature_request(device, FEATURE.DEVICE_NAME, 0x20)
	if kind:
		kind = ord(kind[:1])
		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("device %d type %d = %s", devnumber, kind, DEVICE_KIND[kind])
		return DEVICE_KIND[kind]


def get_name(device):
	"""Reads a device's name.

	:returns: a string with the device name, or ``None`` if the device is not
	available or does not support the ``DEVICE_NAME`` feature.
	"""
	name_length = feature_request(device, FEATURE.DEVICE_NAME)
	if name_length:
		name_length = ord(name_length[:1])

		name = b''
		while len(name) < name_length:
			fragment = feature_request(device, FEATURE.DEVICE_NAME, 0x10, len(name))
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
	battery = feature_request(device, FEATURE.BATTERY_STATUS)
	if battery:
		discharge, dischargeNext, status = _unpack('!BBB', battery[:3])
		if _log.isEnabledFor(_DEBUG):
			_log.debug("device %d battery %d%% charged, next level %d%% charge, status %d = %s",
						device.number, discharge, dischargeNext, status, BATTERY_STATUS[status])
		return discharge, BATTERY_STATUS[status]


def get_keys(device):
	count = feature_request(device, FEATURE.REPROG_CONTROLS)
	if count:
		return KeysArray(device, ord(count[:1]))


def get_mouse_pointer_info(device):
	pointer_info = feature_request(device, FEATURE.MOUSE_POINTER)
	if pointer_info:
		dpi, flags = _unpack('!HB', pointer_info[:3])
		acceleration = ('none', 'low', 'med', 'high')[flags & 0x3]
		suggest_os_ballistics = (flags & 0x04) != 0
		suggest_vertical_orientation = (flags & 0x08) != 0
		return {
				'dpi': dpi,
				'acceleration': acceleration,
				'suggest_os_ballistics': suggest_os_ballistics,
				'suggest_vertical_orientation': suggest_vertical_orientation
			}
