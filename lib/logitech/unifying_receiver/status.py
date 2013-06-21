#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from time import time as _timestamp
from weakref import proxy as _proxy

from struct import unpack as _unpack
try:
	unicode
	# if Python2, unicode_literals will mess our first (un)pack() argument
	_unpack_str = _unpack
	_unpack = lambda x, *args: _unpack_str(str(x), *args)
except:
	pass

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR.status')
del getLogger

from .common import NamedInts as _NamedInts, strhex as _strhex
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20

#
#
#

ALERT = _NamedInts(NONE=0x00, NOTIFICATION=0x01, SHOW_WINDOW=0x02, ATTENTION=0x04, ALL=0xFF)

KEYS = _NamedInts(
				BATTERY_LEVEL=1,
				BATTERY_CHARGING=2,
				BATTERY_STATUS=3,
				LIGHT_LEVEL=4,
				LINK_ENCRYPTED=5,
				NOTIFICATION_FLAGS=6,
				ERROR=7,
			)

# If the battery charge is under this percentage, trigger an attention event
# (blink systray icon/notification/whatever).
_BATTERY_ATTENTION_LEVEL = 5

# If no updates have been receiver from the device for a while, ping the device
# and update it status accordinly.
_STATUS_TIMEOUT = 5 * 60  # seconds

#
#
#

class ReceiverStatus(dict):
	"""The 'runtime' status of a receiver, mostly about the pairing process --
	is the pairing lock open or closed, any pairing errors, etc.
	"""
	def __init__(self, receiver, changed_callback):
		assert receiver
		self._receiver = _proxy(receiver)

		assert changed_callback
		self._changed_callback = changed_callback

		# self.updated = 0

		self.lock_open = False
		self.new_device = None

		self[KEYS.ERROR] = None
		# self[KEYS.NOTIFICATION_FLAGS] = receiver.enable_notifications()

	def __str__(self):
		count = len(self._receiver)
		return ('No paired devices.' if count == 0 else
				'1 paired device.' if count == 1 else
				'%d paired devices.' % count)
	__unicode__ = __str__

	def _changed(self, alert=ALERT.NOTIFICATION, reason=None):
		# self.updated = _timestamp()
		self._changed_callback(self._receiver, alert=alert, reason=reason)

	def poll(self, timestamp):
		r = self._receiver
		assert r

		if _log.isEnabledFor(_DEBUG):
			_log.debug("polling status of %s", r)

		# make sure to read some stuff that may be read later by the UI
		r.serial, r.firmware, None

		# get an update of the notification flags
		# self[KEYS.NOTIFICATION_FLAGS] = _hidpp10.get_notification_flags(r)

	def process_notification(self, n):
		if n.sub_id == 0x4A:
			self.lock_open = bool(n.address & 0x01)
			reason = 'pairing lock is ' + ('open' if self.lock_open else 'closed')
			_log.info("%s: %s", self._receiver, reason)

			self[KEYS.ERROR] = None
			if self.lock_open:
				self.new_device = None

			pair_error = ord(n.data[:1])
			if pair_error:
				self[KEYS.ERROR] = error_string = _hidpp10.PAIRING_ERRORS[pair_error]
				self.new_device = None
				_log.warn("pairing error %d: %s", pair_error, error_string)

			self._changed(reason=reason)
			return True

#
#
#

