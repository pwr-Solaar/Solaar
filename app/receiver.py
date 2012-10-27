#
#
#

from logging import getLogger as _Logger

from threading import Event as _Event
from struct import pack as _pack

from logitech.unifying_receiver import base as _base
from logitech.unifying_receiver import api as _api
from logitech.unifying_receiver import listener as _listener
from logitech import devices as _devices
from logitech.devices.constants import (STATUS, STATUS_NAME, PROPS, NAMES)

#
#
#


class _FeaturesArray(object):
	__slots__ = ('device', 'features', 'supported')

	def __init__(self, device):
		self.device = device
		self.features = None
		self.supported = True

	def _check(self):
		if not self.supported:
			return False

		if self.features is not None:
			return True

		if self.device.status >= STATUS.CONNECTED:
			handle = self.device.receiver.handle
			try:
				index = _api.get_feature_index(handle, self.device.number, _api.FEATURE.FEATURE_SET)
			except _api._FeatureNotSupported:
				index = None

			if index is None:
				self.supported = False
			else:
				count = _base.request(handle, self.device.number, _pack('!B', index) + b'\x00')
				if count is None:
					self.supported = False
				else:
					count = ord(count[:1])
					self.features = [None] * (1 + count)
					self.features[0] = _api.FEATURE.ROOT
					self.features[index] = _api.FEATURE.FEATURE_SET
					return True

		return False

	__bool__ = __nonzero__ = _check

	def __getitem__(self, index):
		if not self._check():
			return None

		if index < 0 or index >= len(self.features):
			raise IndexError
		if self.features[index] is None:
			fs_index = self.features.index(_api.FEATURE.FEATURE_SET)
			feature = _base.request(self.device.receiver.handle, self.device.number, _pack('!BB', fs_index, 0x10), _pack('!B', index))
			if feature is not None:
				self.features[index] = feature[:2]

		return self.features[index]

	def __contains__(self, value):
		if self._check():
			if value in self.features:
				return True

			for index in range(0, len(self.features)):
				f = self.features[index] or self.__getitem__(index)
				assert f is not None
				if f == value:
					return True
				if f > value:
					break

		return False

	def index(self, value):
		if self._check():
			if self.features is not None and value in self.features:
				return self.features.index(value)
		raise ValueError("%s not in list" % repr(value))

	def __iter__(self):
		if self._check():
			yield _api.FEATURE.ROOT
			index = 1
			last_index = len(self.features)
			while index < last_index:
				yield self.__getitem__(index)
				index += 1

	def __len__(self):
		return len(self.features) if self._check() else 0


