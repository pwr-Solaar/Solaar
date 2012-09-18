"""A few functions to deal with the Logitech Universal Receiver.

Uses the HID api exposed through hidapi.py.
Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

References:
http://julien.danjou.info/blog/2012/logitech-k750-linux-support
http://6xq.net/git/lars/lshidpp.git/plain/doc/logitech_hidpp_2.0_specification_draft_2012-06-04.pdf
"""

# import logging
from . import hidapi


_TIMEOUT = 1000


class NoReceiver(Exception):
	"""May be thrown when trying to talk through a previously connected
	receiver that is no longer available (either because it was physically
	disconnected or some other reason)."""
	pass


FEATURE_ROOT = '\x00\x00'
FEATURE_GET_FEATURE_SET = '\x00\x01'
FEATURE_GET_FIRMWARE = '\x00\x03'
FEATURE_GET_NAME = '\x00\x05'
FEATURE_GET_BATTERY = '\x10\x00'
FEATURE_GET_REPROGRAMMABLE_KEYS = '\x1B\x00'
FEATURE_GET_WIRELESS_STATUS = '\x1D\x4B'
FEATURE_UNKNOWN_1 = '\x1D\xF3'
FEATURE_UNKNOWN_2 = '\x40\xA0'
FEATURE_UNKNOWN_3 = '\x41\x00'
FEATURE_GET_SOLAR_CHARGE = '\x43\x01'
FEATURE_UNKNOWN_4 = '\x45\x20'


DEVICE_TYPES = ( "Keyboard", "Remote Control", "NUMPAD", "Mouse", "Touchpad", "Trackball", "Presenter", "Receiver" )

_DEVICE_FEATURES = {}


def _write(receiver, device, data):
	# just in case
	# hidapi.read(receiver, 128, 0)
	data = '\x10' + chr(device) + data
	# print "w[", data.encode("hex"), "]",
	return hidapi.write(receiver, data)


def _read(receiver, device, timeout=_TIMEOUT):
	data = hidapi.read(receiver, 128, timeout)
	if data is None:
		print "r(None)"
		return None

	if not data:
		# print "r[ ]"
		return ""

	# print "r[", data.encode("hex"), "]",
	# if len(data) < 7:
	# 	print "short", len(data),

	# if ord(data[0]) == 0x20:
	# 	# no idea what it does, not in any specs
	# 	return _read(receiver, device)

	if ord(data[1]) == 0:
		# print "no device",
		return _read(receiver, device)

	if ord(data[1]) != device:
		# print "wrong device",
		return _read(receiver, device)

	# print ""
	return data


def _get_feature_index(receiver, device, feature_id):
	if device not in _DEVICE_FEATURES:
		_DEVICE_FEATURES[device] = [ 0 ] * 0x10
		pass
	elif feature_id in _DEVICE_FEATURES[device]:
		return _DEVICE_FEATURES[device].index(feature_id)

	if not _write(receiver, device, FEATURE_ROOT + feature_id + '\x00'):
		# print "write failed, closing receiver"
		close(receiver)
		raise NoReceiver()

	while True:
		reply = _read(receiver, device)
		if not reply:
			break

		if reply[2:4] != FEATURE_ROOT:
			# ignore
			continue

		# only return active and supported features
		if ord(reply[4]) and ord(reply[5]) & 0xA0 == 0:
			index = ord(reply[4])
			_DEVICE_FEATURES[device][index] = feature_id
			return index

		# huh?
		return 0


def _request(receiver, device, feature_id, function='\x00', param1='\x00', param2='\x00', param3='\x00', reply_function=None):
	feature_index = _get_feature_index(receiver, device, feature_id)
	if not feature_index or feature_index == -1:
		return None

	feature_index = chr(feature_index)
	if not _write(receiver, device, feature_index + function + param1 + param2 + param3):
		# print "write failed, closing receiver"
		close(receiver)
		raise NoReceiver()

	def _read_reply(receiver, device, attempts=2):
		reply = _read(receiver, device)
		if not reply:
			if attempts > 0:
				return _read_reply(receiver, device, attempts - 1)
			return None

		if reply[0] == '\x10' and reply[2] == '\x8F':
			# invalid device
			return None

		if reply[0] == '\x11' and reply[2] == feature_index:
			if reply[3] == reply_function if reply_function else function:
				return reply

		if reply[0] == '\x11':
			return _read_reply(receiver, device, attempts - 1)

	return _read_reply(receiver, device)


def _get_feature_set(receiver, device):
	features = [ 0 ] * 0x10
	reply = _request(receiver, device, FEATURE_GET_FEATURE_SET)
	if reply:
		for index in range(1, 1 + ord(reply[4])):
			reply = _request(receiver, device, FEATURE_GET_FEATURE_SET, '\x10', chr(index))
			if reply:
				features[index] = reply[4:6].upper()
				# print "feature", reply[4:6].encode('hex'), "index", index

	return features


