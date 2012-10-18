#
#
#

from logging import getLogger as _Logger
_LOG_LEVEL = 6

from threading import Event as _Event

from logitech.unifying_receiver import base as _base
from logitech.unifying_receiver import api as _api
from logitech.unifying_receiver import listener as _listener
from logitech import devices as _devices
from logitech.devices.constants import (STATUS, STATUS_NAME, PROPS, NAMES)

#
#
#

class DeviceInfo(object):
	"""A device attached to the receiver.
	"""
	def __init__(self, receiver, number, status=STATUS.UNKNOWN):
		self.LOG = _Logger("Device-%d" % number)
		self.receiver = receiver
		self.number = number
		self._name = None
		self._kind = None
		self._firmware = None
		self._features = None

		self._status = status
		self.props = {}

	@property
	def handle(self):
		return self.receiver.handle

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, new_status):
		if new_status != self._status and not (new_status == STATUS.CONNECTED and self._status > new_status):
			self.LOG.debug("status %d => %d", self._status, new_status)
			urgent = new_status < STATUS.CONNECTED or self._status < STATUS.CONNECTED
			self._status = new_status
			self.receiver._device_changed(self, urgent)

	@property
	def status_text(self):
		if self._status < STATUS.CONNECTED:
			return STATUS_NAME[self._status]

		t = []
		if self.props.get(PROPS.BATTERY_LEVEL):
			t.append('Battery: %d%%' % self.props[PROPS.BATTERY_LEVEL])
		if self.props.get(PROPS.BATTERY_STATUS):
			t.append(self.props[PROPS.BATTERY_STATUS])
		if self.props.get(PROPS.LIGHT_LEVEL):
			t.append('Light: %d lux' % self.props[PROPS.LIGHT_LEVEL])
		return ', '.join(t) if t else STATUS_NAME[STATUS.CONNECTED]

	@property
	def name(self):
		if self._name is None:
			if self._status >= STATUS.CONNECTED:
				self._name = self.receiver.request(_api.get_device_name, self.number, self.features)
		return self._name or '?'

	@property
	def device_name(self):
		return self.name

	@property
	def kind(self):
		if self._kind is None:
			if self._status >= STATUS.CONNECTED:
				self._kind = self.receiver.request(_api.get_device_kind, self.number, self.features)
		return self._kind or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			if self._status >= STATUS.CONNECTED:
				self._firmware = self.receiver.request(_api.get_device_firmware, self.number, self.features)
		return self._firmware or ()

	@property
	def features(self):
		if self._features is None:
			if self._status >= STATUS.CONNECTED:
				self._features = self.receiver.request(_api.get_device_features, self.number)
		return self._features or ()

	def ping(self):
		return self.receiver.request(_api.ping, self.number)

	def process_event(self, code, data):
		if code == 0x10 and data[:1] == b'\x8F':
			self.status = STATUS.UNAVAILABLE
			return True

		if code == 0x11:
			status = _devices.process_event(self, data, self.receiver)
			if status:
				if type(status) == int:
					self.status = status
					return True

				if type(status) == tuple:
					p = dict(self.props)
					self.props.update(status[1])
					if self.status == status[0]:
						if p != self.props:
							self.receiver._device_changed(self)
					else:
						self.status = status[0]
					return True

				self.LOG.warn("don't know how to handle status %s", status)

		return False

	def __hash__(self):
		return self.number

	def __str__(self):
		return 'DeviceInfo(%d,%s,%d)' % (self.number, self.name, self._status)

	def __repr__(self):
		return '<DeviceInfo(number=%d,name=%s,status=%d)>' % (self.number, self.name, self._status)

#
#
#

