#
#
#

import logging

from .constants import (STATUS, PROPS)
from ..unifying_receiver.constants import (FEATURE, BATTERY_STATUS, BATTERY_OK)
from ..unifying_receiver import api as _api

#
#
#

_DEVICE_MODULES = {}

def _module(device):
	shortname = device.codename.lower().replace(' ', '_')
	if shortname not in _DEVICE_MODULES:
		try:
			m = __import__(shortname, globals(), level=1)
			_DEVICE_MODULES[shortname] = m
		except:
			# logging.exception(shortname)
			_DEVICE_MODULES[shortname] = None

	return _DEVICE_MODULES[shortname]

#
#
#

def default_request_status(devinfo):
	if FEATURE.BATTERY in devinfo.features:
		reply = _api.get_device_battery_level(devinfo.handle, devinfo.number, features=devinfo.features)
		if reply:
			b_discharge, dischargeNext, b_status = reply
			return STATUS.CONNECTED, {
								PROPS.BATTERY_LEVEL: b_discharge,
								PROPS.BATTERY_STATUS: b_status,
							}

	reply = _api.ping(devinfo.handle, devinfo.number)
	return STATUS.CONNECTED if reply else STATUS.UNAVAILABLE


def default_process_event(devinfo, data):
	feature_index = ord(data[0:1])
	if feature_index >= len(devinfo.features):
		# logging.warn("mistery event %s for %s", repr(data), devinfo)
		return None

	feature = devinfo.features[feature_index]
	feature_function = ord(data[1:2]) & 0xF0

	if feature == FEATURE.BATTERY:
		if feature_function == 0x00:
			b_discharge = ord(data[2:3])
			b_status = ord(data[3:4])
			return STATUS.CONNECTED, {
								PROPS.BATTERY_LEVEL: b_discharge,
								PROPS.BATTERY_STATUS: BATTERY_STATUS[b_status],
								PROPS.UI_FLAGS: 0 if BATTERY_OK(b_status) else STATUS.UI_NOTIFY,
							}
		# ?
	elif feature == FEATURE.REPROGRAMMABLE_KEYS:
		if feature_function == 0x00:
			logging.debug('reprogrammable key: %s', repr(data))
			# TODO
			pass
		# ?
	elif feature == FEATURE.WIRELESS:
		if feature_function == 0x00:
			logging.debug("wireless status: %s", repr(data))
			if data[2:5] == b'\x01\x01\x01':
				return STATUS.CONNECTED, {PROPS.UI_FLAGS: STATUS.UI_NOTIFY}
			# TODO
			pass
		# ?


def request_status(devinfo):
	"""Trigger a status request for a device.

	:param devinfo: the device info tuple.
	:param listener: the EventsListener that will be used to send the request,
	and which will receive the status events from the device.
	"""
	m = _module(devinfo)
	if m and 'request_status' in m.__dict__:
		return m.request_status(devinfo)
	return default_request_status(devinfo)


def process_event(devinfo, data):
	"""Process an event received for a device.

	:param devinfo: the device info tuple.
	:param data: the event data (event packet sans the first two bytes: reply code and device number)
	"""
	default_result = default_process_event(devinfo, data)
	if default_result is not None:
		return default_result

	m = _module(devinfo)
	if m and 'process_event' in m.__dict__:
		return m.process_event(devinfo, data)
