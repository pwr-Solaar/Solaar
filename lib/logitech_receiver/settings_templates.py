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

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

from .i18n import _
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import (
				bytes2int as _bytes2int,
				int2bytes as _int2bytes,
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
				RangeValidator as _RangeV,
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
						label=label, description=description, device_kind=device_kind)
		return setting(device)
	return instantiate

def feature_range(name, feature, min_value, max_value,
					read_function_id=_FeatureRW.default_read_fnid,
					write_function_id=_FeatureRW.default_write_fnid,
					rw=None,
					bytes_count=None,
					label=None, description=None, device_kind=None):
	validator = _RangeV(min_value, max_value, bytes_count=bytes_count)
	if rw is None:
		rw = _FeatureRW(feature, read_function_id, write_function_id)
	return _Setting(name, rw, validator, kind=_KIND.range, label=label, description=description, device_kind=device_kind)

#
# common strings for settings
#

_SMOOTH_SCROLL = ('smooth-scroll', _("Smooth Scrolling"),
							_("High-sensitivity mode for vertical scroll with the wheel."))
_LOW_RES_SCROLL = ('lowres-smooth-scroll', _("HID++ Scrolling"),
							_("HID++ mode for vertical scroll with the wheel."))

_HI_RES_SCROLL = ('hi-res-scroll', _("High Resolution Scrolling"),
							_("High-sensitivity mode for vertical scroll with the wheel."))
_HIRES_INV = ('hires-smooth-invert', _("High Resolution Wheel Invert"),
							_("High-sensitivity wheel invert mode for vertical scroll."))
_HIRES_RES = ('hires-smooth-resolution', _("Wheel Resolution"),
							_("High-sensitivity mode for vertical scroll with the wheel."))
_SIDE_SCROLL = ('side-scroll', _("Side Scrolling"),
							_("When disabled, pushing the wheel sideways sends custom button events\n"
							"instead of the standard side-scrolling events."))
_DPI = ('dpi', _("Sensitivity (DPI)"), None)
_POINTER_SPEED = ('pointer_speed', _("Sensitivity (Pointer Speed)"), None)
_FN_SWAP = ('fn-swap', _("Swap Fx function"),
							_("When set, the F1..F12 keys will activate their special function,\n"
						 	"and you must hold the FN key to activate their standard function.")
						 	+ '\n\n' +
						 	_("When unset, the F1..F12 keys will activate their standard function,\n"
						 	"and you must hold the FN key to activate their special function."))
_HAND_DETECTION = ('hand-detection', _("Hand Detection"),
							_("Turn on illumination when the hands hover over the keyboard."))
_BACKLIGHT = ('backlight', _("Backlight"),
				   _("Turn illumination on or off on keyboard."))

_SMART_SHIFT = ('smart-shift', _("Smart Shift"),
							_("Automatically switch the mouse wheel between ratchet and freespin mode.\n"
							"The mouse wheel is always free at 0, and always locked at 50"))
#
#
#

def _register_hand_detection(register=_R.keyboard_hand_detection,
					true_value=b'\x00\x00\x00', false_value=b'\x00\x00\x30', mask=b'\x00\x00\xFF'):
	return register_toggle(_HAND_DETECTION[0], register, true_value=true_value, false_value=false_value,
					label=_HAND_DETECTION[1], description=_HAND_DETECTION[2],
					device_kind=(_DK.keyboard,))

def _register_fn_swap(register=_R.keyboard_fn_swap, true_value=b'\x00\x01', mask=b'\x00\x01'):
	return register_toggle(_FN_SWAP[0], register, true_value=true_value, mask=mask,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=(_DK.keyboard,))

def _register_smooth_scroll(register=_R.mouse_button_flags, true_value=0x40, mask=0x40):
	return register_toggle(_SMOOTH_SCROLL[0], register, true_value=true_value, mask=mask,
					label=_SMOOTH_SCROLL[1], description=_SMOOTH_SCROLL[2],
					device_kind=(_DK.mouse, _DK.trackball))

def _register_side_scroll(register=_R.mouse_button_flags, true_value=0x02, mask=0x02):
	return register_toggle(_SIDE_SCROLL[0], register, true_value=true_value, mask=mask,
 					label=_SIDE_SCROLL[1], description=_SIDE_SCROLL[2],
					device_kind=(_DK.mouse, _DK.trackball))

