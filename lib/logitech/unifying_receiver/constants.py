#
# Constants used by the rest of the API.
#

from binascii import hexlify as _hexlify
from struct import pack as _pack

from .common import *


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
					SOLAR_CHARGE=b'\x43\x01',
				))

def _feature_name(key):
	if key is None:
		return None
	if type(key) == int:
		return FEATURE_NAME[_pack('!H', key)]
	return 'UNKNOWN_' + _hexlify(key)


"""Feature names indexed by feature id."""
FEATURE_NAME = FallbackDict(_feature_name)
FEATURE_NAME[FEATURE.ROOT] = 'ROOT'
FEATURE_NAME[FEATURE.FEATURE_SET] = 'FEATURE_SET'
FEATURE_NAME[FEATURE.FIRMWARE] = 'FIRMWARE'
FEATURE_NAME[FEATURE.NAME] = 'NAME'
FEATURE_NAME[FEATURE.BATTERY] = 'BATTERY'
FEATURE_NAME[FEATURE.REPROGRAMMABLE_KEYS] = 'REPROGRAMMABLE_KEYS'
FEATURE_NAME[FEATURE.WIRELESS_STATUS] = 'WIRELESS_STATUS'
FEATURE_NAME[FEATURE.SOLAR_CHARGE] = 'SOLAR_CHARGE'


_DEVICE_TYPES = ('Keyboard', 'Remote Control', 'NUMPAD', 'Mouse',
				'Touchpad', 'Trackball', 'Presenter', 'Receiver')

"""Possible types of devices connected to an UR."""
DEVICE_TYPE = FallbackDict(lambda x: 'unknown', list2dict(_DEVICE_TYPES))


_FIRMWARE_TYPES = ('Main (HID)', 'Bootloader', 'Hardware', 'Other')

"""Names of different firmware levels possible, ordered from top to bottom."""
FIRMWARE_TYPE = FallbackDict(lambda x: 'Unknown', list2dict(_FIRMWARE_TYPES))


_BATTERY_STATUSES = ('Discharging (in use)', 'Recharging', 'Almost full',
					'Full', 'Slow recharge', 'Invalid battery', 'Thermal error',
					'Charging error')

"""Names for possible battery status values."""
BATTERY_STATUS = FallbackDict(lambda x: 'unknown', list2dict(_BATTERY_STATUSES))

_KEY_NAMES = ( 'unknown_0000', 'Volume up', 'Volume down', 'Mute', 'Play/Pause',
				'Next', 'Previous', 'Stop', 'Application switcher',
				'unknown_0009', 'Calculator', 'unknown_000b', 'unknown_000c',
				'unknown_000d', 'Mail')

"""Standard names for reprogrammable keys."""
KEY_NAME = FallbackDict(lambda x: 'unknown_%04x' % x, list2dict(_KEY_NAMES))

"""Possible flags on a reprogrammable key."""
KEY_FLAG = type('REPROGRAMMABLE_KEY_FLAGS', (), dict(
					REPROGRAMMABLE=0x10,
					FN_SENSITIVE=0x08,
					NONSTANDARD=0x04,
					IS_FN=0x02,
					MSE=0x01,
				))

_ERROR_NAMES = ('Ok', 'Unknown', 'Invalid argument', 'Out of range',
				'Hardware error', 'Logitech internal', 'Invalid feature index',
				'Invalid function', 'Busy', 'Unsupported')

"""Names for error codes."""
ERROR_NAME = FallbackDict(lambda x: 'Unknown error', list2dict(_ERROR_NAMES))