class Receiver(_listener.EventsListener):
	"""Keeps the status of a Unifying Receiver.
	"""
	NAME = kind = 'Unifying Receiver'
	max_devices = _api.MAX_ATTACHED_DEVICES

	def __init__(self, path, handle):
		super(Receiver, self).__init__(handle, self._events_handler)
		self.path = path

		self._status = STATUS.BOOTING
		self.status_changed = _Event()
		self.status_changed.urgent = False
		self.status_changed.reason = None

		self.LOG = _Logger("Receiver-%s" % path)
		self.LOG.info("initializing")

		self.devices = {}
		self.events_handler = None

		init = (_base.request(handle, 0xFF, b'\x81\x00') and
				_base.request(handle, 0xFF, b'\x80\x00', b'\x00\x01') and
				_base.request(handle, 0xFF, b'\x81\x02'))
		if init:
			self.LOG.info("initialized")
		else:
			self.LOG.warn("initialization failed")

		if _base.request(handle, 0xFF, b'\x80\x02', b'\x02'):
			self.LOG.info("triggered device events")
		else:
			self.LOG.warn("failed to trigger device events")

	def close(self):
		"""Closes the receiver's handle.

		The receiver can no longer be used in API calls after this.
		"""
		self.LOG.info("closing")
		self.stop()

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, new_status):
		if new_status != self._status:
			self.LOG.debug("status %d => %d", self._status, new_status)
			self._status = new_status
			self.status_changed.reason = self
			self.status_changed.urgent = True
			self.status_changed.set()

	@property
	def status_text(self):
		status = self._status
		if status == STATUS.UNKNOWN:
			return 'Initializing...'
		if status == STATUS.UNAVAILABLE:
			return 'Receiver not found.'
		if status == STATUS.BOOTING:
			return 'Scanning...'
		if status == STATUS.CONNECTED:
			return 'No devices found.'
		if len(self.devices) > 1:
			return '%d devices found' % len(self.devices)
		return '1 device found'

	@property
	def device_name(self):
		return self.NAME

	def _device_changed(self, dev, urgent=False):
		self.status_changed.reason = dev
		self.status_changed.urgent = urgent
		self.status_changed.set()

	def _events_handler(self, event):
		if event.code == 0x10 and event.data[0:2] == b'\x41\x04':
			state_code = ord(event.data[2:3]) & 0xF0
			state = STATUS.UNAVAILABLE if state_code == 0x60 else \
					STATUS.CONNECTED if state_code == 0xA0 else \
					STATUS.CONNECTED if state_code == 0x20 else \
					None
			if state is None:
				self.LOG.warn("don't know how to handle status 0x%02x: %s", state_code, event)
				return

			if event.devnumber in self.devices:
				self.devices[event.devnumber].status = state
				return

			if event.devnumber < 1 or event.devnumber > self.max_devices:
				self.LOG.warn("got event for invalid device number %d: %s", event.devnumber, event)
				return

			dev = DeviceInfo(self, event.devnumber, state)
			if state == STATUS.CONNECTED:
				n, k = dev.name, dev.kind
			else:
				# we can query the receiver for the device short name
				dev_id = self.request(_base.request, 0xFF, b'\x83\xB5', event.data[4:5])
				if dev_id:
					shortname = str(dev_id[2:].rstrip(b'\x00'))
					if shortname in NAMES:
						dev._name, dev._kind = NAMES[shortname]
					else:
						self.LOG.warn("could not properly detect inactive device %d: %s", event.devnumber, shortname)
			self.devices[event.devnumber] = dev
			self.LOG.info("new device ready %s", dev)
			self.status = STATUS.CONNECTED + len(self.devices)
			return

		if event.devnumber == 0xFF:
			if event.code == 0xFF and event.data is None:
				# receiver disconnected
				self.LOG.info("disconnected")
				self.devices = {}
				self.status = STATUS.UNAVAILABLE
				return
			self.LOG.warn("don't know how to handle event %s", event)
		elif event.devnumber in self.devices:
			dev = self.devices[event.devnumber]
			if dev.process_event(event.code, event.data):
				return

		if self.events_handler:
			self.events_handler(event)

	def __str__(self):
		return 'Receiver(%s,%x,%d:%d)' % (self.path, self._handle, self._active, self._status)

	@classmethod
	def open(self):
		"""Opens the first Logitech Unifying Receiver found attached to the machine.

		:returns: An open file handle for the found receiver, or ``None``.
		"""
		for rawdevice in _base.list_receiver_devices():
			_Logger("receiver").log(_LOG_LEVEL, "checking %s", rawdevice)

			handle = _base.try_open(rawdevice.path)
			if handle:
				receiver = Receiver(rawdevice.path, handle)
				receiver.start()
				return receiver

		return None
