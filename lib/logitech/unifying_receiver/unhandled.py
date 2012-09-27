#
# Optional hook for unhandled data packets received while talking to the UR.
# These are usually broadcast events received from the attached devices.
#

import logging
_l = logging.getLogger('logitech.unifying_receiver.unhandled')


def _logging_unhandled_hook(reply_code, device, data):
	"""Default unhandled hook, logs the reply as DEBUG."""
	_l.debug("UNHANDLED (,%d) code 0x%02x data [%s]", device, reply_code, data.encode('hex'))


_unhandled_hook = _logging_unhandled_hook


def _publish(reply_code, device, data):
	"""Delivers a reply to the unhandled hook, if any."""
	if _unhandled_hook is not None:
		_unhandled_hook.__call__(reply_code, device, data)


def set_unhandled_hook(hook=None):
	"""Sets the function that will be called on unhandled incoming events.

	The hook must be a function with the signature: ``_(int, int, str)``, where
	the parameters are: (reply code, device number, data).

	This hook will only be called by the request() function, when it receives
	replies that do not match the requested feature call. As such, it is not
	suitable for intercepting broadcast events from the device (e.g. special
	keys being pressed, battery charge events, etc), at least not in a timely
	manner. However, these events *may* be delivered here if they happen while
	doing a feature call to the device.

	The default implementation logs the unhandled reply as DEBUG.
	"""
	global _unhandled_hook
	_unhandled_hook = hook
