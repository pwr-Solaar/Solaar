#
#
#

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('listener')
del getLogger

import logitech.unifying_receiver as _lur

#
#
#

class _DUMMY_RECEIVER(object):
	__slots__ = ['name', 'max_devices', 'status']
	name = _lur.Receiver.name
	max_devices = _lur.Receiver.max_devices
	status = 'Receiver not found.'
	__bool__ = __nonzero__ = lambda self: False
	__str__ = lambda self: 'DUMMY'
DUMMY = _DUMMY_RECEIVER()

#
#
#

_DEVICE_TIMEOUT = 3 * 60  # seconds
_DEVICE_STATUS_POLL = 60  # seconds

# def fake_device(listener):
# 	dev = _lur.PairedDevice(listener.receiver, 6)
# 	dev._wpid = '1234'
# 	dev._kind = 'touchpad'
# 	dev._codename = 'T650'
# 	dev._name = 'Wireless Rechargeable Touchpad T650'
# 	dev._serial = '0123456789'
# 	dev._protocol = 2.0
# 	dev.status = _lur.status.DeviceStatus(dev, listener._status_changed)
# 	return dev

class ReceiverListener(_lur.listener.EventsListener):
	"""Keeps the status of a Unifying Receiver.
	"""
	def __init__(self, receiver, status_changed_callback=None):
		super(ReceiverListener, self).__init__(receiver, self._events_handler)
		self.tick_period = _DEVICE_STATUS_POLL

		self.status_changed_callback = status_changed_callback

		receiver.status = _lur.status.ReceiverStatus(receiver, self._status_changed)
		_lur.Receiver.create_device = self.create_device

	def create_device(self, receiver, number):
		dev = _lur.PairedDevice(receiver, number)
		dev.status = _lur.status.DeviceStatus(dev, self._status_changed)
		return dev

	def has_started(self):
		# self._status_changed(self.receiver)
		self.receiver.enable_notifications()

		for dev in self.receiver:
			dev.codename, dev.kind, dev.name
			# dev.status._changed(dev.protocol > 0)

		# fake = fake_device(self)
		# self.receiver._devices[fake.number] = fake
		# self._status_changed(fake, _lur.status.ALERT.LOW)

		self.receiver.notify_devices()
		self._status_changed(self.receiver, _lur.status.ALERT.LOW)

	def has_stopped(self):
		if self.receiver:
			self.receiver.enable_notifications(False)
			self.receiver.close()

		self.receiver = None
		self._status_changed(None, alert=_lur.status.ALERT.LOW)

	def tick(self, timestamp):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("tick: polling status")

		# read these in case they haven't been read already
		self.receiver.serial, self.receiver.firmware

		if self.receiver.status.lock_open:
			# don't mess with stuff while pairing
			return

		for dev in self.receiver:
			if dev.status:
				# read these in case they haven't been read already
				dev.wpid, dev.serial, dev.protocol, dev.firmware

				if dev.status.get(_lur.status.BATTERY_LEVEL) is None:
					battery = _lur.hidpp20.get_battery(dev) or _lur.hidpp10.get_battery(dev)
					if battery:
						dev.status[_lur.status.BATTERY_LEVEL], dev.status[_lur.status.BATTERY_STATUS] = battery
						self._status_changed(dev)

			elif len(dev.status) > 0 and timestamp - dev.status.updated > _DEVICE_TIMEOUT:
				dev.status.clear()
				self._status_changed(dev, _lur.status.ALERT.LOW)

	def _status_changed(self, device, alert=_lur.status.ALERT.NONE, reason=None):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("status_changed %s: %s (%X) %s", device, None if device is None else device.status, alert, reason or '')
		if self.status_changed_callback:
			if device is None or device is self.receiver:
				self.status_changed_callback(self.receiver or DUMMY, None, alert, reason)
			else:
				self.status_changed_callback(self.receiver or DUMMY, device, alert, reason)
				if device.status is None:
					self.status_changed_callback(self.receiver, None)

	def _events_handler(self, event):
		if event.devnumber == 0xFF:
			if self.receiver.status is not None:
				self.receiver.status.process_event(event)

		else:
			assert event.devnumber > 0 and event.devnumber <= self.receiver.max_devices
			known_device = event.devnumber in self.receiver

			dev = self.receiver[event.devnumber]
			if dev:
				if dev.status is not None and dev.status.process_event(event):
					if self.receiver.status.lock_open and not known_device:
						assert event.sub_id == 0x41
						self.receiver.pairing_result = dev
					return
			else:
				_log.warn("received event %s for invalid device %d", event, event.devnumber)

	def __str__(self):
		return '<ReceiverListener(%s,%d)>' % (self.receiver.path, self.receiver.status)

	@classmethod
	def open(self, status_changed_callback=None):
		receiver = _lur.Receiver.open()
		if receiver:
			receiver.handle = _lur.listener.ThreadedHandle(receiver.handle, receiver.path)
			receiver.kind = 'applications-system'
			rl = ReceiverListener(receiver, status_changed_callback)
			rl.start()
			return rl
