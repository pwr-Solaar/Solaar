#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

from . import configuration
from logitech.unifying_receiver import (Receiver,
										listener as _listener,
										status as _status)

#
#
#

from collections import namedtuple
_GHOST_DEVICE = namedtuple('_GHOST_DEVICE', ['receiver', 'number', 'name', 'kind', 'serial', 'status', 'online'])
_GHOST_DEVICE.__bool__ = lambda self: False
_GHOST_DEVICE.__nonzero__ = _GHOST_DEVICE.__bool__
del namedtuple

def _ghost(device):
	return _GHOST_DEVICE(
					receiver=device.receiver,
					number=device.number,
					name=device.name,
					kind=device.kind,
					serial=device.serial,
					status=None,
					online=False)

#
#
#

# how often to poll devices that haven't updated their statuses on their own
# (through notifications)
_POLL_TICK = 5 * 60  # seconds


class ReceiverListener(_listener.EventsListener):
	"""Keeps the status of a Receiver.
	"""
	def __init__(self, receiver, status_changed_callback):
		super(ReceiverListener, self).__init__(receiver, self._notifications_handler)
		# no reason to enable polling yet
		self.tick_period = _POLL_TICK
		self._last_tick = 0

		assert status_changed_callback
		self.status_changed_callback = status_changed_callback
		receiver.status = _status.ReceiverStatus(receiver, self._status_changed)

	def has_started(self):
		_log.info("%s: notifications listener has started (%s)", self.receiver, self.receiver.handle)
		notification_flags = self.receiver.enable_notifications()
		self.receiver.status[_status.KEYS.NOTIFICATION_FLAGS] = notification_flags
		self.receiver.notify_devices()
		self._status_changed(self.receiver)  #, _status.ALERT.NOTIFICATION)

	def has_stopped(self):
		r, self.receiver = self.receiver, None
		assert r is not None
		_log.info("%s: notifications listener has stopped", r)

		# because udev is not notifying us about device removal,
		# make sure to clean up in _all_listeners
		_all_listeners.pop(r.path, None)

		r.status = 'The receiver was unplugged.'
		if r:
			try:
				r.close()
			except:
				_log.exception("closing receiver %s" % r.path)
		self.status_changed_callback(r)  #, _status.ALERT.NOTIFICATION)

	def tick(self, timestamp):
		if not self.tick_period:
			raise Exception("tick() should not be called without a tick_period: %s", self)

		# not necessary anymore, we're now using udev monitor to watch for receiver status
		# if self._last_tick > 0 and timestamp - self._last_tick > _POLL_TICK * 2:
		# 	# if we missed a couple of polls, most likely the computer went into
		# 	# sleep, and we have to reinitialize the receiver again
		# 	_log.warn("%s: possible sleep detected, closing this listener", self.receiver)
		# 	self.stop()
		# 	return

		self._last_tick = timestamp

		try:
			# read these in case they haven't been read already
			# self.receiver.serial, self.receiver.firmware
			if self.receiver.status.lock_open:
				# don't mess with stuff while pairing
				return

			self.receiver.status.poll(timestamp)

			# Iterating directly through the reciver would unnecessarily probe
			# all possible devices, even unpaired ones.
			# Checking for each device number in turn makes sure only already
			# known devices are polled.
			# This is okay because we should have already known about them all
			# long before the first poll() happents, through notifications.
			for number in range(1, 6):
				if number in self.receiver:
					dev = self.receiver[number]
					if dev and dev.status is not None:
						dev.status.poll(timestamp)
		except Exception as e:
			_log.exception("polling", e)

	def _status_changed(self, device, alert=_status.ALERT.NONE, reason=None):
		assert device is not None
		if _log.isEnabledFor(_DEBUG):
			if device.kind is None:
				_log.debug("status_changed %s: %s, %s (%X) %s", device,
							'present' if bool(device) else 'removed',
							device.status, alert, reason or '')
			else:
				_log.debug("status_changed %s: %s %s, %s (%X) %s", device,
							'paired' if bool(device) else 'unpaired',
							'online' if device.online else 'offline',
							device.status, alert, reason or '')

		if device.kind is None:
			assert device == self.receiver
			# the status of the receiver changed
			self.status_changed_callback(device, alert, reason)
			return

		assert device.receiver == self.receiver
		if not device:
			# device was unpaired, and since the object is weakref'ed
			# it won't be valid for much longer
			_log.warn("device %s was unpaired, ghosting", device)
			device = _ghost(device)

		self.status_changed_callback(device, alert, reason)

		if not device:
			# the device was just unpaired, need to update the
			# status of the receiver as well
			self.status_changed_callback(self.receiver)

	def _notifications_handler(self, n):
		assert self.receiver
		# _log.debug("%s: handling %s", self.receiver, n)
		if n.devnumber == 0xFF:
			# a receiver notification
			if self.receiver.status is not None:
				self.receiver.status.process_notification(n)
			return

		# a device notification
		assert n.devnumber > 0 and n.devnumber <= self.receiver.max_devices
		already_known = n.devnumber in self.receiver
		if not already_known and n.sub_id == 0x41:
			dev = self.receiver.register_new_device(n.devnumber, n)
		else:
			dev = self.receiver[n.devnumber]

		if not dev:
			_log.warn("%s: received %s for invalid device %d: %r", self.receiver, n, n.devnumber, dev)
			return

		if not already_known:
			# _log.info("%s triggered new device %s", n, dev)
			dev.status = _status.DeviceStatus(dev, self._status_changed)
			dev.status.configuration = configuration
			# the receiver changed status as well
			self._status_changed(self.receiver)

		assert dev
		assert dev.status is not None
		dev.status.process_notification(n)
		if self.receiver.status.lock_open and not already_known:
			# this should be the first notification after a device was paired
			assert n.sub_id == 0x41 and n.address == 0x04
			_log.info("%s: pairing detected new device", self.receiver)
			self.receiver.status.new_device = dev
		else:
			if dev.online is None:
				dev.ping()

	def __str__(self):
		return '<ReceiverListener(%s,%s)>' % (self.receiver.path, self.receiver.handle)
	__unicode__ = __str__

