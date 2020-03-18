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

import errno as _errno

from logging import getLogger, INFO as _INFO
_log = getLogger(__name__)
del getLogger


from .i18n import _
from . import base as _base
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import strhex as _strhex
from .descriptors import DEVICES as _DESCRIPTORS
from .settings_templates import check_feature_settings as _check_feature_settings
from .base_usb import product_information as _product_information

_R = _hidpp10.REGISTERS

#
#
#

class PairedDevice(object):
	def __init__(self, receiver, number, link_notification=None):
		assert receiver
		self.receiver = receiver

		assert number > 0 and number <= receiver.max_devices
		# Device number, 1..6 for unifying devices, 1 otherwise.
		self.number = number
		# 'device active' flag; requires manual management.
		self.online = None

		# the Wireless PID is unique per device model
		self.wpid = None
		self.descriptor = None

		# mouse, keyboard, etc (see _hidpp10.DEVICE_KIND)
		self._kind = None
		# Unifying peripherals report a codename.
		self._codename = None
		# the full name of the model
		self._name = None
		# HID++ protocol version, 1.0 or 2.0
		self._protocol = None
		# serial number (an 8-char hex string)
		self._serial = None

		self._firmware = None
		self._keys = None
		self._registers = None
		self._settings = None

		# Misc stuff that's irrelevant to any functionality, but may be
		# displayed in the UI and caching it here helps.
		self._polling_rate = None
		self._power_switch = None

		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("new PairedDevice(%s, %s, %s)", receiver, number, link_notification)

		if link_notification is not None:
			self.online = not bool(ord(link_notification.data[0:1]) & 0x40)
			self.wpid = _strhex(link_notification.data[2:3] + link_notification.data[1:2])
			# assert link_notification.address == (0x04 if unifying else 0x03)
			kind = ord(link_notification.data[0:1]) & 0x0F
			self._kind = _hidpp10.DEVICE_KIND[kind]
		else:
			# force a reading of the wpid
			pair_info = receiver.read_register(_R.receiver_info, 0x20 + number - 1)
			if pair_info:
				# may be either a Unifying receiver, or an Unifying-ready receiver
				self.wpid = _strhex(pair_info[3:5])
				kind = ord(pair_info[7:8]) & 0x0F
				self._kind = _hidpp10.DEVICE_KIND[kind]
				self._polling_rate = ord(pair_info[2:3])

			else:
				# unifying protocol not supported, must be a Nano receiver
				device_info = self.receiver.read_register(_R.receiver_info, 0x04)
				if device_info is None:
					_log.error("failed to read Nano wpid for device %d of %s", number, receiver)
					raise _base.NoSuchDevice(number=number, receiver=receiver, error="read Nano wpid")

				self.wpid = _strhex(device_info[3:5])
				self._polling_rate = 0
				self._power_switch = '(' + _("unknown") + ')'

		# the wpid is necessary to properly identify wireless link on/off notifications
		# also it gets set to None on this object when the device is unpaired
		assert self.wpid is not None, "failed to read wpid: device %d of %s" % (number, receiver)

		self.descriptor = _DESCRIPTORS.get(self.wpid)
		if self.descriptor is None:
			# Last chance to correctly identify the device; many Nano receivers
			# do not support this call.
			codename = self.receiver.read_register(_R.receiver_info, 0x40 + self.number - 1)
			if codename:
				codename_length = ord(codename[1:2])
				codename = codename[2:2 + codename_length]
				self._codename = codename.decode('ascii')
				self.descriptor = _DESCRIPTORS.get(self._codename)

		if self.descriptor:
			self._name = self.descriptor.name
			self._protocol = self.descriptor.protocol
			if self._codename is None:
				self._codename = self.descriptor.codename
			if self._kind is None:
				self._kind = self.descriptor.kind

		if self._protocol is not None:
			self.features = None if self._protocol < 2.0 else _hidpp20.FeaturesArray(self)
		else:
			# may be a 2.0 device; if not, it will fix itself later
			self.features = _hidpp20.FeaturesArray(self)

	@property
	def protocol(self):
		if self._protocol is None and self.online is not False:
			self._protocol = _base.ping(self.receiver.handle, self.number)
			# if the ping failed, the peripheral is (almost) certainly offline
			self.online = self._protocol is not None

			# if _log.isEnabledFor(_DEBUG):
			# 	_log.debug("device %d protocol %s", self.number, self._protocol)
		return self._protocol or 0

	@property
	def codename(self):
		if self._codename is None:
			codename = self.receiver.read_register(_R.receiver_info, 0x40 + self.number - 1)
			if codename:
				codename_length = ord(codename[1:2])
				codename = codename[2:2 + codename_length]
				self._codename = codename.decode('ascii')
				# if _log.isEnabledFor(_DEBUG):
				#	 _log.debug("device %d codename %s", self.number, self._codename)
			else:
				self._codename = '? (%s)' % self.wpid
		return self._codename

	@property
	def name(self):
		if self._name is None:
			if self.online and self.protocol >= 2.0:
				self._name = _hidpp20.get_name(self)
		return self._name or self.codename  or ('Unknown device %s' % self.wpid)

	@property
	def kind(self):
		if self._kind is None:
			pair_info = self.receiver.read_register(_R.receiver_info, 0x20 + self.number - 1)
			if pair_info:
				kind = ord(pair_info[7:8]) & 0x0F
				self._kind = _hidpp10.DEVICE_KIND[kind]
				self._polling_rate = ord(pair_info[2:3])
			elif self.online and self.protocol >= 2.0:
				self._kind = _hidpp20.get_kind(self)
		return self._kind or '?'

	@property
	def firmware(self):
		if self._firmware is None and self.online:
			if self.protocol >= 2.0:
				self._firmware = _hidpp20.get_firmware(self)
			else:
				self._firmware = _hidpp10.get_firmware(self)
		return self._firmware or ()

	@property
	def serial(self):
		if self._serial is None:
			serial = self.receiver.read_register(_R.receiver_info, 0x30 + self.number - 1)
			if serial:
				ps = ord(serial[9:10]) & 0x0F
				self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps]
			else:
				# some Nano receivers?
				serial = self.receiver.read_register(0x2D5)

			if serial:
				self._serial = _strhex(serial[1:5])
			else:
				# fallback...
				self._serial = self.receiver.serial
		return self._serial or '?'

	@property
	def power_switch_location(self):
		if self._power_switch is None:
			ps = self.receiver.read_register(_R.receiver_info, 0x30 + self.number - 1)
			if ps is not None:
				ps = ord(ps[9:10]) & 0x0F
				self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps]
			else:
				self._power_switch = '(unknown)'
		return self._power_switch

	@property
	def polling_rate(self):
		if self._polling_rate is None:
			pair_info = self.receiver.read_register(_R.receiver_info, 0x20 + self.number - 1)
			if pair_info:
				self._polling_rate = ord(pair_info[2:3])
			else:
				self._polling_rate = 0
		return self._polling_rate

	@property
	def keys(self):
		if self._keys is None:
			if self.online and self.protocol >= 2.0:
				self._keys = _hidpp20.get_keys(self) or ()
		return self._keys

	@property
	def registers(self):
		if self._registers is None:
			if self.descriptor and self.descriptor.registers:
				self._registers = list(self.descriptor.registers)
			else:
				self._registers = []
		return self._registers

	@property
	def settings(self):
		if self._settings is None:
			if self.descriptor and self.descriptor.settings:
				self._settings = [s(self) for s in self.descriptor.settings]
			else:
				self._settings = []

		_check_feature_settings(self, self._settings)
		return self._settings

	def enable_notifications(self, enable=True):
		"""Enable or disable device (dis)connection notifications on this
		receiver."""
		if not bool(self.receiver) or self.protocol >= 2.0:
			return False

		if enable:
			set_flag_bits = ( _hidpp10.NOTIFICATION_FLAG.battery_status
							| _hidpp10.NOTIFICATION_FLAG.keyboard_illumination
							| _hidpp10.NOTIFICATION_FLAG.wireless
							| _hidpp10.NOTIFICATION_FLAG.software_present )
		else:
			set_flag_bits = 0
		ok = _hidpp10.set_notification_flags(self, set_flag_bits)
		if ok is None:
			_log.warn("%s: failed to %s device notifications", self, 'enable' if enable else 'disable')

		flag_bits = _hidpp10.get_notification_flags(self)
		flag_names = None if flag_bits is None else tuple(_hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits))
		if _log.isEnabledFor(_INFO):
			_log.info("%s: device notifications %s %s", self, 'enabled' if enable else 'disabled', flag_names)
		return flag_bits if ok else None

	def request(self, request_id, *params):
		return _base.request(self.receiver.handle, self.number, request_id, *params)

	read_register = _hidpp10.read_register
	write_register = _hidpp10.write_register

	def feature_request(self, feature, function=0x00, *params):
		if self.protocol >= 2.0:
			return _hidpp20.feature_request(self, feature, function, *params)

	def ping(self):
		"""Checks if the device is online, returns True of False"""
		protocol = _base.ping(self.receiver.handle, self.number)
		self.online = protocol is not None
		if protocol is not None:
			self._protocol = protocol
		return self.online

	def __index__(self):
		return self.number
	__int__ = __index__

	def __eq__(self, other):
		return other is not None and self.kind == other.kind and self.wpid == other.wpid

	def __ne__(self, other):
		return other is None or self.kind != other.kind or self.wpid != other.wpid

	def __hash__(self):
		return self.wpid.__hash__()

	__bool__ = __nonzero__ = lambda self: self.wpid is not None and self.number in self.receiver

	def __str__(self):
		return '<PairedDevice(%d,%s,%s,%s)>' % (self.number, self.wpid, self.codename or '?', self.serial)
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
		# USB product id, used for some Nano receivers
		self.product_id = device_info.product_id
		product_info = _product_information(self.product_id)
		if not product_info:
			raise Exception("Unknown receiver type", self.product_id)

		# read the serial immediately, so we can find out max_devices
		serial_reply = self.read_register(_R.receiver_info, 0x03)
		if serial_reply :
			self.serial = _strhex(serial_reply[1:5])
			self.max_devices = ord(serial_reply[6:7])
			# TODO _properly_ figure out which receivers do and which don't support unpairing
			# This code supposes that receivers that don't unpair support a pairing request for device index 0
			self.may_unpair = self.write_register(_R.receiver_pairing) is None
		else: # handle receivers that don't have a serial number specially (i.e., c534)
			self.serial = None
			self.max_devices = product_info.get('max_devices',1)
			self.may_unpair = product_info.get('may_unpair',False)

		self.name = product_info.get('name','')
		self.re_pairs = product_info.get('re_pairs',False)
		self._str = '<%s(%s,%s%s)>' % (self.name.replace(' ', ''), self.path, '' if isinstance(self.handle, int) else 'T', self.handle)

		self._firmware = None
		self._devices = {}
		self._remaining_pairings = None

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

	# how many pairings remain (None for unknown, -1 for unlimited)
	def remaining_pairings(self,cache=True):
		if self._remaining_pairings is None or not cache:
			ps = self.read_register(_R.receiver_connection)
			if ps is not None:
				ps = ord(ps[2:3])
				self._remaining_pairings = ps-5 if ps >= 5 else -1
		return self._remaining_pairings

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
		if ok is None:
			_log.warn("%s: failed to %s receiver notifications", self, 'enable' if enable else 'disable')
			return None

		flag_bits = _hidpp10.get_notification_flags(self)
		flag_names = None if flag_bits is None else tuple(_hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits))
		if _log.isEnabledFor(_INFO):
			_log.info("%s: receiver notifications %s => %s", self, 'enabled' if enable else 'disabled', flag_names)
		return flag_bits

	def notify_devices(self):
		"""Scan all devices."""
		if self.handle:
			if not self.write_register(_R.receiver_connection, 0x02):
				_log.warn("%s: failed to trigger device link notifications", self)

	def register_new_device(self, number, notification=None):
		if self._devices.get(number) is not None:
			raise IndexError("%s: device number %d already registered" % (self, number))

		assert notification is None or notification.devnumber == number
		assert notification is None or notification.sub_id == 0x41

		try:
			dev = PairedDevice(self, number, notification)
			assert dev.wpid
			if _log.isEnabledFor(_INFO):
				_log.info("%s: found new device %d (%s)", self, number, dev.wpid)
			self._devices[number] = dev
			return dev
		except _base.NoSuchDevice:
			_log.exception("register_new_device")

		_log.warning("%s: looked for device %d, not found", self, number)
		self._devices[number] = None

	def set_lock(self, lock_closed=True, device=0, timeout=0):
		if self.handle:
			action = 0x02 if lock_closed else 0x01
			reply = self.write_register(_R.receiver_pairing, action, device, timeout)
			if reply:
				return True
			_log.warn("%s: failed to %s the receiver lock", self, 'close' if lock_closed else 'open')

	def count(self):
		count = self.read_register(_R.receiver_connection)
		return 0 if count is None else ord(count[1:2])

	# def has_devices(self):
	# 	return len(self) > 0 or self.count() > 0

	def request(self, request_id, *params):
		if bool(self):
			return _base.request(self.handle, 0xFF, request_id, *params)

	read_register = _hidpp10.read_register
	write_register = _hidpp10.write_register

	def __iter__(self):
		for number in range(1, 1 + self.max_devices):
			if number in self._devices:
				dev = self._devices[number]
			else:
				dev = self.__getitem__(number)
			if dev is not None:
				yield dev

	def __getitem__(self, key):
		if not bool(self):
			return None

		dev = self._devices.get(key)
		if dev is not None:
			return dev

		if not isinstance(key, int):
			raise TypeError('key must be an integer')
		if key < 1 or key > self.max_devices:
			raise IndexError(key)

		return self.register_new_device(key)

	def __delitem__(self, key):
		self._unpair_device(key, False)

	def _unpair_device(self, key, force=False):
		key = int(key)

		if self._devices.get(key) is None:
			raise IndexError(key)

		dev = self._devices[key]
		if not dev:
			if key in self._devices:
				del self._devices[key]
			return

		if self.re_pairs and not force:
			# invalidate the device, but these receivers don't unpair per se
			dev.online = False
			dev.wpid = None
			if key in self._devices:
				del self._devices[key]
			_log.warn("%s removed device %s", self, dev)
		else:
			reply = self.write_register(_R.receiver_pairing, 0x03, key)
			if reply:
				# invalidate the device
				dev.online = False
				dev.wpid = None
				if key in self._devices:
					del self._devices[key]
				_log.warn("%s unpaired device %s", self, dev)
			else:
				_log.error("%s failed to unpair device %s", self, dev)
				raise IndexError(key)

	def __len__(self):
		return len([d for d in self._devices.values() if d is not None])

	def __contains__(self, dev):
		if isinstance(dev, int):
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
