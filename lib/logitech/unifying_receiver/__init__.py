"""Low-level interface for devices connected through a Logitech Universal
Receiver (UR).

Uses the HID api exposed through hidapi.py, a Python thin layer over a native
implementation.

Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

Strongly recommended to use these functions from a single thread; calling
multiple functions from different threads has a high chance of mixing the
replies and causing apparent failures.

Basic order of operations is:
	- open() to obtain a UR handle
	- request() to make a feature call to one of the devices attached to the UR
	- close() to close the UR handle

References:
http://julien.danjou.info/blog/2012/logitech-k750-linux-support
http://6xq.net/git/lars/lshidpp.git/plain/doc/
"""

import logging

if logging.root.level > logging.DEBUG:
	log = logging.getLogger('LUR')
	log.addHandler(logging.NullHandler())
	log.propagate = 0

del logging


from .constants import *
from .exceptions import *
from .api import *
