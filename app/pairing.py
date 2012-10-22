#
#
#

from logging import getLogger as _Logger

from receiver import DeviceInfo as _DeviceInfo
from logitech.devices.constants import (STATUS, NAMES)

_l = _Logger('pairing')


class State(object):
	TICK = 300
	PAIR_TIMEOUT = 60 * 1000 / TICK

	def __init__(self, watcher):
		self._watcher = watcher
		self.reset()

	def reset(self):
		self.success = None
		self.detected_device = None
		self._countdown = self.PAIR_TIMEOUT

	def countdown(self, assistant):
		if self._countdown == self.PAIR_TIMEOUT:
			self.start_scan()
			self._countdown -= 1
			return True

		if self._countdown < 0:
			return False

		self._countdown -= 1
		if self._countdown > 0 and self.success is None:
			return True

		self.stop_scan()
		assistant.scan_complete(assistant, self.detected_device)
		return False

	def start_scan(self):
		self.reset()
		self._watcher.receiver.events_filter = self.filter_events
		reply = self._watcher.receiver.request(0xFF, b'\x80\xB2', b'\x01')
		_l.debug("start scan reply %s", repr(reply))

	def stop_scan(self):
		if self._countdown >= 0:
			self._countdown = -1
			reply = self._watcher.receiver.request(0xFF, b'\x80\xB2', b'\x02')
			_l.debug("stop scan reply %s", repr(reply))
			self._watcher.receiver.events_filter = None

	def filter_events(self, event):
		if event.devnumber == 0xFF:
			if event.code == 0x10:
				if event.data == b'\x4A\x01\x00\x00\x00':
					_l.debug("receiver listening for device wakeup")
					return True
				if event.data == b'\x4A\x00\x01\x00\x00':
					_l.debug("receiver gave up")
					self.success = False
					return True
			return False

		if event.devnumber in self._watcher.receiver.devices:
			return False

		_l.debug("event for new device? %s", event)
		if event.code == 0x10 and event.data[0:2] == b'\x41\x04':
			state_code = ord(event.data[2:3]) & 0xF0
			state = STATUS.UNAVAILABLE if state_code == 0x60 else \
					STATUS.CONNECTED if state_code == 0xA0 else \
					STATUS.CONNECTED if state_code == 0x20 else \
					None
			if state is None:
				_l.warn("don't know how to handle status 0x%02x: %s", state_code, event)
			elif event.devnumber < 1 or event.devnumber > self.max_devices:
				_l.warn("got event for invalid device number %d: %s", event.devnumber, event)
			else:
				dev = _DeviceInfo(self._watcher.receiver, event.devnumber, state)
				if state == STATUS.CONNECTED:
					n, k = dev.name, dev.kind
					_l.debug("detected active device %s", dev)
				else:
					# we can query the receiver for the device short name
					dev_id = self.request(0xFF, b'\x83\xB5', event.data[4:5])
					if dev_id:
						shortname = str(dev_id[2:].rstrip(b'\x00'))
						if shortname in NAMES:
							dev._name, dev._kind = NAMES[shortname]
							_l.debug("detected new device %s", dev)
						else:
							_l.warn("could not properly detect inactive device %d: %s", event.devnumber, shortname)
				self.detected_device = dev

		return True


def unpair(receiver, devnumber):
	reply = receiver.request(0xFF, b'\x80\xB2', b'\x03' + chr(devnumber))
	_l.debug("unpair %d reply %s", devnumber, repr(reply))

