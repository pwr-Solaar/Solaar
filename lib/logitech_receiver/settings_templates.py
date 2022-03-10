# -*- python-mode -*-

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

from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import WARN as _WARN
from logging import getLogger
from time import time as _time

from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from . import special_keys as _special_keys
from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes
from .common import unpack as _unpack
from .i18n import _
from .settings import ActionSettingRW as _ActionSettingRW
from .settings import BitFieldSetting as _BitFieldSetting
from .settings import BitFieldValidator as _BitFieldV
from .settings import BitFieldWithOffsetAndMaskSetting as _BitFieldOMSetting
from .settings import BitFieldWithOffsetAndMaskValidator as _BitFieldOMV
from .settings import ChoicesMapValidator as _ChoicesMapV
from .settings import ChoicesValidator as _ChoicesV
from .settings import FeatureRW as _FeatureRW
from .settings import LongSettings as _LongSettings
from .settings import MultipleRangeValidator as _MultipleRangeV
from .settings import RangeValidator as _RangeV
from .settings import Setting as _Setting
from .settings import Settings as _Settings
from .special_keys import DISABLE as _DKEY

_log = getLogger(__name__)
del getLogger

_DK = _hidpp10.DEVICE_KIND
_R = _hidpp10.REGISTERS
_F = _hidpp20.FEATURE

_GG = _hidpp20.GESTURE
_GP = _hidpp20.PARAM

# Setting classes are used to control the settings that the Solaar GUI shows and manipulates.
# Each setting class has to several class variables:
# name, which is used as a key when storing information about the setting,
#   setting classes can have the same name, as long as devices only have one setting with the same name;
# label, which is shown in the Solaar main window;
# description, which is shown when the mouse hovers over the setting in the main window;
# either register or feature, the register or feature that the setting uses;
# rw_class, the class of the reader/writer (if it is not the standard one),
# rw_options, a dictionary of options for the reader/writer.
# validator_class, the class of the validator (default settings.BooleanValidator)
# validator_options, a dictionary of options for the validator
# persist (inherited True), which is whether to store the value and apply it when setting up the device.
#
# The different setting classes imported from settings.py are for different numbers and kinds of arguments.
# _Setting is for settings with a single value (boolean, number in a range, and symbolic choice).
# _Settings is for settings that are maps from keys to values
#    and permit reading or writing the entire map or just one key/value pair.
# The _BitFieldSetting class is for settings that have multiple boolean values packed into a bit field.
# _BitFieldOMSetting is similar.
# _LongSettings is for settings that have an even more complex structure.
#
# When settings are created a reader/writer and a validator are created.

# If the setting class has a value for rw_class then an instance of that class is created.
# Otherwise if the setting has a register then an instance of settings.RegisterRW is created.
# and if the setting has a feature then then an instance of _FeatureRW is created.
# The instance is created with the register or feature as the first argument and rw_options as keyword arguments.
# _RegisterRW doesn't use any options.
# _FeatureRW options include
#   read_fnid - the feature function (times 16) to read the value (default 0x00),
#   write_fnid - the feature function (times 16) to write the value (default 0x10),
#   prefix - a prefix to add to the data being written and the read request (default b''), used for features
#     that provide and set multiple settings (e.g., to read and write function key inversion for current host)
#   no_reply - whether to wait for a reply (default false) (USE WITH EXTREME CAUTION).
#
# There are three simple validator classes - _BooleanV, _RangeV, and _ChoicesV
# _BooleanV is for boolean values and is the default.  It takes
#   true_value is the raw value for true (default 0x01), this can be an integer or a byte string,
#   false_value is the raw value for false (default 0x00), this can be an integer or a byte string,
#   mask is used to keep only some bits from a sequence of bits, this can be an integer or a byte string,
#   read_skip_byte_count is the number of bytes to ignore at the beginning of the read value (default 0),
#   write_prefix_bytes is a byte string to write before the value (default empty).
# _RangeV is for an integer in a range.  It takes
#   byte_count is number of bytes that the value is stored in (defaults to size of max_value).
# _RangeV uses min_value and max_value from the setting class as minimum and maximum.

# _ChoicesV is for symbolic choices.  It takes one positional and three keyword arguments:
#   choices is a list of named integers that are the valid choices,
#   byte_count is the number of bytes for the integer (default size of largest choice integer),
#   read_skip_byte_count is as for _BooleanV,
#   write_prefix_bytes is as for _BooleanV.
# Settings that use _ChoicesV should have a choices_universe class variable of the potential choices,
# or None for no limitation and optionally a choices_extra class variable with an extra choice.
# The choices_extra is so that there is no need to specially extend a large existing NamedInts.
# _ChoicesMapV validator is for map settings that map onto symbolic choices.   It takes
#   choices_map is a map from keys to possible values
#   byte_count is as for _ChoicesV,
#   read_skip_byte_count is as for _ChoicesV,
#   write_prefix_bytes is as for _ChoicesV,
#   key_byte_count is the number of bytes for the key integer (default size of largest key),
#   extra_default is an extra raw value that is used as a default value (default None).
# Settings that use _ChoicesV should have keys_universe and choices_universe class variable of
# the potential keys and potential choices or None for no limitation.

# _BitFieldV validator is for bit field settings.  It takes one positional and one keyword argument
#   the positional argument is the number of bits in the bit field
#   byte_count is the size of the bit field (default size of the bit field)
#
# A few settings work very differently.  They divert a key, which is then used to start and stop some special action.
# These settings have reader/writer classes that perform special processing instead of sending commands to the device.


# yapf: disable
class FnSwapVirtual(_Setting):  # virtual setting to hold fn swap strings
    name = 'fn-swap'
    label = _('Swap Fx function')
    description = (_('When set, the F1..F12 keys will activate their special function,\n'
                     'and you must hold the FN key to activate their standard function.') + '\n\n' +
                   _('When unset, the F1..F12 keys will activate their standard function,\n'
                     'and you must hold the FN key to activate their special function.'))
# yapf: enable


