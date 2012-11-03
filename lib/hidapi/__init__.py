"""Generic Human Interface Device API."""

__author__ = "Daniel Pavel"
__license__ = "GPL"
__version__ = "0.4"

try:
	from hidapi.udev import *
except ImportError:
	from hidapi.native import *
