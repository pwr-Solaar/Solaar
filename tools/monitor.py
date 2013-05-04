#
#
#
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
sys.path += (sys.path[0] + '/../lib',)

import hidapi
from logitech.unifying_receiver.base import DEVICE_UNIFYING_RECEIVER
from logitech.unifying_receiver.base import DEVICE_UNIFYING_RECEIVER_2
from logitech.unifying_receiver.base import DEVICE_NANO_RECEIVER


def print_event(action, device):
	print ("~~~~ device [%s] %s" % (action, device))


hidapi.monitor(print_event,
		DEVICE_UNIFYING_RECEIVER,
		DEVICE_UNIFYING_RECEIVER_2,
		DEVICE_NANO_RECEIVER
	)
