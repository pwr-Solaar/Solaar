#
# Optional hook for unhandled data packets received while talking to the UR.
# These are usually broadcast events received from the attached devices.
#

import logging
from binascii import hexlify as _hexlify


def _logdebug_hook(reply_code, devnumber, data):
	"""Default unhandled hook, logs the reply as DEBUG."""
	_l = logging.getLogger('lur.unhandled')
	_l.debug("UNHANDLED (,%d) code 0x%02x data [%s]", devnumber, reply_code, _hexlify(data))


"""The function that will be called on unhandled incoming events.

The hook must be a function with the signature: ``_(int, int, str)``, where
the parameters are: (reply_code, devnumber, data).

This hook will only be called by the request() function, when it receives
replies that do not match the requested feature call. As such, it is not
suitable for intercepting broadcast events from the device (e.g. special
keys being pressed, battery charge events, etc), at least not in a timely
manner. However, these events *may* be delivered here if they happen while
doing a feature call to the device.

The default implementation logs the unhandled reply as DEBUG.
"""
hook = _logdebug_hook


def _publish(reply_code, devnumber, data):
	"""Delivers a reply to the unhandled hook, if any."""
	if hook is not None:
		hook.__call__(reply_code, devnumber, data)
