#
# Functions specific to the K750 solar keyboard.
#

import logging
from struct import unpack as _unpack

from ..unifying_receiver import api as _api
from . import constants as C

#
#
#

NAME = 'Wireless Solar Keyboard K750'

_CHARGE_LIMITS = (75, 40, 20, 10, -1)

#
#
#

def _trigger_solar_charge_events(receiver, devinfo):
	return _api.request(receiver, devinfo.number,
						feature=_api.C.FEATURE.SOLAR_CHARGE, function=b'\x03', params=b'\x78\x01',
						features_array=devinfo.features)


def _charge_status(data):
	charge, lux = _unpack('!BH', data[2:5])

	d = {}

	for i in range(0, len(_CHARGE_LIMITS)):
		if charge >= _CHARGE_LIMITS[i]:
			charge_index = i
			break
	else:
		charge_index = 0
	d[C.PROPS.BATTERY_LEVEL] = charge
	text = 'Battery %d%%' % charge

	if lux > 0:
		d[C.PROPS.LIGHT_LEVEL] = lux
		text = 'Light: %d lux' % lux + ', ' + text

	d[C.PROPS.TEXT] = text
	return 0x10 << charge_index, d


def request_status(devinfo, listener):
	reply = listener.request(_trigger_solar_charge_events, devinfo)
	if reply is None:
		return C.STATUS.UNAVAILABLE


def process_event(devinfo, listener, data):
	if data[:2] == b'\x09\x00' and data[7:11] == b'GOOD':
		# usually sent after the keyboard is turned on
		return _charge_status(data)

	if data[:2] == b'\x09\x10' and data[7:11] == b'GOOD':
		# regular solar charge events
		return _charge_status(data)

	if data[:2] == b'\x09\x20' and data[7:11] == b'GOOD':
		logging.debug("Solar key pressed")
		if _trigger_solar_charge_events(listener.receiver, devinfo) is None:
			return C.STATUS.UNAVAILABLE
		return _charge_status(data)

	if data[:2] == b'\x05\x00':
		# wireless device status
		if data[2:5] == b'\x01\x01\x01':
			logging.debug("Keyboard just started")
			return C.STATUS.CONNECTED