class RegisterHandDetection(_Setting):
    name = 'hand-detection'
    label = _('Hand Detection')
    description = _('Turn on illumination when the hands hover over the keyboard.')
    register = _R.keyboard_hand_detection
    validator_options = {'true_value': b'\x00\x00\x00', 'false_value': b'\x00\x00\x30', 'mask': b'\x00\x00\xFF'}


class RegisterSmoothScroll(_Setting):
    name = 'smooth-scroll'
    label = _('Scroll Wheel Smooth Scrolling')
    description = _('High-sensitivity mode for vertical scroll with the wheel.')
    register = _R.mouse_button_flags
    validator_options = {'true_value': 0x40, 'mask': 0x40}


class RegisterSideScroll(_Setting):
    name = 'side-scroll'
    label = _('Side Scrolling')
    description = _(
        'When disabled, pushing the wheel sideways sends custom button events\n'
        'instead of the standard side-scrolling events.'
    )
    register = _R.mouse_button_flags
    validator_options = {'true_value': 0x02, 'mask': 0x02}


# different devices have different sets of permissable dpis, so this should be subclassed
class RegisterDpi(_Setting):
    name = 'dpi-old'
    label = _('Sensitivity (DPI - older mice)')
    description = _('Mouse movement sensitivity')
    register = _R.mouse_dpi
    choices_universe = _NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))
    validator_class = _ChoicesV
    validator_options = {'choices': choices_universe}


class RegisterFnSwap(FnSwapVirtual):
    register = _R.keyboard_fn_swap
    validator_options = {'true_value': b'\x00\x01', 'mask': b'\x00\x01'}


class FnSwap(FnSwapVirtual):
    feature = _F.FN_INVERSION


class NewFnSwap(FnSwapVirtual):
    feature = _F.NEW_FN_INVERSION


# ignore the capabilities part of the feature - all devices should be able to swap Fn state
# just use the current host (first byte = 0xFF) part of the feature to read and set the Fn state
class K375sFnSwap(FnSwapVirtual):
    feature = _F.K375S_FN_INVERSION
    rw_options = {'prefix': b'\xFF'}
    validator_options = {'true_value': b'\x01', 'false_value': b'\x00', 'read_skip_byte_count': 1}


class Backlight(_Setting):
    name = 'backlight-qualitative'
    description = _('Set illumination time for keyboard.')
    feature = _F.BACKLIGHT
    choices_universe = _NamedInts(Off=0, Short=5, Medium=20, Long=60, VeryLong=180)
    validator_class = _ChoicesV
    validator_options = {'choices': choices_universe}


class Backlight2(_Setting):
    label = _('Backlight')
    description = _('Turn illumination on or off on keyboard.')
    name = 'backlight'
    feature = _F.BACKLIGHT2


class Backlight3(_Setting):
    name = 'backlight-timed'
    description = _('Set illumination time for keyboard.')
    feature = _F.BACKLIGHT3
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20, 'suffix': 0x09}
    validator_class = _RangeV
    min_value = 0
    max_value = 1000
    validator_options = {'byte_count': 2}


class HiResScroll(_Setting):
    name = 'hi-res-scroll'
    label = _('Scroll Wheel High Resolution')
    description = (
        _('High-sensitivity mode for vertical scroll with the wheel.') + '\n' +
        _('Set to ignore if scrolling is abnormally fast or slow')
    )
    feature = _F.HI_RES_SCROLLING


class LowresSmoothScroll(_Setting):
    name = 'lowres-smooth-scroll'
    label = _('Scroll Wheel Diversion')
    description = (
        _('HID++ mode for vertical scroll with the wheel.') + '\n' + _('Effectively turns off wheel scrolling in Linux.')
    )
    feature = _F.LOWRES_WHEEL


class HiresSmoothInvert(_Setting):
    name = 'hires-smooth-invert'
    label = _('Scroll Wheel Direction')
    description = _('Invert direction for vertical scroll with wheel.')
    feature = _F.HIRES_WHEEL
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    validator_options = {'true_value': 0x04, 'mask': 0x04}


class HiresSmoothResolution(_Setting):
    name = 'hires-smooth-resolution'
    label = _('Scroll Wheel Resolution')
    description = (
        _('High-sensitivity mode for vertical scroll with the wheel.') + '\n' +
        _('Set to ignore if scrolling is abnormally fast or slow')
    )
    feature = _F.HIRES_WHEEL
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    validator_options = {'true_value': 0x02, 'mask': 0x02}


class PointerSpeed(_Setting):
    name = 'pointer_speed'
    label = _('Sensitivity (Pointer Speed)')
    description = _('Speed multiplier for mouse (256 is normal multiplier).')
    feature = _F.POINTER_SPEED
    validator_class = _RangeV
    min_value = 0x002e
    max_value = 0x01ff
    validator_options = {'byte_count': 2}


class ThumbMode(_Setting):
    name = 'thumb-scroll-mode'
    label = _('Thumb Wheel Diversion')
    description = _('HID++ mode for horizontal scroll with the thumb wheel.') + '\n' + \
        _('Effectively turns off thumb scrolling in Linux.')
    feature = _F.THUMB_WHEEL
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    validator_options = {'true_value': b'\x01\x00', 'false_value': b'\x00\x00', 'mask': b'\x01\x00'}


class ThumbInvert(_Setting):
    name = 'thumb-scroll-invert'
    label = _('Thumb Wheel Direction')
    description = _('Invert thumb wheel scroll direction.')
    feature = _F.THUMB_WHEEL
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    validator_options = {'true_value': b'\x00\x01', 'false_value': b'\x00\x00', 'mask': b'\x00\x01'}


