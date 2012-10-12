#
#
#

import logging

from . import k750
from . import constants as C

from ..unifying_receiver import api as _api

#
#
#

_REQUEST_STATUS_FUNCTIONS = {
					C.NAME.K750: k750.request_status,
				}

_PROCESS_EVENT_FUNCTIONS = {
					C.NAME.K750: k750.process_event,
				}

#
#
#

def ping(devinfo, listener=None):
	if listener is None:
		reply = _api.ping(devinfo.number)
	elif listener:
		reply = listener.request(_api.ping, devinfo.number)
	else:
		return None

	return C.STATUS.CONNECTED if reply else C.STATUS.UNAVAILABLE


def default_request_status(devinfo, listener=None):
	if _api.C.FEATURE.BATTERY in devinfo.features:
		if listener is None:
			reply = _api.get_device_battery_level(devinfo.handle, devinfo.number, features=devinfo.features)
		elif listener:
			reply = listener.request(_api.get_device_battery_level, devinfo.number, features=devinfo.features)
		else:
			reply = None

		if reply:
			discharge, dischargeNext, status = reply
			return C.STATUS.CONNECTED, {C.PROPS.BATTERY_LEVEL: discharge}


def default_process_event(devinfo, data, listener=None):
	feature_index = ord(data[0:1])
	if feature_index >= len(devinfo.features):
		logging.warn("mistery event %s for %s", repr(data), devinfo)
		return None

	feature = devinfo.features[feature_index]
	feature_function = ord(data[1:2]) & 0xF0

	if feature == _api.C.FEATURE.BATTERY:
		if feature_function == 0:
			discharge = ord(data[2:3])
			status = _api.C.BATTERY_STATUS[ord(data[3:4])]
			return C.STATUS.CONNECTED, {C.PROPS.BATTERY_LEVEL: discharge, C.PROPS.BATTERY_STATUS: status}
		# ?
	elif feature == _api.C.FEATURE.REPROGRAMMABLE_KEYS:
		if feature_function == 0:
			logging.debug('reprogrammable key: %s', repr(data))
			# TODO
			pass
		# ?
	elif feature == _api.C.FEATURE.WIRELESS:
		if feature_function == 0:
			logging.debug("wireless status: %s", repr(data))
			# TODO
			pass
		# ?


def request_status(devinfo, listener=None):
	"""Trigger a status request for a device.

	:param devinfo: the device info tuple.
	:param listener: the EventsListener that will be used to send the request,
	and which will receive the status events from the device.
	"""
	if devinfo.name in _REQUEST_STATUS_FUNCTIONS:
		return _REQUEST_STATUS_FUNCTIONS[devinfo.name](devinfo, listener)
	return default_request_status(devinfo, listener) or ping(devinfo, listener)


def process_event(devinfo, data, listener=None):
	"""Process an event received for a device.

	:param devinfo: the device info tuple.
	:param data: the event data (event packet sans the first two bytes: reply code and device number)
	"""
	default_result = default_process_event(devinfo, data, listener)
	if default_result is not None:
		return default_result

	if devinfo.name in _PROCESS_EVENT_FUNCTIONS:
		return _PROCESS_EVENT_FUNCTIONS[devinfo.name](devinfo, data, listener)