class DeviceStatus(dict):
	"""Holds the 'runtime' status of a peripheral -- things like
	active/inactive, battery charge, lux, etc. It updates them mostly by
	processing incoming notification events from the device itself.
	"""
	def __init__(self, device, changed_callback):
		assert device
		self._device = _proxy(device)

		assert changed_callback
		self._changed_callback = changed_callback

		# is the device active?
		self._active = None

		# timestamp of when this status object was last updated
		self.updated = 0

		# optional object able to persist device settings
		self.configuration = None

	def __str__(self):
		def _item(name, format):
			value = self.get(name)
			if value is not None:
				return format % value

		def _items():
			battery_level = _item(KEYS.BATTERY_LEVEL, 'Battery: %d%%')
			if battery_level:
				yield battery_level
				battery_status = _item(KEYS.BATTERY_STATUS, ' (%s)')
				if battery_status:
					yield battery_status

			light_level = _item(KEYS.LIGHT_LEVEL, 'Light: %d lux')
			if light_level:
				if battery_level:
					yield ', '
				yield light_level

		return ''.join(i for i in _items())

	__unicode__ = __str__

	def __bool__(self):
		return bool(self._active)
	__nonzero__ = __bool__

	def set_battery_info(self, level, status, timestamp=None):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("%s: battery %d%%, %s", self._device, level, status)

		# TODO: this is also executed when pressing Fn+F7 on K800.
		old_level, self[KEYS.BATTERY_LEVEL] = self.get(KEYS.BATTERY_LEVEL), level
		old_status, self[KEYS.BATTERY_STATUS] = self.get(KEYS.BATTERY_STATUS), status

		charging = status in ('charging', 'recharging', 'slow recharge')
		old_charging, self[KEYS.BATTERY_CHARGING] = self.get(KEYS.BATTERY_CHARGING), charging

		changed = old_level != level or old_status != status or old_charging != charging
		alert, reason = ALERT.NONE, None

		if not _hidpp20.BATTERY_OK(status) or level <= _BATTERY_ATTENTION_LEVEL:
			_log.warn("%s: battery %d%%, ALERT %s", self._device, level, status)
			alert = ALERT.NOTIFICATION | ALERT.ATTENTION
			reason = 'Battery: %d%% (%s)' % (level, status)

		if changed or reason:
			self._changed(alert=alert, reason=reason, timestamp=timestamp)

	def read_battery(self, timestamp=None):
		if self._active:
			d = self._device
			assert d

			if d.protocol < 2.0:
				battery = _hidpp10.get_battery(d)
			else:
				battery = _hidpp20.get_battery(d)

			# Really unnecessary, if the device has SOLAR_DASHBOARD it should be
			# broadcasting it's battery status anyway, it will just take a little while.
			# However, when the device has just been detected, it will not show
			# any battery status for a while (broadcasts happen every 90 seconds).
			if battery is None and _hidpp20.FEATURE.SOLAR_DASHBOARD in d.features:
				d.feature_request(_hidpp20.FEATURE.SOLAR_DASHBOARD, 0x00, 1, 1)
				return

			if battery is not None:
				level, status = battery
				self.set_battery_info(level, status)
			elif KEYS.BATTERY_STATUS in self:
				self[KEYS.BATTERY_STATUS] = None
				self[KEYS.BATTERY_CHARGING] = None
				self._changed()

	def _changed(self, active=None, alert=ALERT.NONE, reason=None, timestamp=None):
		assert self._changed_callback
		d = self._device
		# assert d  # may be invalid when processing the 'unpaired' notification

		if active is not None:
			d.online = active
			was_active, self._active = self._active, active
			if active:
				if not was_active:
					# Make sure to set notification flags on the device, they
					# get cleared when the device is turned off (but not when the device
					# goes idle, and we can't tell the difference right now).
					self[KEYS.NOTIFICATION_FLAGS] = d.enable_notifications()
					if self.configuration:
						self.configuration.attach_to(d)
			else:
				if was_active:
					battery = self.get(KEYS.BATTERY_LEVEL)
					self.clear()
					# If we had a known battery level before, assume it's not going
					# to change much while the device is offline.
					if battery is not None:
						self[KEYS.BATTERY_LEVEL] = battery

		if self.updated == 0 and active == True:
			# if the device is active on the very first status notification,
			# (meaning just when the program started or a new receiver was just
			# detected), pop-up a notification about it
			alert |= ALERT.NOTIFICATION
		self.updated = timestamp or _timestamp()

		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("device %d changed: active=%s %s", self._device.number, self._active, dict(self))
		self._changed_callback(d, alert, reason)

	def poll(self, timestamp):
		d = self._device
		if not d:
			_log.error("polling status of invalid device")
			return

		if self._active:
			if _log.isEnabledFor(_DEBUG):
				_log.debug("polling status of %s", d)

			# read these from the device, the UI may need them later
			d.protocol, d.firmware, d.kind, d.name, d.settings, None

			# make sure we know all the features of the device
			# if d.features:
			# 	d.features[:]

			# devices may go out-of-range while still active, or the computer
			# may go to sleep and wake up without the devices available
			if timestamp - self.updated > _STATUS_TIMEOUT:
				if d.ping():
					timestamp = self.updated = _timestamp()
				else:
					self._changed(active=False, reason='out of range')

			# if still active, make sure we know the battery level
			if KEYS.BATTERY_LEVEL not in self:
				self.read_battery(timestamp)

		elif timestamp - self.updated > _STATUS_TIMEOUT:
			if d.ping():
				self._changed(active=True)
			else:
				self.updated = _timestamp()

	def process_notification(self, n):
		# incoming packets with SubId >= 0x80 are supposedly replies from
		# HID++ 1.0 requests, should never get here
		assert n.sub_id < 0x80

		# 0x40 to 0x7F appear to be HID++ 1.0 notifications
		if n.sub_id >= 0x40:
			return self._process_hidpp10_notification(n)

		# some custom battery events for HID++ 1.0 devices
		if self._device.protocol < 2.0:
			# README assuming HID++ 2.0 devices don't use the 0x07/0x0D registers
			# however, this has not been fully verified yet
			if n.sub_id in (0x07, 0x0D) and len(n.data) == 3 and n.data[2:3] == b'\x00':
				return self._process_hidpp10_custom_notification(n)
		else:
			# assuming 0x00 to 0x3F are feature (HID++ 2.0) notifications
			try:
				feature = self._device.features[n.sub_id]
			except IndexError:
				_log.warn("%s: notification from invalid feature index %02X: %s", self._device, n.sub_id, n)
				return False

			return self._process_feature_notification(n, feature)

	def _process_hidpp10_custom_notification(self, n):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("%s (%s) custom battery notification %s", self._device, self._device.protocol, n)

		if n.sub_id == 0x07:
			# message layout: 10 ix  07("address")  <LEVEL> <STATUS>  00 00
			level, status = _hidpp10.parse_battery_reply_07(n.address, ord(n.data[:1]))
			self.set_battery_info(level, status)
			return True

		if n.sub_id == 0x0D:
			# message layout: 10 ix  0D("address")  <CHARGE> <?> <STATUS> 00
			level, status = _hidpp10.parse_battery_reply_0D(n.address, ord(n.data[1:2]))
			self.set_battery_info(level, status)
			return True

		_log.warn("%s: unrecognized %s", self._device, n)

	def _process_hidpp10_notification(self, n):
		# unpair notification
		if n.sub_id == 0x40:
			if n.address == 0x02:
				# device un-paired
				self.clear()
				dev = self._device
				dev.wpid = None
				dev.status = None
				self._changed(active=False, alert=ALERT.ALL, reason='unpaired')
			else:
				_log.warn("%s: disconnection with unknown type %02X: %s", self._device, n.address, n)
			return True

		# wireless link notification
		if n.sub_id == 0x41:
			protocol_name = ('unifying (eQuad DJ)' if n.address == 0x04
						else 'eQuad' if n.address == 0x03
						else None)
			if protocol_name:
				if _log.isEnabledFor(_DEBUG):
					wpid = _strhex(n.data[2:3] + n.data[1:2])
					assert wpid == self._device.wpid, "%s wpid mismatch, got %s" % (self._device, wpid)

				flags = ord(n.data[:1]) & 0xF0
				link_encrypyed = bool(flags & 0x20)
				link_established = not (flags & 0x40)
				if _log.isEnabledFor(_DEBUG):
					sw_present = bool(flags & 0x10)
					has_payload = bool(flags & 0x80)
					_log.debug("%s: %s connection notification: software=%s, encrypted=%s, link=%s, payload=%s",
								self._device, protocol_name, sw_present, link_encrypyed, link_established, has_payload)
				self[KEYS.LINK_ENCRYPTED] = link_encrypyed
				self._changed(active=link_established)
			else:
				_log.warn("%s: connection notification with unknown protocol %02X: %s", self._device.number, n.address, n)

			return True

		if n.sub_id == 0x49:
			# raw input event? just ignore it
			# if n.address == 0x01, no idea what it is, but they keep on coming
			# if n.address == 0x03, it's an actual input event
			return True

		# power notification
		if n.sub_id == 0x4B:
			if n.address == 0x01:
				if _log.isEnabledFor(_DEBUG):
					_log.debug("%s: device powered on", self._device)
				reason = str(self) or 'powered on'
				self._changed(active=True, alert=ALERT.NOTIFICATION, reason=reason)
			else:
				_log.info("%s: unknown %s", self._device, n)
			return True

		_log.warn("%s: unrecognized %s", self._device, n)

	def _process_feature_notification(self, n, feature):
		if feature == _hidpp20.FEATURE.BATTERY_STATUS:
			if n.address == 0x00:
				discharge = ord(n.data[:1])
				battery_status = ord(n.data[1:2])
				self.set_battery_info(discharge, _hidpp20.BATTERY_STATUS[battery_status])
			else:
				_log.info("%s: unknown BATTERY %s", self._device, n)
			return True

		# TODO: what are REPROG_CONTROLS_V{2,3}?
		if feature == _hidpp20.FEATURE.REPROG_CONTROLS:
			if n.address == 0x00:
				_log.info("%s: reprogrammable key: %s", self._device, n)
			else:
				_log.info("%s: unknown REPROGRAMMABLE KEYS %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.WIRELESS_DEVICE_STATUS:
			if n.address == 0x00:
				if _log.isEnabledFor(_DEBUG):
					_log.debug("wireless status: %s", n)
				if n.data[0:3] == b'\x01\x01\x01':
					self._changed(active=True, alert=ALERT.NOTIFICATION, reason='powered on')
				else:
					_log.info("%s: unknown WIRELESS %s", self._device, n)
			else:
				_log.info("%s: unknown WIRELESS %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.SOLAR_DASHBOARD:
			if n.data[5:9] == b'GOOD':
				charge, lux, adc = _unpack('!BHH', n.data[:5])
				self[KEYS.BATTERY_LEVEL] = charge
				# guesstimate the battery voltage, emphasis on 'guess'
				self[KEYS.BATTERY_STATUS] = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
				if n.address == 0x00:
					self[KEYS.LIGHT_LEVEL] = None
					self[KEYS.BATTERY_CHARGING] = None
					self._changed(active=True)
				elif n.address == 0x10:
					self[KEYS.LIGHT_LEVEL] = lux
					self[KEYS.BATTERY_CHARGING] = lux > 200
					self._changed(active=True)
				elif n.address == 0x20:
					_log.debug("%s: Light Check button pressed", self._device)
					self._changed(alert=ALERT.SHOW_WINDOW)
					# first cancel any reporting
					# self._device.feature_request(_hidpp20.FEATURE.SOLAR_DASHBOARD)
					# trigger a new report chain
					reports_count = 15
					reports_period = 2  # seconds
					self._device.feature_request(_hidpp20.FEATURE.SOLAR_DASHBOARD, 0x00, reports_count, reports_period)
				else:
					_log.info("%s: unknown SOLAR CHAGE %s", self._device, n)
			else:
				_log.warn("%s: SOLAR CHARGE not GOOD? %s", self._device, n)
			return True

		if feature == _hidpp20.FEATURE.TOUCHMOUSE_RAW_POINTS:
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
