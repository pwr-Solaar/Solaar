# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""Low-level interface for devices connected through a Logitech Universal
Receiver (UR).

Uses the HID api exposed through hidapi.py, a Python thin layer over a native
implementation.

Incomplete. Based on a bit of documentation, trial-and-error, and guesswork.

References:
http://julien.danjou.info/blog/2012/logitech-k750-linux-support
http://6xq.net/git/lars/lshidpp.git/plain/doc/
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

_DEBUG = logging.DEBUG
_log = logging.getLogger(__name__)
_log.setLevel(logging.root.level)
# if logging.root.level > logging.DEBUG:
# 	_log.addHandler(logging.NullHandler())
# 	_log.propagate = 0

del logging


__version__ = '0.9'


from .common import strhex
from .base import NoReceiver, NoSuchDevice, DeviceUnreachable
from .receiver import Receiver, PairedDevice
from .hidpp20 import FeatureNotSupported, FeatureCallError

from . import listener
from . import status