class ReportRate(_Setting):
    name = 'report_rate'
    label = _('Polling Rate (ms)')
    description = (
        _('Frequency of device polling, in milliseconds') + '\n' +
        _('Set to ignore if unusual device behaviour is experienced')
    )
    feature = _F.REPORT_RATE
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    choices_universe = _NamedInts.range(1, 8)

    class rw_class(_FeatureRW):
        def write(self, device, data_bytes):
            # Host mode is required for report rate to be adjustable
            if _hidpp20.get_onboard_mode(device) != _hidpp20.ONBOARD_MODES.MODE_HOST:
                _hidpp20.set_onboard_mode(device, _hidpp20.ONBOARD_MODES.MODE_HOST)
            return super().write(device, data_bytes)

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            if device.wpid == '408E':
                return None  # host mode borks the function keys on the G915 TKL keyboard
            reply = device.feature_request(_F.REPORT_RATE, 0x00)
            assert reply, 'Oops, report rate choices cannot be retrieved!'
            rate_list = []
            rate_flags = _bytes2int(reply[0:1])
            for i in range(0, 8):
                if (rate_flags >> i) & 0x01:
                    rate_list.append(i + 1)
            return cls(choices=_NamedInts.list(rate_list), byte_count=1) if rate_list else None


class DivertCrown(_Setting):
    name = 'divert-crown'
    label = _('Divert crown events')
    description = _('Make crown send CROWN HID++ notifications (which trigger Solaar rules but are otherwise ignored).')
    feature = _F.CROWN
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    validator_options = {'true_value': 0x02, 'false_value': 0x01, 'mask': 0xff}


class CrownSmooth(_Setting):
    name = 'crown-smooth'
    label = _('Crown smooth scroll')
    description = _('Set crown smooth scroll')
    feature = _F.CROWN
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    validator_options = {'true_value': 0x01, 'false_value': 0x02, 'read_skip_byte_count': 1, 'write_prefix_bytes': b'\x00'}


class DivertGkeys(_Setting):
    name = 'divert-gkeys'
    label = _('Divert G Keys')
    description = (
        _('Make G keys send GKEY HID++ notifications (which trigger Solaar rules but are otherwise ignored).') + '\n' +
        _('May also make M keys and MR key send HID++ notifications')
    )
    feature = _F.GKEY
    validator_options = {'true_value': 0x01, 'false_value': 0x00, 'mask': 0xff}

    class rw_class(_FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x20)

        def read(self, device):  # no way to read, so just assume not diverted
            return b'\x00'


class SmartShift(_Setting):
    name = 'smart-shift'
    label = _('Scroll Wheel Rachet')
    description = _(
        'Automatically switch the mouse wheel between ratchet and freespin mode.\n'
        'The mouse wheel is always free at 0, and always ratcheted at 50'
    )
    feature = _F.SMART_SHIFT
    rw_options = {'read_fnid': 0x00, 'write_fnid': 0x10}

    class rw_class(_FeatureRW):
        MIN_VALUE = 0
        MAX_VALUE = 50

        def __init__(self, feature, read_fnid, write_fnid):
            super().__init__(feature, read_fnid, write_fnid)

        def read(self, device):
            value = super().read(device)
            if _bytes2int(value[0:1]) == 1:
                # Mode = Freespin, map to minimum
                return _int2bytes(self.MIN_VALUE, count=1)
            else:
                # Mode = smart shift, map to the value, capped at maximum
                threshold = min(_bytes2int(value[1:2]), self.MAX_VALUE)
                return _int2bytes(threshold, count=1)

        def write(self, device, data_bytes):
            threshold = _bytes2int(data_bytes)
            # Freespin at minimum
            mode = 1 if threshold == self.MIN_VALUE else 2
            # Ratchet at maximum
            if threshold == self.MAX_VALUE:
                threshold = 255
            data = _int2bytes(mode, count=1) + _int2bytes(threshold, count=1)
            return super().write(device, data)

    min_value = rw_class.MIN_VALUE
    max_value = rw_class.MAX_VALUE
    validator_class = _RangeV


class SmartShiftEnhanced(SmartShift):
    feature = _F.SMART_SHIFT_ENHANCED
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}


# the keys for the choice map are Logitech controls (from special_keys)
# each choice value is a NamedInt with the string from a task (to be shown to the user)
# and the integer being the control number for that task (to be written to the device)
# Solaar only remaps keys (controlled by key gmask and group), not other key reprogramming
class ReprogrammableKeys(_Settings):
    name = 'reprogrammable-keys'
    label = _('Key/Button Actions')
    description = (
        _('Change the action for the key or button.') + '\n' +
        _('Changing important actions (such as for the left mouse button) can result in an unusable system.')
    )
    feature = _F.REPROG_CONTROLS_V4
    keys_universe = _special_keys.CONTROL
    choices_universe = _special_keys.CONTROL

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device, key):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            return b'\x00\x00' + _int2bytes(int(key_struct.mapped_to), 2)

        def write(self, device, key, data_bytes):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            key_struct.remap(_special_keys.CONTROL[_bytes2int(data_bytes)])
            return True

    class validator_class(_ChoicesMapV):
        @classmethod
        def build(cls, setting_class, device):
            choices = {}
            for k in device.keys:
                tgts = k.remappable_to
                if len(tgts) > 1:
                    choices[k.key] = tgts
            return cls(choices, key_byte_count=2, byte_count=2, extra_default=0) if choices else None


class DivertKeys(_Settings):
    name = 'divert-keys'
    label = _('Key/Button Diversion')
    description = _('Make the key or button send HID++ notifications (which trigger Solaar rules but are otherwise ignored).')
    feature = _F.REPROG_CONTROLS_V4
    keys_universe = _special_keys.CONTROL
    choices_universe = _NamedInts(**{_('Regular'): 0, _('Diverted'): 1})

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device, key):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            return b'\x00\x00\x01' if 'diverted' in key_struct.mapping_flags else b'\x00\x00\x00'

        def write(self, device, key, data_bytes):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            key_struct.set_diverted(data_bytes == b'\x01')
            return True

    class validator_class(_ChoicesMapV):
        @classmethod
        def build(cls, setting_class, device):
            choices = {}
            for k in device.keys:
                if 'divertable' in k.flags and 'virtual' not in k.flags:
                    choices[k.key] = setting_class.choices_universe
            if not choices:
                return None
            return cls(choices, key_byte_count=2, byte_count=1, mask=0x01)


