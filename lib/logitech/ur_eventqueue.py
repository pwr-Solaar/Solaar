"""Low-level interface for devices connected through a Logitech Universal
Receiver (UR).

Uses the HID api exposed through hidapi.py.
Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

In the context of this API, 'device' is the number (1..6 according to the
documentation) of the device attached to the UR.

References:
http://julien.danjou.info/blog/2012/logitech-k750-linux-support
http://6xq.net/git/lars/lshidpp.git/plain/doc/
"""


#
# Logging set-up.
# Add a new logging level for tracing low-level writes and reads.
#

import logging
import threading

from . import hidapi


LOG_LEVEL = 1

def _urll_trace(self, msg, *args):
	if self.isEnabledFor(LOG_LEVEL):
		args = (None if x is None
				else x.encode('hex') if type(x) == str and any(c < '\x20' or c > '\x7E' for c in x)
				else x
				for x in args)
		self.log(LOG_LEVEL, msg, *args)

logging.addLevelName(LOG_LEVEL, 'trace1')
logging.Logger.trace1 = _urll_trace
_log = logging.getLogger('logitech.ur_lowlevel')
_log.setLevel(LOG_LEVEL)


#
#
#


"""Possible features available on a Logitech device.

A particular device might not support all these features, and may support other
unknown features as well.
"""
FEATURE = type('FEATURE', (),
				dict(
					ROOT=b'\x00\x00',
					FEATURE_SET=b'\x00\x01',
					FIRMWARE=b'\x00\x03',
					NAME=b'\x00\x05',
					BATTERY=b'\x10\x00',
					REPROGRAMMABLE_KEYS=b'\x1B\x00',
					WIRELESS_STATUS=b'\x1D\x4B',
					# UNKNOWN_1=b'\x1D\xF3',
					# UNKNOWN_2=b'\x40\xA0',
					# UNKNOWN_3=b'\x41\x00',
					SOLAR_CHARGE=b'\x43\x01',
					# UNKNOWN_4=b'\x45\x20',
				))


"""Possible types of devices connected to an UR."""
DEVICE_TYPES = ("Keyboard", "Remote Control", "NUMPAD", "Mouse",
				"Touchpad", "Trackball", "Presenter", "Receiver")


"""Default timeout on read (in ms)."""
DEFAULT_TIMEOUT = 1000


"""Minimum size of a reply data packet."""
_MIN_REPLY_SIZE = 7


"""Maximum size of a reply data packet."""
_MAX_REPLY_SIZE = 32

class NoReceiver(Exception):
	"""May be raised when trying to talk through a previously connected
	receiver that is no longer available."""
	pass


#
#
#


