"""Generic Human Interface Device API."""

from __future__ import absolute_import

__author__ = "Daniel Pavel"
__license__ = "GPL"
__version__ = "0.3"

#
# This package exists in case a future pure-Python implementation is feasible.
#


try:
	from hidapi.udev import *
except ImportError:
	from hidapi.native import *