class AdjustableDpi(_Setting):
    """Pointer Speed feature"""
    # Assume sensorIdx 0 (there is only one sensor)
    # [2] getSensorDpi(sensorIdx) -> sensorIdx, dpiMSB, dpiLSB
    # [3] setSensorDpi(sensorIdx, dpi)
    name = 'dpi'
    label = _('Sensitivity (DPI)')
    description = _('Mouse movement sensitivity')
    feature = _F.ADJUSTABLE_DPI
    rw_options = {'read_fnid': 0x20, 'write_fnid': 0x30}
    choices_universe = _NamedInts.range(200, 4000, str, 50)

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            # [1] getSensorDpiList(sensorIdx)
            reply = device.feature_request(_F.ADJUSTABLE_DPI, 0x10)
            assert reply, 'Oops, DPI list cannot be retrieved!'
            dpi_list = []
            step = None
            for val in _unpack('!7H', reply[1:1 + 14]):
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
            return cls(choices=_NamedInts.list(dpi_list), byte_count=3) if dpi_list else None

        def validate_read(self, reply_bytes):  # special validator to use default DPI if needed
            reply_value = _bytes2int(reply_bytes[1:3])
            if reply_value == 0:  # use default value instead
                reply_value = _bytes2int(reply_bytes[3:5])
            valid_value = self.choices[reply_value]
            assert valid_value is not None, '%s: failed to validate read value %02X' % (self.__class__.__name__, reply_value)
            return valid_value


class SpeedChange(_Setting):
    """Implements the ability to switch Sensitivity by clicking on the DPI_Change button."""
    name = 'speed-change'
    label = _('Sensitivity Switching')
    description = _(
        'Switch the current sensitivity and the remembered sensitivity when the key or button is pressed.\n'
        'If there is no remembered sensitivity, just remember the current sensitivity'
    )
    choices_universe = _special_keys.CONTROL
    choices_extra = _NamedInt(0, _('Off'))
    feature = _F.POINTER_SPEED
    rw_options = {'name': 'speed change'}

    class rw_class(_ActionSettingRW):
        def press_action(self):  # switch sensitivity
            currentSpeed = self.device.persister.get('pointer_speed', None) if self.device.persister else None
            newSpeed = self.device.persister.get('_speed-change', None) if self.device.persister else None
            speed_setting = next(filter(lambda s: s.name == 'pointer_speed', self.device.settings), None)
            if newSpeed is not None:
                if speed_setting:
                    speed_setting.write(newSpeed)
                else:
                    _log.error('cannot save sensitivity setting on %s', self.device)
                from solaar.ui import status_changed as _status_changed
                _status_changed(self.device, refresh=True)  # update main window
            if self.device.persister:
                self.device.persister['_speed-change'] = currentSpeed

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            key_index = device.keys.index(_special_keys.CONTROL.DPI_Change)
            key = device.keys[key_index] if key_index is not None else None
            if key is not None and 'divertable' in key.flags:
                keys = [setting_class.choices_extra, key.key]
                return cls(choices=_NamedInts.list(keys), byte_count=2)


class DpiSliding(_Setting):
    """ Implements the ability to smoothly modify the DPI by sliding a mouse horizontally while holding the DPI button.
        Abides by the following FSM:
        When the button is pressed, go into `pressed` state and begin accumulating displacement.
        If the button is released in this state swap DPI slots.
        If the state is `pressed` and the mouse moves enough to switch DPI go into the `moved` state.
        When the button is released in this state the DPI is set according to the total displacement.
    """
    name = 'dpi-sliding'
    label = _('DPI Sliding Adjustment')
    description = _('Adjust the DPI by sliding the mouse horizontally while holding the button down.')
    choices_universe = _special_keys.CONTROL
    choices_extra = _NamedInt(0, _('Off'))
    feature = _F.REPROG_CONTROLS_V4
    rw_options = {'name': 'dpi sliding'}

    class rw_class(_ActionSettingRW):
        def activate_action(self):
            self.key.set_rawXY_reporting(True)
            self.dpiSetting = next(filter(lambda s: s.name == 'dpi', self.device.settings), None)
            self.dpiChoices = list(self.dpiSetting.choices)
            self.otherDpiIdx = self.device.persister.get('_dpi-sliding', -1) if self.device.persister else -1
            if not isinstance(self.otherDpiIdx, int) or self.otherDpiIdx < 0 or self.otherDpiIdx >= len(self.dpiChoices):
                self.otherDpiIdx = self.dpiChoices.index(self.dpiSetting.read())
            self.fsmState = 'idle'
            self.dx = 0.
            self.movingDpiIdx = None

        def deactivate_action(self):
            self.key.set_rawXY_reporting(False)

        def setNewDpi(self, newDpiIdx):
            newDpi = self.dpiChoices[newDpiIdx]
            self.dpiSetting.write(newDpi)
            from solaar.ui import status_changed as _status_changed
            _status_changed(self.device, refresh=True)  # update main window

        def displayNewDpi(self, newDpiIdx):
            from solaar.ui import notify as _notify
            # import here to avoid circular import when running `solaar show`,
            # which does not require this method

            if _notify.available:
                reason = 'DPI %d [min %d, max %d]' % (self.dpiChoices[newDpiIdx], self.dpiChoices[0], self.dpiChoices[-1])
                # if there is a progress percentage then the reason isn't shown
                # asPercentage = int(float(newDpiIdx) / float(len(self.dpiChoices) - 1) * 100.)
                # _notify.show(self.device, reason=reason, progress=asPercentage)
                _notify.show(self.device, reason=reason)

        def press_action(self):  # start tracking
            if self.fsmState == 'idle':
                self.fsmState = 'pressed'
                self.dx = 0.
                # While in 'moved' state, the index into 'dpiChoices' of the currently selected DPI setting
                self.movingDpiIdx = None

        def release_action(self):  # adjust DPI and stop tracking
            if self.fsmState == 'pressed':  # Swap with other DPI
                thisIdx = self.dpiChoices.index(self.dpiSetting.read())
                newDpiIdx, self.otherDpiIdx = self.otherDpiIdx, thisIdx
                if self.device.persister:
                    self.device.persister['_dpi-sliding'] = self.otherDpiIdx
                self.setNewDpi(newDpiIdx)
                self.displayNewDpi(newDpiIdx)
            elif self.fsmState == 'moved':  # Set DPI according to displacement
                self.setNewDpi(self.movingDpiIdx)
            self.fsmState = 'idle'

        def move_action(self, dx, dy):
            currDpi = self.dpiSetting.read()
            self.dx += float(dx) / float(currDpi) * 15.  # yields a more-or-less DPI-independent dx of about 5/cm
            if self.fsmState == 'pressed':
                if abs(self.dx) >= 1.:
                    self.fsmState = 'moved'
                    self.movingDpiIdx = self.dpiChoices.index(currDpi)
            elif self.fsmState == 'moved':
                currIdx = self.dpiChoices.index(self.dpiSetting.read())
                newMovingDpiIdx = min(max(currIdx + int(self.dx), 0), len(self.dpiChoices) - 1)
                if newMovingDpiIdx != self.movingDpiIdx:
                    self.movingDpiIdx = newMovingDpiIdx
                    self.displayNewDpi(newMovingDpiIdx)

    class validator_class(_ChoicesV):
        sliding_keys = [_special_keys.CONTROL.DPI_Switch]

        @classmethod
        def build(cls, setting_class, device):
            # need _F.REPROG_CONTROLS_V4 feature and a DPI Switch that can send raw XY
            # and _F.ADJUSTABLE_DPI so that the DPI can be adjusted
            if _F.ADJUSTABLE_DPI in device.features:
                keys = []
                for key in cls.sliding_keys:
                    key_index = device.keys.index(key)
                    dkey = device.keys[key_index] if key_index is not None else None
                    if dkey is not None and 'raw XY' in dkey.flags and 'divertable' in dkey.flags:
                        keys.append(dkey.key)
                if not keys:  # none of the keys designed for this, so look for any key with correct flags
                    for key in device.keys:
                        if 'raw XY' in key.flags and 'divertable' in key.flags and 'virtual' not in key.flags:
                            keys.append(key.key)
                if keys:
                    keys.insert(0, setting_class.choices_extra)
                    return cls(choices=_NamedInts.list(keys), byte_count=2)


