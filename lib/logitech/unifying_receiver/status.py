#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from time import time as _timestamp
from struct import unpack as _unpack
from weakref import proxy as _proxy

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR.status')
del getLogger

from .common import NamedInts as _NamedInts, strhex as _strhex
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20

#
#
#

ALERT = _NamedInts(NONE=0x00, LOW=0x01, MED=0x02, HIGH=0xFF)

# device properties that may be reported
ENCRYPTED='encrypted'
BATTERY_LEVEL='battery-level'
BATTERY_STATUS='battery-status'
LIGHT_LEVEL='light-level'
ERROR='error'

# if not updates have been receiver from the device for a while, assume
# it has gone offline and clear all its know properties.
_STATUS_TIMEOUT = 120  # seconds

#
#
#

class ReceiverStatus(dict):
	def __init__(self, receiver, changed_callback):
		assert receiver
		self._receiver = _proxy(receiver)

		assert changed_callback
		self._changed_callback = changed_callback

		# self.updated = 0

		self.lock_open = False
		self.new_device = None
		self[ERROR] = None

	def __str__(self):
		count = len(self._receiver)
		return ('No devices found.' if count == 0 else
				'1 device found.' if count == 1 else
				'%d devices found.' % count)
	__unicode__ = __str__

	def _changed(self, alert=ALERT.LOW, reason=None):
		# self.updated = _timestamp()
		self._changed_callback(self._receiver, alert=alert, reason=reason)

	def process_notification(self, n):
		if n.sub_id == 0x4A:
			self.lock_open = bool(n.address & 0x01)
			reason = 'pairing lock is ' + ('open' if self.lock_open else 'closed')
			_log.info("%s: %s", self._receiver, reason)
			if self.lock_open:
				self[ERROR] = None
				self.new_device = None

			pair_error = ord(n.data[:1])
			if pair_error:
				self[ERROR] = _hidpp10.PAIRING_ERRORS[pair_error]
				self.new_device = None
				_log.warn("pairing error %d: %s", pair_error, self[ERROR])
			else:
				self[ERROR] = None

			self._changed(reason=reason)
			return True

#
#
#

