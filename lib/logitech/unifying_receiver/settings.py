#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

# from weakref import proxy as _proxy
from copy import copy as _copy

from .common import NamedInt as _NamedInt, NamedInts as _NamedInts

#
#
#

KIND = _NamedInts(toggle=0x1, choice=0x02, range=0x12)

class _Setting(object):
	__slots__ = ['name', 'label', 'description', 'kind', 'persister',
					'_rw', '_validator', '_device', '_value']

	def __init__(self, name, rw, validator, kind=None, label=None, description=None):
		assert name
		self.name = name
		self.label = label or name
		self.description = description

		self._rw = rw
		self._validator = validator

		assert kind is None or kind & validator.kind != 0
		self.kind = kind or validator.kind
		self.persister = None

	def __call__(self, device):
		assert not hasattr(self, '_value')
		o = _copy(self)
		o._value = None
		o._device = device  # _proxy(device)
		return o

	@property
	def choices(self):
		return self._validator.choices if self._validator.kind & KIND.choice else None

	def read(self, cached=True):
		if self._value is None and self.persister:
			self._value = self.persister.get(self.name)

		if cached and self._value is not None:
			if self.persister and self.name not in self.persister:
				self.persister[self.name] = self._value
			return self._value

		if self._device.online:
			reply = self._rw.read(self._device)
			if reply:
				self._value = self._validator.validate_read(reply)
			if self.persister and self.name not in self.persister:
				self.persister[self.name] = self._value
			return self._value

	def write(self, value):
		if self._device:
			data_bytes = self._validator.prepare_write(value)
			reply = self._rw.write(self._device, data_bytes)
			if reply:
				self._value = self._validator.validate_write(value, reply)
			if self.persister and self._value is not None:
				self.persister[self.name] = self._value
			return self._value

	def apply(self):
		if self._value is not None:
			self.write(self._value)

	def __str__(self):
		if hasattr(self, '_value'):
			assert hasattr(self, '_device')
			return '<Setting([%s:%s] %s:%s=%s)>' % (self._rw.kind, self._validator.kind, self._device.codename, self.name, self._value)
		return '<Setting([%s:%s] %s)>' % (self._rw.kind, self._validator.kind, self.name)
	__unicode__ = __repr__ = __str__

#
# read/write low-level operators
#

class _RegisterRW(object):
	__slots__ = ['register']

	kind = _NamedInt(0x01, 'register')

	def __init__(self, register):
		assert isinstance(register, int)
		self.register = register

	def read(self, device):
		return device.read_register(self.register)

	def write(self, device, data_bytes):
		return device.write_register(self.register, data_bytes)


class _FeatureRW(object):
	__slots__ = ['feature', 'read_fnid', 'write_fnid']

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

class _BooleanValidator(object):
	__slots__ = ['true_value', 'false_value', 'mask', 'write_returns_value']

	kind = KIND.toggle
	default_true = 0x01
	default_false = 0x00
	# mask specifies all the affected bits in the value
	default_mask = 0xFF

	def __init__(self, true_value=default_true, false_value=default_false, mask=default_mask, write_returns_value=False):
		self.true_value = true_value
		self.false_value = false_value
		self.mask = mask
		self.write_returns_value = write_returns_value

	def _validate_value(self, reply_bytes, expected_value):
		if isinstance(expected_value, int):
			return ord(reply_bytes[:1]) & self.mask == expected_value
		else:
			for i in range(0, len(self.mask)):
				masked_value = ord(reply_bytes[i:i+1]) & ord(self.mask[i:i+1])
				if masked_value != ord(expected_value[i:i+1]):
					return False
			return True

	def validate_read(self, reply_bytes):
		return self._validate_value(reply_bytes, self.true_value)

	def prepare_write(self, value):
		# FIXME: this does not work right when there is more than one flag in
		# the same register!
		return self.true_value if value else self.false_value

	def validate_write(self, value, reply_bytes):
		if self.write_returns_value:
			return self._validate_value(reply_bytes, self.true_value)

		# just assume the value was written correctly, otherwise there would not
		# be any reply_bytes to check
		return bool(value)


class _ChoicesValidator(object):
	__slots__ = ['choices', 'write_returns_value']

	kind = KIND.choice

	def __init__(self, choices, write_returns_value=False):
		assert isinstance(choices, _NamedInts)
		self.choices = choices
		self.write_returns_value = write_returns_value

	def validate_read(self, reply_bytes):
		assert self.choices is not None
		reply_value = ord(reply_bytes[:1])
		valid_value = self.choices[reply_value]
		assert valid_value is not None, "%: failed to validate read value %02X" % (self.__class__.__name__, reply_value)
		return valid_value

	def prepare_write(self, value):
		assert self.choices is not None
		choice = self.choices[value]
		if choice is None:
			raise ValueError("invalid choice " + repr(value))
		assert isinstance(choice, _NamedInt)
		return choice.bytes(1)

	def validate_write(self, value, reply_bytes):
		assert self.choices is not None
		if self.write_returns_value:
			reply_value = ord(reply_bytes[:1])
			choice = self.choices[reply_value]
			assert choice is not None, "failed to validate write reply %02X" % reply_value
			return choice

		# just assume the value was written correctly, otherwise there would not
		# be any reply_bytes to check
		return self.choices[value]

#
# pre-defined basic setting descriptors
#

def register_toggle(name, register,
					true_value=_BooleanValidator.default_true, false_value=_BooleanValidator.default_false,
					mask=_BooleanValidator.default_mask, write_returns_value=False,
					label=None, description=None):
	rw = _RegisterRW(register)
	validator = _BooleanValidator(true_value=true_value, false_value=false_value, mask=mask, write_returns_value=write_returns_value)
	return _Setting(name, rw, validator, label=label, description=description)


def register_choices(name, register, choices,
					kind=KIND.choice, write_returns_value=False,
					label=None, description=None):
	assert choices
	rw = _RegisterRW(register)
	validator = _ChoicesValidator(choices, write_returns_value=write_returns_value)
	return _Setting(name, rw, validator, kind=kind, label=label, description=description)


def feature_toggle(name, feature,
					read_function_id=_FeatureRW.default_read_fnid, write_function_id=_FeatureRW.default_write_fnid,
					true_value=_BooleanValidator.default_true, false_value=_BooleanValidator.default_false,
					mask=_BooleanValidator.default_mask, write_returns_value=False,
					label=None, description=None):
	rw = _FeatureRW(feature, read_function_id, write_function_id)
	validator = _BooleanValidator(true_value=true_value, false_value=false_value, mask=mask, write_returns_value=write_returns_value)
	return _Setting(name, rw, validator, label=label, description=description)