class DisableKeyboardKeys(_BitFieldSetting):
    name = 'disable-keyboard-keys'
    label = _('Disable keys')
    description = _('Disable specific keyboard keys.')
    feature = _F.KEYBOARD_DISABLE_KEYS
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    _labels = {k: (None, _('Disables the %s key.') % k) for k in _DKEY}
    choices_universe = _DKEY

    class validator_class(_BitFieldV):
        @classmethod
        def build(cls, setting_class, device):
            mask = device.feature_request(_F.KEYBOARD_DISABLE_KEYS, 0x00)[0]
            options = [_DKEY[1 << i] for i in range(8) if mask & (1 << i)]
            return cls(options) if options else None


class MouseGesture(_Setting):
    """Implements the ability to send mouse gestures
    by sliding a mouse horizontally or vertically while holding the App Switch button."""
    name = 'mouse-gestures'
    label = _('Mouse Gestures')
    description = _('Send a gesture by sliding the mouse while holding the button down.')
    feature = _F.REPROG_CONTROLS_V4
    rw_options = {'name': 'mouse gesture'}
    choices_universe = _special_keys.CONTROL
    choices_extra = _NamedInt(0, _('Off'))

    class rw_class(_ActionSettingRW):
        def activate_action(self):
            self.key.set_rawXY_reporting(True)
            self.dpiSetting = next(filter(lambda s: s.name == 'dpi', self.device.settings), None)
            self.fsmState = 'idle'
            self.initialize_data()

        def deactivate_action(self):
            self.key.set_rawXY_reporting(False)

        def initialize_data(self):
            self.dx = 0.
            self.dy = 0.
            self.lastEv = None
            self.data = [0]

        def press_action(self):
            if self.fsmState == 'idle':
                self.fsmState = 'pressed'
                self.initialize_data()

        def release_action(self):
            if self.fsmState == 'pressed':
                # emit mouse gesture notification
                from .base import _HIDPP_Notification as _HIDPP_Notification
                from .common import pack as _pack
                from .diversion import process_notification as _process_notification
                self.push_mouse_event()
                if _log.isEnabledFor(_INFO):
                    _log.info('mouse gesture notification %s', self.data)
                payload = _pack('!' + (len(self.data) * 'h'), *self.data)
                notification = _HIDPP_Notification(0, 0, 0, 0, payload)
                _process_notification(self.device, self.device.status, notification, _hidpp20.FEATURE.MOUSE_GESTURE)
                self.fsmState = 'idle'

        def move_action(self, dx, dy):
            if self.fsmState == 'pressed':
                now = _time() * 1000  # _time_ns() / 1e6
                if self.lastEv is not None and now - self.lastEv > 50.:
                    self.push_mouse_event()
                dpi = self.dpiSetting.read() if self.dpiSetting else 1000
                dx = float(dx) / float(dpi) * 15.  # This multiplier yields a more-or-less DPI-independent dx of about 5/cm
                self.dx += dx
                dy = float(dy) / float(dpi) * 15.  # This multiplier yields a more-or-less DPI-independent dx of about 5/cm
                self.dy += dy
                self.lastEv = now

        def key_action(self, key):
            self.push_mouse_event()
            self.data.append(1)
            self.data.append(key)
            self.data[0] += 1
            self.lastEv = _time() * 1000  # _time_ns() / 1e6
            if _log.isEnabledFor(_DEBUG):
                _log.debug('mouse gesture key event %d %s', key, self.data)

        def push_mouse_event(self):
            x = int(self.dx)
            y = int(self.dy)
            if x == 0 and y == 0:
                return
            self.data.append(0)
            self.data.append(x)
            self.data.append(y)
            self.data[0] += 1
            self.dx = 0.
            self.dy = 0.
            if _log.isEnabledFor(_DEBUG):
                _log.debug('mouse gesture move event %d %d %s', x, y, self.data)

    class validator_class(_ChoicesV):
        MouseGestureKeys = [_special_keys.CONTROL.Mouse_Gesture_Button, _special_keys.CONTROL.MultiPlatform_Gesture_Button]

        @classmethod
        def build(cls, setting_class, device):
            if device.kind == _DK.mouse:
                keys = []
                for key in cls.MouseGestureKeys:
                    key_index = device.keys.index(key)
                    dkey = device.keys[key_index] if key_index is not None else None
                    if dkey is not None and 'raw XY' in dkey.flags and 'divertable' in dkey.flags:
                        keys.append(dkey.key)
                if not keys:  # none of the keys designed for this, so look for any key with correct flags
                    for key in device.keys:
                        if 'raw XY' in key.flags and 'divertable' in key.flags and 'virtual' not in key.flags:
                            keys.append(key.key)
                if keys:
                    keys.insert(0, setting_class.choices_extra)
                    return cls(choices=_NamedInts.list(keys), byte_count=2)


