"""A few functions to deal with the Logitech Universal Receiver.

It is assumed a single UR device is attached to the machine.

Uses hidapi.
"""

import logging
import threading

from . import ur_lowlevel as urll
from urll import FEATURE


_log = logging.getLogger('logitech.ur')
_log.setLevel(logging.DEBUG)


# class NoDevice(Exception):
# 	"""May be thrown when trying to talk through a previously present device
# 	that is no longer available."""
# 	pass


class _EventQueue(threading.Thread):
	def __init__(self, receiver, timeout=urll.DEFAULT_TIMEOUT):
		super(_EventQueue, self).__init__()
		self.daemon = True
		self.receiver = receiver
		self.timeout = timeout
		self.active = True

	def stop(self):
		self.active = False
		self.join()

	def run(self):
		while self.active:
			data = urll.read(self.receiver.handle, self.timeout)
			if not self.active:
				# in case the queue has been stopped while reading
				break
			if data:
				self.receiver._dispatch(*data)


class Receiver:
	def __init__(self, path, handle=None, timeout=urll.DEFAULT_TIMEOUT):
		self.path = path
		self.handle = handle

		self.DEVICE_FEATURES = {}
		self.hooks = {}

		self.event_queue = _EventQueue(self.handle, timeout)
		self.event_queue.start()

	def close(self):
		self.event_queue.stop()
		self.event_queue = None

		urll.close(self.handle)
		self.handle = None

		self.hooks = {}
		self.DEVICE_FEATURES = {}

	def ping(self, device):
		reply = self.event_queue.req()
		if not urll.write(self.handle, device, '\x00\x10\x00\x00\xAA'):
			# print "write failed",
			return False

		reply = urll.read(self.handle, device)
		if not reply:
			# print "no data",
			return False

		# 10018f00100900
		if ord(reply[0]) == 0x10:
			if ord(reply[2]) == 0x8F:
				# print "invalid",
				return False

		# 110100100200aa00000000000000000000000000
		if ord(reply[0]) == 0x11:
			if reply[2:4] == "\x00\x10" and reply[6] == "\xAA":
				# success
				return True

		# print "unknown"
		return False

	def hook(self, device, feature, function=None, callback=None):
		features = self.DEVICE_FEATURES[device]
		if feature not in features:
			raise Exception("feature " + feature + " not supported by device")

		feature_index = features.index(feature)
		key = (device, feature_index, function, callback)
		if key not in self.hooks:
			self.hooks[key] = []
		if callback is None:
			if callback in self.hooks[key]:
				self.hooks[key].remove(callback)
		else:
			self.hooks[key].append(callback)

	def _dispatch(self, status, device, data):
		_log.debug("incoming event %2x:%2x:%s", status, device, data.encode('hex'))
		dispatched = False
		for (key, callback) in self.hooks.items():
			if key[0] == device and key[1] == ord(data[0]):
				if key[2] is not None and key[2] == data[1] & 0xFF:
					callback.__call__(data)

		if not dispatched:
			_log.debug("ignored incoming event %2x:%2x:%s",
						status, device, data.encode('hex'))

	def _request(self, device, data=''):
		if urll.write(self.handler, device, data):
			pass

	def find_device(self, device_type=None, name=None):
		"""Gets the device number for the first device matching.

		The device type and name are case-insensitive.
		"""
		# Apparently a receiver supports up to 6 devices.
		for device in range(1, 7):
			if self.ping(device):
				if device not in self.DEVICE_FEATURES:
					self.DEVICE_FEATURES[device] = \
								urll.get_device_features(self.handle, device)
				# print get_reprogrammable_keys(receiver, device)
				# d_firmware = get_firmware_version(receiver, device)
				# print "device", device, "[", d_name, "/", d_type, "]"
				# print "firmware", d_firmware, "features", _DEVICE_FEATURES[device]
				if device_type:
					d_type = self.get_type(device)
					if d_type is None or device_type.lower() != d_type.lower():
						continue
				if name:
					d_name = self.get_name(device)
					if d_name is None or name.lower() != d_name.lower():
						continue
				return device

	def get_type(self, device):
		reply = self._request(device, FEATURE.GET_NAME, '\x20')
		if reply:
			return DEVICE_TYPES[ord(reply[2][2])]

	def get_name(self, device):
		reply = self._request(device, FEATURE.GET_NAME)
		if reply:
			charcount = ord(reply[4])
			name = ''
			index = 0
			while len(name) < charcount:
				reply = self._request(device, FEATURE.NAME, '\x10', chr(index))
				if reply:
					name += reply[4:4 + charcount - index]
					index = len(name)
				else:
					break
			return name

	def get_firmware_version(self, device, firmware_type=0):
		reply = self._request(device,
						FEATURE.FIRMWARE, '\x10', chr(firmware_type))
		if reply:
			return '%s %s.%s' % (reply[5:8],
							reply[8:10].encode('hex'), reply[10:12].encode('hex'))

	def get_battery_level(self, device):
		reply = self._request(device, FEATURE.BATTERY)
		if reply:
			return (ord(reply[4]), ord(reply[5]), ord(reply[6]))

	def get_reprogrammable_keys(self, device):
		count = self._request(device, FEATURE.REPROGRAMMABLE_KEYS)
		if count:
			keys = []
			for index in range(ord(count[4])):
				key = self._request(device,
								FEATURE.REPROGRAMMABLE_KEYS, '\x10', chr(index))
				keys.append(key[4:6], keys[6:8], ord(key[8]))
			return keys

	def get_solar_charge(self, device):
		reply = self._request(device, FEATURE.SOLAR_CHARGE,
						'\x03', '\x78', '\x01', reply_function='\x10')
		if reply:
			charge = ord(reply[4])
			lux = ord(reply[5]) << 8 | ord(reply[6])
			# lux = int(round(((255 * ord(reply[5])) + ord(reply[6])) / 538.0, 2) * 100)
			return (charge, lux)


#
#
#

def get():
	"""Gets a Receiver object for the Unifying Receiver connected to the machine.

	It is assumed a single receiver is connected to the machine. If more than
	one are present, the first one found will be returned.

	:returns: a Receiver object, or None.
	"""
	receiver = urll.open()
	if receiver:
		return Receiver(*receiver)