class Receiver(threading.Thread):
	def __init__(self, handle, path, timeout=DEFAULT_TIMEOUT):
		super(Receiver, self).__init__(name='Unifying_Receiver_' + path)
		self.handle = handle
		self.path = path
		self.timeout = timeout

		self.read_data = None
		self.data_available = threading.Event()

		self.devices = {}
		self.hooks = {}

		self.active = True
		self.start()

	def __del__(self):
		self.close()

	def close(self):
		self.active = False

		try:
			hidapi.close(self.handle)
			_log.trace1("|%s:| closed", self.path)
			return True
		except Exception as e:
			_log.warn("|%s:| closing: %s", self.path, e)

		self.hooks = None
		self.devices = None

	def run(self):
		while self.active:
			data = hidapi.read(self.handle, _MAX_REPLY_SIZE, self.timeout)
			if self.active and data:
				_log.trace1("|%s|*| => r[%s]", self.path, data)
				if len(data) < _MIN_REPLY_SIZE:
					_log.trace1("|%s|*| => r[%s] short read", self.path, data)
				if len(data) > _MAX_REPLY_SIZE:
					_log.trace1("|%s|*| => r[%s] long read", self.path, data)
				if not self._dispatch_to_hooks(data):
					self.read_data = data
					self.data_available.set()

	def _dispatch_to_hooks(self, data):
		if data[0] == b'\x11':
			for key in self.hooks:
				if key == data[1:3]:
					self.hooks[key].__call__(data[3:])
					return True

	def set_hook(self, device, feature_index, function=b'\x00', callback=None):
		key = '%c%s%c' % (device, feature_index, function)
		if callback is None:
			if key in self.hooks:
				del self.hooks[key]
		else:
			self.hooks[key] = callback
		return True

	def _write(self, device, data):
		wdata = b'\x10' + chr(device) + data + b'\x00' * (5 - len(data))
		if hidapi.write(self.handle, wdata):
			_log.trace1("|%s|%d| <= w[%s]", self.path, device, wdata)
			return True
		else:
			_log.trace1("|%s|%d| <= w[%s] failed ", self.path, device, wdata)
			raise NoReceiver()

	def _read(self, device, feature_index=None, function=None, timeout=DEFAULT_TIMEOUT):
		while True:
			self.data_available.wait()
			data = self.data
			self.data_available.clear()

			if data[1] == chr(device):
				if feature_index is None or data[2] == feature_index:
					if function is None or data[3] == function:
						return data

			_log.trace1("|%s:| ignoring read data [%s]", self.path, data)

	def _request(self, device, feature_index, function=b'\x00', data=b''):
		self._write(device, feature_index + function + data)
		return self._read(device, feature_index, function)

	def _request_direct(self, device, feature_index, function=b'\x00', data=b''):
		self._write(device, feature_index + function + data)
		while True:
			data = hidapi.read(self.handle, _MAX_REPLY_SIZE, self.timeout)

			if not data:
				continue

			if data[1] == chr(device) and data[2] == feature_index and data[3] == function:
				return data


	def ping(self, device):
		"""Pings a device to check if it is attached to the UR.

		:returns: True if the device is connected to the UR, False if the device is
		not attached, None if no conclusive reply is received.
		"""
		if self._write(device, b'\x00\x10\x00\x00\xAA'):
			while True:
				reply = self._read(device, timeout=DEFAULT_TIMEOUT*3)

				# ping ok
				if reply[0] == b'\0x11' and reply[1] == chr(device):
					if reply[2:4] == b'\x00\x10' and reply[6] == b'\xAA':
						_log.trace1("|%s|%d| ping: ok %s", self.path, device, reply[2])
						return True

				# ping failed
				if reply[0] == b'\0x10' and reply[1] == chr(device):
					if reply[2:4] == b'\x8F\x00':
						_log.trace1("|%s|%d| ping: device not present", self.path, device)
						return False

				_log.trace1("|%s|%d| ping: unknown reply", self.path, device, reply)

	def scan_devices(self):
		for device in range(1, 7):
			self.get_device(device)

		return self.devices.values()

	def get_device(self, device, query=True):
		if device in self.devices:
			value = self.devices[device]
			_log.trace1("|%s:%d| device info %s", self.path, device, value)
			return value

		if query and self.ping(device):
			d_type = self.get_type(device)
			d_name = self.get_name(device)
			features_array = self._get_features(device)
			value = (d_type, d_name, features_array)
			self.devices[device] = value
			_log.trace1("|%s:%d| device info %s", self.path, device, value)
			return value

		_log.trace1("|%s:%d| device not found", self.path, device)

	def _get_feature_index(self, device, feature):
		"""Reads the index of a device's feature.

		:returns: An int, or None if the feature is not available.
		"""
		_log.trace1("|%s|%d| get feature index <%s>", self.path, device, feature)
		reply = self._request(device, b'\x00', b'\x00', feature)
		# only consider active and supported features
		if ord(reply[4]) and ord(reply[5]) & 0xA0 == 0:
			_log.trace1("|%s|%d| feature <%s> has index %s", self.path, device, feature, reply[4])
			return ord(reply[4])

		_log.trace1("|%s|%d| feature <%s> not available", self.path, device, feature)

	def _get_features(self, device):
		"""Returns an array of feature ids.

		Their position in the array is the index to be used when accessing that
		feature on the device.

		Only call this function in the initial set-up of the device, because
		other messages and events not related to querying the feature set
		will be ignored.
		"""
		_log.trace1("|%s|%d| get device features", self.path, device)

		# get the index of the FEATURE_SET
		fs_index = self._get_feature_index(device, FEATURE.FEATURE_SET)
		fs_index = chr(fs_index)

		# Query all the available features on the device, even if unknown.

		# get the number of active features the device has
		features_count = self._request(device, fs_index)
		features_count = ord(features_count[4])
		_log.trace1("|%s|%d| found %d features", self.path, device, features_count)

		# a device may have a maximum of 15 features
		features = [None] * 0x10
		for index in range(1, 1 + features_count):
			# for each index, get the feature residing at that index
			feature = self._request(device, fs_index, b'\x10', chr(index))
			features[index] = feature[4:6].upper()
			_log.trace1("|%s|%d| feature <%s> at index %d", self.path, device, features[index], index)

		return None if all(c is None for c in features) else features

	def get_type(self, device):
		if device in self.devices:
			return self.devices[device][0]

		dnt_index = self._get_feature_index(device, FEATURE.NAME)
		dnt_index = chr(dnt_index)
		d_type = self._request(device, dnt_index, b'\x20')
		d_type = ord(d_type[4])
		return DEVICE_TYPES[d_type]

	def get_name(self, device):
		if device in self.devices:
			return self.devices[device][1]

		dnt_index = self._get_feature_index(device, FEATURE.NAME)
		dnt_index = chr(dnt_index)
		self._write(device, dnt_index)
		name_length = self._read(device, dnt_index, b'\x00')
		name_length = ord(name_length[4])

		d_name = ''
		while len(d_name) < name_length:
			name_index = len(d_name)
			name_fragment = self._request(device, dnt_index, b'\x10', chr(name_index))
			name_fragment = name_fragment[:name_length - len(d_name)]
			d_name += name_fragment

		return d_name