class Multiplatform(_Setting):
    name = 'multiplatform'
    label = _('Set OS')
    description = _('Change keys to match OS.')
    feature = _F.MULTIPLATFORM
    rw_options = {'read_fnid': 0x00, 'write_fnid': 0x30}
    choices_universe = _NamedInts(**{'OS ' + str(i + 1): i for i in range(8)})

    # multiplatform OS bits
    OSS = [('Linux', 0x0400), ('MacOS', 0x2000), ('Windows', 0x0100), ('iOS', 0x4000), ('Android', 0x1000), ('WebOS', 0x8000),
           ('Chrome', 0x0800), ('WinEmb', 0x0200), ('Tizen', 0x0001)]

    # the problem here is how to construct the right values for the rules Set GUI,
    # as, for example, the integer value for 'Windows' can be different on different devices

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            def _str_os_versions(low, high):
                def _str_os_version(version):
                    if version == 0:
                        return ''
                    elif version & 0xFF:
                        return str(version >> 8) + '.' + str(version & 0xFF)
                    else:
                        return str(version >> 8)

                return '' if low == 0 and high == 0 else ' ' + _str_os_version(low) + '-' + _str_os_version(high)

            infos = device.feature_request(_F.MULTIPLATFORM)
            assert infos, 'Oops, multiplatform count cannot be retrieved!'
            flags, _ignore, num_descriptors = _unpack('!BBB', infos[:3])
            if not (flags & 0x02):  # can't set platform so don't create setting
                return []
            descriptors = []
            for index in range(0, num_descriptors):
                descriptor = device.feature_request(_F.MULTIPLATFORM, 0x10, index)
                platform, _ignore, os_flags, low, high = _unpack('!BBHHH', descriptor[:8])
                descriptors.append((platform, os_flags, low, high))
            choices = _NamedInts()
            for os_name, os_bit in setting_class.OSS:
                for platform, os_flags, low, high in descriptors:
                    os = os_name + _str_os_versions(low, high)
                    if os_bit & os_flags and platform not in choices and os not in choices:
                        choices[platform] = os
            return cls(choices=choices, read_skip_byte_count=6, write_prefix_bytes=b'\xff') if choices else None


class DualPlatform(_Setting):
    name = 'multiplatform'
    label = _('Set OS')
    description = _('Change keys to match OS.')
    choices_universe = _NamedInts()
    choices_universe[0x00] = 'iOS, MacOS'
    choices_universe[0x01] = 'Android, Windows'
    feature = _F.DUALPLATFORM
    rw_options = {'read_fnid': 0x00, 'write_fnid': 0x20}
    validator_class = _ChoicesV
    validator_options = {'choices': choices_universe}


class ChangeHost(_Setting):
    name = 'change-host'
    label = _('Change Host')
    description = _('Switch connection to a different host')
    persist = False  # persisting this setting is harmful
    feature = _F.CHANGE_HOST
    rw_options = {'read_fnid': 0x00, 'write_fnid': 0x10, 'no_reply': True}
    choices_universe = _NamedInts(**{'Host ' + str(i + 1): i for i in range(3)})

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            infos = device.feature_request(_F.CHANGE_HOST)
            assert infos, 'Oops, host count cannot be retrieved!'
            numHosts, currentHost = _unpack('!BB', infos[:2])
            hostNames = _hidpp20.get_host_names(device)
            hostNames = hostNames if hostNames is not None else {}
            if currentHost not in hostNames or hostNames[currentHost][1] == '':
                import socket  # find name of current host and use it
                hostNames[currentHost] = (True, socket.gethostname().partition('.')[0])
            choices = _NamedInts()
            for host in range(0, numHosts):
                paired, hostName = hostNames.get(host, (True, ''))
                choices[host] = str(host + 1) + ':' + hostName if hostName else str(host + 1)
            return cls(choices=choices, read_skip_byte_count=1) if choices and len(choices) > 1 else None


