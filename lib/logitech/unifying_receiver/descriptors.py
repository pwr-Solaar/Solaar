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


def _feature_fn_swap():
	return _settings.feature_toggle(_FN_SWAP[0], _hidpp20.FEATURE.FN_INVERSION,
					write_returns_value=True,
					label=_FN_SWAP[1], description=_FN_SWAP[2])


def check_features(device, already_known):
	if device.protocol is not None and device.protocol < 2.0:
		return
	if not any(s.name == _FN_SWAP[0] for s in already_known) and _hidpp20.FEATURE.FN_INVERSION in device.features:
		already_known.append(_feature_fn_swap())

#
#
#

_DeviceDescriptor = namedtuple('_DeviceDescriptor',
				['name', 'kind', 'product_id', 'codename', 'protocol', 'registers', 'settings'])

DEVICES = {}

def _D(name, codename=None, kind=None, product_id=None, protocol=None, registers=None, settings=None):
	if kind is None:
		kind = (_hidpp10.DEVICE_KIND.mouse if 'Mouse' in name
				else _hidpp10.DEVICE_KIND.keyboard if 'Keyboard' in name
				else _hidpp10.DEVICE_KIND.touchpad if 'Touchpad' in name
				else _hidpp10.DEVICE_KIND.trackball if 'Trackball' in name
				else None)
	assert kind is not None, "descriptor for %s does not have 'kind' set" % name

	# heuristic: the codename is the last word in the device name
	if codename is None:
		codename = name.split(' ')[-1]
	assert codename is not None, "descriptor for %s does not have codename set" % name

	if protocol is not None:
		# ? 2.0 devices should not have any registers
		assert protocol < 2.0 or registers is None

	DEVICES[codename] = _DeviceDescriptor(
					name=name,
					kind=kind,
					product_id=product_id,
					codename=codename,
					protocol=protocol,
					registers=registers,
					settings=settings)
	if product_id:
		DEVICES[product_id] = DEVICES[codename]

#
#
#

# Some HID++1.0 registers and HID++2.0 features can be discovered at run-time,
# so they are not specified here.
#
# For known registers, however, please do specify them here -- avoids
# unnecessary communication with the device and makes it easier to make certain
# decisions when querying the device's state.
#
# Specify a negative value to blacklist a certain register for a device.
#
# Usually, state registers (battery, leds, some features, etc) are only used by
# HID++ 1.0 devices, while HID++ 2.0 devices use features for the same
# functionalities. This is a rule that's been discovered by trial-and-error,
# so it may change in the future.

# Well-known registers (in hex):
#  * 00 - notification flags (all devices)
#    01 - mice: smooth scrolling
#    07 - battery status
#    09 - keyboards: FN swap (if it has the FN key)
#    0D - battery charge
#       a device may have either the 07 or 0D register available;
#       no known device uses both
#    51 - leds
#    63 - mice: DPI
#    F1 - firmware info
# Some registers appear to be universally supported, no matter the HID++ version
# (marked with *). The rest may or may not be supported, and their values may or
# may not mean the same thing across different devices.

# The 'registers' field indicates read-only registers, specifying a state.
# The 'settings' field indicates a read/write register; based on them Solaar
# generates, at runtime, the settings controls in the device panel.
#
# HID++ 2.0 features are not specified here, they are always discovered at
# run-time.

# Keyboards

_D('Wireless Keyboard K230', protocol=2.0)
_D('Wireless Keyboard K270')
_D('Wireless Keyboard K350')
_D('Wireless Keyboard K360', protocol=2.0)
_D('Wireless Touch Keyboard K400', protocol=2.0)
_D('Wireless Keyboard K700', codename='MK700', protocol=1.0,
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_fn_swap(0x09, true_value=b'\x00\x01', mask=b'\x00\x01'),
						],
				)
_D('Wireless Solar Keyboard K750', protocol=2.0,
				settings=[
							_feature_fn_swap()
						],
				)
_D('Wireless Illuminated Keyboard K800', protocol=1.0,
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_fn_swap(0x09, true_value=b'\x00\x01', mask=b'\x00\x01'),
						],
				)

# Mice

_D('Wireless Mouse M215', protocol=1.0)
_D('Wireless Mouse M315')
_D('Wireless Mouse M325')
_D('Wireless Mouse M505')
_D('Wireless Mouse M510', protocol=1.0,
				registers={'battery_charge': -0x0D, 'battery_status': 0x07},
				settings=[
							_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
						],
				)
_D('Couch Mouse M515', protocol=2.0)
_D('Wireless Mouse M525', protocol=2.0)
_D('Touch Mouse M600')
_D('Marathon Mouse M705', protocol=1.0,
				registers={'battery_charge': 0x0D},
				settings=[
							_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
							# _register_dpi(0x63, _NamedInts(**{'100': 10, '300': 30, '350':35, '500':50})),
						],
				)
_D('Zone Touch Mouse T400')
_D('Touch Mouse T620')
_D('Logitech Cube', kind=_hidpp10.DEVICE_KIND.mouse, protocol=2.0)
_D('Anywhere Mouse MX', codename='Anywhere MX',
				# registers={'battery_charge': 0x0D},
				# settings=[
				# 			_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
				# 		],
				)
_D('Performance Mouse MX', codename='Performance MX', protocol=1.0,
				registers={'battery_charge': -0x0D, 'battery_status': 0x07, 'leds': 0x51},
				settings=[
							_register_dpi(0x63, _NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))),
						],
				)

# Trackballs

_D('Wireless Trackball M570')

# Touchpads

_D('Wireless Rechargeable Touchpad T650')

#
# classic Nano devices
# a product_id is necessary to properly identify them
#

_D('VX Nano Cordless Laser Mouse', codename='VX Nano', protocol=1.0, product_id='c526',
				registers={'battery_charge': 0x0D, 'battery_status': -0x07},
				settings=[
							_register_smooth_scroll(0x01, true_value=0x40, mask=0x40),
						],
				)

del namedtuple
