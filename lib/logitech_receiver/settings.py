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

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

from copy import copy as _copy
import math

from .common import (
				NamedInt as _NamedInt,
				NamedInts as _NamedInts,
				bytes2int as _bytes2int,
				int2bytes as _int2bytes,
			)

#
#
#

KIND = _NamedInts(toggle=0x01, choice=0x02, range=0x04)

class Setting(object):
	"""A setting descriptor.
	Needs to be instantiated for each specific device."""
	__slots__ = ('name', 'label', 'description', 'kind', 'device_kind',
					'_rw', '_validator', '_device', '_value')

	def __init__(self, name, rw, validator, kind=None, label=None, description=None, device_kind=None):
		assert name
		self.name = name
		self.label = label or name
		self.description = description
		self.device_kind = device_kind

		self._rw = rw
		self._validator = validator

		assert kind is None or kind & validator.kind != 0
		self.kind = kind or validator.kind

	def __call__(self, device):
		assert not hasattr(self, '_value')
		# combined keyboards and touchpads (e.g., K400) break this assertion so don't use it
		# assert self.device_kind is None or device.kind in self.device_kind
		p = device.protocol
		if p == 1.0:
			# HID++ 1.0 devices do not support features
			assert self._rw.kind == RegisterRW.kind
		elif p >= 2.0:
			# HID++ 2.0 devices do not support registers
			assert self._rw.kind == FeatureRW.kind

		o = _copy(self)
		o._value = None
		o._device = device
		return o

	@property
	def choices(self):
		assert hasattr(self, '_value')
		assert hasattr(self, '_device')

		return self._validator.choices if self._validator.kind & KIND.choice else None

	@property
	def range(self):
		assert hasattr(self, '_value')
		assert hasattr(self, '_device')

		if self._validator.kind == KIND.range:
			return (self._validator.min_value, self._validator.max_value)

	def read(self, cached=True):
		assert hasattr(self, '_value')
		assert hasattr(self, '_device')

		if _log.isEnabledFor(_DEBUG):
			_log.debug("%s: settings read %r from %s", self.name, self._value, self._device)

		if self._value is None and self._device.persister:
			# We haven't read a value from the device yet,
			# maybe we have something in the configuration.
			self._value = self._device.persister.get(self.name)

		if cached and self._value is not None:
			if self._device.persister and self.name not in self._device.persister:
				# If this is a new device (or a new setting for an old device),
				# make sure to save its current value for the next time.
				self._device.persister[self.name] = self._value
			return self._value

		if self._device.online:
			reply = self._rw.read(self._device)
			if reply:
				self._value = self._validator.validate_read(reply)
			if self._device.persister and self.name not in self._device.persister:
				# Don't update the persister if it already has a value,
				# otherwise the first read might overwrite the value we wanted.
				self._device.persister[self.name] = self._value
			return self._value

	def write(self, value):
		assert hasattr(self, '_value')
		assert hasattr(self, '_device')
		assert value is not None

		if _log.isEnabledFor(_DEBUG):
			_log.debug("%s: settings write %r to %s", self.name, value, self._device)

		if self._device.online:
			# Remember the value we're trying to set, even if the write fails.
			# This way even if the device is offline or some other error occurs,
			# the last value we've tried to write is remembered in the configuration.
			self._value = value
			if self._device.persister:
				self._device.persister[self.name] = value

			current_value = None
			if self._validator.needs_current_value:
				# the validator needs the current value, possibly to merge flag values
				current_value = self._rw.read(self._device)

			data_bytes = self._validator.prepare_write(value, current_value)
			if data_bytes is not None:
				if _log.isEnabledFor(_DEBUG):
					_log.debug("%s: settings prepare write(%s) => %r", self.name, value, data_bytes)

				reply = self._rw.write(self._device, data_bytes)
				if not reply:
					# tell whomever is calling that the write failed
					return None

			return value

	def apply(self):
		assert hasattr(self, '_value')
		assert hasattr(self, '_device')

		if _log.isEnabledFor(_DEBUG):
			_log.debug("%s: apply %s (%s)", self.name, self._value, self._device)

		value = self.read()
		if value is not None:
			self.write(value)

	def __str__(self):
		if hasattr(self, '_value'):
			assert hasattr(self, '_device')
			return '<Setting([%s:%s] %s:%s=%s)>' % (self._rw.kind, self._validator.kind, self._device.codename, self.name, self._value)
		return '<Setting([%s:%s] %s)>' % (self._rw.kind, self._validator.kind, self.name)
	__unicode__ = __repr__ = __str__

