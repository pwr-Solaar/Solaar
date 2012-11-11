#
#
#

from logging import getLogger as _Logger
_l = _Logger('pairing')

from logitech.unifying_receiver import base as _base

state = None

class State(object):
	TICK = 400
	PAIR_TIMEOUT = 60 * 1000 / TICK

	def __init__(self, listener):
		self.listener = listener
		self.reset()

	def device(self, number):
		return self.listener.devices.get(number)

	def reset(self):
		self.success = None
		self.detected_device = None
		self._countdown = self.PAIR_TIMEOUT

	def countdown(self, assistant):
		if self._countdown < 0 or not self.listener:
			return False

		if self._countdown == self.PAIR_TIMEOUT:
			self.start_scan()
			self._countdown -= 1
			return True

		self._countdown -= 1
		if self._countdown > 0 and self.success is None:
			return True

		self.stop_scan()
		assistant.scan_complete(assistant, self.detected_device)
		return False

	def start_scan(self):
		self.reset()
		self.listener.events_filter = self.filter_events
		reply = _base.request(self.listener.handle, 0xFF, b'\x80\xB2', b'\x01')
		_l.debug("start scan reply %s", repr(reply))

	def stop_scan(self):
		if self._countdown >= 0:
			self._countdown = -1
			reply = _base.request(self.listener.handle, 0xFF, b'\x80\xB2', b'\x02')
			_l.debug("stop scan reply %s", repr(reply))
			self.listener.events_filter = None

	def filter_events(self, event):
		if event.devnumber == 0xFF:
			if event.code == 0x10:
				if event.data == b'\x4A\x01\x00\x00\x00':
					_l.debug("receiver listening for device wakeup")
					return True
				if event.data == b'\x4A\x00\x01\x00\x00':
					_l.debug("receiver gave up")
					self.success = False
					# self.success = True
					# self.detected_device = self.listener.receiver.devices[1]
					return True
			return False

		if event.devnumber in self.listener.receiver.devices:
			return False

		_l.debug("event for new device? %s", event)
		if event.code == 0x10 and event.data[0:2] == b'\x41\x04':
			self.detected_device = self.listener.make_device(event)
			return True

		return True

	def unpair(self, device):
		return self.listener.unpair_device(device)
