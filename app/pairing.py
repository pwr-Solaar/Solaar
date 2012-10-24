#
#
#

from logging import getLogger as _Logger
_l = _Logger('pairing')


state = None

class State(object):
	TICK = 300
	PAIR_TIMEOUT = 60 * 1000 / TICK

	def __init__(self, watcher):
		self._watcher = watcher
		self.reset()

	def device(self, number):
		return self._watcher.receiver.devices.get(number)

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
			self.detected_device = self._watcher.receiver.make_device(event)
			return True

		return True

	def unpair(self, number):
		_l.debug("unpair %d", number)
		self._watcher.receiver.unpair_device(number)
