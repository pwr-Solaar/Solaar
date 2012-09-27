#
# Logitech Unifying Receiver API.
#

import logging
import struct
from binascii import hexlify

from .constants import *
from .exceptions import *
from . import base
from .unhandled import _publish as _unhandled_publish


_LOG_LEVEL = 5
_l = logging.getLogger('logitech.unifying_receiver.api')

#
#
#

from collections import namedtuple

"""Tuple returned by list_devices and find_device_by_name."""
AttachedDeviceInfo = namedtuple('AttachedDeviceInfo', [
				'number',
				'type',
				'name',
				'firmware',
				'features_array'])

"""Firmware information."""
FirmwareInfo = namedtuple('FirmwareInfo', [
				'level',
				'type',
				'name',
				'version',
				'build',
				'extras'])

def _makeFirmwareInfo(level, type, name=None, version=None, build=None, extras=None):
	return FirmwareInfo(level, type, name, version, build, extras)

del namedtuple

#
#
#

def open():
	"""Opens the first Logitech UR found attached to the machine.

	:returns: An open file handle for the found receiver, or ``None``.
	"""
	for rawdevice in base.list_receiver_devices():
		_l.log(_LOG_LEVEL, "checking %s", rawdevice)

		receiver = base.try_open(rawdevice.path)
		if receiver:
			return receiver

	return None


"""Closes a HID device handle."""
close = base.close


def request(handle, device, feature, function=b'\x00', params=b'', features_array=None):
	"""Makes a feature call to the device, and returns the reply data.

	Basically a write() followed by (possibly multiple) reads, until a reply
	matching the called feature is received. In theory the UR will always reply
	to feature call; otherwise this function will wait indefinitely.

	Incoming data packets not matching the feature and function will be
	delivered to the unhandled hook (if any), and ignored.

	The optional ``features_array`` parameter is a cached result of the
	get_device_features function for this device, necessary to find the feature
	index. If the ``features_arrary`` is not provided, one will be obtained by
	manually calling get_device_features before making the request call proper.

	:raises FeatureNotSupported: if the device does not support the feature.
	"""

	feature_index = None
	if feature == FEATURE.ROOT:
		feature_index = b'\x00'
	else:
		if features_array is None:
			features_array = get_device_features(handle, device)
			if features_array is None:
				_l.log(_LOG_LEVEL, "(%d,%d) no features array available", handle, device)
				return None
		if feature in features_array:
			feature_index = struct.pack('!B', features_array.index(feature))

	if feature_index is None:
		_l.warn("(%d,%d) feature <%s:%s> not supported", handle, device, hexlify(feature), FEATURE_NAME(feature))
		raise FeatureNotSupported(device, feature)

	return base.request(handle, device, feature_index + function, params)


def ping(handle, device):
	"""Pings a device number to check if it is attached to the UR.

	:returns: True if the device is connected to the UR, False if the device is
	not attached, None if no conclusive reply is received.
	"""

	ping_marker = b'\xAA'

	def _status(reply):
		if not reply:
			return None

		reply_code, reply_device, reply_data = reply

		if reply_device != device:
			# oops
			_l.log(_LOG_LEVEL, "(%d,%d) ping: reply for another device %d: %s", handle, device, reply_device, hexlify(reply_data))
			_unhandled_publish(reply_code, reply_device, reply_data)
			return _status(base.read(handle))

		if (reply_code == 0x11 and reply_data[:2] == b'\x00\x10' and reply_data[4:5] == ping_marker):
			# ping ok
			_l.log(_LOG_LEVEL, "(%d,%d) ping: ok [%s]", handle, device, hexlify(reply_data))
			return True

		if (reply_code == 0x10 and reply_data[:2] == b'\x8F\x00'):
			# ping failed
			_l.log(_LOG_LEVEL, "(%d,%d) ping: device not present", handle, device)
			return False

		if (reply_code == 0x11 and reply_data[:2] == b'\x09\x00' and len(reply_data) == 18 and reply_data[7:11] == b'GOOD'):
			# some devices may reply with a SOLAR_CHARGE event before the
			# ping_ok reply, especially right after the device connected to the
			# receiver
			_l.log(_LOG_LEVEL, "(%d,%d) ping: solar status %s", handle, device, hexlify(reply_data))
			_unhandled_publish(reply_code, reply_device, reply_data)
			return _status(base.read(handle))

		# ugh
		_l.log(_LOG_LEVEL, "(%d,%d) ping: unknown reply for this device: %d=[%s]", handle, device, reply[0], hexlify(reply[2]))
		_unhandled_publish(reply_code, reply_device, reply_data)
		return None

	_l.log(_LOG_LEVEL, "(%d,%d) pinging", handle, device)
	base.write(handle, device, b'\x00\x10\x00\x00' + ping_marker)
	# pings may take a while to reply success
	return _status(base.read(handle, base.DEFAULT_TIMEOUT * 3))


