#
#
#

from . import k750
from .constants import *


_REQUEST_STATUS_FUNCTIONS = {
		k750.NAME : k750.request_status,
	}

def request_status(devinfo, listener):
	if devinfo.name in _REQUEST_STATUS_FUNCTIONS:
		return _REQUEST_STATUS_FUNCTIONS[devinfo.name](devinfo, listener)


_PROCESS_EVENT_FUNCTIONS = {
		k750.NAME : k750.process_event,
	}

def process_event(devinfo, listener, data):
	if devinfo.name in _PROCESS_EVENT_FUNCTIONS:
		return _PROCESS_EVENT_FUNCTIONS[devinfo.name](devinfo, listener, data)
