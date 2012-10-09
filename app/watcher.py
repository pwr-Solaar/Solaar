#
#
#

import logging
import threading
import time
from binascii import hexlify as _hexlify

from logitech.unifying_receiver import api
from logitech.unifying_receiver.listener import EventsListener
from logitech import devices
from logitech.devices import constants as C


_STATUS_TIMEOUT = 31  # seconds
_THREAD_SLEEP = 2  # seconds

_UNIFYING_RECEIVER = 'Unifying Receiver'
_NO_RECEIVER = 'Receiver not found.'
_INITIALIZING = 'Initializing...'
_SCANNING = 'Scanning...'
_NO_DEVICES = 'No devices found.'
_OKAY = 'Status ok.'


class _DevStatus(api.AttachedDeviceInfo):
	timestamp = time.time()
	code = C.STATUS.UNKNOWN
	text = _INITIALIZING
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
		self.rstatus.pair = None

		self.devices = {}

	def run(self):
		self.active = True

		while self.active:
			if self.listener is None:
				self._device_status_changed(self.rstatus, (C.STATUS.UNKNOWN, _INITIALIZING))
				self._update_status_text()

				receiver = api.open()
				if receiver:
					self._device_status_changed(self.rstatus, (C.STATUS.BOOTING, _SCANNING))
					self._update_status_text()

					for devinfo in api.list_devices(receiver):
						self._new_device(devinfo)
					logging.debug("initial scan finished: %s", self.devices)
					if self.devices:
						self._device_status_changed(self.rstatus, (C.STATUS.CONNECTED, _OKAY))
					else:
						self._device_status_changed(self.rstatus, (C.STATUS.CONNECTED, _NO_DEVICES))
					self._update_status_text()

					self.listener = EventsListener(receiver, self._events_callback)
					self.listener.start()
				else:
					self._device_status_changed(self.rstatus, (C.STATUS.UNAVAILABLE, _NO_RECEIVER))
			elif not self.listener.active:
				self.listener = None
				self._device_status_changed(self.rstatus, (C.STATUS.UNAVAILABLE, _NO_RECEIVER))
				self.devices.clear()

			if self.active:
				update_icon = True
				if self.listener and self.devices:
					update_icon &= self._check_old_statuses()

			if self.active:
				if update_icon:
					self._update_status_text()
				time.sleep(_THREAD_SLEEP)

		self.listener.stop()
		if self.listener:
			api.close(self.listener.receiver)
		self.listener = None

	def stop(self):
		self.active = False
		self.join()

	def full_scan(self, *args):
		if self.active and self.listener:
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
		if self.listener and devstatus:
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
		if not self.active:
			return None

		if type(dev) == int:
			dev = self.listener.request(api.get_device_info, dev)
		if dev:
			devstatus = _DevStatus(*dev)
			devstatus.refresh = self._request_status
			self.devices[dev.number] = devstatus
			self._device_status_changed(devstatus, C.STATUS.CONNECTED)
			logging.debug("new devstatus %s", devstatus)
			return devstatus

	def _events_callback(self, code, devnumber, data):
		logging.debug("%s: event (%02x %02x [%s])", time.asctime(), code, devnumber, _hexlify(data))

		updated = False

		if devnumber in self.devices:
			devstatus = self.devices[devnumber]
			if code == 0x10 and data[:1] == b'\x8F':
				updated = True
				self._device_status_changed(devstatus, C.STATUS.UNAVAILABLE)
			elif code == 0x11:
				status = devices.process_event(devstatus, self.listener, data)
				updated |= self._device_status_changed(devstatus, status)
			else:
				logging.warn("unknown event code %02x", code)
		elif devnumber:
			self._new_device(devnumber)
			updated = True
		else:
			logging.warn("don't know how to handle event (%02x, %02x, [%s])", code, devnumber, _hexlify(data))

		if updated:
			self._update_status_text()

	def _device_status_changed(self, devstatus, status=None):
		if status is None:
			return False

		old_status_code = devstatus.code
		devstatus.timestamp = time.time()

		if type(status) == int:
			status_code = status
			if status_code in C.STATUS_NAME:
				status_text = C.STATUS_NAME[status_code]
		else:
			status_code = status[0]
			if isinstance(status[1], str):
				status_text = status[1]
			elif isinstance(status[1], dict):
				status_text = ''
				for key, value in status[1].items():
					if key == 'text':
						status_text = value
					else:
						setattr(devstatus, key, value)
			else:
				status_code = C.STATUS.UNKNOWN
				status_text = ''

		if not (status_code == C.STATUS.CONNECTED and old_status_code > C.STATUS.CONNECTED):
			# if this is not just a ping for a device with an already known status
			devstatus.code = status_code
			devstatus.text = status_text
			logging.debug("%s: device '%s' status update %s => %s: %s",  time.asctime(), devstatus.name, old_status_code, status_code, status_text)

			if status_code < C.STATUS.CONNECTED or old_status_code < C.STATUS.CONNECTED or status_code < old_status_code:
				self._notify(devstatus.code, devstatus.name, devstatus.text)

		return True

	def _notify(self, *args):
		if self.notify:
			self.notify(*args)

	def _update_status_text(self):
		last_status_text = self.status_text

		if self.devices:
			lines = []
			if self.rstatus.code < C.STATUS.CONNECTED:
				lines += (self.rstatus.text, '')

			devstatuses = [self.devices[d] for d in range(1, 1 + api.C.MAX_ATTACHED_DEVICES) if d in self.devices]
			for devstatus in devstatuses:
				if devstatus.text:
					if ' ' in devstatus.text:
						lines.append('<b>' + devstatus.name + '</b>')
						lines.append('      ' + devstatus.text)
					else:
						lines.append('<b>' + devstatus.name + '</b> ' + devstatus.text)
				else:
					lines.append('<b>' + devstatus.name + '</b>')
				lines.append('')

			self.status_text = '\n'.join(lines).rstrip('\n')
		else:
			self.status_text = self.rstatus.text

		if self.status_text != last_status_text:
			self.status_changed.set()
