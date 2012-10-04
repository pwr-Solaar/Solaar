#
#
#

import logging
import threading
import time

from logitech.unifying_receiver import api
from logitech.unifying_receiver.listener import EventsListener
from logitech import devices


_STATUS_TIMEOUT = 34  # seconds
_THREAD_SLEEP = 5  # seconds


_UNIFYING_RECEIVER = 'Unifying Receiver'
_NO_DEVICES = 'No devices attached.'
_SCANNING = 'Initializing...'
_NO_RECEIVER = 'not found'
_FOUND_RECEIVER = 'found'


class _DevStatus(api.AttachedDeviceInfo):
	timestamp = time.time()
	code = devices.STATUS.UNKNOWN
	text = ''
	refresh = None


class WatcherThread(threading.Thread):
	"""Keeps a map of all attached devices and their statuses."""
	def __init__(self, notify_callback=None):
		super(WatcherThread, self).__init__(name='WatcherThread')
		self.daemon = True
		self.active = False

		self.notify = notify_callback
		self.status_text = None
		self.status_changed = threading.Event()

		self.listener = None

		self.rstatus = _DevStatus(0, _UNIFYING_RECEIVER, _UNIFYING_RECEIVER, None, None)
		self.rstatus.refresh = self.full_scan
		self.devices = {0: self.rstatus}

	def run(self):
		self.active = True
		self._notify(0, _UNIFYING_RECEIVER, _SCANNING)

		while self.active:
			if self.listener is None:
				receiver = api.open()
				if receiver:
					self._device_status_changed(self.rstatus, (devices.STATUS.CONNECTED, _FOUND_RECEIVER))

					for devinfo in api.list_devices(receiver):
						self._new_device(devinfo)

					if len(self.devices) == 1:
						self._device_status_changed(self.rstatus, (devices.STATUS.CONNECTED, _NO_DEVICES))

					self._update_status_text()

					self.listener = EventsListener(receiver, self._events_callback)
					self.listener.start()
				else:
					self._device_status_changed(self.rstatus, (devices.STATUS.UNAVAILABLE, _NO_RECEIVER))
			elif not self.listener.active:
				self.listener = None
				self._device_status_changed(self.rstatus, (devices.STATUS.UNAVAILABLE, _NO_RECEIVER))
				self.devices = {0: self.rstatus}

			if self.active:
				update_icon = True
				if self.listener and len(self.devices) > 1:
					update_icon &= self._check_old_statuses()

			if self.active:
				if update_icon:
					self._update_status_text()
				time.sleep(_THREAD_SLEEP)

	def stop(self):
		self.active = False
		if self.listener:
			self.listener.stop()
			api.close(self.listener.receiver)

	def full_scan(self, _=None):
		updated = False

		for devnumber in range(1, 1 + api.C.MAX_ATTACHED_DEVICES):
			devstatus = self.devices.get(devnumber)
			if devstatus:
				status = devices.request_status(devstatus, self.listener)
				updated |= self._device_status_changed(devstatus, status)
			else:
				devstatus = self._new_device(devnumber)
				updated |= devstatus is not None

		if updated:
			self._update_status_text()

	def _request_status(self, devstatus):
		if devstatus:
			status = devices.request_status(devstatus, self.listener)
			self._device_status_changed(devstatus, status)

	def _check_old_statuses(self):
		updated = False

		for devstatus in list(self.devices.values()):
			if devstatus != self.rstatus:
				if time.time() - devstatus.timestamp > _STATUS_TIMEOUT:
					status = devices.ping(devstatus, self.listener)
					updated |= self._device_status_changed(devstatus, status)

		return updated

	def _new_device(self, dev):
		if type(dev) == int:
			dev = api.get_device_info(self.listener.receiver, dev)
		logging.debug("new devstatus from %s", dev)
		if dev:
			devstatus = _DevStatus(*dev)
			devstatus.refresh = self._request_status
			self.devices[dev.number] = devstatus
			self._device_status_changed(devstatus, devices.STATUS.CONNECTED)
			return devstatus

	def _events_callback(self, code, devnumber, data):
		logging.debug("%s: event %02x %d %s", time.asctime(), code, devnumber, repr(data))

		updated = False

		if devnumber in self.devices:
			devstatus = self.devices[devnumber]
			if code == 0x10 and data[0] == 'b\x8F':
				updated = True
				self._device_status_changed(devstatus, devices.STATUS.UNAVAILABLE)
			elif code == 0x11:
				status = devices.process_event(devstatus, self.listener, data)
				updated |= self._device_status_changed(devstatus, status)
			else:
				logging.warn("unknown event code %02x", code)
		elif devnumber:
			self._new_device(devnumber)
			updated = True
		else:
			logging.warn("don't know how to handle event (%d, %d, %s)", code, devnumber, data)

		if updated:
			self._update_status_text()

	def _device_status_changed(self, devstatus, status=None):
		if status is None:
			return False

		old_status_code = devstatus.code
		devstatus.timestamp = time.time()

		if type(status) == int:
			devstatus.code = status
			if devstatus.code in devices.STATUS_NAME:
				devstatus.text = devices.STATUS_NAME[devstatus.code]
		else:
			devstatus.code = status[0]
			if isinstance(status[1], str):
				devstatus.text = status[1]
			elif isinstance(status[1], dict):
				for key, value in status[1].items():
					setattr(devstatus, key, value)

		if old_status_code != devstatus.code:
			logging.debug("%s: device '%s' status changed %s => %s: %s",  time.asctime(), devstatus.name, old_status_code, devstatus.code, devstatus.text)
			if devstatus.code // 256 != old_status_code // 256:
				self._notify(devstatus.code, devstatus.name, devstatus.text)

		return True

	def _notify(self, *args):
		if self.notify:
			self.notify(*args)

	def _update_status_text(self):
		last_status_text = self.status_text

		if self.rstatus.code < 0:
			self.status_text = '<b>' + self.rstatus.name + '</b>: ' + self.rstatus.text
		else:
			all_statuses = []
			for devnumber in range(1, 1 + api.C.MAX_ATTACHED_DEVICES):
				if devnumber in self.devices:
					devstatus = self.devices[devnumber]
					if devstatus.text:
						if ' ' in devstatus.text:
							all_statuses.append('<b>' + devstatus.name + '</b>')
							all_statuses.append('      ' + devstatus.text)
						else:
							all_statuses.append('<b>' + devstatus.name + '</b>: ' + devstatus.text)
					else:
						all_statuses.append('<b>' + devstatus.name + '</b>')
					all_statuses.append('')

			if all_statuses:
				self.status_text = '\n'.join(all_statuses).rstrip('\n')
			else:
				self.status_text = '<b>' + self.rstatus.name + '</b>: ' + _NO_DEVICES

		if self.status_text != last_status_text:
			self.status_changed.set()