def find_device_by_name(handle, device_name):
	"""Searches for an attached device by name.

	:returns: an AttachedDeviceInfo tuple, or ``None``.
	"""
	_l.log(_LOG_LEVEL, "(%d,) searching for device '%s'", handle, device_name)

	for device in range(1, 1 + base.MAX_ATTACHED_DEVICES):
		features_array = get_device_features(handle, device)
		if features_array:
			d_name = get_device_name(handle, device, features_array)
			if d_name == device_name:
				return get_device_info(handle, device, device_name=d_name, features_array=features_array)


def list_devices(handle):
	"""List all devices attached to the UR.

	:returns: a list of AttachedDeviceInfo tuples.
	"""
	_l.log(_LOG_LEVEL, "(%d,) listing all devices", handle)

	devices = []

	for device in range(1, 1 + base.MAX_ATTACHED_DEVICES):
		features_array = get_device_features(handle, device)
		if features_array:
			devices.append(get_device_info(handle, device, features_array=features_array))

	return devices


def get_device_info(handle, device, device_name=None, features_array=None):
	"""Gets the complete info for a device (type, name, firmwares, and features_array).

	:returns: an AttachedDeviceInfo tuple, or ``None``.
	"""
	if features_array is None:
		features_array = get_device_features(handle, device)
		if features_array is None:
			return None

	d_type = get_device_type(handle, device, features_array)
	d_name = get_device_name(handle, device, features_array) if device_name is None else device_name
	d_firmware = get_device_firmware(handle, device, features_array)
	devinfo = AttachedDeviceInfo(device, d_type, d_name, d_firmware, features_array)
	_l.log(_LOG_LEVEL, "(%d,%d) found device %s", handle, device, devinfo)
	return devinfo


def get_feature_index(handle, device, feature):
	"""Reads the index of a device's feature.

	:returns: An int, or ``None`` if the feature is not available.
	"""
	_l.log(_LOG_LEVEL, "(%d,%d) get feature index <%s:%s>", handle, device, hexlify(feature), FEATURE_NAME(feature))
	if len(feature) != 2:
		raise ValueError("invalid feature <%s>: it must be a two-byte string" % feature)

	# FEATURE.ROOT should always be available for any attached devices
	reply = base.request(handle, device, FEATURE.ROOT, feature)
	if reply:
		# only consider active and supported features
		feature_index = ord(reply[0:1])
		if feature_index:
			feature_flags = ord(reply[1:2]) & 0xE0
			_l.log(_LOG_LEVEL, "(%d,%d) feature <%s:%s> has index %d flags %02x", handle, device, hexlify(feature), FEATURE_NAME(feature), feature_index, feature_flags)
			if feature_flags == 0:
				return feature_index

			if feature_flags & 0x80:
				_l.warn("(%d,%d) feature <%s:%s> not supported: obsolete", handle, device, hexlify(feature), FEATURE_NAME(feature))
			if feature_flags & 0x40:
				_l.warn("(%d,%d) feature <%s:%s> not supported: hidden", handle, device, hexlify(feature), FEATURE_NAME(feature))
			if feature_flags & 0x20:
				_l.warn("(%d,%d) feature <%s:%s> not supported: Logitech internal", handle, device, hexlify(feature), FEATURE_NAME(feature))
			raise FeatureNotSupported(device, feature)
		else:
			_l.warn("(%d,%d) feature <%s:%s> not supported by the device", handle, device, hexlify(feature), FEATURE_NAME(feature))
			raise FeatureNotSupported(device, feature)


def get_device_features(handle, device):
	"""Returns an array of feature ids.

	Their position in the array is the index to be used when requesting that
	feature on the device.
	"""
	_l.log(_LOG_LEVEL, "(%d,%d) get device features", handle, device)

	# get the index of the FEATURE_SET
	# FEATURE.ROOT should always be available for all devices
	fs_index = base.request(handle, device, FEATURE.ROOT, FEATURE.FEATURE_SET)
	if fs_index is None:
		# _l.warn("(%d,%d) FEATURE_SET not available", handle, device)
		return None
	fs_index = fs_index[:1]

	# For debugging purposes, query all the available features on the device,
	# even if unknown.

	# get the number of active features the device has
	features_count = base.request(handle, device, fs_index + b'\x00')
	if not features_count:
		# this can happen if the device disappeard since the fs_index request
		# otherwise we should get at least a count of 1 (the FEATURE_SET we've just used above)
		_l.log(_LOG_LEVEL, "(%d,%d) no features available?!", handle, device)
		return None

	features_count = ord(features_count[:1])
	_l.log(_LOG_LEVEL, "(%d,%d) found %d features", handle, device, features_count)

	# a device may have a maximum of 15 features, other than FEATURE.ROOT
	features = [None] * 0x10
	for index in range(1, 1 + features_count):
		# for each index, get the feature residing at that index
		feature = base.request(handle, device, fs_index + b'\x10', struct.pack('!B', index))
		if feature:
			feature = feature[0:2].upper()
			features[index] = feature
			_l.log(_LOG_LEVEL, "(%d,%d) feature <%s:%s> at index %d", handle, device, hexlify(feature), FEATURE_NAME(feature), index)

	return None if all(c == None for c in features) else features


