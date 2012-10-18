#
#
#

import logging

from .constants import (STATUS, PROPS)
from ..unifying_receiver.constants import (FEATURE, BATTERY_STATUS)
from ..unifying_receiver import api as _api

#
#
#

_DEVICE_MODULES = {}

def _module(device_name):
	if device_name not in _DEVICE_MODULES:
		shortname = device_name.split(' ')[-1].lower()
		try:
			m = __import__(shortname, globals(), level=1)
			_DEVICE_MODULES[device_name] = m
		except:
			# logging.exception(shortname)
			_DEVICE_MODULES[device_name] = None

	return _DEVICE_MODULES[device_name]

#
#
#

def default_request_status(devinfo, listener=None):
	if FEATURE.BATTERY in devinfo.features:
		if listener:
			reply = listener.request(_api.get_device_battery_level, devinfo.number, features=devinfo.features)
		else:
			reply = _api.get_device_battery_level(devinfo.handle, devinfo.number, features=devinfo.features)

		if reply:
			discharge, dischargeNext, status = reply
			return STATUS.CONNECTED, {PROPS.BATTERY_LEVEL: discharge, PROPS.BATTERY_STATUS: status}

	if listener:
		reply = listener.request(_api.ping, devinfo.number)
	else:
		reply = _api.ping(devinfo.handle, devinfo.number)

	return STATUS.CONNECTED if reply else STATUS.UNAVAILABLE


def default_process_event(devinfo, data, listener=None):
	feature_index = ord(data[0:1])
	if feature_index >= len(devinfo.features):
		logging.warn("mistery event %s for %s", repr(data), devinfo)
		return None

	feature = devinfo.features[feature_index]
	feature_function = ord(data[1:2]) & 0xF0

	if feature == FEATURE.BATTERY:
		if feature_function == 0:
			discharge = ord(data[2:3])
			status = BATTERY_STATUS[ord(data[3:4])]
			return STATUS.CONNECTED, {PROPS.BATTERY_LEVEL: discharge, PROPS.BATTERY_STATUS: status}
		# ?
	elif feature == FEATURE.REPROGRAMMABLE_KEYS:
		if feature_function == 0:
			logging.debug('reprogrammable key: %s', repr(data))
			# TODO
			pass
		# ?
	elif feature == FEATURE.WIRELESS:
		if feature_function == 0:
			logging.debug("wireless status: %s", repr(data))
			if data[2:5] == b'\x01\x01\x01':
				return STATUS.CONNECTED
			# TODO
			pass
		# ?


def request_status(devinfo, listener=None):
	"""Trigger a status request for a device.

	:param devinfo: the device info tuple.
	:param listener: the EventsListener that will be used to send the request,
	and which will receive the status events from the device.
	"""
	m = _module(devinfo.name)
	if m and 'request_status' in m.__dict__:
		return m.request_status(devinfo, listener)
	return default_request_status(devinfo, listener)


def process_event(devinfo, data, listener=None):
	"""Process an event received for a device.

	:param devinfo: the device info tuple.
	:param data: the event data (event packet sans the first two bytes: reply code and device number)
	"""
	default_result = default_process_event(devinfo, data, listener)
	if default_result is not None:
		return default_result

	m = _module(devinfo.name)
	if m and 'process_event' in m.__dict__:
		return m.process_event(devinfo, data, listener)