class DeviceInfo(object):
	"""A device attached to the receiver.
	"""
	def __init__(self, receiver, number, pair_code, status=STATUS.UNKNOWN):
		self.LOG = _Logger("Device[%d]" % number)
		self.receiver = receiver
		self.number = number
		self._pair_code = pair_code
		self._serial = None
		self._codename = None
		self._name = None
		self._kind = None
		self._firmware = None

		self._status = status
		self.props = {}

		self.features = _FeaturesArray(self)

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

		if new_status < STATUS.CONNECTED:
			self.props.clear()

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
				self._name = _api.get_device_name(self.receiver.handle, self.number, self.features)
		return self._name or self.codename

	@property
	def device_name(self):
		return self.name

	@property
	def kind(self):
		if self._kind is None:
			if self._status < STATUS.CONNECTED:
				codename = self.codename
				if codename in NAMES:
					self._kind = NAMES[codename][-1]
			else:
				self._kind = _api.get_device_kind(self.receiver.handle, self.number, self.features)
		return self._kind or '?'

	@property
	def serial(self):
		if self._serial is None:
			# dodgy
			b = bytearray(self._pair_code)
			b[0] -= 0x10
			serial = _base.request(self.receiver.handle, 0xFF, b'\x83\xB5', bytes(b))
			if serial:
				self._serial = _base._hex(serial[1:5])
		return self._serial or '?'

	@property
	def codename(self):
		if self._codename is None:
			codename = _base.request(self.receiver.handle, 0xFF, b'\x83\xB5', self._pair_code)
			if codename:
				self._codename = codename[2:].rstrip(b'\x00').decode('ascii')
		return self._codename or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			if self._status >= STATUS.CONNECTED:
				self._firmware = _api.get_device_firmware(self.receiver.handle, self.number, self.features)
		return self._firmware or ()

	def ping(self):
		return _api.ping(self.receiver.handle, self.number)

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

		self.LOG = _Logger("Receiver[%s]" % path)
		self.LOG.info("initializing")

		self._serial = None
		self._firmware = None

		self.devices = {}
		self.events_filter = None
		self.events_handler = None

		if _base.request(handle, 0xFF, b'\x80\x00', b'\x00\x01'):
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

	def count_devices(self):
		return _api.count_devices(self._handle)

	@property
	def serial(self):
		if self._serial is None:
			if self:
				self._serial, self._firmware = _api.get_receiver_info(self._handle)
		return self._serial or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			if self:
				self._serial, self._firmware = _api.get_receiver_info(self._handle)
		return self._firmware or ('?', '?')


	def _device_changed(self, dev, urgent=False):
		self.status_changed.reason = dev
		self.status_changed.urgent = urgent
		self.status_changed.set()

	def _events_handler(self, event):
		if self.events_filter and self.events_filter(event):
			return

		if event.code == 0x10 and event.data[0:2] == b'\x41\x04':
			if event.devnumber in self.devices:
				state_code = ord(event.data[2:3]) & 0xF0
				state = STATUS.UNAVAILABLE if state_code == 0x60 else \
						STATUS.CONNECTED if state_code == 0xA0 else \
						STATUS.CONNECTED if state_code == 0x20 else \
						None
				if state is None:
					self.LOG.warn("don't know how to handle status 0x%02X: %s", state_code, event)
				else:
					self.devices[event.devnumber].status = state
				return

			dev = self.make_device(event)
			if dev is None:
				self.LOG.warn("failed to make new device from %s", event)
			else:
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
		elif event.devnumber in self.devices:
			dev = self.devices[event.devnumber]
			if dev.process_event(event.code, event.data):
				return

		if self.events_handler and self.events_handler(event):
			return

		self.LOG.warn("don't know how to handle event %s", event)

	def make_device(self, event):
		if event.devnumber < 1 or event.devnumber > self.max_devices:
			self.LOG.warn("got event for invalid device number %d: %s", event.devnumber, event)
			return None

		state_code = ord(event.data[2:3]) & 0xF0
		state = STATUS.UNAVAILABLE if state_code == 0x60 else \
				STATUS.CONNECTED if state_code == 0xA0 else \
				STATUS.CONNECTED if state_code == 0x20 else \
				None
		if state is None:
			self.LOG.warn("don't know how to handle device status 0x%02X: %s", state_code, event)
			return None

		return DeviceInfo(self, event.devnumber, event.data[4:5], state)

	def unpair_device(self, number):
		if number in self.devices:
			dev = self.devices[number]
			reply = _base.request(self._handle, 0xFF, b'\x80\xB2', _pack('!BB', 0x03, number))
			if reply:
				self.LOG.debug("remove device %s => %s", dev, _base._hex(reply))
				del self.devices[number]
				self.LOG.warn("unpaired device %s", dev)
				self.status = STATUS.CONNECTED + len(self.devices)
				return True
			self.LOG.warn("failed to unpair device %s", dev)
		return False

	def __str__(self):
		return 'Receiver(%s,%X,%d)' % (self.path, self._handle, self._status)

	@classmethod
	def open(self):
		"""Opens the first Logitech Unifying Receiver found attached to the machine.

		:returns: An open file handle for the found receiver, or ``None``.
		"""
		for rawdevice in _base.list_receiver_devices():
			_Logger("receiver").debug("checking %s", rawdevice)
			handle = _base.try_open(rawdevice.path)
			if handle:
				receiver = Receiver(rawdevice.path, handle)
				receiver.start()
				return receiver

		return None
