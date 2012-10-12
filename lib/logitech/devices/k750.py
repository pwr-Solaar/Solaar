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

def _charge_status(data, hasLux=False):
	charge, lux = _unpack('!BH', data[2:5])

	d = {}

	_CHARGE_LEVELS = (10, 25, 256)
	for i in range(0, len(_CHARGE_LEVELS)):
		if charge < _CHARGE_LEVELS[i]:
			charge_index = i
			break
	d[C.PROPS.BATTERY_LEVEL] = charge
	text = 'Battery %d%%' % charge

	if hasLux:
		d[C.PROPS.LIGHT_LEVEL] = lux
		text = 'Light: %d lux' % lux + ', ' + text
	else:
		d[C.PROPS.LIGHT_LEVEL] = None

	d[C.PROPS.TEXT] = text
	return 0x10 << charge_index, d


def request_status(devinfo, listener=None):
	def _trigger_solar_charge_events(handle, devinfo):
		return _api.request(handle, devinfo.number,
							feature=_api.C.FEATURE.SOLAR_CHARGE, function=b'\x03', params=b'\x78\x01',
							features=devinfo.features)
	if listener is None:
		reply = _trigger_solar_charge_events(devinfo.handle, devinfo)
	elif listener:
		reply = listener.request(_trigger_solar_charge_events, devinfo)
	else:
		reply = 0

	if reply is None:
		return C.STATUS.UNAVAILABLE


def process_event(devinfo, data, listener=None):
	if data[:2] == b'\x09\x00' and data[7:11] == b'GOOD':
		# usually sent after the keyboard is turned on or just connected
		return _charge_status(data)

	if data[:2] == b'\x09\x10' and data[7:11] == b'GOOD':
		# regular solar charge events
		return _charge_status(data, True)

	if data[:2] == b'\x09\x20' and data[7:11] == b'GOOD':
		logging.debug("Solar key pressed")
		return request_status(devinfo, listener) or _charge_status(data)

	if data[:2] == b'\x05\x00':
		# wireless device status
		if data[2:5] == b'\x01\x01\x01':
			logging.debug("Keyboard just started")
			return C.STATUS.CONNECTED
