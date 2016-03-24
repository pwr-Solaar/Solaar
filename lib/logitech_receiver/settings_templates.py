# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import absolute_import, division, print_function, unicode_literals


from .i18n import _
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import (
				bytes2int as _bytes2int,
				NamedInts as _NamedInts,
				unpack as _unpack,
			)
from .settings import (
				KIND as _KIND,
				Setting as _Setting,
				RegisterRW as _RegisterRW,
				FeatureRW as _FeatureRW,
				BooleanValidator as _BooleanV,
				ChoicesValidator as _ChoicesV,
			)

_DK = _hidpp10.DEVICE_KIND
_R = _hidpp10.REGISTERS
_F = _hidpp20.FEATURE

#
# pre-defined basic setting descriptors
#

def register_toggle(name, register,
					true_value=_BooleanV.default_true,
					false_value=_BooleanV.default_false,
					mask=_BooleanV.default_mask,
					label=None, description=None, device_kind=None):
	validator = _BooleanV(true_value=true_value, false_value=false_value, mask=mask)
	rw = _RegisterRW(register)
	return _Setting(name, rw, validator, label=label, description=description, device_kind=device_kind)


def register_choices(name, register, choices,
					kind=_KIND.choice,
					label=None, description=None, device_kind=None):
	assert choices
	validator = _ChoicesV(choices)
	rw = _RegisterRW(register)
	return _Setting(name, rw, validator, kind=kind, label=label, description=description, device_kind=device_kind)


def feature_toggle(name, feature,
					read_function_id=_FeatureRW.default_read_fnid,
					write_function_id=_FeatureRW.default_write_fnid,
					true_value=_BooleanV.default_true,
					false_value=_BooleanV.default_false,
					mask=_BooleanV.default_mask,
					label=None, description=None, device_kind=None):
	validator = _BooleanV(true_value=true_value, false_value=false_value, mask=mask)
	rw = _FeatureRW(feature, read_function_id, write_function_id)
	return _Setting(name, rw, validator, label=label, description=description, device_kind=device_kind)

def feature_choices(name, feature, choices,
					read_function_id, write_function_id,
					bytes_count=None,
					label=None, description=None, device_kind=None):
	assert choices
	validator = _ChoicesV(choices, bytes_count=bytes_count)
	rw = _FeatureRW(feature, read_function_id, write_function_id)
	return _Setting(name, rw, validator, kind=_KIND.choice, label=label, description=description, device_kind=device_kind)

def feature_choices_dynamic(name, feature, choices_callback,
					read_function_id, write_function_id,
					bytes_count=None,
					label=None, description=None, device_kind=None):
	# Proxy that obtains choices dynamically from a device
	def instantiate(device):
		# Obtain choices for this feature
		choices = choices_callback(device)
		setting = feature_choices(name, feature, choices,
						read_function_id, write_function_id,
						bytes_count=bytes_count,
						label=None, description=None, device_kind=None)
		return setting(device)
	return instantiate

#
# common strings for settings
#

_SMOOTH_SCROLL = ('smooth-scroll', _("Smooth Scrolling"),
							_("High-sensitivity mode for vertical scroll with the wheel."))
_SIDE_SCROLL = ('side-scroll', _("Side Scrolling"),
							_("When disabled, pushing the wheel sideways sends custom button events\n"
							"instead of the standard side-scrolling events."))
_DPI = ('dpi', _("Sensitivity (DPI)"), None)
_FN_SWAP = ('fn-swap', _("Swap Fx function"),
							_("When set, the F1..F12 keys will activate their special function,\n"
						 	"and you must hold the FN key to activate their standard function.")
						 	+ '\n\n' +
						 	_("When unset, the F1..F12 keys will activate their standard function,\n"
						 	"and you must hold the FN key to activate their special function."))
_HAND_DETECTION = ('hand-detection', _("Hand Detection"),
							_("Turn on illumination when the hands hover over the keyboard."))

#
#
#

def _register_hand_detection(register=_R.keyboard_hand_detection,
					true_value=b'\x00\x00\x00', false_value=b'\x00\x00\x30', mask=b'\x00\x00\xFF'):
	return register_toggle(_HAND_DETECTION[0], register, true_value=true_value, false_value=false_value,
					label=_HAND_DETECTION[1], description=_HAND_DETECTION[2],
					device_kind=_DK.keyboard)

def _register_fn_swap(register=_R.keyboard_fn_swap, true_value=b'\x00\x01', mask=b'\x00\x01'):
	return register_toggle(_FN_SWAP[0], register, true_value=true_value, mask=mask,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=_DK.keyboard)

def _register_smooth_scroll(register=_R.mouse_button_flags, true_value=0x40, mask=0x40):
	return register_toggle(_SMOOTH_SCROLL[0], register, true_value=true_value, mask=mask,
					label=_SMOOTH_SCROLL[1], description=_SMOOTH_SCROLL[2],
					device_kind=_DK.mouse)