#
# read/write low-level operators
#

class RegisterRW(object):
	__slots__ = ('register', )

	kind = _NamedInt(0x01, 'register')

	def __init__(self, register):
		assert isinstance(register, int)
		self.register = register

	def read(self, device):
		return device.read_register(self.register)

	def write(self, device, data_bytes):
		return device.write_register(self.register, data_bytes)


class FeatureRW(object):
	__slots__ = ('feature', 'read_fnid', 'write_fnid')

	kind = _NamedInt(0x02, 'feature')
	default_read_fnid = 0x00
	default_write_fnid = 0x10

	def __init__(self, feature, read_fnid=default_read_fnid, write_fnid=default_write_fnid):
		assert isinstance(feature, _NamedInt)
		self.feature = feature
		self.read_fnid = read_fnid
		self.write_fnid = write_fnid

	def read(self, device):
		assert self.feature is not None
		return device.feature_request(self.feature, self.read_fnid)

	def write(self, device, data_bytes):
		assert self.feature is not None
		return device.feature_request(self.feature, self.write_fnid, data_bytes)

#
# value validators
# handle the conversion from read bytes, to setting value, and back
#

class BooleanValidator(object):
	__slots__ = ('true_value', 'false_value', 'mask', 'needs_current_value')

	kind = KIND.toggle
	default_true = 0x01
	default_false = 0x00
	# mask specifies all the affected bits in the value
	default_mask = 0xFF

	def __init__(self, true_value=default_true, false_value=default_false, mask=default_mask):
		if isinstance(true_value, int):
			assert isinstance(false_value, int)
			if mask is None:
				mask = self.default_mask
			else:
				assert isinstance(mask, int)
			assert true_value & false_value == 0
			assert true_value & mask == true_value
			assert false_value & mask == false_value
			self.needs_current_value = (mask != self.default_mask)
		elif isinstance(true_value, bytes):
			if false_value is None or false_value == self.default_false:
				false_value = b'\x00' * len(true_value)
			else:
				assert isinstance(false_value, bytes)
			if mask is None or mask == self.default_mask:
				mask = b'\xFF' * len(true_value)
			else:
				assert isinstance(mask, bytes)
			assert len(mask) == len(true_value) == len(false_value)
			tv = _bytes2int(true_value)
			fv = _bytes2int(false_value)
			mv = _bytes2int(mask)
			assert tv & fv == 0
			assert tv & mv == tv
			assert fv & mv == fv
			self.needs_current_value = any(m != b'\xFF' for m in mask)
		else:
			raise Exception("invalid mask '%r', type %s" % (mask, type(mask)))

		self.true_value = true_value
		self.false_value = false_value
		self.mask = mask

	def validate_read(self, reply_bytes):
		if isinstance(self.mask, int):
			reply_value = ord(reply_bytes[:1]) & self.mask
			if _log.isEnabledFor(_DEBUG):
				_log.debug("BooleanValidator: validate read %r => %02X", reply_bytes, reply_value)
			if reply_value == self.true_value:
				return True
			if reply_value == self.false_value:
				return False
			_log.warn("BooleanValidator: reply %02X mismatched %02X/%02X/%02X",
							reply_value, self.true_value, self.false_value, self.mask)
			return False

		count = len(self.mask)
		mask = _bytes2int(self.mask)
		reply_value = _bytes2int(reply_bytes[:count]) & mask

		true_value = _bytes2int(self.true_value)
		if reply_value == true_value:
			return True

		false_value = _bytes2int(self.false_value)
		if reply_value == false_value:
			return False

		_log.warn("BooleanValidator: reply %r mismatched %r/%r/%r",
						reply_bytes, self.true_value, self.false_value, self.mask)
		return False

	def prepare_write(self, new_value, current_value=None):
		if new_value is None:
			new_value = False
		else:
			assert isinstance(new_value, bool)

		to_write = self.true_value if new_value else self.false_value

		if isinstance(self.mask, int):
			if current_value is not None and self.needs_current_value:
				to_write |= ord(current_value[:1]) & (0xFF ^ self.mask)
			if current_value is not None and to_write == ord(current_value[:1]):
				return None
		else:
			to_write = bytearray(to_write)
			count = len(self.mask)
			for i in range(0, count):
				b = ord(to_write[i:i+1])
				m = ord(self.mask[i : i + 1])
				assert b & m == b
				# b &= m
				if current_value is not None and self.needs_current_value:
					b |= ord(current_value[i : i + 1]) & (0xFF ^ m)
				to_write[i] = b
			to_write = bytes(to_write)

			if current_value is not None and to_write == current_value[:len(to_write)]:
				return None

		if _log.isEnabledFor(_DEBUG):
			_log.debug("BooleanValidator: prepare_write(%s, %s) => %r", new_value, current_value, to_write)

		return to_write


