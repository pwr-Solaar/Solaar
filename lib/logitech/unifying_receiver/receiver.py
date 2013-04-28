#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

import errno as _errno
from weakref import proxy as _proxy

from logging import getLogger
_log = getLogger('LUR').getChild('receiver')
del getLogger

from . import base as _base
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import strhex as _strhex, NamedInts as _NamedInts
from . import descriptors as _descriptors

#
#
#

"""A receiver may have a maximum of 6 paired devices at a time."""
MAX_PAIRED_DEVICES = 6


class PairedDevice(object):
	def __init__(self, receiver, number):
		assert receiver
		self.receiver = _proxy(receiver)
		assert number > 0 and number <= receiver.max_devices
		self.number = number

		self._unifying = receiver.max_devices > 1
		self._protocol = None
		self._wpid = None
		self._power_switch = None
		self._polling_rate = None
		self._codename = None
		self._name = None
		self._kind = None
		self._serial = None
		self._firmware = None
		self._keys = None

		self.features = _hidpp20.FeaturesArray(self) if self._unifying else None
		self._registers = None
		self._settings = None

	@property
	def protocol(self):
		if self._protocol is None:
			self._protocol = _base.ping(self.receiver.handle, self.number)
			# _log.debug("device %d protocol %s", self.number, self._protocol)
		return self._protocol or 0

	@property
	def wpid(self):
		if self._wpid is None:
			if self._unifying:
				pair_info = self.receiver.request(0x83B5, 0x20 + self.number - 1)
				if pair_info:
					self._wpid = _strhex(pair_info[3:5])
					if self._kind is None:
						kind = ord(pair_info[7:8]) & 0x0F
						self._kind = _hidpp10.DEVICE_KIND[kind]
					if self._polling_rate is None:
						self._polling_rate = ord(pair_info[2:3])
			# else:
			# 	device_info = self.receiver.request(0x83B5, 0x04)
			# 	self.wpid = _strhex(device_info[3:5])
		return self._wpid

	@property
	def polling_rate(self):
		if self._polling_rate is None and self._unifying:
			self.wpid, 0
		return self._polling_rate

	@property
	def power_switch_location(self):
		if self._power_switch is None and self._unifying:
			ps = self.receiver.request(0x83B5, 0x30 + self.number - 1)
			if ps:
				ps = ord(ps[9:10]) & 0x0F
				self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps]
		return self._power_switch

	@property
	def codename(self):
		if self._codename is None and self._unifying:
			codename = self.receiver.request(0x83B5, 0x40 + self.number - 1)
			if codename:
				self._codename = codename[2:].rstrip(b'\x00').decode('utf-8')
				# _log.debug("device %d codename %s", self.number, self._codename)
		return self._codename

	@property
	def name(self):
		if self._name is None and self._unifying:
			if self.codename in _descriptors.DEVICES:
				self._name, self._kind = _descriptors.DEVICES[self._codename][:2]
			elif self.protocol >= 2.0:
				self._name = _hidpp20.get_name(self)
		return self._name or self.codename or '?'

	@property
	def kind(self):
		if self._kind is None and self._unifying:
			pair_info = self.receiver.request(0x83B5, 0x20 + self.number - 1)
			if pair_info:
				kind = ord(pair_info[7:8]) & 0x0F
				self._kind = _hidpp10.DEVICE_KIND[kind]
				if self._wpid is None:
					self._wpid = _strhex(pair_info[3:5])
			if self._kind is None:
				if self.codename in _descriptors.DEVICES:
					self._name, self._kind = _descriptors.DEVICES[self._codename][:2]
				elif self.protocol >= 2.0:
					self._kind = _hidpp20.get_kind(self)
		return self._kind or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			p = self.protocol
			if p >= 2.0:
				self._firmware = _hidpp20.get_firmware(self)
			if self._firmware is None and p == 1.0:
				self._firmware = _hidpp10.get_firmware(self)
		return self._firmware or ()

	@property
	def serial(self):
		if self._serial is None and self._unifying:
			self._serial = _hidpp10.get_serial(self)
		return self._serial or '?'

	@property
	def keys(self):
		if self._keys is None and self._unifying:
			self._keys = _hidpp20.get_keys(self) or ()
		return self._keys

	@property
	def registers(self):
		if self._registers is None:
			descriptor = _descriptors.DEVICES.get(self.codename)
			if descriptor is None or descriptor.registers is None:
				self._registers = _NamedInts()
			else:
				self._registers = descriptor.registers
		return self._registers

	@property
	def settings(self):
		if self._settings is None:
			descriptor = _descriptors.DEVICES.get(self.codename)
			if descriptor is None or descriptor.settings is None:
				self._settings = []
			else:
				self._settings = [s(self) for s in descriptor.settings]

		if self.features:
			_descriptors.check_features(self, self._settings)
		return self._settings

	def request(self, request_id, *params):
		return _base.request(self.receiver.handle, self.number, request_id, *params)

	def feature_request(self, feature, function=0x00, *params):
		if self._unifying:
			return _hidpp20.feature_request(self, feature, function, *params)

	def ping(self):
		return _base.ping(self.receiver.handle, self.number) is not None

	def __index__(self):
		return self.number
	__int__ = __index__

	def __eq__(self, other):
		return self.serial == other.serial

	def __ne__(self, other):
		return self.serial != other.serial

	def __hash__(self):
		return self.serial.__hash__()

	def __str__(self):
		return '<PairedDevice(%d,%s)>' % (self.number, self.codename or '?')
	__unicode__ = __repr__ = __str__

