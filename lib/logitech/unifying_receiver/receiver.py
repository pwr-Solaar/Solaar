#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

import errno as _errno
from weakref import proxy as _proxy

from logging import getLogger
_log = getLogger('LUR.receiver')
del getLogger

from . import base as _base
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import strhex as _strhex
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

		self.wpid = None
		self.polling_rate = 0

		self._kind = None
		self._codename = None
		self._name = None

		self._protocol = None if self.receiver.unifying_supported else 1.0
		self._power_switch = None if self.receiver.unifying_supported else '(unknown)'
		self.serial = _hidpp10.get_serial(self) if self.receiver.unifying_supported else self.receiver.serial

		if self.receiver.unifying_supported:
			pair_info = self.receiver.request(0x83B5, 0x20 + self.number - 1)
			if pair_info:
				self.wpid = _strhex(pair_info[3:5])
				kind = ord(pair_info[7:8]) & 0x0F
				self._kind = _hidpp10.DEVICE_KIND[kind]
				self.polling_rate = ord(pair_info[2:3])
			else:
				# no device at this address...
				return

		# else:
		# 	# guesswork...
		# 	descriptor = _descriptors.DEVICES.get(self.receiver.product_id)
		# 	if descriptor:
		# 		self._kind = descriptor.kind
		# 		self._codename = descriptor.codename
		# 		self._name = descriptor.name

		# 		device_info = self.receiver.request(0x83B5, 0x04)
		# 		if device_info:
		# 			self.wpid = _strhex(device_info[3:5])

		self._firmware = None
		self._keys = None

		self.features = _hidpp20.FeaturesArray(self) if self.receiver.unifying_supported else None
		self._registers = None
		self._settings = None

	@property
	def protocol(self):
		if self._protocol is None:
			self._protocol = _base.ping(self.receiver.handle, self.number)
			# _log.debug("device %d protocol %s", self.number, self._protocol)
		return self._protocol or 0

	@property
	def power_switch_location(self):
		if self._power_switch is None:
			ps = self.receiver.request(0x83B5, 0x30 + self.number - 1)
			if ps:
				ps = ord(ps[9:10]) & 0x0F
				self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps]
		return self._power_switch

	@property
	def codename(self):
		if self._codename is None:
			codename = self.receiver.request(0x83B5, 0x40 + self.number - 1)
			if codename:
				self._codename = codename[2:].rstrip(b'\x00').decode('utf-8')
				# _log.debug("device %d codename %s", self.number, self._codename)
		return self._codename

	@property
	def name(self):
		if self._name is None:
			if self.codename in _descriptors.DEVICES:
				self._name, self._kind = _descriptors.DEVICES[self._codename][:2]
			elif self.protocol >= 2.0:
				self._name = _hidpp20.get_name(self)
		return self._name or self.codename or '?'

	@property
	def kind(self):
		if self._kind is None and self.receiver.unifying_supported:
			pair_info = self.receiver.request(0x83B5, 0x20 + self.number - 1)
			if pair_info:
				kind = ord(pair_info[7:8]) & 0x0F
				self._kind = _hidpp10.DEVICE_KIND[kind]
				if self.wpid is None:
					self.wpid = _strhex(pair_info[3:5])
			if self._kind is None:
				if self.codename in _descriptors.DEVICES:
					self._name, self._kind = _descriptors.DEVICES[self._codename][:2]
				elif self.protocol >= 2.0:
					self._kind = _hidpp20.get_kind(self)
		return self._kind or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			if self.protocol < 2.0:
				self._firmware = _hidpp10.get_firmware(self)
			else:
				self._firmware = _hidpp20.get_firmware(self)
		return self._firmware or ()

	# @property
	# def serial(self):
	# 	if self._serial is None:
	# 		self._serial = _hidpp10.get_serial(self)
	# 	return self._serial or '?'

	@property
	def keys(self):
		if self._keys is None:
			if self.protocol >= 2.0:
				self._keys = _hidpp20.get_keys(self) or ()
		return self._keys

	@property
	def registers(self):
		if self._registers is None:
			descriptor = _descriptors.DEVICES.get(self.codename)
			if descriptor is None or descriptor.registers is None:
				self._registers = {}
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

	def enable_notifications(self, enable=True):
		"""Enable or disable device (dis)connection notifications on this
		receiver."""
		if not self.receiver or not self.receiver.handle or self.protocol >= 2.0:
			return False

		if enable:
			set_flag_bits = ( _hidpp10.NOTIFICATION_FLAG.battery_status
							| _hidpp10.NOTIFICATION_FLAG.wireless
							| _hidpp10.NOTIFICATION_FLAG.software_present )
		else:
			set_flag_bits = 0
		ok = _hidpp10.set_notification_flags(self, set_flag_bits)

		flag_bits = _hidpp10.get_notification_flags(self)
		flag_names = None if flag_bits is None else tuple(_hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits))

		if ok:
			_log.info("%s: device notifications %s %s", self, 'enabled' if enable else 'disabled', flag_names)
		else:
			_log.warn("%s: failed to %s device notifications %s", self, 'enable' if enable else 'disable', flag_names)
		return flag_bits if ok else None

	def request(self, request_id, *params):
		return _base.request(self.receiver.handle, self.number, request_id, *params)

	def feature_request(self, feature, function=0x00, *params):
		if self.protocol >= 2.0:
			return _hidpp20.feature_request(self, feature, function, *params)

	def ping(self):
		return _base.ping(self.receiver.handle, self.number) is not None

	def __index__(self):
		return self.number
	__int__ = __index__

	def __eq__(self, other):
		return other is not None and self.kind == other.kind and self.serial == other.serial

	def __ne__(self, other):
		return other is None or self.kind != other.kind or self.serial != other.serial

	def __hash__(self):
		return self.serial.__hash__()

	def __str__(self):
		return '<PairedDevice(%d,%s,%s)>' % (self.number, self.wpid, self.codename or '?')
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

	def __init__(self, handle, device_info):
		assert handle
		self.handle = handle
		assert device_info
		self.path = device_info.path
		self.product_id = device_info.product_id

		# read the serial immediately, so we can find out max_devices
		# this will tell us if it's a Unifying or Nano receiver
		serial_reply = self.request(0x83B5, 0x03)
		assert serial_reply
		self.serial = _strhex(serial_reply[1:5])
		self.max_devices = ord(serial_reply[6:7])

		if self.max_devices == 1:
			self.name = 'Nano Receiver'
		elif self.max_devices == 6:
			self.name = 'Unifying Receiver'
		else:
			raise Exception("unknown receiver type")
		self._str = '<%s(%s,%s%s)>' % (self.name.replace(' ', ''), self.path, '' if type(self.handle) == int else 'T', self.handle)

		old_equad_reply = self.request(0x83B5, 0x04)
		self.unifying_supported = old_equad_reply is None
		_log.info("%s (%s) uses protocol %s", self.name, self.path, 'eQuad' if old_equad_reply else 'eQuad DJ')

		self._firmware = None
		self._devices = {}

	def close(self):
		handle, self.handle = self.handle, None
		self._devices.clear()
		return (handle and _base.close(handle))

	def __del__(self):
		self.close()

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
			set_flag_bits = ( _hidpp10.NOTIFICATION_FLAG.battery_status
							| _hidpp10.NOTIFICATION_FLAG.wireless
							| _hidpp10.NOTIFICATION_FLAG.software_present )
		else:
			set_flag_bits = 0
		ok = _hidpp10.set_notification_flags(self, set_flag_bits)

		flag_bits = _hidpp10.get_notification_flags(self)
		flag_names = None if flag_bits is None else tuple(_hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits))

		if ok:
			_log.info("%s: receiver notifications %s => %s", self, 'enabled' if enable else 'disabled', flag_names)
		else:
			_log.warn("%s: failed to %s receiver notifications %s", self, 'enable' if enable else 'disable', flag_names)
		return flag_bits if ok else None

	def notify_devices(self):
		"""Scan all devices."""
		if self.handle:
			if not self.request(0x8002, 0x02):
				_log.warn("%s: failed to trigger device link notifications", self)

	def register_new_device(self, number):
		if self._devices.get(number) is not None:
			raise IndexError("%s: device number %d already registered" % (self, number))

		dev = PairedDevice(self, number)
		if dev.wpid:
			_log.info("%s: found new device %d (%s)", self, number, dev.wpid)
			self._devices[number] = dev
			return dev

		_log.warning("%s: looked for device %d, not found", self, number)
		self._devices[number] = None

	def set_lock(self, lock_closed=True, device=0, timeout=0):
		if self.handle:
			lock = 0x02 if lock_closed else 0x01
			reply = self.request(0x80B2, lock, device, timeout)
			if reply:
				return True
			_log.warn("%s: failed to %s the receiver lock", self, 'close' if lock_closed else 'open')

	def count(self):
		count = self.request(0x8102)
		return 0 if count is None else ord(count[1:2])

	# def has_devices(self):
	# 	return len(self) > 0 or self.count() > 0

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

	def __eq__(self, other):
		return other is not None and self.kind == other.kind and self.path == other.path

	def __ne__(self, other):
		return other is None or self.kind != other.kind or self.path != other.path

	def __hash__(self):
		return self.path.__hash__()

	def __str__(self):
		return self._str
	__unicode__ = __repr__ = __str__

	__bool__ = __nonzero__ = lambda self: self.handle is not None

	@classmethod
	def open(self, device_info):
		"""Opens a Logitech Receiver found attached to the machine, by Linux device path.

		:returns: An open file handle for the found receiver, or ``None``.
		"""
		try:
			handle = _base.open_path(device_info.path)
			if handle:
				return Receiver(handle, device_info)
		except OSError as e:
			_log.exception("open %s", device_info)
			if e.errno == _errno.EACCES:
				raise
		except:
			_log.exception("open %s", device_info)
