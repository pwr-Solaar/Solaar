#
#
#

from . import k750
from .constants import *

from ..unifying_receiver import api as _api
from ..unifying_receiver.common import FallbackDict as _FDict


def ping(devinfo, listener):
	reply = listener.request(_api.ping, devinfo.number)
	return STATUS.CONNECTED if reply else STATUS.UNAVAILABLE


def default_request_status(devinfo, listener):
	if _api.C.FEATURE.BATTERY in devinfo.features:
		reply = listener.request(_api.get_device_battery_level, devinfo.number, features_array=devinfo.features)
		if reply:
			discharge, dischargeNext, status = reply
			return STATUS.CONNECTED, {PROPS.BATTERY_LEVEL: discharge}


def default_process_event(devinfo, listener, data):
	feature_index = ord(data[0:1])
	feature = devinfo.features[feature_index]

	if feature == _api.C.FEATURE.BATTERY:
		if ord(data[1:2]) & 0xF0 == 0:
			discharge = ord(data[2:3])
			status = _api.C.BATTERY_STATUS[ord(data[3:4])]
			return STATUS.CONNECTED, {BATTERY_LEVEL: discharge, BATTERY_STATUS: status}
		# ?
	elif feature == _api.C.FEATURE.REPROGRAMMABLE_KEYS:
		if ord(data[1:2]) & 0xF0 == 0:
			print 'reprogrammable key', repr(data)
			# TODO
			pass
		# ?
	elif feature == _api.C.FEATURE.WIRELESS:
		if ord(data[1:2]) & 0xF0 == 0:
			# TODO
			pass
		# ?


_REQUEST_STATUS_FUNCTIONS = _FDict()
_REQUEST_STATUS_FUNCTIONS[k750.NAME] = k750.request_status

def request_status(devinfo, listener):
	if listener:
		return _REQUEST_STATUS_FUNCTIONS[devinfo.name](devinfo, listener) or default_request_status(devinfo, listener) or ping(devinfo, listener)


_PROCESS_EVENT_FUNCTIONS = _FDict()
_PROCESS_EVENT_FUNCTIONS[k750.NAME] = k750.process_event

def process_event(devinfo, listener, data):
	if listener:
		return default_process_event(devinfo, listener, data) or _PROCESS_EVENT_FUNCTIONS[devinfo.name](devinfo, listener, data)
