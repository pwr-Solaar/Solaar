#
#
#

import errno as _errno

from logging import getLogger
_log = getLogger('LUR').getChild('receiver')
del getLogger

from . import base as _base
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import strhex as _strhex, FirmwareInfo as _FirmwareInfo
from .devices import DEVICES as _DEVICES

#
#
#

"""A receiver may have a maximum of 6 paired devices at a time."""
MAX_PAIRED_DEVICES = 6


class PairedDevice(object):
	def __init__(self, receiver, number):
		assert receiver
		self.receiver = receiver
		assert number > 0 and number <= MAX_PAIRED_DEVICES
		self.number = number

		self._protocol = None
		self._wpid = None
		self._power_switch = None
		self._codename = None
		self._name = None
		self._kind = None
		self._serial = None
		self._firmware = None
		self._keys = None

		self.features = _hidpp20.FeaturesArray(self)

	def __del__(self):
		del self.receiver
		del self.features
		del self._keys

	@property
	def protocol(self):
		if self._protocol is None:
			self._protocol = _base.ping(self.receiver.handle, self.number)
			# _log.debug("device %d protocol %s", self.number, self._protocol)
		return self._protocol or 0

	@property
	def wpid(self):
		if self._wpid is None:
			pair_info = self.receiver.request(0x83B5, 0x20 + self.number - 1)
			if pair_info:
				self._wpid = _strhex(pair_info[3:5])
				if self._kind is None:
					kind = ord(pair_info[7:8]) & 0x0F
					self._kind = _hidpp10.DEVICE_KIND[kind]
		return self._wpid

	@property
	def power_switch_location(self):
		if self._power_switch is None:
			self.serial
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
			if self.protocol < 2.0:
				if self.codename in _DEVICES:
					_, self._name, self._kind = _DEVICES[self._codename]
			else:
				self._name = _hidpp20.get_name(self)
		return self._name or self.codename or '?'

	@property
	def kind(self):
		if self._kind is None:
			pair_info = self.receiver.request(0x83B5, 0x20 + self.number - 1)
			if pair_info:
				kind = ord(pair_info[7:8]) & 0x0F
				self._kind = _hidpp10.DEVICE_KIND[kind]
				if self._wpid is None:
					self._wpid = _strhex(pair_info[3:5])
			if self._kind is None:
				if self.protocol < 2.0:
					if self.codename in _DEVICES:
						_, self._name, self._kind = _DEVICES[self._codename]
				else:
					self._kind = _hidpp20.get_kind(self)
		return self._kind or '?'

	@property
	def firmware(self):
		if self._firmware is None and self.protocol >= 2.0:
			self._firmware = _hidpp20.get_firmware(self)
			# _log.debug("device %d firmware %s", self.number, self._firmware)
		return self._firmware or ()

	@property
	def serial(self):
		if self._serial is None:
			serial = self.receiver.request(0x83B5, 0x30 + self.number - 1)
			if serial:
				self._serial = _strhex(serial[1:5])
				# _log.debug("device %d serial %s", self.number, self._serial)
				ps_location = ord(serial[9:10]) & 0x0F
				self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps_location]
		return self._serial or '?'

	@property
	def keys(self):
		if self._keys is None:
			self._keys = _hidpp20.get_keys(self) or ()
		return self._keys

	def request(self, request_id, *params):
		return _base.request(self.receiver.handle, self.number, request_id, *params)

	def feature_request(self, feature, function=0x00, *params):
		return _hidpp20.feature_request(self, feature, function, *params)

	def ping(self):
		return _base.ping(self.receiver.handle, self.number) is not None

	def __index__(self):
		return self.number
	__int__ = __index__

	def __hash__(self):
		return self.number

	def __cmp__(self, other):
		return self.number - other.number

	def __eq__(self, other):
		return self.receiver == other.receiver and self.number == other.number

	def __str__(self):
		return '<PairedDevice(%d,%s)>' % (self.number, self.codename or '?')
	__repr__ = __str__

#
#
#

class Receiver(object):
	"""A Unifying Receiver instance.

	The paired devices are available through the sequence interface.
	"""
	name = 'Unifying Receiver'
	kind = None
	max_devices = MAX_PAIRED_DEVICES
	create_device = PairedDevice

	def __init__(self, handle, path=None):
		assert handle
		self.handle = handle
		assert path
		self.path = path

		self.number = 0xFF
		self._serial = None
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
		if self._serial is None and self.handle:
			serial = self.request(0x83B5, 0x03)
			if serial:
				self._serial = _strhex(serial[1:5])
		return self._serial

	@property
	def firmware(self):
		if self._firmware is None and self.handle:
			firmware = []

			reply = self.request(0x83B5, 0x02)
			if reply:
				fw_version = _strhex(reply[1:5])
				fw_version = '%s.%s.B%s' % (fw_version[0:2], fw_version[2:4], fw_version[4:8])
				firmware.append(_FirmwareInfo(_hidpp20.FIRMWARE_KIND.Firmware, '', fw_version, None))

			reply = self.request(0x81F1, 0x04)
			if reply:
				bl_version = _strhex(reply[1:3])
				bl_version = '%s.%s' % (bl_version[0:2], bl_version[2:4])
				firmware.append(_FirmwareInfo(_hidpp20.FIRMWARE_KIND.Bootloader, '', bl_version, None))

			self._firmware = tuple(firmware)

		return self._firmware

	def enable_notifications(self, enable=True):
		"""Enable or disable device (dis)connection events on this receiver."""
		if not self.handle:
			return False
		if enable:
			# set all possible flags
			ok = self.request(0x8000, 0xFF, 0xFF)  # and self.request(0x8002, 0x02)
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
				_log.warn("failed to trigger device events")

	def set_lock(self, lock_closed=True, device=0, timeout=0):
		if self.handle:
			lock = 0x02 if lock_closed else 0x01
			reply = self.request(0x80B2, lock, device, timeout)
			if reply:
				return True
			_log.warn("failed to %s the receiver lock", 'close' if lock_closed else 'open')

	def request(self, request_id, *params):
		if self.handle:
			return _base.request(self.handle, 0xFF, request_id, *params)

	def __iter__(self):
		for number in range(1, 1 + MAX_PAIRED_DEVICES):
			dev = self.__getitem__(number)
			if dev is not None:
				yield dev

	def __getitem__(self, key):
		if not self.handle:
			return None

		if key in self._devices:
			return self._devices[key]

		if type(key) != int:
			raise TypeError('key must be an integer')
		if key < 1 or key > MAX_PAIRED_DEVICES:
			raise IndexError(key)

		dev = Receiver.create_device(self, key)
		if dev is not None and dev.wpid:
			self._devices[key] = dev
			return dev

		# no paired device at this index
		self._devices[key] = None

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
		count = self.request(0x8102)
		return 0 if count is None else ord(count[1:2])

	def __contains__(self, dev):
		if type(dev) == int:
			return dev in self._devices

		return self.__contains__(dev.number)

	def __str__(self):
		return '<Receiver(%s,%s%s)>' % (self.path, '' if type(self.handle) == int else 'T', self.handle)
	__repr__ = __str__

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