_GESTURE2_GESTURES_LABELS = {
    _GG['Tap1Finger']: (_('Single tap'), _('Performs a left click.')),
    _GG['Tap2Finger']: (_('Single tap with two fingers'), _('Performs a right click.')),
    _GG['Tap3Finger']: (_('Single tap with three fingers'), None),
    _GG['Click1Finger']: (None, None),
    _GG['Click2Finger']: (None, None),
    _GG['Click3Finger']: (None, None),
    _GG['DoubleTap1Finger']: (_('Double tap'), _('Performs a double click.')),
    _GG['DoubleTap2Finger']: (_('Double tap with two fingers'), None),
    _GG['DoubleTap3Finger']: (_('Double tap with three fingers'), None),
    _GG['Track1Finger']: (None, None),
    _GG['TrackingAcceleration']: (None, None),
    _GG['TapDrag1Finger']: (_('Tap and drag'), _('Drags items by dragging the finger after double tapping.')),
    _GG['TapDrag2Finger']:
    (_('Tap and drag with two fingers'), _('Drags items by dragging the fingers after double tapping.')),
    _GG['Drag3Finger']: (_('Tap and drag with three fingers'), None),
    _GG['TapGestures']: (None, None),
    _GG['FnClickGestureSuppression']:
    (_('Suppress tap and edge gestures'), _('Disables tap and edge gestures (equivalent to pressing Fn+LeftClick).')),
    _GG['Scroll1Finger']: (_('Scroll with one finger'), _('Scrolls.')),
    _GG['Scroll2Finger']: (_('Scroll with two fingers'), _('Scrolls.')),
    _GG['Scroll2FingerHoriz']: (_('Scroll horizontally with two fingers'), _('Scrolls horizontally.')),
    _GG['Scroll2FingerVert']: (_('Scroll vertically with two fingers'), _('Scrolls vertically.')),
    _GG['Scroll2FingerStateless']: (_('Scroll with two fingers'), _('Scrolls.')),
    _GG['NaturalScrolling']: (_('Natural scrolling'), _('Inverts the scrolling direction.')),
    _GG['Thumbwheel']: (_('Thumbwheel'), _('Enables the thumbwheel.')),
    _GG['VScrollInertia']: (None, None),
    _GG['VScrollBallistics']: (None, None),
    _GG['Swipe2FingerHoriz']: (None, None),
    _GG['Swipe3FingerHoriz']: (None, None),
    _GG['Swipe4FingerHoriz']: (None, None),
    _GG['Swipe3FingerVert']: (None, None),
    _GG['Swipe4FingerVert']: (None, None),
    _GG['LeftEdgeSwipe1Finger']: (None, None),
    _GG['RightEdgeSwipe1Finger']: (None, None),
    _GG['BottomEdgeSwipe1Finger']: (None, None),
    _GG['TopEdgeSwipe1Finger']: (_('Swipe from the top edge'), None),
    _GG['LeftEdgeSwipe1Finger2']: (_('Swipe from the left edge'), None),
    _GG['RightEdgeSwipe1Finger2']: (_('Swipe from the right edge'), None),
    _GG['BottomEdgeSwipe1Finger2']: (_('Swipe from the bottom edge'), None),
    _GG['TopEdgeSwipe1Finger2']: (_('Swipe from the top edge'), None),
    _GG['LeftEdgeSwipe2Finger']: (_('Swipe two fingers from the left edge'), None),
    _GG['RightEdgeSwipe2Finger']: (_('Swipe two fingers from the right edge'), None),
    _GG['BottomEdgeSwipe2Finger']: (_('Swipe two fingers from the bottom edge'), None),
    _GG['TopEdgeSwipe2Finger']: (_('Swipe two fingers from the top edge'), None),
    _GG['Zoom2Finger']: (_('Zoom with two fingers.'), _('Pinch to zoom out; spread to zoom in.')),
    _GG['Zoom2FingerPinch']: (_('Pinch to zoom out.'), _('Pinch to zoom out.')),
    _GG['Zoom2FingerSpread']: (_('Spread to zoom in.'), _('Spread to zoom in.')),
    _GG['Zoom3Finger']: (_('Zoom with three fingers.'), None),
    _GG['Zoom2FingerStateless']: (_('Zoom with two fingers'), _('Pinch to zoom out; spread to zoom in.')),
    _GG['TwoFingersPresent']: (None, None),
    _GG['Rotate2Finger']: (None, None),
    _GG['Finger1']: (None, None),
    _GG['Finger2']: (None, None),
    _GG['Finger3']: (None, None),
    _GG['Finger4']: (None, None),
    _GG['Finger5']: (None, None),
    _GG['Finger6']: (None, None),
    _GG['Finger7']: (None, None),
    _GG['Finger8']: (None, None),
    _GG['Finger9']: (None, None),
    _GG['Finger10']: (None, None),
    _GG['DeviceSpecificRawData']: (None, None),
}

_GESTURE2_PARAMS_LABELS = {
    _GP['ExtraCapabilities']: (None, None),  # not supported
    _GP['PixelZone']: (_('Pixel zone'), None),  # TO DO: replace None with a short description
    _GP['RatioZone']: (_('Ratio zone'), None),  # TO DO: replace None with a short description
    _GP['ScaleFactor']: (_('Scale factor'), _('Sets the cursor speed.')),
}

_GESTURE2_PARAMS_LABELS_SUB = {
    'left': (_('Left'), _('Left-most coordinate.')),
    'bottom': (_('Bottom'), _('Bottom coordinate.')),
    'width': (_('Width'), _('Width.')),
    'height': (_('Height'), _('Height.')),
    'scale': (_('Scale'), _('Cursor speed.')),
}


class Gesture2Gestures(_BitFieldOMSetting):
    name = 'gesture2-gestures'
    label = _('Gestures')
    description = _('Tweak the mouse/touchpad behaviour.')
    feature = _F.GESTURE_2
    rw_options = {'read_fnid': 0x10, 'write_fnid': 0x20}
    choices_universe = _hidpp20.GESTURE
    _labels = _GESTURE2_GESTURES_LABELS

    class validator_class(_BitFieldOMV):
        @classmethod
        def build(cls, setting_class, device):
            options = [g for g in _hidpp20.get_gestures(device).gestures.values() if g.can_be_enabled or g.default_enabled]
            return cls(options) if options else None


class Gesture2Params(_LongSettings):
    name = 'gesture2-params'
    label = _('Gesture params')
    description = _('Change numerical parameters of a mouse/touchpad.')
    feature = _F.GESTURE_2
    rw_options = {'read_fnid': 0x70, 'write_fnid': 0x80}
    choices_universe = _hidpp20.PARAM
    sub_items_universe = _hidpp20.SUB_PARAM
    # item (NamedInt) -> list/tuple of objects that have the following attributes
    # .id (sub-item text), .length (in bytes), .minimum and .maximum

    _labels = _GESTURE2_PARAMS_LABELS
    _labels_sub = _GESTURE2_PARAMS_LABELS_SUB

    class validator_class(_MultipleRangeV):
        @classmethod
        def build(cls, setting_class, device):
            params = _hidpp20.get_gestures(device).params.values()
            items = [i for i in params if i.sub_params]
            if not items:
                return None
            sub_items = {i: i.sub_params for i in items}
            return cls(items, sub_items)