def _register_side_scroll(register=_R.mouse_button_flags, true_value=0x02, mask=0x02):
	return register_toggle(_SIDE_SCROLL[0], register, true_value=true_value, mask=mask,
 					label=_SIDE_SCROLL[1], description=_SIDE_SCROLL[2],
					device_kind=_DK.mouse)

def _register_dpi(register=_R.mouse_dpi, choices=None):
	return register_choices(_DPI[0], register, choices,
					label=_DPI[1], description=_DPI[2],
					device_kind=_DK.mouse)


def _feature_fn_swap():
	return feature_toggle(_FN_SWAP[0], _F.FN_INVERSION,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=_DK.keyboard)

def _feature_new_fn_swap():
	return feature_toggle(_FN_SWAP[0], _F.NEW_FN_INVERSION,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=_DK.keyboard)

def _feature_smooth_scroll():
	return feature_toggle(_SMOOTH_SCROLL[0], _F.HI_RES_SCROLLING,
					label=_SMOOTH_SCROLL[1], description=_SMOOTH_SCROLL[2],
					device_kind=_DK.mouse)

def _feature_adjustable_dpi_choices(device):
	# [1] getSensorDpiList(sensorIdx)
	reply = device.feature_request(_F.ADJUSTABLE_DPI, 0x10)
	# Should not happen, but might happen when the user unplugs device while the
	# query is being executed. TODO retry logic?
	assert reply, 'Oops, DPI list cannot be retrieved!'
	dpi_list = []
	step = None
	for val in _unpack('!7H', reply[1:1+14]):
		if val == 0:
			break
		if val >> 13 == 0b111:
			assert step is None and len(dpi_list) == 1, \
					'Invalid DPI list item: %r' % val
			step = val & 0x1fff
		else:
			dpi_list.append(val)
	if step:
		assert dpi_list == 2, 'Invalid DPI list range: %r' % dpi_list
		dpi_list = range(dpi_list[0], dpi_list[1] + 1, step)
	return _NamedInts.list(dpi_list)

def _feature_adjustable_dpi():
	"""Pointer Speed feature"""
	# Assume sensorIdx 0 (there is only one sensor)
	# [2] getSensorDpi(sensorIdx) -> sensorIdx, dpiMSB, dpiLSB
	# [3] setSensorDpi(sensorIdx, dpi)
	return feature_choices_dynamic(_DPI[0], _F.ADJUSTABLE_DPI,
					_feature_adjustable_dpi_choices,
					read_function_id=0x20,
					write_function_id=0x30,
					bytes_count=3,
					label=_DPI[1], description=_DPI[2],
					device_kind=_DK.mouse)

#
#
#

from collections import namedtuple
_SETTINGS_LIST = namedtuple('_SETTINGS_LIST', [
					'fn_swap',
					'new_fn_swap',
					'smooth_scroll',
					'side_scroll',
					'dpi',
					'hand_detection',
					'typing_illumination',
					])
del namedtuple

RegisterSettings = _SETTINGS_LIST(
				fn_swap=_register_fn_swap,
				new_fn_swap=None,
				smooth_scroll=_register_smooth_scroll,
				side_scroll=_register_side_scroll,
				dpi=_register_dpi,
				hand_detection=_register_hand_detection,
				typing_illumination=None,
			)
FeatureSettings =  _SETTINGS_LIST(
				fn_swap=_feature_fn_swap,
				new_fn_swap=_feature_new_fn_swap,
				smooth_scroll=_feature_smooth_scroll,
				side_scroll=None,
				dpi=_feature_adjustable_dpi,
				hand_detection=None,
				typing_illumination=None,
			)

del _SETTINGS_LIST

#
#
#

def check_feature_settings(device, already_known):
	"""Try to auto-detect device settings by the HID++ 2.0 features they have."""
	if device.features is None:
		return
	if device.protocol and device.protocol < 2.0:
		return

	def check_feature(name, featureId, field_name=None):
		"""
		:param name: user-visible setting name.
		:param featureId: the numeric Feature ID for this setting.
		:param field_name: override the FeatureSettings name if it is
		different from the user-visible setting name. Useful if there
		are multiple features for the same setting.
		"""
		if not featureId in device.features:
			return
		if any(s.name == name for s in already_known):
			return
		if not field_name:
			# Convert user-visible settings name for FeatureSettings
			field_name = name.replace('-', '_')
		feature = getattr(FeatureSettings, field_name)()
		already_known.append(feature(device))

	check_feature(_SMOOTH_SCROLL[0], _F.HI_RES_SCROLLING)
	check_feature(_FN_SWAP[0],      _F.FN_INVERSION)
	check_feature(_FN_SWAP[0],      _F.NEW_FN_INVERSION, 'new_fn_swap')
	check_feature(_DPI[0],          _F.ADJUSTABLE_DPI)
