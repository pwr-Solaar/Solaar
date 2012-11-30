#
#
#

from time import time as _timestamp
from struct import unpack as _unpack

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR.status')
del getLogger

from .common import NamedInts as _NamedInts
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

#
#
#

class ReceiverStatus(dict):
	def __init__(self, receiver, changed_callback):
		assert receiver
		self._receiver = receiver

		assert changed_callback
		self._changed_callback = changed_callback

		# self.updated = 0

		self.lock_open = False
		self.new_device = None
		self[ERROR] = None

	def __str__(self):
		count = len([1 for d in self._receiver if d is not None])
		return ('No devices found.' if count == 0 else
				'1 device found.' if count == 1 else
				'%d devices found.' % count)

	def _changed(self, alert=ALERT.LOW, reason=None):
		# self.updated = _timestamp()
		self._changed_callback(self._receiver, alert=alert, reason=reason)

	def process_event(self, event):
		if event.sub_id == 0x4A:
			self.lock_open = bool(event.address & 0x01)
			reason = 'pairing lock is ' + ('open' if self.lock_open else 'closed')
			_log.info("%s: %s", self._receiver, reason)
			if self.lock_open:
				self[ERROR] = None
				self.new_device = None

			pair_error = ord(event.data[:1])
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
		self._device = device

		assert changed_callback
		self._changed_callback = changed_callback

		self._active = None
		self.updated = 0

	def __str__(self):
		t = []
		if self.get(BATTERY_LEVEL) is not None:
			b = 'Battery: %d%%' % self[BATTERY_LEVEL]
			if self.get(BATTERY_STATUS):
				b += ' (' + self[BATTERY_STATUS] + ')'
			t.append(b)
		if self.get(LIGHT_LEVEL) is not None:
			t.append('Light: %d lux' % self[LIGHT_LEVEL])
		return ', '.join(t)

	def __bool__(self):
		return self.updated and self._active
	__nonzero__ = __bool__

	def _changed(self, active=True, alert=ALERT.NONE, reason=None):
		assert self._changed_callback
		self._active = active
		if not active:
			battery = self.get(BATTERY_LEVEL)
			self.clear()
			if battery is not None:
				self[BATTERY_LEVEL] = battery
		if self.updated == 0:
			alert |= ALERT.LOW
		self.updated = _timestamp()
		# if _log.isEnabledFor(_DEBUG):
		# 	_log.debug("device %d changed: active=%s %s", self._device.number, self._active, dict(self))
		self._changed_callback(self._device, alert, reason)

	# @property
	# def battery(self):
	# 	battery = _hidpp10.get_battery_level(self)
	# 	if battery is None:
	# 		battery = _hidpp20.get_battery_level(self)
	# 	return battery

	def process_event(self, event):
		if event.sub_id == 0x40:
			if event.address == 0x02:
				# device un-paired
				self.clear()
				self._device.status = None
				self._changed(False, ALERT.HIGH, 'unpaired')
				self._device = None
			else:
				_log.warn("device %d disconnection notification %s with unknown type %02X", self._device.number, event, event.address)
			return True

		if event.sub_id == 0x41:
			if event.address == 0x04:  # unifying protocol
				# wpid = _strhex(event.data[4:5] + event.data[3:4])
				# assert wpid == device.wpid

				flags = ord(event.data[:1]) & 0xF0
				link_encrypyed = bool(flags & 0x20)
				link_established = not (flags & 0x40)
				if _log.isEnabledFor(_DEBUG):
					sw_present = bool(flags & 0x10)
					has_payload = bool(flags & 0x80)
					_log.debug("device %d connection notification: software=%s, encrypted=%s, link=%s, payload=%s",
								self._device.number, sw_present, link_encrypyed, link_established, has_payload)
				self[ENCRYPTED] = link_encrypyed
				self._changed(link_established)

			elif event.address == 0x03:
				_log.warn("device %d connection notification %s with eQuad protocol, ignored", self._device.number, event)

			else:
				_log.warn("device %d connection notification %s with unknown protocol %02X", self._device.number, event, event.address)

			return True

		if event.sub_id >= 0x40:
			# this can't possibly be an event, can it?
			if _log.isEnabledFor(_DEBUG):
				_log.debug("ignoring non-event %s", event)
			return False

		# this must be a feature event, assuming no device has more than 0x40 features
		if event.sub_id >= len(self._device.features):
			_log.warn("device %d got event from unknown feature index %02X", self._device.number, event.sub_id)
			return False

		feature = self._device.features[event.sub_id]

		if feature == _hidpp20.FEATURE.BATTERY:
			if event.address == 0x00:
				discharge = ord(event.data[:1])
				battery_status = ord(event.data[1:2])
				self[BATTERY_LEVEL] = discharge
				self[BATTERY_STATUS] = BATTERY_STATUS[battery_status]
				if _hidpp20.BATTERY_OK(battery_status):
					alert = ALERT.NONE
					reason = self[ERROR] = None
				else:
					alert = ALERT.MED
					reason = self[ERROR] = self[BATTERY_STATUS]
				self._changed(alert=alert, reason=reason)
			else:
				_log.warn("don't know how to handle BATTERY event %s", event)
			return True

		if feature == _hidpp20.FEATURE.REPROGRAMMABLE_KEYS:
			if event.address == 0x00:
				_log.debug('reprogrammable key: %s', event)
			else:
				_log.warn("don't know how to handle REPROGRAMMABLE KEYS event %s", event)
			return True

		if feature == _hidpp20.FEATURE.WIRELESS:
			if event.address == 0x00:
				_log.debug("wireless status: %s", event)
				if event.data[0:3] == b'\x01\x01\x01':
					self._changed(alert=ALERT.LOW, reason='powered on')
			else:
				_log.warn("don't know how to handle WIRELESS event %s", event)
			return True

		if feature == _hidpp20.FEATURE.SOLAR_CHARGE:
			if event.data[5:9] == b'GOOD':
				charge, lux, adc = _unpack('!BHH', event.data[:5])
				self[BATTERY_LEVEL] = charge
				# guesstimate the battery voltage, emphasis on 'guess'
				self[BATTERY_STATUS] = '%1.2fV' % (adc * 2.67793237653 / 0x0672)
				if event.address == 0x00:
					self[LIGHT_LEVEL] = None
					self._changed()
				elif event.address == 0x10:
					self[LIGHT_LEVEL] = lux
					if lux > 200:  # guesstimate
						self[BATTERY_STATUS] += ', charging'
					self._changed()
				elif event.address == 0x20:
					_log.debug("Solar key pressed")
					# first cancel any reporting
					self._device.feature_request(_hidpp20.FEATURE.SOLAR_CHARGE)
					reports_count = 10
					reports_period = 3  # seconds
					self._changed(alert=ALERT.MED)
					# trigger a new report chain
					self._device.feature_request(_hidpp20.FEATURE.SOLAR_CHARGE, 0x00, reports_count, reports_period)
				else:
					self._changed()
			else:
				_log.warn("SOLAR_CHARGE event not GOOD? %s", event)
			return True

		if feature == _hidpp20.FEATURE.TOUCH_MOUSE:
			if event.address == 0x00:
				_log.debug("TOUCH MOUSE points event: %s", event)
			elif event.address == 0x10:
				touch = ord(event.data[:1])
				button_down = bool(touch & 0x02)
				mouse_lifted = bool(touch & 0x01)
				_log.debug("TOUCH MOUSE status: button_down=%s mouse_lifted=%s", button_down, mouse_lifted)
			return True

		_log.warn("don't know how to handle event %s for feature %s", event, feature)
