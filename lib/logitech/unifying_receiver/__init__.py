"""Low-level interface for devices connected through a Logitech Universal
Receiver (UR).

Uses the HID api exposed through hidapi.py, a Python thin layer over a native
implementation.

Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

References:
http://julien.danjou.info/blog/2012/logitech-k750-linux-support
http://6xq.net/git/lars/lshidpp.git/plain/doc/
"""

import logging

_DEBUG = logging.DEBUG
_log = logging.getLogger('LUR')
_log.setLevel(logging.root.level)
# if logging.root.level > logging.DEBUG:
# 	_log.addHandler(logging.NullHandler())
# 	_log.propagate = 0

del logging


from .common import strhex
from .base import NoReceiver, NoSuchDevice, DeviceUnreachable
from .receiver import Receiver, PairedDevice, MAX_PAIRED_DEVICES
from .hidpp20 import FeatureNotSupported, FeatureCallError

from . import listener
from . import status