def get_device_firmware(handle, device, features_array=None):
	"""Reads a device's firmware info.

	:returns: a list of FirmwareInfo tuples, ordered by firmware layer.
	"""
	fw_count = request(handle, device, FEATURE.FIRMWARE, features_array=features_array)
	if fw_count:
		fw_count = ord(fw_count[:1])

		fw = []
		for index in range(0, fw_count):
			index = struct.pack('!B', index)
			fw_info = request(handle, device, FEATURE.FIRMWARE, function=b'\x10', params=index, features_array=features_array)
			if fw_info:
				fw_level = ord(fw_info[:1]) & 0x0F
				if fw_level == 0 or fw_level == 1:
					fw_type = FIRMWARE_TYPES[fw_level]
					name, = struct.unpack('!3s', fw_info[1:4])
					name = name.decode('ascii')
					version = ( chr(0x30 + (ord(fw_info[4:5]) >> 4)) +
								chr(0x30 + (ord(fw_info[4:5]) & 0x0F)) +
								'.' +
								chr(0x30 + (ord(fw_info[5:6]) >> 4)) +
								chr(0x30 + (ord(fw_info[5:6]) & 0x0F)))
					build, = struct.unpack('!H', fw_info[6:8])
					extras = fw_info[9:].rstrip(b'\x00')
					if extras:
						fw_info = _makeFirmwareInfo(level=fw_level, type=fw_type, name=name, version=version, build=build, extras=extras)
					else:
						fw_info = _makeFirmwareInfo(level=fw_level, type=fw_type, name=name, version=version, build=build)
				elif fw_level == 2:
					fw_info = _makeFirmwareInfo(level=2, type=FIRMWARE_TYPES[2], version=ord(fw_info[1:2]))
				else:
					fw_info = _makeFirmwareInfo(level=fw_level, type=FIRMWARE_TYPES[-1])

				fw.append(fw_info)
				_l.log(_LOG_LEVEL, "(%d:%d) firmware %s", handle, device, fw_info)
		return fw


def get_device_type(handle, device, features_array=None):
	"""Reads a device's type.

	:see DEVICE_TYPES:
	:returns: a string describing the device type, or ``None`` if the device is
	not available or does not support the ``NAME`` feature.
	"""
	d_type = request(handle, device, FEATURE.NAME, function=b'\x20', features_array=features_array)
	if d_type:
		d_type = ord(d_type[:1])
		_l.log(_LOG_LEVEL, "(%d,%d) device type %d = %s", handle, device, d_type, DEVICE_TYPES[d_type])
		return DEVICE_TYPES[d_type]


def get_device_name(handle, device, features_array=None):
	"""Reads a device's name.

	:returns: a string with the device name, or ``None`` if the device is not
	available or does not support the ``NAME`` feature.
	"""
	name_length = request(handle, device, FEATURE.NAME, features_array=features_array)
	if name_length:
		name_length = ord(name_length[:1])

		d_name = b''
		while len(d_name) < name_length:
			name_index = struct.pack('!B', len(d_name))
			name_fragment = request(handle, device, FEATURE.NAME, function=b'\x10', params=name_index, features_array=features_array)
			name_fragment = name_fragment[:name_length - len(d_name)]
			d_name += name_fragment

		d_name = d_name.decode('ascii')
		_l.log(_LOG_LEVEL, "(%d,%d) device name %s", handle, device, d_name)
		return d_name


def get_device_battery_level(handle, device, features_array=None):
	"""Reads a device's battery level.

	:raises FeatureNotSupported: if the device does not support this feature.
	"""
	battery = request(handle, device, FEATURE.BATTERY, features_array=features_array)
	if battery:
		discharge, dischargeNext, status = struct.unpack('!BBB', battery[:3])
		_l.log(_LOG_LEVEL, "(%d:%d) battery %d%% charged, next level %d%% charge, status %d = %s", discharge, dischargeNext, status, BATTERY_STATUSES[status])
		return (discharge, dischargeNext, status)