def _register_dpi(register=_R.mouse_dpi, choices=None):
	return register_choices(_DPI[0], register, choices,
					label=_DPI[1], description=_DPI[2],
					device_kind=(_DK.mouse, _DK.trackball))


def _feature_fn_swap():
	return feature_toggle(_FN_SWAP[0], _F.FN_INVERSION,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=(_DK.keyboard,))

def _feature_new_fn_swap():
	return feature_toggle(_FN_SWAP[0], _F.NEW_FN_INVERSION,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=(_DK.keyboard,))

def _feature_k375s_fn_swap():
	return feature_toggle(_FN_SWAP[0], _F.K375S_FN_INVERSION,
					label=_FN_SWAP[1], description=_FN_SWAP[2],
					device_kind=(_DK.keyboard,))

# FIXME: This will enable all supported backlight settings, we should allow the users to select which settings they want to enable.
def _feature_backlight2():
	return feature_toggle(_BACKLIGHT[0], _F.BACKLIGHT2,
						  label=_BACKLIGHT[1], description=_BACKLIGHT[2],
						  device_kind=(_DK.keyboard,))

def _feature_hi_res_scroll():
	return feature_toggle(_HI_RES_SCROLL[0], _F.HI_RES_SCROLLING,
					label=_HI_RES_SCROLL[1], description=_HI_RES_SCROLL[2],
					device_kind=(_DK.mouse, _DK.trackball))

def _feature_lowres_smooth_scroll():
	return feature_toggle(_LOW_RES_SCROLL[0], _F.LOWRES_WHEEL,
					label=_LOW_RES_SCROLL[1], description=_LOW_RES_SCROLL[2],
					device_kind=(_DK.mouse, _DK.trackball))
def _feature_hires_smooth_invert():
	return feature_toggle(_HIRES_INV[0], _F.HIRES_WHEEL,
					read_function_id=0x10,
					write_function_id=0x20,
					true_value=0x04, mask=0x04,
					label=_HIRES_INV[1], description=_HIRES_INV[2],
					device_kind=(_DK.mouse, _DK.trackball))

def _feature_hires_smooth_resolution():
	return feature_toggle(_HIRES_RES[0], _F.HIRES_WHEEL,
					read_function_id=0x10,
					write_function_id=0x20,
					true_value=0x02, mask=0x02,
					label=_HIRES_RES[1], description=_HIRES_RES[2],
					device_kind=(_DK.mouse, _DK.trackball))

def _feature_smart_shift():
	_MIN_SMART_SHIFT_VALUE = 0
	_MAX_SMART_SHIFT_VALUE = 50
	class _SmartShiftRW(_FeatureRW):
		def __init__(self, feature):
			super(_SmartShiftRW, self).__init__(feature)

		def read(self, device):
			value = super(_SmartShiftRW, self).read(device)
			if _bytes2int(value[0:1]) == 1:
				# Mode = Freespin, map to minimum
				return _int2bytes(_MIN_SMART_SHIFT_VALUE, count=1)
			else:
				# Mode = smart shift, map to the value, capped at maximum
				threshold = min(_bytes2int(value[1:2]), _MAX_SMART_SHIFT_VALUE)
				return _int2bytes(threshold, count=1)

		def write(self, device, data_bytes):
			threshold = _bytes2int(data_bytes)
			# Freespin at minimum
			mode = 1 if threshold == _MIN_SMART_SHIFT_VALUE else 2

			# Ratchet at maximum
			if threshold == _MAX_SMART_SHIFT_VALUE:
				threshold = 255

			data = _int2bytes(mode, count=1) + _int2bytes(threshold, count=1) * 2
			return super(_SmartShiftRW, self).write(device, data)

	return feature_range(_SMART_SHIFT[0], _F.SMART_SHIFT,
	                _MIN_SMART_SHIFT_VALUE, _MAX_SMART_SHIFT_VALUE,
					bytes_count=1,
					rw=_SmartShiftRW(_F.SMART_SHIFT),
					label=_SMART_SHIFT[1], description=_SMART_SHIFT[2],
					device_kind=(_DK.mouse, _DK.trackball))

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
		assert len(dpi_list) == 2, 'Invalid DPI list range: %r' % dpi_list
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
					device_kind=(_DK.mouse, _DK.trackball))

