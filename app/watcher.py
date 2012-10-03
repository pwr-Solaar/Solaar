#
#
#

import logging
import threading
import time

import constants as C
from logitech.unifying_receiver import api
from logitech.unifying_receiver.listener import EventsListener
from logitech import devices


_STATUS_TIMEOUT = 97  # seconds
_THREAD_SLEEP = 7  # seconds
_FORGET_TIMEOUT = 5 * 60  # seconds


class _DevStatus(api.AttachedDeviceInfo):
	timestamp = time.time()
	code = devices.STATUS.CONNECTED
	props = {devices.PROPS.TEXT: devices.STATUS_NAME[devices.STATUS.CONNECTED]}
	refresh = None


class WatcherThread(threading.Thread):
	def __init__(self, notify_callback=None):
		super(WatcherThread, self).__init__(name='WatcherThread')
		self.daemon = True
		self.active = False

		self.notify = notify_callback
		self.status_text = None
		self.status_changed = threading.Event()

		self.listener = None
		self.devices = {}

	def run(self):
		self.active = True
		self._notify(0, C.UNIFYING_RECEIVER, C.SCANNING)

		while self.active:
			if self.listener is None:
				receiver = api.open()
				if receiver:
					self._notify(1, C.UNIFYING_RECEIVER, C.FOUND_RECEIVER)
					for devinfo in api.list_devices(receiver):
						devstatus = _DevStatus(*devinfo)
						self.devices[devinfo.number] = devstatus
						self._notify(devices.STATUS.CONNECTED, devstatus.name, devices.STATUS_NAME[devices.STATUS.CONNECTED])
					self.listener = EventsListener(receiver, self._events_callback)
					self.listener.start()
					self._update_status()
				else:
					self._notify(-1, C.UNIFYING_RECEIVER, C.NO_RECEIVER)
			elif not self.listener.active:
				self.listener = None
				self._notify(-1, C.UNIFYING_RECEIVER, C.NO_RECEIVER)
				self.devices.clear()

			if self.active:
				update_icon = True
				if self.listener and self.devices:
					update_icon &= self._check_old_statuses()

			if self.active:
				if update_icon:
					self._update_status()
				time.sleep(_THREAD_SLEEP)

	def stop(self):
		self.active = False
		if self.listener:
			self.listener.stop()
			api.close(self.listener.receiver)

	def has_receiver(self):
		return self.listener is not None and self.listener.active

	def request_all_statuses(self, _=None):
		updated = False

		for d in range(1, 7):
			devstatus = self.devices.get(d)
			if devstatus:
				status = devices.request_status(devstatus, self.listener)
				updated |= self._device_status_changed(devstatus, status)
			else:
				devstatus = self._new_device(d)
				updated |= devstatus is not None

		if updated:
			self._update_status()

	def _check_old_statuses(self):
		updated = False

		for devstatus in list(self.devices.values()):
			if time.time() - devstatus.timestamp > _STATUS_TIMEOUT:
				status = devices.ping(devstatus, self.listener)
				updated |= self._device_status_changed(devstatus, status)

		return updated

	def _new_device(self, device):
		devinfo = api.get_device_info(self.listener.receiver, device)
		if devinfo:
			devstatus = _DevStatus(*devinfo)
			self.devices[device] = devstatus
			self._notify(devstatus.code, devstatus.name, devstatus.props[devices.PROPS.TEXT])
			return devinfo

	def _events_callback(self, code, device, data):
		logging.debug("%s: event %02x %d %s", time.asctime(), code, device, repr(data))

		updated = False

		if device in self.devices:
			devstatus = self.devices[device]
			if code == 0x10 and data[0] == 'b\x8F':
				updated = True
				self._device_status_changed(devstatus, devices.STATUS.UNAVAILABLE)
			elif code == 0x11:
				status = devices.process_event(devstatus, self.listener, data)
				updated |= self._device_status_changed(devstatus, status)
			else:
				logging.warn("unknown event code %02x", code)
		elif device:
			logging.debug("got event (%d, %d, %s) for new device", code, device, repr(data))
			self._new_device(device)
			updated = True
		else:
			logging.warn("don't know how to handle event (%d, %d, %s)", code, device, data)

		if updated:
			self._update_status()

	def _device_status_changed(self, devstatus, status):
		if status is None:
			return False

		old_status_code = devstatus.code
		devstatus.timestamp = time.time()

		if type(status) == int:
			devstatus.code = status
			if devstatus.code in devices.STATUS_NAME:
				devstatus.props[devices.PROPS.TEXT] = devices.STATUS_NAME[devstatus.code]
		else:
			devstatus.code = status[0]
			devstatus.props.update(status[1])

		if old_status_code != devstatus.code:
			logging.debug("%s: device status changed %s => %s: %s",  time.asctime(), old_status_code, devstatus.code, devstatus.props)
			# if not (devstatus.code == 0 and old_status_code > 0):
			self._notify(devstatus.code, devstatus.name, devstatus.props[devices.PROPS.TEXT])

		return True

	def _notify(self, *args):
		if self.notify:
			self.notify(*args)

	def notify_full(self):
		if self.listener and self.listener.active:
			if self.devices:
				for devstatus in self.devices.values():
					self._notify(0, devstatus.name, devstatus.props[devices.PROPS.TEXT])
			else:
				self._notify(0, C.UNIFYING_RECEIVER, C.NO_DEVICES)
		else:
			self._notify(-1, C.UNIFYING_RECEIVER, C.NO_RECEIVER)

	def _update_status(self):
		last_status_text = self.status_text

		if self.listener and self.listener.active:
			if self.devices:
				all_statuses = []
				for d in self.devices:
					devstatus = self.devices[d]
					status_text = devstatus.props[devices.PROPS.TEXT]
					if status_text:
						if ' ' in status_text:
							all_statuses.append(devstatus.name)
							all_statuses.append('    ' + status_text)
						else:
							all_statuses.append(devstatus.name + ' ' + status_text)
					else:
						all_statuses.append(devstatus.name)
				self.status_text = '\n'.join(all_statuses)
			else:
				self.status_text = C.NO_DEVICES
		else:
			self.status_text = C.NO_RECEIVER

		if self.status_text != last_status_text:
			self.status_changed.set()