#
#
#

# all known receiver listeners
# listeners that stop on their own may remain here
_all_listeners = {}


def start(device_info, status_changed_callback):
	assert status_changed_callback
	receiver = Receiver.open(device_info)
	if receiver:
		rl = ReceiverListener(receiver, status_changed_callback)
		rl.start()
		_all_listeners[device_info.path] = rl
		return rl
	else:
		_log.warn("failed to open %s", device_info)


def stop_all():
	listeners = list(_all_listeners.values())
	_all_listeners.clear()

	if listeners:
		_log.info("stopping %s", listeners)

		for l in listeners:
			l.stop()

	configuration.save()

	if listeners:
		for l in listeners:
			l.join()


_status_callback = None
_error_callback = None

def start_scanner(status_changed_callback, error_callback):
	global _status_callback, _error_callback
	if _status_callback:
		raise Exception("scanner was already set-up")

	_status_callback = status_changed_callback
	_error_callback = error_callback

	from logitech.unifying_receiver import base as _base
	_base.notify_on_receivers_glib(_process_receiver_event)


# receiver add/remove events will start/stop listener threads
def _process_receiver_event(action, device_info):
	assert action is not None
	assert device_info is not None

	_log.info("receiver event %s %s", action, device_info)

	# whatever the action, stop any previous receivers at this path
	l = _all_listeners.pop(device_info.path, None)
	if l is not None:
		assert isinstance(l, ReceiverListener)
		l.stop()

	if action == 'add':
		# a new receiver device was detected
		try:
			start(device_info, _status_callback)
		except OSError:
			# permission error, ignore this path for now
			_error_callback('permissions', device_info.path)