def _feature_pointer_speed():
	"""Pointer Speed feature"""
	# min and max values taken from usb traces of Win software
	return feature_range(_POINTER_SPEED[0], _F.POINTER_SPEED, 0x002e, 0x01ff,
					read_function_id=0x0,
					write_function_id=0x10,
					bytes_count=2,
					label=_POINTER_SPEED[1], description=_POINTER_SPEED[2],
					device_kind=(_DK.mouse, _DK.trackball))
#
#
#

from collections import namedtuple
_SETTINGS_LIST = namedtuple('_SETTINGS_LIST', [
					'fn_swap',
					'new_fn_swap',
					'k375s_fn_swap',
					'smooth_scroll',
					'hi_res_scroll',
					'lowres_smooth_scroll',
					'hires_smooth_invert',
					'hires_smooth_resolution',
					'side_scroll',
					'dpi',
					'pointer_speed',
					'hand_detection',
					'backlight',
					'typing_illumination',
					'smart_shift',
					])
del namedtuple

RegisterSettings = _SETTINGS_LIST(
				fn_swap=_register_fn_swap,
				new_fn_swap=None,
				k375s_fn_swap=None,
				smooth_scroll=_register_smooth_scroll,
				hi_res_scroll=None,
				lowres_smooth_scroll=None,
				hires_smooth_invert=None,
				hires_smooth_resolution=None,
				side_scroll=_register_side_scroll,
				dpi=_register_dpi,
				pointer_speed=None,
				hand_detection=_register_hand_detection,
				backlight=None,
				typing_illumination=None,
				smart_shift=None,
			)
FeatureSettings =  _SETTINGS_LIST(
				fn_swap=_feature_fn_swap,
				new_fn_swap=_feature_new_fn_swap,
				k375s_fn_swap=_feature_k375s_fn_swap,
				smooth_scroll=None,
				hi_res_scroll=_feature_hi_res_scroll,
				lowres_smooth_scroll=_feature_lowres_smooth_scroll,
				hires_smooth_invert=_feature_hires_smooth_invert,
				hires_smooth_resolution=_feature_hires_smooth_resolution,
				side_scroll=None,
				dpi=_feature_adjustable_dpi,
				pointer_speed=_feature_pointer_speed,
				hand_detection=None,
				backlight=_feature_backlight2,
				typing_illumination=None,
				smart_shift=_feature_smart_shift,
			)

del _SETTINGS_LIST

#
#
#

def check_feature_settings(device, already_known):
	"""Try to auto-detect device settings by the HID++ 2.0 features they have."""
	if device.features is None or not device.online:
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

		try:
			detected = feature(device)
			if _log.isEnabledFor(_DEBUG):
			    _log.debug("check_feature[%s] detected %s", featureId, detected)
			already_known.append(detected)
		except Exception as reason:
			_log.error("check_feature[%s] inconsistent feature %s", featureId, reason)

	check_feature(_HI_RES_SCROLL[0], _F.HI_RES_SCROLLING)
	check_feature(_LOW_RES_SCROLL[0], _F.LOWRES_WHEEL)
	check_feature(_HIRES_INV[0],     _F.HIRES_WHEEL, "hires_smooth_invert")
	check_feature(_HIRES_RES[0],     _F.HIRES_WHEEL, "hires_smooth_resolution")
	check_feature(_FN_SWAP[0],       _F.FN_INVERSION)
	check_feature(_FN_SWAP[0],       _F.NEW_FN_INVERSION, 'new_fn_swap')
	check_feature(_FN_SWAP[0],       _F.K375S_FN_INVERSION, 'k375s_fn_swap')
	check_feature(_DPI[0],           _F.ADJUSTABLE_DPI)
	check_feature(_POINTER_SPEED[0], _F.POINTER_SPEED)
	check_feature(_SMART_SHIFT[0],   _F.SMART_SHIFT)
	check_feature(_BACKLIGHT[0],   	 _F.BACKLIGHT2)
