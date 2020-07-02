#
#
#
from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import hidapi

from logitech.unifying_receiver.base import DEVICE_NANO_RECEIVER, DEVICE_UNIFYING_RECEIVER, DEVICE_UNIFYING_RECEIVER_2

sys.path += (sys.path[0] + '/../lib', )


def print_event(action, device):
    print('~~~~ device [%s] %s' % (action, device))


hidapi.monitor(print_event, DEVICE_UNIFYING_RECEIVER,
               DEVICE_UNIFYING_RECEIVER_2, DEVICE_NANO_RECEIVER)
