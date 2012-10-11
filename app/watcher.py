#
#
#

from threading import Thread
import time
from logging import getLogger as _Logger

from logitech.unifying_receiver import api
from logitech.unifying_receiver.listener import EventsListener
from logitech import devices
from logitech.devices import constants as C

import actions


_l = _Logger('watcher')

_STATUS_TIMEOUT = 61  # seconds
_THREAD_SLEEP = 3  # seconds
_SLEEP_QUANT = 0.33  # seconds

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

	def __str__(self):
		return 'DevStatus(%d,%s,%d)' % (self.number, self.name, self.code)


class Watcher(Thread):
	"""Keeps a map of all attached devices and their statuses."""
	def __init__(self, status_changed_callback, notify_callback=None):
		super(Watcher, self).__init__(group='Solaar', name='Watcher')
		self.daemon = True
		self.active = False

		self.notify = notify_callback
		self.status_text = None
		self.status_changed_callback = status_changed_callback

		self.listener = None

		self.rstatus = _DevStatus(0, 0xFF, None, _UNIFYING_RECEIVER, None, None)
		self.rstatus.max_devices = api.C.MAX_ATTACHED_DEVICES
		self.rstatus.refresh = (actions.full_scan, self)
		self.rstatus.pair = None  # (actions.pair, self)

		self.devices = {}

	def run(self):
		self.active = True

		while self.active:
			if self.listener is None:
				self._update_status_text()

				receiver = api.open()
				if receiver:
					self._device_status_changed(self.rstatus, (C.STATUS.BOOTING, _SCANNING))
					self._update_status_text()

					for devinfo in api.list_devices(receiver):
						self._new_device(devinfo)
					if self.devices:
						self._update_status_text()

					self.listener = EventsListener(receiver, self._events_callback)
					self.listener.start()

					# need to wait for the thread to come alive
					time.sleep(_SLEEP_QUANT / 2)
			elif not self.listener:
				self.listener = None
				self.devices.clear()

			if self.listener:
				if self.devices:
					update_icon = self._device_status_changed(self.rstatus, (C.STATUS.CONNECTED, _OKAY))
					update_icon |= self._check_old_statuses()
				else:
					update_icon = self._device_status_changed(self.rstatus, (C.STATUS.CONNECTED, _NO_DEVICES))
			else:
				update_icon = self._device_status_changed(self.rstatus, (C.STATUS.UNAVAILABLE, _NO_RECEIVER))

			if update_icon:
				self._update_status_text()

			for i in range(0, int(_THREAD_SLEEP / _SLEEP_QUANT)):
				if self.active:
					time.sleep(_SLEEP_QUANT)
				else:
					break

		if self.listener:
			self.listener.stop()
			api.close(self.listener.receiver)
			self.listener = None

	def stop(self):
		self.active = False
		self.join()

	def _request_status(self, devstatus):
		if self.listener and devstatus:
			status = devices.request_status(devstatus, self.listener)
			self._device_status_changed(devstatus, status)

	def _check_old_statuses(self):
		updated = False

		for devstatus in self.devices.values():
			if devstatus != self.rstatus:
				if time.time() - devstatus.timestamp > _STATUS_TIMEOUT:
					status = devices.ping(devstatus, self.listener)
					updated |= self._device_status_changed(devstatus, status)

		return updated

	def _new_device(self, dev):
		if not self.active:
			return None

		if type(dev) == int:
			# assert self.listener
			dev = self.listener.request(api.get_device_info, dev)

		if dev:
			devstatus = _DevStatus(*dev)
			devstatus.refresh = self._request_status
			self.devices[dev.number] = devstatus
			_l.debug("new devstatus %s", devstatus)
			self._device_status_changed(devstatus, C.STATUS.CONNECTED)
			self._device_status_changed(self.rstatus, (C.STATUS.CONNECTED, _OKAY))
			return devstatus

	def _device_status_changed(self, devstatus, status):
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
				_l.warn("don't know how to handle status %s", status)
				return False

		if ((status_code == old_status_code and status_text == devstatus.text) or
			(status_code == C.STATUS.CONNECTED and old_status_code > C.STATUS.CONNECTED)):
			# this is just successful ping for a device with an already known status
			return False

		devstatus.code = status_code
		devstatus.text = status_text
		_l.debug("%s update %s => %s: %s",  devstatus, old_status_code, status_code, status_text)

		if self.notify:
			self.notify(devstatus.code, devstatus.name, devstatus.text)

		return True

	def _events_callback(self, code, devnumber, data):
		# _l.debug("event %s", (code, devnumber, data))

		updated = False

		if devnumber in self.devices:
			devstatus = self.devices[devnumber]
			if code == 0x10 and data[:1] == b'\x8F':
				updated = True
				self._device_status_changed(devstatus, C.STATUS.UNAVAILABLE)
			elif code == 0x11:
				status = devices.process_event(devstatus, data)
				updated |= self._device_status_changed(devstatus, status)
			else:
				_l.warn("unknown event code %02x", code)
		elif devnumber:
			self._new_device(devnumber)
			updated = True
		else:
			_l.warn("don't know how to handle event %s", (code, devnumber, data))

		if updated:
			self._update_status_text()

	def _update_status_text(self):
		last_status_text = self.status_text

		if self.devices:
			lines = []
			if self.rstatus.code < C.STATUS.CONNECTED:
				lines += (self.rstatus.text, '')

			devstatuses = [self.devices[d] for d in range(1, 1 + self.rstatus.max_devices) if d in self.devices]
			for devstatus in devstatuses:
				if devstatus.text:
					if ' ' in devstatus.text:
						lines += ('<b>' + devstatus.name + '</b>', '      ' + devstatus.text)
					else:
						lines.append('<b>' + devstatus.name + '</b> ' + devstatus.text)
				else:
					lines.append('<b>' + devstatus.name + '</b>')
				lines.append('')

			self.status_text = '\n'.join(lines).rstrip('\n')
		else:
			self.status_text = self.rstatus.text

		if self.status_text != last_status_text:
			self.status_changed_callback(self.status_text, self.rstatus, self.devices)
