#
#
#

from threading import Thread
import time
import logging
from collections import namedtuple

from logitech.devices.constants import STATUS
from receiver import Receiver


_DUMMY_RECEIVER = namedtuple('_DUMMY_RECEIVER', ['NAME', 'kind', 'status', 'status_text', 'max_devices', 'devices'])
_DUMMY_RECEIVER.__nonzero__ = lambda _: False
_DUMMY_RECEIVER.device_name = Receiver.NAME
DUMMY = _DUMMY_RECEIVER(Receiver.NAME, Receiver.NAME, STATUS.UNAVAILABLE, 'Receiver not found.', Receiver.max_devices, {})


def _sleep(seconds, granularity, breakout=lambda: False):
	for index in range(0, int(seconds / granularity)):
		if breakout():
			return
		time.sleep(granularity)


class Watcher(Thread):
	"""Keeps an active receiver object if possible, and updates the UI when
	necessary.
	"""
	def __init__(self, apptitle, update_ui, notify=None):
		super(Watcher, self).__init__(group=apptitle, name='Watcher')
		self.daemon = True
		self._active = False

		self.update_ui = update_ui
		self.notify = notify or (lambda d: None)

		self.receiver = DUMMY

	def run(self):
		self._active = True
		notify_missing = True

		while self._active:
			if self.receiver == DUMMY:
				r = Receiver.open()
				if r:
					logging.info("receiver %s ", r)
					self.update_ui(r)
					self.notify(r)
					r.events_handler = self._events_callback

					# give it some time to read all devices
					r.status_changed.clear()
					_sleep(8, 0.4, r.status_changed.is_set)
					if r.devices:
						logging.info("%d device(s) found", len(r.devices))
						for d in r.devices.values():
							self.notify(d)
					else:
						# if no devices found so far, assume none at all
						logging.info("no devices found")
						r.status = STATUS.CONNECTED

					self.receiver = r
					notify_missing = True
				else:
					if notify_missing:
						_sleep(0.8, 0.4, lambda: not self._active)
						notify_missing = False
						self.update_ui(DUMMY)
						self.notify(DUMMY)
					_sleep(4, 0.4, lambda: not self._active)
					continue

			if self._active:
				if self.receiver:
					logging.debug("waiting for status_changed")
					sc = self.receiver.status_changed
					sc.wait()
					sc.clear()
					logging.debug("status_changed %s %d", sc.reason, sc.urgent)
					self.update_ui(self.receiver)
					if sc.reason and sc.urgent:
						self.notify(sc.reason)
				else:
					self.receiver = DUMMY
					self.update_ui(DUMMY)
					self.notify(DUMMY)

		if self.receiver:
			self.receiver.close()

	def stop(self):
		if self._active:
			logging.info("stopping %s", self)
			self._active = False
			if self.receiver:
				# break out of an eventual wait()
				self.receiver.status_changed.reason = None
				self.receiver.status_changed.set()
			self.join()

	def _events_callback(self, event):
		logging.warn("don't know how to handle event %s", event)
