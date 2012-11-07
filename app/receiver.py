#
#
#

from logging import getLogger as _Logger
from struct import pack as _pack
from time import sleep as _sleep

from logitech.unifying_receiver import base as _base
from logitech.unifying_receiver import api as _api
from logitech.unifying_receiver.listener import EventsListener as _EventsListener
from logitech.unifying_receiver.common import FallbackDict as _FallbackDict
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
		if self.supported:
			if self.features is not None:
				return True

			if self.device.status >= STATUS.CONNECTED:
				handle = self.device.handle
				try:
					index = _api.get_feature_index(handle, self.device.number, _api.FEATURE.FEATURE_SET)
				except _api._FeatureNotSupported:
					self.supported = False
				else:
					count = None if index is None else _base.request(handle, self.device.number, _pack('!BB', index, 0x00))
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
			feature = _base.request(self.device.handle, self.device.number, _pack('!BB', fs_index, 0x10), _pack('!B', index))
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

#
#
#

class DeviceInfo(_api.PairedDevice):
	"""A device attached to the receiver.
	"""
	def __init__(self, listener, number, serial_prefix, status=STATUS.UNKNOWN):
		super(DeviceInfo, self).__init__(listener.handle, number)

		self.LOG = _Logger("Device[%d]" % number)
		self._listener = listener
		self._pair_code = _pack('!B', 0x40 + number - 1)
		self._serial_prefix = _base._hex(serial_prefix)
		self._serial = None
		self._codename = None

		self._status = status
		self.props = {}

		self.features = _FeaturesArray(self)

		# read them now, otherwise it it temporarily hang the UI
		# if status >= STATUS.CONNECTED:
		# 	n, k, s, f = self.name, self.kind, self.serial, self.firmware

	@property
	def receiver(self):
		return self._listener.receiver

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, new_status):
		if new_status != self._status and not (new_status == STATUS.CONNECTED and self._status > new_status):
			self.LOG.debug("status %d => %d", self._status, new_status)
			urgent = new_status < STATUS.CONNECTED or self._status < STATUS.CONNECTED
			self._status = new_status
			self._listener.status_changed(self, urgent)

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
			if self._status < STATUS.CONNECTED:
				codename = self.codename
				if codename in NAMES:
					self._name, self._kind = NAMES[codename]
			else:
				self._name = _api.get_device_name(self.handle, self.number, self.features)
		return self._name or self.codename

	@property
	def kind(self):
		if self._kind is None:
			if self._status < STATUS.CONNECTED:
				codename = self.codename
				if codename in NAMES:
					self._name, self._kind = NAMES[codename]
			else:
				self._kind = _api.get_device_kind(self.handle, self.number, self.features)
		return self._kind or '?'

	@property
	def serial(self):
		if self._serial is None:
			# dodgy
			b = bytearray(self._pair_code)
			b[0] -= 0x10
			serial = _base.request(self.handle, 0xFF, b'\x83\xB5', bytes(b))
			if serial:
				self._serial = self._serial_prefix + '-' + _base._hex(serial[1:5])
		return self._serial or self._serial_prefix + '-?'

	@property
	def codename(self):
		if self._codename is None:
			codename = _base.request(self.handle, 0xFF, b'\x83\xB5', self._pair_code)
			if codename:
				self._codename = codename[2:].rstrip(b'\x00').decode('ascii')
		return self._codename or '?'

	@property
	def firmware(self):
		if self._firmware is None:
			if self._status >= STATUS.CONNECTED:
				self._firmware = _api.get_device_firmware(self.handle, self.number, self.features)
		return self._firmware or ()

	def process_event(self, code, data):
		if code == 0x10 and data[:1] == b'\x8F':
			self.status = STATUS.UNAVAILABLE
			return True

		if code == 0x11:
			status = _devices.process_event(self, data)
			if status:
				if type(status) == int:
					self.status = status
					return True

				if type(status) == tuple:
					p = dict(self.props)
					self.props.update(status[1])
					if self.status == status[0]:
						if p != self.props:
							self._listener.status_changed(self)
					else:
						self.status = status[0]
					return True

				self.LOG.warn("don't know how to handle processed event status %s", status)

		return False

	def __str__(self):
		return 'DeviceInfo(%d,%s,%d)' % (self.number, self._name or '?', self._status)

#
#
#

_RECEIVER_STATUS_NAME = _FallbackDict(
							lambda x:
								'1 device found' if x == STATUS.CONNECTED + 1 else
								'%d devices found' if x > STATUS.CONNECTED else
								'?',
							{
								STATUS.UNKNOWN: 'Initializing...',
								STATUS.UNAVAILABLE: 'Receiver not found.',
								STATUS.BOOTING: 'Scanning...',
								STATUS.CONNECTED: 'No devices found.',
							}
						)