class DeviceStatus(dict):
	def __init__(self, device, changed_callback):
		assert device
		self._device = _proxy(device)

		assert changed_callback
		self._changed_callback = changed_callback

		self._active = None
		self.updated = 0

	def __str__(self):
		def _item(name, format):
			value = self.get(name)
			if value is not None:
				return format % value

		def _items():
			battery_level = _item(BATTERY_LEVEL, 'Battery: %d%%')
			if battery_level:
				yield battery_level
				battery_status = _item(BATTERY_STATUS, ' <small>(%s)</small>')
				if battery_status:
					yield battery_status

			light_level = _item(LIGHT_LEVEL, 'Light: %d lux')
			if light_level:
				if battery_level:
					yield ', '
				yield light_level

		return ''.join(i for i in _items())

	__unicode__ = __str__

	def __bool__(self):
		return bool(self._active)
	__nonzero__ = __bool__

	def _changed(self, active=True, alert=ALERT.NONE, reason=None, timestamp=None):
		assert self._changed_callback
		self._active = active
		if not active:
			battery = self.get(BATTERY_LEVEL)
			self.clear()
			if battery is not None:
				self[BATTERY_LEVEL] = battery
		if self.updated == 0:
			alert |= ALERT.LOW
		self.updated = timestamp or _timestamp()
		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("device %d changed: active=%s %s", self._device.number, self._active, dict(self))
		self._changed_callback(self._device, alert, reason)

	def poll(self, timestamp):
		if self._active:
			d = self._device
			if not d:
				_log.error("polling status of invalid device")
				return

			# read these from the device in case they haven't been read already
			d.protocol, d.serial, d.firmware

			if BATTERY_LEVEL not in self:
				battery = _hidpp10.get_battery(d)
				if battery is None and d.protocol >= 2.0:
					battery = _hidpp20.get_battery(d)

					# really unnecessary, if the device has SOLAR_CHARGE it should be
					# broadcasting it's battery status anyway, it will just take a little while
					# if battery is None and _hidpp20.FEATURE.SOLAR_CHARGE in d.features:
					# 	d.feature_request(_hidpp20.FEATURE.SOLAR_CHARGE, 0x00, 1, 1)
					# 	return

				if battery:
					self[BATTERY_LEVEL], self[BATTERY_STATUS] = battery
					self._changed(timestamp=timestamp)
				elif BATTERY_STATUS in self:
					self[BATTERY_STATUS] = None
					self._changed(timestamp=timestamp)

			# make sure we know all the features of the device
			if d.features:
				d.features[:]

		elif len(self) > 0 and timestamp - self.updated > _STATUS_TIMEOUT:
			# if the device has been inactive for too long, clear out any known
			# properties, they are most likely obsolete anyway
			self.clear()
			self._changed(active=False, timestamp=timestamp)

	def process_notification(self, n):
		# incoming packets with SubId >= 0x80 are supposedly replies from
		# HID++ 1.0 requests, should never get here
		assert n.sub_id < 0x80

		# 0x40 to 0x7F appear to be HID++ 1.0 notifications
		if n.sub_id >= 0x40:
			return self._process_hidpp10_notification(n)

		# assuming 0x00 to 0x3F are feature (HID++ 2.0) notifications
		try:
			feature = self._device.features[n.sub_id]
		except IndexError:
			_log.warn("%s: notification from invalid feature index %02X: %s", self._device, n.sub_id, n)
			return False

		return self._process_feature_notification(n, feature)

	def _process_hidpp10_notification(self, n):
		if n.sub_id == 0x40:
			if n.address == 0x02:
				# device un-paired
				self.clear()
				self._device.status = None
				self._changed(False, ALERT.HIGH, 'unpaired')
			else:
				_log.warn("%s: disconnection with unknown type %02X: %s", self._device, n.address, n)
			return True

		if n.sub_id == 0x41:
			if n.address == 0x04:  # unifying protocol
				# wpid = _strhex(n.data[4:5] + n.data[3:4])
				# assert wpid == device.wpid

				flags = ord(n.data[:1]) & 0xF0
				link_encrypyed = bool(flags & 0x20)
				link_established = not (flags & 0x40)
				if _log.isEnabledFor(_DEBUG):
					sw_present = bool(flags & 0x10)
					has_payload = bool(flags & 0x80)
					_log.debug("%s: connection notification: software=%s, encrypted=%s, link=%s, payload=%s",
								self._device, sw_present, link_encrypyed, link_established, has_payload)
				self[ENCRYPTED] = link_encrypyed
				self._changed(link_established)

			elif n.address == 0x03:  # eQuad protocol
				# Nano devices might not have been initialized fully
				if self._device._kind is None:
					kind = ord(n.data[:1]) & 0x0F
					self._device._kind = _hidpp10.DEVICE_KIND[kind]
				if self._device._wpid is None:
					self._device._wpid = _strhex(n.data[2:3] + n.data[1:2])

				flags = ord(n.data[:1]) & 0xF0
				link_encrypyed = bool(flags & 0x20)
				link_established = not (flags & 0x40)
				if _log.isEnabledFor(_DEBUG):
					sw_present = bool(flags & 0x10)
					has_payload = bool(flags & 0x80)
					_log.debug("%s: eQuad connection notification: software=%s, encrypted=%s, link=%s, payload=%s",
								self._device, sw_present, link_encrypyed, link_established, has_payload)
				self[ENCRYPTED] = link_encrypyed
				self._changed(link_established)

			else:
				_log.warn("%s: connection notification with unknown protocol %02X: %s", self._device.number, n.address, n)

			return True

		if n.sub_id == 0x49:
			# raw input event? just ignore it
			# if n.address == 0x01, no idea what it is, but they keep on coming
			# if n.address == 0x03, it's an actual input event
			return True

		if n.sub_id == 0x4B:
			if n.address == 0x01:
				if _log.isEnabledFor(_DEBUG):
					_log.debug("%s: device powered on", self._device)
				self._changed(alert=ALERT.LOW, reason='powered on')
			else:
				_log.info("%s: unknown %s", self._device, n)
			return True

		_log.warn("%s: unrecognized %s", self._device, n)

	def _process_feature_notification(self, n, feature):
		if feature == _hidpp20.FEATURE.BATTERY:
			if n.address == 0x00:
				discharge = ord(n.data[:1])
				battery_status = ord(n.data[1:2])
				self[BATTERY_LEVEL] = discharge
				self[BATTERY_STATUS] = BATTERY_STATUS[battery_status]
				if _hidpp20.BATTERY_OK(battery_status):
					alert = ALERT.NONE
					reason = self[ERROR] = None
					if _log.isEnabledFor(_DEBUG):
						_log.debug("%s: battery %d% charged, %s", self._device, discharge, self[BATTERY_STATUS])
				else:
					alert = ALERT.MED
					reason = self[ERROR] = self[BATTERY_STATUS]
					_log.warn("%s: battery %d% charged, ALERT %s", self._device, discharge, reason)
				self._changed(alert=alert, reason=reason)
			else:
				_log.info("%s: unknown BATTERY %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.REPROGRAMMABLE_KEYS:
			if n.address == 0x00:
				_log.info("%s: reprogrammable key: %s", self._device, n)
			else:
				_log.info("%s: unknown REPROGRAMMABLE KEYS %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.WIRELESS:
			if n.address == 0x00:
				if _log.isEnabledFor(_DEBUG):
					_log.debug("wireless status: %s", n)
				if n.data[0:3] == b'\x01\x01\x01':
					self._changed(alert=ALERT.LOW, reason='powered on')
				else:
					_log.info("%s: unknown WIRELESS %s", self._device, n)
			else:
				_log.info("%s: unknown WIRELESS %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.SOLAR_CHARGE:
			if n.data[5:9] == b'GOOD':
				charge, lux, adc = _unpack(b'!BHH', n.data[:5])
				self[BATTERY_LEVEL] = charge
				# guesstimate the battery voltage, emphasis on 'guess'
				self[BATTERY_STATUS] = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
				if n.address == 0x00:
					self[LIGHT_LEVEL] = None
					self._changed()
				elif n.address == 0x10:
					self[LIGHT_LEVEL] = lux
					if lux > 200:  # guesstimate
						self[BATTERY_STATUS] += ', charging'
					self._changed()
				elif n.address == 0x20:
					_log.debug("%s: Solar key pressed", self._device)
					self._changed(alert=ALERT.MED)
					# first cancel any reporting
					self._device.feature_request(_hidpp20.FEATURE.SOLAR_CHARGE)
					# trigger a new report chain
					reports_count = 15
					reports_period = 2  # seconds
					self._device.feature_request(_hidpp20.FEATURE.SOLAR_CHARGE, 0x00, reports_count, reports_period)
				else:
					_log.info("%s: unknown SOLAR CHAGE %s", self._device, n)
			else:
				_log.warn("%s: SOLAR CHARGE not GOOD? %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.TOUCH_MOUSE:
			if n.address == 0x00:
				_log.info("%s: TOUCH MOUSE points %s", self._device, n)
			elif n.address == 0x10:
				touch = ord(n.data[:1])
				button_down = bool(touch & 0x02)
				mouse_lifted = bool(touch & 0x01)
				_log.info("%s: TOUCH MOUSE status: button_down=%s mouse_lifted=%s", self._device, button_down, mouse_lifted)
			else:
				_log.info("%s: unknown TOUCH MOUSE %s", self._device, n)
			return True

		_log.info("%s: unrecognized %s for feature %s (index %02X)", self._device, n, feature, n.sub_id)