_PING_DEVICE = '\x10\x00\x00\x10\x00\x00\xAA'


def open():
	"""Gets the HID device handle for the Unifying Receiver.

	It is assumed a single receiver is connected to the machine. If more than
	one are present, the first one found will be returned.

	:returns: an opaque device handle if a receiver is found, or None.
	"""
	# USB ids for (Logitech, Unifying Receiver)
	for rawdevice in hidapi.enumerate(0x046d, 0xc52b, 2):
		# print "checking", rawdevice,
		receiver = hidapi.open_path(rawdevice.path)
		if not receiver:
			# could be a permissions problem
			# in any case, unreachable
			# print "failed to open"
			continue

		# ping on a device id we know to be invalid
		hidapi.write(receiver, _PING_DEVICE)

		# if this is the right hidraw device, we'll receive a 'bad subdevice'
		# otherwise, the read should produce nothing
		reply = hidapi.read(receiver, 32, 200)
		if reply:
			# print "r[", reply.encode("hex"), "]",
			if reply == '\x01\x00\x00\x00\x00\x00\x00\x00':
				# no idea what this is
				# print "nope"
				pass
			elif reply[:4] == "\x10\x00\x8F\x00":
				# print "found"
				return receiver
			# print "unknown"
		else:
			# print "no reply"
			pass
		hidapi.close(receiver)


def close(receiver):
	"""Closes a HID device handle obtained with open()."""
	if receiver:
		try:
			hidapi.close(receiver)
			# print "closed", receiver
			return True
		except:
			pass
	return False


def ping(receiver, device):
	# print "ping", device,
	if not _write(receiver, device, _PING_DEVICE[2:]):
		# print "write failed",
		return False

	reply = _read(receiver, device)
	if not reply:
		# print "no data",
		return False

	# 10018f00100900
	if ord(reply[0]) == 0x10 and ord(reply[2]) == 0x8F:
		# print "invalid",
		return False

	# 110100100200aa00000000000000000000000000
	if ord(reply[0]) == 0x11 and reply[2:4] == "\x00\x10" and reply[6] == "\xAA":
		return True

	return False


def get_name(receiver, device):
	reply = _request(receiver, device, FEATURE_GET_NAME)
	if reply:
		charcount = ord(reply[4])
		name = ''
		index = 0
		while len(name) < charcount:
			reply = _request(receiver, device, FEATURE_GET_NAME, '\x10', chr(index))
			if reply:
				name += reply[4:4 + charcount - index]
				index = len(name)
			else:
				break
		return name


def get_type(receiver, device):
	reply = _request(receiver, device, FEATURE_GET_NAME, '\x20')
	if reply:
		return DEVICE_TYPES[ord(reply[4])]


def get_firmware_version(receiver, device, firmware_type=0):
	reply = _request(receiver, device, FEATURE_GET_FIRMWARE, '\x10', chr(firmware_type))
	if reply:
		return '%s %s.%s' % (reply[5:8], reply[8:10].encode('hex'), reply[10:12].encode('hex'))


def get_battery_level(receiver, device):
	reply = _request(receiver, device, FEATURE_GET_BATTERY)
	if reply:
		return ( ord(reply[4]), ord(reply[5]), ord(reply[6]) )


def get_reprogrammable_keys(receiver, device):
	count = _request(receiver, device, FEATURE_GET_REPROGRAMMABLE_KEYS)
	if count:
		keys = []
		for index in range(ord(count[4])):
			key = _request(receiver, device, FEATURE_GET_REPROGRAMMABLE_KEYS, '\x10', chr(index))
			keys.append( key[4:6], keys[6:8], ord(key[8]) )
		return keys


def get_solar_charge(receiver, device):
	reply = _request(receiver, device, FEATURE_GET_SOLAR_CHARGE, '\x03', '\x78', '\x01', reply_function='\x10')
	if reply:
		charge = ord(reply[4])
		lux = ord(reply[5]) << 8 | ord(reply[6])
		# lux = int(round(((255 * ord(reply[5])) + ord(reply[6])) / 538.0, 2) * 100)
		return (charge, lux)


def find_device(receiver, match_device_type=None, match_name=None):
	"""Gets the device number for the first device matching.

	The device type and name are case-insensitive.
	"""
	# Apparently a receiver supports up to 6 devices.
	for device in range(1, 7):
		if ping(receiver, device):
			if device not in _DEVICE_FEATURES:
				_DEVICE_FEATURES[device] = _get_feature_set(receiver, device)
			# print get_reprogrammable_keys(receiver, device)
			# d_firmware = get_firmware_version(receiver, device)
			# print "device", device, "[", d_name, "/", d_type, "] firmware", d_firmware, "features", _DEVICE_FEATURES[device]
			if match_device_type:
				d_type = get_type(receiver, device)
				if d_type is None or match_device_type.lower() != d_type.lower():
					continue
			if match_name:
				d_name = get_name(receiver, device)
				if d_name is None or match_name.lower() != d_name.lower():
					continue
			return device
