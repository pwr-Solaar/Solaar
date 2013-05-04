#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple

from .common import NamedInts as _NamedInts
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from . import settings as _settings

#
# common strings for settings
#

_SMOOTH_SCROLL = ('smooth-scroll', 'Smooth Scrolling', 'High-sensitivity mode for vertical scroll with the wheel.')
_DPI = ('dpi', 'Sensitivity (DPI)', None)
_FN_SWAP = ('fn-swap', 'Swap Fx function', ('When set, the F1..F12 keys will activate their special function,\n'
						 					'and you must hold the FN key to activate their standard function.\n'
						 					'\n'
						 					'When unset, the F1..F12 keys will activate their standard function,\n'
						 					'and you must hold the FN key to activate their special function.'))

# this register is only applicable to HID++ 1.0 devices, it should not exist with HID++ 2.0 devices
# using Features
def _register_fn_swap(register, true_value, mask):
	return _settings.register_toggle(_FN_SWAP[0], register, true_value=true_value, mask=mask,
					label=_FN_SWAP[1], description=_FN_SWAP[2])


def _register_smooth_scroll(register, true_value, mask):
	return _settings.register_toggle(_SMOOTH_SCROLL[0], register, true_value=true_value, mask=mask,
					label=_SMOOTH_SCROLL[1], description=_SMOOTH_SCROLL[2])


def _register_dpi(register, choices):
	return _settings.register_choices(_DPI[0], register, choices,
					label=_DPI[1], description=_DPI[2])


def check_features(device, already_known):
	if _hidpp20.FEATURE.FN_STATUS in device.features and not any(s.name == 'fn-swap' for s in already_known):
		tfn = _settings.feature_toggle(_FN_SWAP[0], _hidpp20.FEATURE.FN_STATUS, write_returns_value=True,
						label=_FN_SWAP[1], description=_FN_SWAP[2])
		already_known.append(tfn(device))

#
#
#

_DeviceDescriptor = namedtuple('_DeviceDescriptor',
				['name', 'kind', 'codename', 'registers', 'settings'])

DEVICES = {}

def _D(name, codename=None, kind=None, registers=None, settings=None):
	if kind is None:
		kind = (_hidpp10.DEVICE_KIND.mouse if 'Mouse' in name
				else _hidpp10.DEVICE_KIND.keyboard if 'Keyboard' in name
				else _hidpp10.DEVICE_KIND.touchpad if 'Touchpad' in name
				else _hidpp10.DEVICE_KIND.trackball if 'Trackball' in name
				else None)
	assert kind is not None

	if codename is None:
		codename = name.split(' ')[-1]
	assert codename is not None

	DEVICES[codename] = _DeviceDescriptor(name, kind, codename, registers, settings)

#
#
#

# Some HID++1.0 registers and HID++2.0 features can be discovered at run-time,
# so they are not specified here.
# Registers are only supported for HID++ 1.0 devices. Specify a negative value
# to blacklist that register (prevent Solaar from accessing the register)

# Keyboards

_D('Wireless Keyboard K230')
_D('Wireless Keyboard K270')
_D('Wireless Keyboard K350')
_D('Wireless Keyboard K360')
_D('Wireless Touch Keyboard K400')
_D('Wireless Keyboard K710',
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_fn_swap(0x09, true_value=b'\x00\x01', mask=b'\x00\x01'),
						],
				)
_D('Wireless Solar Keyboard K750')
_D('Wireless Illuminated Keyboard K800',
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_fn_swap(0x09, true_value=b'\x00\x01', mask=b'\x00\x01'),
						],
				)

# Mice

_D('Wireless Mouse M315')
_D('Wireless Mouse M325')
_D('Wireless Mouse M505')
_D('Wireless Mouse M510',
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
						],
				)
_D('Couch Mouse M515')
_D('Wireless Mouse M525')
_D('Touch Mouse M600')
_D('Marathon Mouse M705',
				registers={'battery_charge': 0x0D},
				settings=[
							_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
							# _register_dpi(0x63, _NamedInts(**{'100': 10, '300': 30, '350':35, '500':50})),
						],
				)
_D('Zone Touch Mouse T400')
_D('Touch Mouse T620')
_D('Logitech Cube', kind='mouse')
_D('Anywhere Mouse MX', codename='Anywhere MX',
				registers={'battery_charge': 0x0D},
				settings=[
							_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
						],
				)
_D('Performance Mouse MX', codename='Performance MX',
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_dpi(0x63, _NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))),
						],
				)

# Trackballs

_D('Wireless Trackball M570')

# Touchpads

_D('Wireless Rechargeable Touchpad T650')

del namedtuple
