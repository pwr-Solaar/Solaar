#
#
#

import logging

from . import k750
from . import constants as C

from ..unifying_receiver import api as _api


def ping(devinfo, listener):
	reply = listener.request(_api.ping, devinfo.number)
	return C.STATUS.CONNECTED if reply else C.STATUS.UNAVAILABLE


def default_request_status(devinfo, listener):
	if _api.C.FEATURE.BATTERY in devinfo.features:
		reply = listener.request(_api.get_device_battery_level, devinfo.number, features=devinfo.features)
		if reply:
			discharge, dischargeNext, status = reply
			return C.STATUS.CONNECTED, {C.PROPS.BATTERY_LEVEL: discharge}


def default_process_event(devinfo, data):
	feature_index = ord(data[0:1])
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


_REQUEST_STATUS_FUNCTIONS = {
					k750.NAME: k750.request_status
				}

def request_status(devinfo, listener):
	"""Trigger a status request for a device.

	:param devinfo: the device info tuple.
	:param listener: the EventsListener that will be used to send the request,
	and which will receive the status events from the device.
	"""
	if listener:
		if devinfo.name in _REQUEST_STATUS_FUNCTIONS:
			return _REQUEST_STATUS_FUNCTIONS[devinfo.name](devinfo, listener)
		return default_request_status(devinfo, listener) or ping(devinfo, listener)


_PROCESS_EVENT_FUNCTIONS = {
					k750.NAME: k750.process_event
				}

def process_event(devinfo, data):
	"""Process an event received for a device.

	When using an EventsListener, it is assumed this event was received through
	its callback, where you may call LUR APIs directly.

	:param devinfo: the device info tuple.
	:param data: the event data (event packet sans the first two bytes: reply code and device number)
	"""
	default_result = default_process_event(devinfo, data)
	if default_result is not None:
		return default_result

	if devinfo.name in _PROCESS_EVENT_FUNCTIONS:
		return _PROCESS_EVENT_FUNCTIONS[devinfo.name](devinfo, data)