class MKeyLEDs(_BitFieldSetting):
    name = 'm-key-leds'
    label = _('M-Key LEDs')
    description = _('Control the M-Key LEDs.')
    feature = _F.MKEYS
    choices_universe = _NamedInts()
    for i in range(8):
        choices_universe[1 << i] = 'M' + str(i + 1)
    _labels = {k: (None, _('Lights up the %s key.') % k) for k in choices_universe}

    class rw_class(_FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x10)

        def read(self, device):  # no way to read, so just assume off
            return b'\x00'

    class validator_class(_BitFieldV):
        @classmethod
        def build(cls, setting_class, device):
            number = device.feature_request(setting_class.feature, 0x00)[0]
            options = [setting_class.choices_universe[1 << i] for i in range(number)]
            return cls(options) if options else None


class MRKeyLED(_Setting):
    name = 'mr-key-led'
    label = _('MR-Key LED')
    description = _('Control the MR-Key LED.')
    feature = _F.MR

    class rw_class(_FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x00)

        def read(self, device):  # no way to read, so just assume off
            return b'\x00'


## Only implemented for devices that can produce Key and Consumer Codes (e.g., Craft)
## and devices that can produce Key, Mouse, and Horizontal Scroll (e.g., M720)
## Only interested in current host, so use 0xFF for it
class PersistentRemappableAction(_Settings):
    name = 'persistent-remappable-keys'
    label = _('Persistent Key/Button Mapping')
    description = (
        _('Permanently change the mapping for the key or button.') + '\n' +
        _('Changing important keys or buttons (such as for the left mouse button) can result in an unusable system.')
    )
    persist = False  # This setting is persistent in the device so no need to persist it here
    feature = _F.PERSISTENT_REMAPPABLE_ACTION
    keys_universe = _special_keys.CONTROL
    choices_universe = _special_keys.KEYS

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device, key):
            ks = device.remap_keys[device.remap_keys.index(key)]
            return b'\x00\x00' + ks.data_bytes

        def write(self, device, key, data_bytes):
            ks = device.remap_keys[device.remap_keys.index(key)]
            v = ks.remap(data_bytes)
            return v

    class validator_class(_ChoicesMapV):
        @classmethod
        def build(cls, setting_class, device):
            remap_keys = device.remap_keys
            if not remap_keys:
                return None
            capabilities = device.remap_keys.capabilities
            if capabilities & 0x0041 == 0x0041:  # Key and Consumer Codes
                keys = _special_keys.KEYS_KEYS_CONSUMER
            elif capabilities & 0x0023 == 0x0023:  # Key, Mouse, and HScroll Codes
                keys = _special_keys.KEYS_KEYS_MOUSE_HSCROLL
            else:
                if _log.isEnabledFor(_WARN):
                    _log.warn('%s: unimplemented Persistent Remappable capability %s', device.name, hex(capabilities))
                return None
            choices = {}
            for k in remap_keys:
                key = _special_keys.CONTROL[k.key]
                choices[key] = keys  # TO RECOVER FROM BAD VALUES use _special_keys.KEYS
            return cls(choices, key_byte_count=2, byte_count=4) if choices else None


SETTINGS = [
    RegisterHandDetection,  # simple
    RegisterSmoothScroll,  # simple
    RegisterSideScroll,  # simple
    RegisterDpi,
    RegisterFnSwap,  # working
    HiResScroll,  # simple
    LowresSmoothScroll,  # simple
    HiresSmoothInvert,  # working
    HiresSmoothResolution,  # working
    SmartShift,  # working
    SmartShiftEnhanced,  # simple
    ThumbMode,  # working
    ThumbInvert,  # working
    ReportRate,  # working
    PointerSpeed,  # simple
    AdjustableDpi,  # working
    DpiSliding,  # working
    SpeedChange,
    MouseGesture,  # working
    Backlight,
    Backlight2,  # working
    Backlight3,
    FnSwap,  # simple
    NewFnSwap,  # simple
    K375sFnSwap,  # working
    ReprogrammableKeys,  # working
    PersistentRemappableAction,
    DivertKeys,  # working
    DisableKeyboardKeys,  # working
    DivertCrown,  # working
    CrownSmooth,  # working
    DivertGkeys,  # working
    MKeyLEDs,  # working
    MRKeyLED,  # working
    Multiplatform,  # working
    DualPlatform,  # simple
    ChangeHost,  # working
    Gesture2Gestures,  # working
    Gesture2Params,  # working
]

#
#
#


def check_feature(device, sclass):
    if sclass.feature not in device.features:
        return
    try:
        detected = sclass.build(device)
        if _log.isEnabledFor(_INFO):
            _log.info('check_feature %s [%s] detected %s', sclass.name, sclass.feature, detected)
        return detected
    except Exception:
        from traceback import format_exc
        _log.error('check_feature %s [%s] error %s', sclass.name, sclass.feature, format_exc())


# Returns True if device was queried to find features, False otherwise
def check_feature_settings(device, already_known):
    """Auto-detect device settings by the HID++ 2.0 features they have."""
    if device.features is None or not device.online:
        return False
    if device.protocol and device.protocol < 2.0:
        return False
    absent = device.persister.get('_absent', []) if device.persister else []
    newAbsent = []
    for sclass in SETTINGS:
        if sclass.feature:
            if sclass.name not in absent and not any(s.name == sclass.name for s in already_known):
                setting = check_feature(device, sclass)
                if setting:
                    already_known.append(setting)
                    if sclass.name in newAbsent:
                        newAbsent.remove(sclass.name)
                else:
                    if not any(s.name == sclass.name for s in already_known) and sclass.name not in newAbsent:
                        newAbsent.append(sclass.name)
    if device.persister and newAbsent:
        absent.extend(newAbsent)
        device.persister['_absent'] = absent
    return True


def check_feature_setting(device, setting_name):
    for setting in SETTINGS:
        if setting.name == setting_name:
            feature = check_feature(device, setting)
            if feature:
                return feature