#
#
#

class Receiver(object):
	"""A Unifying Receiver instance.

	The paired devices are available through the sequence interface.
	"""
	number = 0xFF
	kind = None

	def __init__(self, handle, path=None):
		assert handle
		self.handle = handle
		assert path
		self.path = path

		serial_reply = self.request(0x83B5, 0x03)
		assert serial_reply
		self._serial = _strhex(serial_reply[1:5])
		self.max_devices = ord(serial_reply[6:7][0])

		if self.max_devices == 1:
			self.name = 'Nano Receiver'
		elif self.max_devices == 6:
			self.name = 'Unifying Receiver'
		else:
			raise Exception("unknown receiver type")
		self._str = '<%s(%s,%s%s)>' % (self.name.replace(' ', ''), self.path, '' if type(self.handle) == int else 'T', self.handle)

		self._firmware = None
		self._devices = {}

	def close(self):
		handle, self.handle = self.handle, None
		self._devices.clear()
		return (handle and _base.close(handle))

	def __del__(self):
		self.close()

	@property
	def serial(self):
		assert self._serial
		# if self._serial is None and self.handle:
		# 	self._serial = _hidpp10.get_serial(self)
		return self._serial

	@property
	def firmware(self):
		if self._firmware is None and self.handle:
			self._firmware = _hidpp10.get_firmware(self)
		return self._firmware

	def enable_notifications(self, enable=True):
		"""Enable or disable device (dis)connection notifications on this
		receiver."""
		if not self.handle:
			return False
		if enable:
			# set all possible flags
			ok = self.request(0x8000, 0xFF, 0xFF, 0xFF)
		else:
			# clear out all possible flags
			ok = self.request(0x8000)

		if ok:
			_log.info("device notifications %s", 'enabled' if enable else 'disabled')
		else:
			_log.warn("failed to %s device notifications", 'enable' if enable else 'disable')
		return ok

	def notify_devices(self):
		"""Scan all devices."""
		if self.handle:
			if not self.request(0x8002, 0x02):
				_log.warn("failed to trigger device link notifications")

	def register_new_device(self, number):
		if self._devices.get(number) is not None:
			raise IndexError("device number %d already registered" % number)
		dev = PairedDevice(self, number)
		# create a device object, but only use it if the receiver knows about it

		# Nano receiver
		#if self.max_devices == 1 and number == 1:
		#	# the Nano receiver does not provide the wpid
		#	_log.info("%s: found Nano device %d (%s)", self, number, dev.serial)
		#	# dev._wpid = self.serial + ':1'
		#	self._devices[number] = dev
		#	return dev

		if dev.wpid:
			_log.info("found device %d (%s)", number, dev.wpid)
			self._devices[number] = dev
			return dev
		self._devices[number] = None

	def set_lock(self, lock_closed=True, device=0, timeout=0):
		if self.handle:
			lock = 0x02 if lock_closed else 0x01
			reply = self.request(0x80B2, lock, device, timeout)
			if reply:
				return True
			_log.warn("failed to %s the receiver lock", 'close' if lock_closed else 'open')

	def count(self):
		count = self.request(0x8102)
		return 0 if count is None else ord(count[1:2])

	def request(self, request_id, *params):
		if self.handle:
			return _base.request(self.handle, 0xFF, request_id, *params)

	def __iter__(self):
		for number in range(1, 1 + self.max_devices):
			if number in self._devices:
				dev = self._devices[number]
			else:
				dev = self.__getitem__(number)
			if dev is not None:
				yield dev

	def __getitem__(self, key):
		if not self.handle:
			return None

		dev = self._devices.get(key)
		if dev is not None:
			return dev

		if type(key) != int:
			raise TypeError('key must be an integer')
		if key < 1 or key > self.max_devices:
			raise IndexError(key)

		return self.register_new_device(key)

	def __delitem__(self, key):
		if self._devices.get(key) is None:
			raise IndexError(key)

		dev = self._devices[key]
		reply = self.request(0x80B2, 0x03, int(key))
		if reply:
			del self._devices[key]
			_log.warn("%s unpaired device %s", self, dev)
		else:
			_log.error("%s failed to unpair device %s", self, dev)
			raise IndexError(key)

	def __len__(self):
		return len([d for d in self._devices.values() if d is not None])

	def __contains__(self, dev):
		if type(dev) == int:
			return self._devices.get(dev) is not None

		return self.__contains__(dev.number)

	def __str__(self):
		return self._str
	__unicode__ = __repr__ = __str__

	__bool__ = __nonzero__ = lambda self: self.handle is not None

	@classmethod
	def open(self):
		"""Opens the first Logitech Unifying Receiver found attached to the machine.

		:returns: An open file handle for the found receiver, or ``None``.
		"""
		exception = None

		for rawdevice in _base.receivers():
			exception = None
			try:
				handle = _base.open_path(rawdevice.path)
				if handle:
					return Receiver(handle, rawdevice.path)
			except OSError as e:
				_log.exception("open %s", rawdevice.path)
				if e.errno == _errno.EACCES:
					exception = e

		if exception:
			# only keep the last exception
			raise exception
