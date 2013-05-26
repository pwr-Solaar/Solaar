#
# Reprogrammable keys information
#

from __future__ import absolute_import, division, print_function, unicode_literals

from .common import NamedInts as _NamedInts

CONTROL = _NamedInts(
	Volume_Up=0x0001,
	Volume_Down=0x0002,
	Mute=0x0003,
	Play__Pause=0x0004,
	Next=0x0005,
	Previous=0x0006,
	Stop=0x0007,
	Application_Switcher=0x0008,
	Calculator=0x000A,
	Mail=0x000E,
	Home=0x001A,
	Music=0x001D,
	Search=0x0029,
	Sleep=0x002F,
)
CONTROL._fallback = lambda x: 'unknown:%04X' % x

TASK = _NamedInts(
	Volume_Up=0x0001,
	Volume_Down=0x0002,
	Mute=0x0003,
	Play__Pause=0x0004,
	Next=0x0005,
	Previous=0x0006,
	Stop=0x0007,
	Application_Switcher=0x0008,
	Calculator=0x000A,
	Mail=0x000E,
	Home=0x001A,
	Music=0x001D,
	Search=0x0029,
	Sleep=0x002F,
)
TASK._fallback = lambda x: 'unknown:%04X' % x

KEY_FLAG = _NamedInts(
	reprogrammable=0x10,
	FN_sensitive=0x08,
	nonstandard=0x04,
	is_FN=0x02,
	mse=0x01
)
