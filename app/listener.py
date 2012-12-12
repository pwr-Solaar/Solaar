#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('listener')
del getLogger

from types import MethodType as _MethodType

from logitech.unifying_receiver import (Receiver,
										listener as _listener,
										status as _status)

#
#
#

class _DUMMY_RECEIVER(object):
	__slots__ = []
	name = Receiver.name
	kind = None
	max_devices = Receiver.max_devices
	status = 'Receiver not found.'
	__bool__ = __nonzero__ = lambda self: False
	__unicode__ = __str__ = __repr__ = lambda self: 'DUMMY'
DUMMY = _DUMMY_RECEIVER()

from collections import namedtuple
_GHOST_DEVICE = namedtuple('_GHOST_DEVICE', ['number', 'name', 'kind', 'status'])
del namedtuple

#
#
#

_POLL_TICK = 60  # seconds


class ReceiverListener(_listener.EventsListener):
	"""Keeps the status of a Unifying Receiver.
	"""
	def __init__(self, receiver, status_changed_callback=None):
		super(ReceiverListener, self).__init__(receiver, self._notifications_handler)
		self.tick_period = _POLL_TICK
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
					self._status_changed(r)
					return dev
		receiver.__register_new_device = receiver.register_new_device
		receiver.register_new_device = _MethodType(_register_with_status, receiver)

	def has_started(self):
		_log.info("notifications listener has started")
		self.receiver.enable_notifications()
		self.receiver.notify_devices()
		self._status_changed(self.receiver, _status.ALERT.LOW)

	def has_stopped(self):
		_log.info("notifications listener has stopped")
		if self.receiver:
			self.receiver.enable_notifications(False)
			self.receiver.close()
		self.receiver = None
		self._status_changed(None, _status.ALERT.LOW)

	def tick(self, timestamp):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("polling status: %s %s", self.receiver, list(iter(self.receiver)))

		if self._last_tick > 0 and timestamp - self._last_tick > _POLL_TICK * 3:
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
			if dev.status is not None:
				dev.status.poll(timestamp)

	def _status_changed(self, device, alert=_status.ALERT.NONE, reason=None):
		if _log.isEnabledFor(_DEBUG):
			_log.debug("status_changed %s: %s %s (%X) %s", device,
						None if device is None else 'active' if device.status else 'inactive',
						None if device is None else device.status,
						alert, reason or '')
		if self.status_changed_callback:
			r = self.receiver or DUMMY
			if device is None or device.kind is None:
				# the status of the receiver changed
				self.status_changed_callback(r, None, alert, reason)
			else:
				if device.status is None:
					# device was unpaired, and since the object is weakref'ed
					# it won't be valid for much longer
					device = _GHOST_DEVICE(number=device.number, name=device.name, kind=device.kind, status=None)
				self.status_changed_callback(r, device, alert, reason)
				if device.status is None:
					self.status_changed_callback(r)

	def _notifications_handler(self, n):
		assert self.receiver
		if n.devnumber == 0xFF:
			# a receiver notification
			if self.receiver.status is not None:
				self.receiver.status.process_notification(n)
		else:
			# a device notification
			assert n.devnumber > 0 and n.devnumber <= self.receiver.max_devices
			already_known = n.devnumber in self.receiver
			dev = self.receiver[n.devnumber]
			if dev and dev.status is not None:
				dev.status.process_notification(n)
				if self.receiver.status.lock_open and not already_known:
					# this should be the first notification after a device was paired
					assert n.sub_id == 0x41 and n.address == 0x04
					_log.info("pairing detected new device")
					self.receiver.status.new_device = dev
			else:
				_log.warn("received notification %s for invalid device %d: %s", n, n.devnumber, dev)

	def __str__(self):
		return '<ReceiverListener(%s,%s)>' % (self.receiver.path, self.receiver.handle)
	__unicode__ = __str__

	@classmethod
	def open(self, status_changed_callback=None):
		receiver = Receiver.open()
		if receiver:
			receiver.handle = _listener.ThreadedHandle(receiver.handle, receiver.path)
			receiver.kind = None
			rl = ReceiverListener(receiver, status_changed_callback)
			rl.start()
			return rl