class ChoicesValidator(object):
	__slots__ = ('choices', 'flag', '_bytes_count', 'needs_current_value')

	kind = KIND.choice

	"""Translates between NamedInts and a byte sequence.
	:param choices: a list of NamedInts
	:param bytes_count: the size of the derived byte sequence. If None, it
	will be calculated from the choices."""
	def __init__(self, choices, bytes_count=None):
		assert choices is not None
		assert isinstance(choices, _NamedInts)
		assert len(choices) > 2
		self.choices = choices
		self.needs_current_value = False

		max_bits = max(x.bit_length() for x in choices)
		self._bytes_count = (max_bits // 8) + (1 if max_bits % 8 else 0)
		if bytes_count:
			assert self._bytes_count <= bytes_count
			self._bytes_count = bytes_count
		assert self._bytes_count < 8

	def validate_read(self, reply_bytes):
		reply_value = _bytes2int(reply_bytes[:self._bytes_count])
		valid_value = self.choices[reply_value]
		assert valid_value is not None, "%s: failed to validate read value %02X" % (self.__class__.__name__, reply_value)
		return valid_value

	def prepare_write(self, new_value, current_value=None):
		if new_value is None:
			choice = self.choices[:][0]
		else:
			if isinstance(new_value, int):
				choice = self.choices[new_value]
			elif int(new_value) in self.choices:
				choice = self.choices[int(new_value)]
			elif new_value in self.choices:
				choice = self.choices[new_value]
			else:
				raise ValueError(new_value)

		if choice is None:
			raise ValueError("invalid choice %r" % new_value)
		assert isinstance(choice, _NamedInt)
		return choice.bytes(self._bytes_count)

class RangeValidator(object):
	__slots__ = ('min_value', 'max_value', 'flag', '_bytes_count', 'needs_current_value')

	kind = KIND.range

	"""Translates between integers and a byte sequence.
	:param min_value: minimum accepted value (inclusive)
	:param max_value: maximum accepted value (inclusive)
	:param bytes_count: the size of the derived byte sequence. If None, it
	will be calculated from the range."""
	def __init__(self, min_value, max_value, bytes_count=None):
		assert max_value > min_value
		self.min_value = min_value
		self.max_value = max_value
		self.needs_current_value = False

		self._bytes_count = math.ceil(math.log(max_value + 1, 256))
		if bytes_count:
			assert self._bytes_count <= bytes_count
			self._bytes_count = bytes_count
		assert self._bytes_count < 8

	def validate_read(self, reply_bytes):
		reply_value = _bytes2int(reply_bytes[:self._bytes_count])
		assert reply_value >= self.min_value, "%s: failed to validate read value %02X" % (self.__class__.__name__, reply_value)
		assert reply_value <= self.max_value, "%s: failed to validate read value %02X" % (self.__class__.__name__, reply_value)
		return reply_value

	def prepare_write(self, new_value, current_value=None):
		if new_value < self.min_value or new_value > self.max_value:
			raise ValueError("invalid choice %r" % new_value)
		return _int2bytes(new_value, self._bytes_count)
