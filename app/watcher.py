#
#
#

from threading import Thread
import time
from logging import getLogger as _Logger

from logitech.devices.constants import STATUS
from receiver import Receiver


class _DUMMY_RECEIVER(object):
	NAME = Receiver.NAME
	device_name = NAME
	kind = Receiver.NAME
	status = STATUS.UNAVAILABLE
	status_text = 'Receiver not found.'
	max_devices = Receiver.max_devices
	devices = {}
	__bool__ = __nonzero__ = lambda self: False
DUMMY = _DUMMY_RECEIVER()

_l = _Logger('watcher')


def _sleep(seconds, granularity, breakout=lambda: False):
	slept = 0
	while slept < seconds and not breakout():
		time.sleep(granularity)
		slept += granularity


class Watcher(Thread):
	"""Keeps an active receiver object if possible, and updates the UI when
	necessary.
	"""
	def __init__(self, apptitle, update_ui, notify=None):
		super(Watcher, self).__init__(group=apptitle, name='Watcher')
		self._active = False
		self._receiver = DUMMY

		self.update_ui = update_ui
		self.notify = notify or (lambda d: None)

	@property
	def receiver(self):
		return self._receiver

	def run(self):
		self._active = True
		notify_missing = True

		while self._active:
			if self._receiver == DUMMY:
				r = Receiver.open()
				if r is None:
					if notify_missing:
						_sleep(0.8, 0.4, lambda: not self._active)
						notify_missing = False
						if self._active:
							self.update_ui(DUMMY)
							self.notify(DUMMY)
					_sleep(4, 0.4, lambda: not self._active)
					continue

				_l.info("receiver %s ", r)
				self._receiver = r
				notify_missing = True

				self.update_ui(r)
				self.notify(r)

			if self._active:
				if self._receiver:
					_l.debug("waiting for status_changed")
					sc = self._receiver.status_changed
					sc.wait()
					if not self._active:
						break
					sc.clear()
					if sc.urgent:
						_l.info("status_changed %s", sc.reason)
					self.update_ui(self._receiver)
					if sc.reason and sc.urgent:
						self.notify(sc.reason)
				else:
					self._receiver = DUMMY
					self.update_ui(DUMMY)
					self.notify(DUMMY)

		if self._receiver:
			self._receiver.close()
		self._receiver = _DUMMY_RECEIVER

	def stop(self):
		if self._active:
			_l.info("stopping %s", self)
			self._active = False
			if self._receiver:
				# break out of an eventual wait()
				self._receiver.status_changed.reason = None
				self._receiver.status_changed.set()
			self.join()
