#
#
#

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('listener')
del getLogger

from types import MethodType as _MethodType

from logitech.unifying_receiver import (Receiver,
										listener as _listener,
										hidpp10 as _hidpp10,
										hidpp20 as _hidpp20,
										status as _status)

#
#
#

class _DUMMY_RECEIVER(object):
	# __slots__ = ['name', 'max_devices', 'status']
	__slots__ = []
	name = Receiver.name
	kind = None
	max_devices = Receiver.max_devices
	status = 'Receiver not found.'
	__bool__ = __nonzero__ = lambda self: False
	__str__ = lambda self: 'DUMMY'
DUMMY = _DUMMY_RECEIVER()

#
#
#

_DEVICE_STATUS_POLL = 30  # seconds
_DEVICE_TIMEOUT = 2 * _DEVICE_STATUS_POLL  # seconds


class ReceiverListener(_listener.EventsListener):
	"""Keeps the status of a Unifying Receiver.
	"""
	def __init__(self, receiver, status_changed_callback=None):
		super(ReceiverListener, self).__init__(receiver, self._events_handler)
		self.tick_period = _DEVICE_STATUS_POLL
		self._last_tick = 0

		self.status_changed_callback = status_changed_callback

		receiver.status = _status.ReceiverStatus(receiver, self._status_changed)

		# enhance the original register_new_device
		def _register_with_status(r, number):
			if bool(self):
				dev = r.__register_new_device(number)
				if dev is not None:
					# read these as soon as possible, they will be used everywhere
					dev.protocol, dev.codename
					dev.status = _status.DeviceStatus(dev, self._status_changed)
					return dev
		receiver.__register_new_device = receiver.register_new_device
		receiver.register_new_device = _MethodType(_register_with_status, receiver)

	def has_started(self):
		_log.info("events listener has started")
		self._status_changed(self.receiver)
		self.receiver.enable_notifications()
		self.receiver.notify_devices()
		self._status_changed(self.receiver, _status.ALERT.LOW)

	def has_stopped(self):
		_log.info("events listener has stopped")
		if self.receiver:
			self.receiver.enable_notifications(False)
			self.receiver.close()
		self.receiver = None
		self._status_changed(None, alert=_status.ALERT.LOW)

	def tick(self, timestamp):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("tick: polling status: %s %s", self.receiver, list(iter(self.receiver)))

		if self._last_tick > 0 and timestamp - self._last_tick > _DEVICE_STATUS_POLL * 2:
			# if we missed a couple of polls, most likely the computer went into
			# sleep, and we have to reinitialize the receiver again
			_log.warn("possible sleep detected, closing this listener")
			self.stop()
			return
		self._last_tick = timestamp

		# read these in case they haven't been read already
		self.receiver.serial, self.receiver.firmware

		if self.receiver.status.lock_open:
			# don't mess with stuff while pairing
			return

		for dev in self.receiver:
			if dev.status:
				# read these in case they haven't been read already
				dev.protocol, dev.serial, dev.firmware

				if _status.BATTERY_LEVEL not in dev.status:
					battery = _hidpp20.get_battery(dev) or _hidpp10.get_battery(dev)
					if battery:
						dev.status[_status.BATTERY_LEVEL], dev.status[_status.BATTERY_STATUS] = battery
						self._status_changed(dev)

			elif len(dev.status) > 0 and timestamp - dev.status.updated > _DEVICE_TIMEOUT:
				dev.status.clear()
				self._status_changed(dev, _status.ALERT.LOW)

	def _status_changed(self, device, alert=_status.ALERT.NONE, reason=None):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("status_changed %s: %s (%X) %s", device, None if device is None else device.status, alert, reason or '')
		if self.status_changed_callback:
			if device is None or device.kind is None:
				self.status_changed_callback(self.receiver or DUMMY, None, alert, reason)
			else:
				self.status_changed_callback(self.receiver or DUMMY, device, alert, reason)
				# if device.status is None:
				# 	self.status_changed_callback(self.receiver, None)

	def _events_handler(self, event):
		assert self.receiver
		if event.devnumber == 0xFF:
			# a receiver envent
			if self.receiver.status is not None:
				self.receiver.status.process_event(event)
		else:
			# a paired device envent
			assert event.devnumber > 0 and event.devnumber <= self.receiver.max_devices
			dev = self.receiver[event.devnumber]
			if dev:
				if dev.status is not None:
					dev.status.process_event(event)
			else:
				if self.receiver.status.lock_open:
					assert event.sub_id == 0x41 and event.address == 0x04
					_log.info("pairing detected new device")
					dev = self.receiver.status.device_paired(event.devnumber)
					dev.status.process_event(event)
				else:
					_log.warn("received event %s for invalid device %d", event, event.devnumber)

	def __str__(self):
		return '<ReceiverListener(%s,%d)>' % (self.receiver.path, self.receiver.status)

	@classmethod
	def open(self, status_changed_callback=None):
		receiver = Receiver.open()
		if receiver:
			receiver.handle = _listener.ThreadedHandle(receiver.handle, receiver.path)
			receiver.kind = None
			rl = ReceiverListener(receiver, status_changed_callback)
			rl.start()
			return rl