def open():
	"""Opens the first Logitech UR found attached to the machine.

	:returns: A Receiver object for the found receiver, or ``None``.
	"""
	# USB ids for (Logitech, Unifying Receiver)
	# interface 2 if the actual receiver interface
	for rawdevice in hidapi.enumerate(0x046d, 0xc52b, 2):

		_log.trace1("checking %s", rawdevice)
		receiver = hidapi.open_path(rawdevice.path)
		if not receiver:
			# could be a file permissions issue
			# in any case, unreachable
			_log.trace1("[%s] open failed", rawdevice.path)
			continue

		_log.trace1("[%s] receiver handle %d", rawdevice.path, receiver)
		# ping on device id 0 (always an error)
		hidapi.write(receiver, b'\x10\x00\x00\x10\x00\x00\xAA')

		# if this is the right hidraw device, we'll receive a 'bad subdevice'
		# otherwise, the read should produce nothing
		reply = hidapi.read(receiver, _MAX_REPLY_SIZE, DEFAULT_TIMEOUT)
		if reply:
			_log.trace1("[%s] receiver %d exploratory ping reply [%s]", rawdevice.path, receiver, reply)

			if reply[:4] == b'\x10\x00\x8F\x00':
				# 'device 0 unreachable' is the expected reply from a valid receiver handle
				_log.trace1("[%s] success: found receiver with handle %d", rawdevice.path, receiver)
				return Receiver(receiver, rawdevice.path)

			if reply == b'\x01\x00\x00\x00\x00\x00\x00\x00':
				# no idea what this is, but it comes up occasionally
				_log.trace1("[%s] receiver %d mistery reply", rawdevice.path, receiver)
			else:
				_log.trace1("[%s] receiver %d unknown reply", rawdevice.path, receiver)
		else:
			_log.trace1("[%s] receiver %d no reply", rawdevice.path, receiver)
			pass

		# ignore
		hidapi.close(receiver)
