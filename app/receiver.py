#
#
#

from logging import getLogger as _Logger
from struct import pack as _pack
from time import time as _timestamp

from logitech.unifying_receiver import base as _base
from logitech.unifying_receiver import api as _api
from logitech.unifying_receiver.listener import EventsListener as _EventsListener
from logitech.unifying_receiver.common import FallbackDict as _FallbackDict
from logitech import devices as _devices
from logitech.devices.constants import (STATUS, STATUS_NAME, PROPS)

#
#
#

class _FeaturesArray(object):
	__slots__ = ('device', 'features', 'supported')

	def __init__(self, device):
		assert device is not None
		self.device = device
		self.features = None
		self.supported = True

	def __del__(self):
		self.supported = False
		self.device = None

	def _check(self):
		# print ("%s check" % self.device)
		if self.supported:
			if self.features is not None:
				return True

			if self.device.protocol < 2.0:
				return False

			if self.device.status >= STATUS.CONNECTED:
				handle = int(self.device.handle)
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
			# print ("features getitem at %d" % index)
			fs_index = self.features.index(_api.FEATURE.FEATURE_SET)
			# technically fs_function is 0x10 for this call, but we add the index to differentiate possibly conflicting requests
			fs_function = 0x10 | (index & 0x0F)
			feature = _base.request(self.device.handle, self.device.number, _pack('!BB', fs_index, fs_function), _pack('!B', index))
			if feature is not None:
				self.features[index] = feature[:2]

		return self.features[index]

	def __contains__(self, value):
		if self._check():
			if value in self.features:
				return True

			# print ("features contains %s" % repr(value))
			for index in range(0, len(self.features)):
				f = self.features[index] or self.__getitem__(index)
				assert f is not None
				if f == value:
					return True
				# we know the features are ordered by value
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
	def __init__(self, handle, number, status_changed_callback, status=STATUS.BOOTING):
		super(DeviceInfo, self).__init__(handle, number)
		self.LOG = _Logger("Device[%d]" % (number))

		assert status_changed_callback
		self.status_changed_callback = status_changed_callback
		self._status = status
		self.status_updated = _timestamp()
		self.props = {}

		self._features = _FeaturesArray(self)

	def __del__(self):
		super(ReceiverListener, self).__del__()
		self._features.supported = False
		self._features.device = None

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, new_status):
		if new_status < STATUS.CONNECTED:
			for p in list(self.props):
				if p != PROPS.BATTERY_LEVEL:
					del self.props[p]
		else:
			self._features._check()
			self.protocol, self.codename, self.name, self.kind

		self.status_updated = _timestamp()
		old_status = self._status
		if new_status != old_status and not (new_status == STATUS.CONNECTED and old_status > new_status):
			self.LOG.debug("status %d => %d", old_status, new_status)
			self._status = new_status
			ui_flags = STATUS.UI_NOTIFY if new_status == STATUS.UNPAIRED else 0
			self.status_changed_callback(self, ui_flags)

	@property
	def status_text(self):
		if self._status < STATUS.CONNECTED:
			return STATUS_NAME[self._status]
		return STATUS_NAME[STATUS.CONNECTED]

	@property
	def properties_text(self):
		t = []
		if self.props.get(PROPS.BATTERY_LEVEL) is not None:
			t.append('Battery: %d%%' % self.props[PROPS.BATTERY_LEVEL])
		if self.props.get(PROPS.BATTERY_STATUS) is not None:
			t.append(self.props[PROPS.BATTERY_STATUS])
		if self.props.get(PROPS.LIGHT_LEVEL) is not None:
			t.append('Light: %d lux' % self.props[PROPS.LIGHT_LEVEL])
		return ', '.join(t)

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
					new_status, new_props = status
					ui_flags = new_props.pop(PROPS.UI_FLAGS, 0)
					old_props = dict(self.props)
					self.props.update(new_props)
					self.status = new_status
					if ui_flags or old_props != self.props:
						self.status_changed_callback(self, ui_flags)
					return True

				self.LOG.warn("don't know how to handle processed event status %s", status)

		return False

	def __str__(self):
		return '<DeviceInfo(%s,%d,%s,%d)>' % (self.handle, self.number, self.codename or '?', self._status)

#
#
#

_RECEIVER_STATUS_NAME = _FallbackDict(
							lambda x:
								'1 device found' if x == STATUS.CONNECTED + 1 else
								('%d devices found' % x) if x > STATUS.CONNECTED else
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
		self.LOG = _Logger("Receiver[%s]" % receiver.path)

		self.receiver = receiver
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

		self.LOG.info("reports %d device(s) paired", len(receiver))

	def __del__(self):
		super(ReceiverListener, self).__del__()
		self.receiver = None

	def trigger_device_events(self):
		if _base.request(int(self._handle), 0xFF, b'\x80\x02', b'\x02'):
			self.LOG.info("triggered device events")
			return True
		self.LOG.warn("failed to trigger device events")

	def change_status(self, new_status):
		if new_status != self.receiver.status:
			self.LOG.debug("status %d => %d", self.receiver.status, new_status)
			self.receiver.status = new_status
			self.receiver.status_text = _RECEIVER_STATUS_NAME[new_status]
			self.status_changed(None, STATUS.UI_NOTIFY)

	def status_changed(self, device=None, ui_flags=0):
		if self.status_changed_callback:
			self.status_changed_callback(self.receiver, device, ui_flags)

	def _device_status_from(self, event):
		state_code = ord(event.data[2:3]) & 0xC0
		state = STATUS.UNAVAILABLE if state_code == 0x40 else \
				STATUS.CONNECTED if state_code == 0x80 else \
				STATUS.CONNECTED if state_code == 0x00 else \
				None
		if state is None:
			self.LOG.warn("failed to identify status of device %d from 0x%02X: %s", event.devnumber, state_code, event)
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
				self.make_device(event)
			return

		if event.devnumber == 0xFF:
			if event.code == 0xFF and event.data is None:
				self.LOG.warn("disconnected")
				self.receiver.devices = {}
				self.change_status(STATUS.UNAVAILABLE)
				self.receiver = None
				return
		elif event.devnumber in self.receiver.devices:
			dev = self.receiver.devices[event.devnumber]
			if dev.process_event(event.code, event.data):
				return

		if self.events_handler and self.events_handler(event):
			return

		# self.LOG.warn("don't know how to handle event %s", event)

	def make_device(self, event):
		if event.devnumber < 1 or event.devnumber > self.receiver.max_devices:
			self.LOG.warn("got event for invalid device number %d: %s", event.devnumber, event)
			return None

		status = self._device_status_from(event)
		if status is not None:
			dev = DeviceInfo(self.handle, event.devnumber, self.status_changed, status)
			self.LOG.info("new device %s", dev)
			dev.status = status
			self.status_changed(dev, STATUS.UI_NOTIFY)
			self.receiver.devices[event.devnumber] = dev
			self.change_status(STATUS.CONNECTED + len(self.receiver.devices))
			if status == STATUS.CONNECTED:
				dev.serial, dev.firmware
			return dev

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
		return '<ReceiverListener(%s,%d,%d)>' % (self.receiver.path, int(self.handle), self.receiver.status)

	@classmethod
	def open(self, status_changed_callback=None):
		receiver = _api.Receiver.open()
		if receiver:
			handle = receiver.handle
			receiver.handle = _api.ThreadedHandle(handle, receiver.path)
			rl = ReceiverListener(receiver, status_changed_callback)
			rl.start()
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
