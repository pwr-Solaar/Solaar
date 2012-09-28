#
# Functions specific to the K750 solar keyboard.
#

import logging
import struct

from ..unifying_receiver import api as _api
from .constants import *

#
#
#

NAME = 'Wireless Solar Keyboard K750'

_STATUS_NAMES = ('excellent', 'good', 'okay', 'poor', 'very low')

_CHARGE_LIMITS = (75, 40, 20, 10, -1)
_LIGHTING_LIMITS = (400, 200, 50, 20, -1)

#
#
#

def _trigger_solar_charge_events(receiver, devinfo):
	return _api.request(receiver, devinfo.number,
						feature=_api.FEATURE.SOLAR_CHARGE, function=b'\x03', params=b'\x78\x01',
						features_array=devinfo.features)


def _charge_status(data):
	charge, lux = struct.unpack('!BH', data[2:5])

	for i in range(0, len(_CHARGE_LIMITS)):
		if charge >= _CHARGE_LIMITS[i]:
			charge_index = i
			break
	text = 'Charge %d%% (%s)' % (charge, _STATUS_NAMES[charge_index])

	if lux > 0:
		for i in range(0, len(_CHARGE_LIMITS)):
			if lux > _LIGHTING_LIMITS[i]:
				lighting_index = i
				break
		text += ', Lighting %s (%d lux)' % (_STATUS_NAMES[lighting_index], lux)

	return 0x10 << charge_index, text


def request_status(devinfo, listener):
	# Constantly requesting the solar charge status triggers a flood of events,
	# which appear to drain the battery rather fast.
	# Instead, ping the device for on/off status, and only ask for solar charge
	# status when the user presses the solar key on the keyboard.
	#
	# reply = listener.request(_trigger_solar_charge_events, devinfo)
	# if reply is None:
	# 	return DEVICE_STATUS.UNAVAILABLE

	reply = listener.request(_api.ping, devinfo.number)
	if not reply:
		return DEVICE_STATUS.UNAVAILABLE


def process_event(devinfo, listener, data):
	if data[:2] == b'\x05\x00':
		# wireless device status
		if data[2:5] == b'\x01\x01\x01':
			logging.debug("Keyboard just started")
			return DEVICE_STATUS.CONNECTED
	elif data[:2] == b'\x09\x00' and data[7:11] == b'GOOD':
		# usually sent after the keyboard is turned on
		return _charge_status(data)
	elif data[:2] == b'\x09\x10' and data[7:11] == b'GOOD':
		# regular solar charge events
		return _charge_status(data)
	elif data[:2] == b'\x09\x20' and data[7:11] == b'GOOD':
		logging.debug("Solar key pressed")
		if _trigger_solar_charge_events(listener.receiver, devinfo) is None:
			return DEVICE_STATUS.UNAVAILABLE
		return _charge_status(data)
