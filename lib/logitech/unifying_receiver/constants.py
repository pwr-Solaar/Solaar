#
# Constants used by the rest of the API.
#


"""Possible features available on a Logitech device.

A particular device might not support all these features, and may support other
unknown features as well.
"""
FEATURE = type('FEATURE', (),
				dict(
					ROOT=b'\x00\x00',
					FEATURE_SET=b'\x00\x01',
					FIRMWARE=b'\x00\x03',
					NAME=b'\x00\x05',
					BATTERY=b'\x10\x00',
					REPROGRAMMABLE_KEYS=b'\x1B\x00',
					WIRELESS_STATUS=b'\x1D\x4B',
					# declared by the K750 keyboard, no documentation found so far
					SOLAR_CHARGE=b'\x43\x01',
					# declared by the K750 keyboard, no documentation found so far
					# UNKNOWN_1DF3=b'\x1D\xF3',
					# UNKNOWN_40A0=b'\x40\xA0',
					# UNKNOWN_4100=b'\x41\x00',
					# UNKNOWN_4520=b'\x45\x20',
				))


"""Feature names indexed by feature id."""
_FEATURE_NAMES = {
			FEATURE.ROOT: 'ROOT',
			FEATURE.FEATURE_SET: 'FEATURE_SET',
			FEATURE.FIRMWARE: 'FIRMWARE',
			FEATURE.NAME: 'NAME',
			FEATURE.BATTERY: 'BATTERY',
			FEATURE.REPROGRAMMABLE_KEYS: 'REPROGRAMMABLE_KEYS',
			FEATURE.WIRELESS_STATUS: 'WIRELESS_STATUS',
			FEATURE.SOLAR_CHARGE: 'SOLAR_CHARGE',
			}
def FEATURE_NAME(feature_code):
	if feature_code is None:
		return None
	if feature_code in _FEATURE_NAMES:
		return _FEATURE_NAMES[feature_code]
	return 'UNKNOWN_%s' % feature_code


"""Possible types of devices connected to an UR."""
DEVICE_TYPES = ("Keyboard", "Remote Control", "NUMPAD", "Mouse",
				"Touchpad", "Trackball", "Presenter", "Receiver")


"""Names of different firmware levels possible, ordered from top to bottom."""
FIRMWARE_TYPES = ("Main (HID)", "Bootloader", "Hardware", "Other")


"""Names for possible battery status values."""
BATTERY_STATUSES = ("Discharging (in use)", "Recharging", "Almost full", "Full",
					"Slow recharge", "Invalid battery", "Thermal error",
					"Charging error")


"""Names for error codes."""
_ERROR_NAMES = ("Ok", "Unknown", "Invalid argument", "Out of range",
				"Hardware error", "Logitech internal", "Invalid feature index",
				"Invalid function", "Busy", "Unsupported")
def ERROR_NAME(error_code):
	if error_code < len(_ERROR_NAMES):
		return _ERROR_NAMES[error_code]
	return 'Unknown Error'
