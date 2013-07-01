#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .settings import (
				KIND as _KIND,
				Setting as _Setting,
				RegisterRW as _RegisterRW,
				FeatureRW as _FeatureRW,
				BooleanValidator as _BooleanV,
				ChoicesValidator as _ChoicesV,
			)

#
# pre-defined basic setting descriptors
#

def register_toggle(name, register,
					true_value=_BooleanV.default_true, false_value=_BooleanV.default_false,
					mask=_BooleanV.default_mask, write_returns_value=False,
					label=None, description=None, device_kind=None):
	rw = _RegisterRW(register)
	validator = _BooleanV(true_value=true_value, false_value=false_value, mask=mask, write_returns_value=write_returns_value)
	return _Setting(name, rw, validator, label=label, description=description, device_kind=device_kind)


def register_choices(name, register, choices,
					kind=_KIND.choice, write_returns_value=False,
					label=None, description=None, device_kind=None):
	assert choices
	rw = _RegisterRW(register)
	validator = _ChoicesV(choices, write_returns_value=write_returns_value)
	return _Setting(name, rw, validator, kind=kind, label=label, description=description, device_kind=device_kind)


def feature_toggle(name, feature,
					read_function_id=_FeatureRW.default_read_fnid, write_function_id=_FeatureRW.default_write_fnid,
					true_value=_BooleanV.default_true, false_value=_BooleanV.default_false,
					mask=_BooleanV.default_mask, write_returns_value=False,
					label=None, description=None, device_kind=None):
	rw = _FeatureRW(feature, read_function_id, write_function_id)
	validator = _BooleanV(true_value=true_value, false_value=false_value, mask=mask, write_returns_value=write_returns_value)
	return _Setting(name, rw, validator, label=label, description=description, device_kind=device_kind)

#
# common strings for settings
#

_SMOOTH_SCROLL = ('smooth-scroll', 'Smooth Scrolling',
							'High-sensitivity mode for vertical scroll with the wheel.')
_DPI = ('dpi', 'Sensitivity (DPI)', None)
_FN_SWAP = ('fn-swap', 'Swap Fx function',
							('When set, the F1..F12 keys will activate their special function,\n'
						 	'and you must hold the FN key to activate their standard function.\n'
						 	'\n'
						 	'When unset, the F1..F12 keys will activate their standard function,\n'
						 	'and you must hold the FN key to activate their special function.'))

#
#
#

def _register_fn_swap(register=0x09, true_value=b'\x00\x01', mask=b'\x00\x01'):
	return register_toggle(_FN_SWAP[0], register, true_value=true_value, mask=mask,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=_hidpp10.DEVICE_KIND.keyboard)

def _register_smooth_scroll(register=0x01, true_value=0x40, mask=0x40):
	return register_toggle(_SMOOTH_SCROLL[0], register, true_value=true_value, mask=mask,
					label=_SMOOTH_SCROLL[1], description=_SMOOTH_SCROLL[2],
					device_kind=_hidpp10.DEVICE_KIND.mouse)

def _register_dpi(register=0x63, choices=None):
	return register_choices(_DPI[0], register, choices,
					label=_DPI[1], description=_DPI[2],
					device_kind=_hidpp10.DEVICE_KIND.mouse)


def _feature_fn_swap():
	return feature_toggle(_FN_SWAP[0], _hidpp20.FEATURE.FN_INVERSION,
					write_returns_value=True,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=_hidpp10.DEVICE_KIND.keyboard)


#
#
#

from collections import namedtuple
_SETTINGS_LIST = namedtuple('_SETTINGS_LIST', [
					'fn_swap',
					'smooth_scroll',
					'dpi',
					'hand_detection',
					'typing_illumination',
					])
del namedtuple

Register = _SETTINGS_LIST(
				fn_swap=_register_fn_swap,
				smooth_scroll=_register_smooth_scroll,
				dpi=_register_dpi,
				hand_detection=None,
				typing_illumination=None,
			)
Feature =  _SETTINGS_LIST(
				fn_swap=_feature_fn_swap,
				smooth_scroll=None,
				dpi=None,
				hand_detection=None,
				typing_illumination=None,
			)

del _SETTINGS_LIST

#
#
#

def check_feature_settings(device, already_known):
	"""Try to auto-detect device settings by the HID++ 2.0 features they have."""
	if device.protocol is not None and device.protocol < 2.0:
		return
	if not any(s.name == _FN_SWAP[0] for s in already_known) and _hidpp20.FEATURE.FN_INVERSION in device.features:
		fn_swap = Feature.fn_swap()
		already_known.append(fn_swap(device))
