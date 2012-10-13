#
#
#

from threading import (Thread, Event)
import time
from logging import getLogger as _Logger

from logitech.unifying_receiver import (api, base)
from logitech.unifying_receiver.listener import EventsListener
from logitech import devices
from logitech.devices import constants as C


_l = _Logger('watcher')

_UNIFYING_RECEIVER = 'Unifying Receiver'
_NO_RECEIVER = 'Receiver not found.'
_INITIALIZING = 'Initializing...'
_SCANNING = 'Scanning...'
_NO_DEVICES = 'No devices found.'
_OKAY = 'Status ok.'


class _DevStatus(api.AttachedDeviceInfo):
	code = C.STATUS.UNKNOWN
	text = _INITIALIZING

	def __str__(self):
		return 'DevStatus(%d,%s,%d)' % (self.number, self.name, self.code)


class Watcher(Thread):
	"""Keeps a map of all attached devices and their statuses."""
	def __init__(self, apptitle, notify=None):
		super(Watcher, self).__init__(group=apptitle, name='Watcher')
		self.daemon = True
		self._active = False

		self.listener = None
		self.no_receiver = Event()

		self.rstatus = _DevStatus(0, 0xFF, 'UR', _UNIFYING_RECEIVER, ())
		self.rstatus.max_devices = api.C.MAX_ATTACHED_DEVICES
		self.rstatus.pair = None

		self.devices = {}

		self.notify = notify
		self.status_changed = Event()

	def run(self):
		self._active = True

		while self._active:
			if self.listener is None:
				receiver = api.open()
				if receiver:
					self._device_status_changed(self.rstatus, C.STATUS.BOOTING, _INITIALIZING)

					init = (base.request(receiver, 0xFF, b'\x81\x00') and
							base.request(receiver, 0xFF, b'\x80\x00', b'\x00\x01') and
							base.request(receiver, 0xFF, b'\x81\x02'))
					if init:
						_l.debug("receiver initialized ok")
					else:
						_l.debug("receiver initialization failed")

					self._device_status_changed(self.rstatus, C.STATUS.BOOTING, _SCANNING)

					self.listener = EventsListener(receiver, self._events_callback)
					self.listener.start()

					_l.debug("requesting devices status")
					self.listener.request(base.request, 0xFF, b'\x80\x02', b'\x02')

					# give it some time to get the devices
					time.sleep(3)
			elif not self.listener:
				self.listener = None
				self.devices.clear()

			if self.listener:
				if self.devices:
					self._device_status_changed(self.rstatus, C.STATUS.CONNECTED, _OKAY)
				else:
					self._device_status_changed(self.rstatus, C.STATUS.CONNECTED, _NO_DEVICES)

				self.no_receiver.wait()
				self.no_receiver.clear()
			else:
				self._device_status_changed(self.rstatus, C.STATUS.UNAVAILABLE, _NO_RECEIVER)
				time.sleep(3)

		if self.listener:
			self.listener.stop()
			self.listener = None

	def stop(self):
		if self._active:
			_l.debug("stopping %s", self)
			self._active = False
			self.no_receiver.set()
			self.join()

	def request_status(self, devstatus=None, **kwargs):
		"""Trigger a status update on a device."""
		if self.listener:
			if devstatus is None or devstatus == self.rstatus:
				for devstatus in self.devices.values():
					self.request_status(devstatus)
			else:
				status = devices.request_status(devstatus, self.listener)
				self._handle_status(devstatus, status)

	def _handle_status(self, devstatus, status):
		if status is not None:
			if type(status) == int:
				self._device_status_changed(devstatus, status)
			else:
				self._device_status_changed(devstatus, *status)

	def _new_device(self, dev):
		if not self._active:
			return None

		if type(dev) == int:
			assert self.listener
			dev = self.listener.request(api.get_device_info, dev)

		if dev:
			devstatus = _DevStatus(*dev)
			self.devices[dev.number] = devstatus
			self._device_status_changed(devstatus, C.STATUS.CONNECTED)
			_l.debug("new devstatus %s", devstatus)
			self._device_status_changed(self.rstatus, C.STATUS.CONNECTED, _OKAY)
			return devstatus

	def _device_status_changed(self, devstatus, status_code, status_data=None):
		old_status_code = devstatus.code
		status_text = devstatus.text

		if status_data is None:
			if status_code in C.STATUS_NAME:
				status_text = C.STATUS_NAME[status_code]
		elif isinstance(status_data, str):
			status_text = status_data
		elif isinstance(status_data, dict):
			status_text = ''
			for key, value in status_data.items():
				if key == 'text':
					status_text = value
				else:
					setattr(devstatus, key, value)
		else:
			_l.warn("don't know how to handle status %s", status_data)
			return False

		if status_code >= C.STATUS.CONNECTED and devstatus.type is None:
			# ghost device that became active
			if devstatus.code != C.STATUS.CONNECTED:
				# initial update, while we're getting the devinfo
				devstatus.code = C.STATUS.CONNECTED
				devstatus.text = C.STATUS_NAME[C.STATUS.CONNECTED]
				self.status_changed.set()
			if self._new_device(devstatus.number) is None:
				_l.warn("could not materialize device from %s", devstatus)
				return False

		if ((status_code == old_status_code and status_text == devstatus.text) or
			(status_code == C.STATUS.CONNECTED and old_status_code > C.STATUS.CONNECTED)):
			# this is just successful ping for a device with an already known status
			return False

		devstatus.code = status_code
		devstatus.text = status_text
		_l.debug("%s update %s => %s: %s", devstatus, old_status_code, status_code, status_text)

		if self.notify and (status_code <= C.STATUS.CONNECTED or status_code != old_status_code):
			self.notify(devstatus.code, devstatus.name, devstatus.text)

		self.status_changed.set()
		return True

	def _events_callback(self, event):
		if event.code == 0xFF and event.devnumber == 0xFF and event.data is None:
			self.no_receiver.set()
			return

		if event.code == 0x10 and event.data[0:2] == b'\x41\x04':
			# 2 = 0010 ping
			# 6 = 0110 off
			# a = 1010 on
			change = ord(event.data[2:3]) & 0xF0
			status_code = C.STATUS.UNAVAILABLE if change == 0x60 else \
							C.STATUS.CONNECTED if change == 0xA0 else \
							C.STATUS.CONNECTED if change == 0x20 else \
							None
			if status_code is None:
				_l.warn("don't know how to handle status %x: %s", change, event)
				return

			if event.devnumber in self.devices:
				devstatus = self.devices[event.devnumber]
				self._device_status_changed(devstatus, status_code)
				return

			if status_code == C.STATUS.CONNECTED:
				self._new_device(event.devnumber)
				return

			# a device the UR knows about, but is not connected at this time
			dev_id = self.listener.request(base.request, 0xFF, b'\x83\xB5', event.data[4:5])
			name = str(dev_id[2:].rstrip(b'\x00')) if dev_id else '?'
			name = devices.C.FULL_NAME[name]
			ghost = _DevStatus(handle=self.listener.receiver, number=event.devnumber, type=None, name=name, features=[])
			self.devices[event.devnumber] = ghost
			self._device_status_changed(ghost, C.STATUS.UNAVAILABLE)
			self._device_status_changed(self.rstatus, C.STATUS.CONNECTED, _OKAY)
			return

		if event.devnumber in self.devices:
			devstatus = self.devices[event.devnumber]
			if event.code == 0x11:
				status = devices.process_event(devstatus, event.data, self.listener)
				self._handle_status(devstatus, status)
				return
			if event.code == 0x10 and event.data[:1] == b'\x8F':
				self._device_status_changed(devstatus, C.STATUS.UNAVAILABLE)
				return

		_l.warn("don't know how to handle event %s", event)