class ReceiverListener(_EventsListener):
	"""Keeps the status of a Unifying Receiver.
	"""

	def __init__(self, receiver, status_changed_callback=None):
		super(ReceiverListener, self).__init__(receiver.handle, self._events_handler)
		self.receiver = receiver

		self.LOG = _Logger("ReceiverListener(%s)" % receiver.path)

		self.events_filter = None
		self.events_handler = None

		self.status_changed_callback = status_changed_callback

		receiver.kind = receiver.name
		receiver.devices = {}
		receiver.status = STATUS.BOOTING
		receiver.status_text = _RECEIVER_STATUS_NAME[STATUS.BOOTING]

		if _base.request(receiver.handle, 0xFF, b'\x80\x00', b'\x00\x01'):
			self.LOG.info("initialized")
		else:
			self.LOG.warn("initialization failed")

		if _base.request(receiver.handle, 0xFF, b'\x80\x02', b'\x02'):
			self.LOG.info("triggered device events")
		else:
			self.LOG.warn("failed to trigger device events")

	def change_status(self, new_status):
		if new_status != self.receiver.status:
			self.LOG.debug("status %d => %d", self.receiver.status, new_status)
			self.receiver.status = new_status
			self.receiver.status_text = _RECEIVER_STATUS_NAME[new_status]
			self.status_changed(None, True)

	def status_changed(self, device=None, urgent=False):
		if self.status_changed_callback:
			self.status_changed_callback(self.receiver, device, urgent)

	def _device_status_from(self, event):
		state_code = ord(event.data[2:3]) & 0xC0
		state = STATUS.UNAVAILABLE if state_code == 0x40 else \
				STATUS.CONNECTED if state_code == 0x80 else \
				STATUS.CONNECTED if state_code == 0x00 else \
				None
		if state is None:
			self.LOG.warn("don't know how to handle state code 0x%02X: %s", state_code, event)
		return state

	def _events_handler(self, event):
		if self.events_filter and self.events_filter(event):
			return

		if event.code == 0x10 and event.data[0:2] == b'\x41\x04':

			if event.devnumber in self.receiver.devices:
				status = self._device_status_from(event)
				if status is not None:
					self.receiver.devices[event.devnumber].status = status
			else:
				dev = self.make_device(event)
				if dev is None:
					self.LOG.warn("failed to make new device from %s", event)
				else:
					self.receiver.devices[event.devnumber] = dev
					self.change_status(STATUS.CONNECTED + len(self.receiver.devices))
			return

		if event.devnumber == 0xFF:
			if event.code == 0xFF and event.data is None:
				# receiver disconnected
				self.LOG.warn("disconnected")
				self.receiver.devices = {}
				self.change_status(STATUS.UNAVAILABLE)
				return
		elif event.devnumber in self.receiver.devices:
			dev = self.receiver.devices[event.devnumber]
			if dev.process_event(event.code, event.data):
				return

		if self.events_handler and self.events_handler(event):
			return

		self.LOG.warn("don't know how to handle event %s", event)

	def make_device(self, event):
		if event.devnumber < 1 or event.devnumber > self.receiver.max_devices:
			self.LOG.warn("got event for invalid device number %d: %s", event.devnumber, event)
			return None

		status = self._device_status_from(event)
		if status is not None:
			serial_prefix = event.data[-1:] + event.data[-2:-1]
			dev = DeviceInfo(self, event.devnumber, serial_prefix, status)
			self.LOG.info("new device %s", dev)
			self.status_changed(dev, True)
			return dev

		self.LOG.error("failed to identify status of device %d from %s", event.devnumber, event)

	def unpair_device(self, device):
		try:
			del self.receiver[device.number]
		except IndexError:
			self.LOG.error("failed to unpair device %s", device)
			return False

		del self.receiver.devices[device.number]
		self.LOG.info("unpaired device %s", device)
		self.change_status(STATUS.CONNECTED + len(self.receiver.devices))
		device.status = STATUS.UNPAIRED
		return True

	def __str__(self):
		return '<ReceiverListener(%s,%d)>' % (self.receiver.path, self.receiver.status)

	@classmethod
	def open(self, status_changed_callback=None):
		receiver = _api.Receiver.open()
		if receiver:
			rl = ReceiverListener(receiver, status_changed_callback)
			rl.start()
			while not rl._active:
				_sleep(0.1)
			return rl

#
#
#

class _DUMMY_RECEIVER(object):
	__slots__ = ['name', 'max_devices', 'status', 'status_text', 'devices']
	name = kind = _api.Receiver.name
	max_devices = _api.Receiver.max_devices
	status = STATUS.UNAVAILABLE
	status_text = _RECEIVER_STATUS_NAME[STATUS.UNAVAILABLE]
	devices = {}
	__bool__ = __nonzero__ = lambda self: False
DUMMY = _DUMMY_RECEIVER()
