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

import logging
import socket as _socket

from logging import WARN as _WARN
from struct import pack as _pack
from struct import unpack as _unpack
from time import time as _time
from traceback import format_exc as _format_exc

from solaar.i18n import _

from . import descriptors as _descriptors
from . import hidpp10_constants as _hidpp10_constants
from . import hidpp20
from . import hidpp20_constants as _hidpp20_constants
from . import notify as _notify
from . import special_keys as _special_keys
from .base import _HIDPP_Notification as _HIDPP_Notification
from .common import NamedInt as _NamedInt
from .common import NamedInts as _NamedInts
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes
from .diversion import process_notification as _process_notification
from .settings import KIND as _KIND
from .settings import ActionSettingRW as _ActionSettingRW
from .settings import BitFieldSetting as _BitFieldSetting
from .settings import BitFieldValidator as _BitFieldV
from .settings import BitFieldWithOffsetAndMaskSetting as _BitFieldOMSetting
from .settings import BitFieldWithOffsetAndMaskValidator as _BitFieldOMV
from .settings import ChoicesMapValidator as _ChoicesMapV
from .settings import ChoicesValidator as _ChoicesV
from .settings import FeatureRW as _FeatureRW
from .settings import FeatureRWMap as _FeatureRWMap
from .settings import HeteroValidator as _HeteroV
from .settings import LongSettings as _LongSettings
from .settings import MultipleRangeValidator as _MultipleRangeV
from .settings import PackedRangeValidator as _PackedRangeV
from .settings import RangeFieldSetting as _RangeFieldSetting
from .settings import RangeValidator as _RangeV
from .settings import RawXYProcessing as _RawXYProcessing
from .settings import Setting as _Setting
from .settings import Settings as _Settings
from .special_keys import DISABLE as _DKEY

logger = logging.getLogger(__name__)

_hidpp20 = hidpp20.Hidpp20()
_DK = _hidpp10_constants.DEVICE_KIND
_R = _hidpp10_constants.REGISTERS
_F = _hidpp20_constants.FEATURE

_GG = _hidpp20_constants.GESTURE
_GP = _hidpp20_constants.PARAM

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
# The _RangeFieldSetting class is for settings that have multiple ranges packed into a byte string.
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


class FnSwapVirtual(_Setting):  # virtual setting to hold fn swap strings
    name = "fn-swap"
    label = _("Swap Fx function")
    description = (
        _(
            "When set, the F1..F12 keys will activate their special function,\n"
            "and you must hold the FN key to activate their standard function."
        )
        + "\n\n"
        + _(
            "When unset, the F1..F12 keys will activate their standard function,\n"
            "and you must hold the FN key to activate their special function."
        )
    )


class RegisterHandDetection(_Setting):
    name = "hand-detection"
    label = _("Hand Detection")
    description = _("Turn on illumination when the hands hover over the keyboard.")
    register = _R.keyboard_hand_detection
    validator_options = {"true_value": b"\x00\x00\x00", "false_value": b"\x00\x00\x30", "mask": b"\x00\x00\xFF"}


class RegisterSmoothScroll(_Setting):
    name = "smooth-scroll"
    label = _("Scroll Wheel Smooth Scrolling")
    description = _("High-sensitivity mode for vertical scroll with the wheel.")
    register = _R.mouse_button_flags
    validator_options = {"true_value": 0x40, "mask": 0x40}


class RegisterSideScroll(_Setting):
    name = "side-scroll"
    label = _("Side Scrolling")
    description = _(
        "When disabled, pushing the wheel sideways sends custom button events\n"
        "instead of the standard side-scrolling events."
    )
    register = _R.mouse_button_flags
    validator_options = {"true_value": 0x02, "mask": 0x02}


# different devices have different sets of permissible dpis, so this should be subclassed
class RegisterDpi(_Setting):
    name = "dpi-old"
    label = _("Sensitivity (DPI - older mice)")
    description = _("Mouse movement sensitivity")
    register = _R.mouse_dpi
    choices_universe = _NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))
    validator_class = _ChoicesV
    validator_options = {"choices": choices_universe}


class RegisterFnSwap(FnSwapVirtual):
    register = _R.keyboard_fn_swap
    validator_options = {"true_value": b"\x00\x01", "mask": b"\x00\x01"}


class _PerformanceMXDpi(RegisterDpi):
    choices_universe = _NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))
    validator_options = {"choices": choices_universe}


# set up register settings for devices - this is done here to break up an import loop
_descriptors.get_wpid("0060").settings = [RegisterFnSwap]
_descriptors.get_wpid("2008").settings = [RegisterFnSwap]
_descriptors.get_wpid("2010").settings = [RegisterFnSwap, RegisterHandDetection]
_descriptors.get_wpid("2011").settings = [RegisterFnSwap]
_descriptors.get_usbid(0xC318).settings = [RegisterFnSwap]
_descriptors.get_wpid("C714").settings = [RegisterFnSwap]
_descriptors.get_wpid("100B").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("100F").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("1013").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("1014").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("1017").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("1023").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("4004").settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("101A").settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("101B").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("101D").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("101F").settings = [RegisterSideScroll]
_descriptors.get_usbid(0xC06B).settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_wpid("1025").settings = [RegisterSideScroll]
_descriptors.get_wpid("102A").settings = [RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_usbid(0xC048).settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]
_descriptors.get_usbid(0xC066).settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]


# ignore the capabilities part of the feature - all devices should be able to swap Fn state
# just use the current host (first byte = 0xFF) part of the feature to read and set the Fn state
class K375sFnSwap(FnSwapVirtual):
    feature = _F.K375S_FN_INVERSION
    rw_options = {"prefix": b"\xFF"}
    validator_options = {"true_value": b"\x01", "false_value": b"\x00", "read_skip_byte_count": 1}


class FnSwap(FnSwapVirtual):
    feature = _F.FN_INVERSION


class NewFnSwap(FnSwapVirtual):
    feature = _F.NEW_FN_INVERSION


class Backlight(_Setting):
    name = "backlight-qualitative"
    label = _("Backlight")
    description = _("Set illumination time for keyboard.")
    feature = _F.BACKLIGHT
    choices_universe = _NamedInts(Off=0, Varying=2, VeryShort=5, Short=10, Medium=20, Long=60, VeryLong=180)
    validator_class = _ChoicesV
    validator_options = {"choices": choices_universe}


# MX Keys S requires some extra values, as in 11 02 0c1a 000dff000b000b003c00000000000000
# on/off options (from current) effect (FF-no change) level (from current) durations[6] (from current)
class Backlight2(_Setting):
    name = "backlight"
    label = _("Backlight")
    description = _("Illumination level on keyboard.  Changes made are only applied in Manual mode.")
    feature = _F.BACKLIGHT2
    min_version = 0

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device):
            backlight = device.backlight
            if not backlight.enabled:
                return b"\xFF"
            else:
                return _int2bytes(backlight.mode, 1)

        def write(self, device, data_bytes):
            backlight = device.backlight
            backlight.enabled = data_bytes[0] != 0xFF
            if data_bytes[0] != 0xFF:
                backlight.mode = data_bytes[0]
            backlight.write()
            return True

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            backlight = device.backlight
            choices = _NamedInts()
            choices[0xFF] = _("Disabled")
            if backlight.auto_supported:
                choices[0x1] = _("Automatic")
            if backlight.perm_supported:
                choices[0x3] = _("Manual")
            if not (backlight.auto_supported or backlight.temp_supported or backlight.perm_supported):
                choices[0x0] = _("Enabled")
            return cls(choices=choices, byte_count=1)


class Backlight2Level(_Setting):
    name = "backlight_level"
    label = _("Backlight Level")
    description = _("Illumination level on keyboard when in Manual mode.")
    feature = _F.BACKLIGHT2
    min_version = 3

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device):
            backlight = device.backlight
            return _int2bytes(backlight.level, 1)

        def write(self, device, data_bytes):
            if device.backlight.level != _bytes2int(data_bytes):
                device.backlight.level = _bytes2int(data_bytes)
                device.backlight.write()
            return True

    class validator_class(_RangeV):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(_F.BACKLIGHT2, 0x20)
            assert reply, "Oops, backlight range cannot be retrieved!"
            if reply[0] > 1:
                return cls(min_value=0, max_value=reply[0] - 1, byte_count=1)


class Backlight2Duration(_Setting):
    feature = _F.BACKLIGHT2
    min_version = 3
    validator_class = _RangeV
    min_value = 1
    max_value = 600  # 10 minutes - actual maximum is 2 hours
    validator_options = {"byte_count": 2}

    class rw_class:
        def __init__(self, feature, field):
            self.feature = feature
            self.kind = _FeatureRW.kind
            self.field = field

        def read(self, device):
            backlight = device.backlight
            return _int2bytes(getattr(backlight, self.field) * 5, 2)  # use seconds instead of 5-second units

        def write(self, device, data_bytes):
            backlight = device.backlight
            new_duration = (int.from_bytes(data_bytes, byteorder="big") + 4) // 5  # use ceiling in 5-second units
            if new_duration != getattr(backlight, self.field):
                setattr(backlight, self.field, new_duration)
                backlight.write()
            return True


class Backlight2DurationHandsOut(Backlight2Duration):
    name = "backlight_duration_hands_out"
    label = _("Backlight Delay Hands Out")
    description = _("Delay in seconds until backlight fades out with hands away from keyboard.")
    feature = _F.BACKLIGHT2
    validator_class = _RangeV
    rw_options = {"field": "dho"}


class Backlight2DurationHandsIn(Backlight2Duration):
    name = "backlight_duration_hands_in"
    label = _("Backlight Delay Hands In")
    description = _("Delay in seconds until backlight fades out with hands near keyboard.")
    feature = _F.BACKLIGHT2
    validator_class = _RangeV
    rw_options = {"field": "dhi"}


class Backlight2DurationPowered(Backlight2Duration):
    name = "backlight_duration_powered"
    label = _("Backlight Delay Powered")
    description = _("Delay in seconds until backlight fades out with external power.")
    feature = _F.BACKLIGHT2
    validator_class = _RangeV
    rw_options = {"field": "dpow"}


class Backlight3(_Setting):
    name = "backlight-timed"
    label = _("Backlight")
    description = _("Set illumination time for keyboard.")
    feature = _F.BACKLIGHT3
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20, "suffix": b"\x09"}
    validator_class = _RangeV
    min_value = 0
    max_value = 1000
    validator_options = {"byte_count": 2}


class HiResScroll(_Setting):
    name = "hi-res-scroll"
    label = _("Scroll Wheel High Resolution")
    description = (
        _("High-sensitivity mode for vertical scroll with the wheel.")
        + "\n"
        + _("Set to ignore if scrolling is abnormally fast or slow")
    )
    feature = _F.HI_RES_SCROLLING


class LowresMode(_Setting):
    name = "lowres-scroll-mode"
    label = _("Scroll Wheel Diversion")
    description = _(
        "Make scroll wheel send LOWRES_WHEEL HID++ notifications (which trigger Solaar rules but are otherwise ignored)."
    )
    feature = _F.LOWRES_WHEEL


class HiresSmoothInvert(_Setting):
    name = "hires-smooth-invert"
    label = _("Scroll Wheel Direction")
    description = _("Invert direction for vertical scroll with wheel.")
    feature = _F.HIRES_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x04, "mask": 0x04}


class HiresSmoothResolution(_Setting):
    name = "hires-smooth-resolution"
    label = _("Scroll Wheel Resolution")
    description = (
        _("High-sensitivity mode for vertical scroll with the wheel.")
        + "\n"
        + _("Set to ignore if scrolling is abnormally fast or slow")
    )
    feature = _F.HIRES_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x02, "mask": 0x02}


class HiresMode(_Setting):
    name = "hires-scroll-mode"
    label = _("Scroll Wheel Diversion")
    description = _(
        "Make scroll wheel send HIRES_WHEEL HID++ notifications (which trigger Solaar rules but are otherwise ignored)."
    )
    feature = _F.HIRES_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x01, "mask": 0x01}


class PointerSpeed(_Setting):
    name = "pointer_speed"
    label = _("Sensitivity (Pointer Speed)")
    description = _("Speed multiplier for mouse (256 is normal multiplier).")
    feature = _F.POINTER_SPEED
    validator_class = _RangeV
    min_value = 0x002E
    max_value = 0x01FF
    validator_options = {"byte_count": 2}


class ThumbMode(_Setting):
    name = "thumb-scroll-mode"
    label = _("Thumb Wheel Diversion")
    description = _(
        "Make thumb wheel send THUMB_WHEEL HID++ notifications (which trigger Solaar rules but are otherwise ignored)."
    )
    feature = _F.THUMB_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": b"\x01\x00", "false_value": b"\x00\x00", "mask": b"\x01\x00"}


class ThumbInvert(_Setting):
    name = "thumb-scroll-invert"
    label = _("Thumb Wheel Direction")
    description = _("Invert thumb wheel scroll direction.")
    feature = _F.THUMB_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": b"\x00\x01", "false_value": b"\x00\x00", "mask": b"\x00\x01"}


# change UI to show result of onboard profile change
def profile_change(device, profile_sector):
    if device.setting_callback:
        device.setting_callback(device, OnboardProfiles, [profile_sector])
        for profile in device.profiles.profiles.values() if device.profiles else []:
            if profile.sector == profile_sector:
                resolution_index = profile.resolution_default_index
                device.setting_callback(device, AdjustableDpi, [profile.resolutions[resolution_index]])
                device.setting_callback(device, ReportRate, [profile.report_rate])
                break


class OnboardProfiles(_Setting):
    name = "onboard_profiles"
    label = _("Onboard Profiles")
    description = _("Enable an onboard profile, which controls report rate, sensitivity, and button actions")
    feature = _F.ONBOARD_PROFILES
    choices_universe = _NamedInts(Disabled=0)
    for i in range(1, 16):
        choices_universe[i] = f"Profile {i}"
        choices_universe[i + 0x100] = f"Read-Only Profile {i}"
    validator_class = _ChoicesV

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device):
            enabled = device.feature_request(_F.ONBOARD_PROFILES, 0x20)[0]
            if enabled == 0x01:
                active = device.feature_request(_F.ONBOARD_PROFILES, 0x40)
                return active[:2]
            else:
                return b"\x00\x00"

        def write(self, device, data_bytes):
            if data_bytes == b"\x00\x00":
                result = device.feature_request(_F.ONBOARD_PROFILES, 0x10, b"\x02")
            else:
                device.feature_request(_F.ONBOARD_PROFILES, 0x10, b"\x01")
                result = device.feature_request(_F.ONBOARD_PROFILES, 0x30, data_bytes)
                profile_change(device, _bytes2int(data_bytes))
            return result

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            headers = hidpp20.OnboardProfiles.get_profile_headers(device)
            profiles_list = [setting_class.choices_universe[0]]
            if headers:
                for sector, enabled in headers:
                    if enabled and setting_class.choices_universe[sector]:
                        profiles_list.append(setting_class.choices_universe[sector])
            return cls(choices=_NamedInts.list(profiles_list), byte_count=2) if len(profiles_list) > 1 else None


class ReportRate(_Setting):
    name = "report_rate"
    label = _("Report Rate")
    description = (
        _("Frequency of device movement reports") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    )
    feature = _F.REPORT_RATE
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    choices_universe = _NamedInts()
    choices_universe[1] = "1ms"
    choices_universe[2] = "2ms"
    choices_universe[3] = "3ms"
    choices_universe[4] = "4ms"
    choices_universe[5] = "5ms"
    choices_universe[6] = "6ms"
    choices_universe[7] = "7ms"
    choices_universe[8] = "8ms"

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            # if device.wpid == '408E':
            #    return None  # host mode borks the function keys on the G915 TKL keyboard
            reply = device.feature_request(_F.REPORT_RATE, 0x00)
            assert reply, "Oops, report rate choices cannot be retrieved!"
            rate_list = []
            rate_flags = _bytes2int(reply[0:1])
            for i in range(0, 8):
                if (rate_flags >> i) & 0x01:
                    rate_list.append(setting_class.choices_universe[i + 1])
            return cls(choices=_NamedInts.list(rate_list), byte_count=1) if rate_list else None


class ExtendedReportRate(_Setting):
    name = "report_rate_extended"
    label = _("Report Rate")
    description = (
        _("Frequency of device movement reports") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    )
    feature = _F.EXTENDED_ADJUSTABLE_REPORT_RATE
    rw_options = {"read_fnid": 0x20, "write_fnid": 0x30}
    choices_universe = _NamedInts()
    choices_universe[0] = "8ms"
    choices_universe[1] = "4ms"
    choices_universe[2] = "2ms"
    choices_universe[3] = "1ms"
    choices_universe[4] = "500us"
    choices_universe[5] = "250us"
    choices_universe[6] = "125us"

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(_F.EXTENDED_ADJUSTABLE_REPORT_RATE, 0x10)
            assert reply, "Oops, report rate choices cannot be retrieved!"
            rate_list = []
            rate_flags = _bytes2int(reply[0:2])
            for i in range(0, 6):
                if rate_flags & (0x01 << i):
                    rate_list.append(setting_class.choices_universe[i])
            return cls(choices=_NamedInts.list(rate_list), byte_count=1) if rate_list else None


class DivertCrown(_Setting):
    name = "divert-crown"
    label = _("Divert crown events")
    description = _("Make crown send CROWN HID++ notifications (which trigger Solaar rules but are otherwise ignored).")
    feature = _F.CROWN
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x02, "false_value": 0x01, "mask": 0xFF}


class CrownSmooth(_Setting):
    name = "crown-smooth"
    label = _("Crown smooth scroll")
    description = _("Set crown smooth scroll")
    feature = _F.CROWN
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x01, "false_value": 0x02, "read_skip_byte_count": 1, "write_prefix_bytes": b"\x00"}


class DivertGkeys(_Setting):
    name = "divert-gkeys"
    label = _("Divert G and M Keys")
    description = _("Make G and M keys send HID++ notifications (which trigger Solaar rules but are otherwise ignored).")
    feature = _F.GKEY
    validator_options = {"true_value": 0x01, "false_value": 0x00, "mask": 0xFF}

    class rw_class(_FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x20)

        def read(self, device):  # no way to read, so just assume not diverted
            return b"\x00"


class ScrollRatchet(_Setting):
    name = "scroll-ratchet"
    label = _("Scroll Wheel Ratcheted")
    description = _("Switch the mouse wheel between speed-controlled ratcheting and always freespin.")
    feature = _F.SMART_SHIFT
    choices_universe = _NamedInts(**{_("Freespinning"): 1, _("Ratcheted"): 2})
    validator_class = _ChoicesV
    validator_options = {"choices": choices_universe}


class SmartShift(_Setting):
    name = "smart-shift"
    label = _("Scroll Wheel Ratchet Speed")
    description = _(
        "Use the mouse wheel speed to switch between ratcheted and freespinning.\n"
        "The mouse wheel is always ratcheted at 50."
    )
    feature = _F.SMART_SHIFT
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x10}

    class rw_class(_FeatureRW):
        MIN_VALUE = 1
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
            mode = 0  # 1 if threshold <= self.MIN_VALUE else 2
            # Ratchet at maximum
            if threshold >= self.MAX_VALUE:
                threshold = 255
            data = _int2bytes(mode, count=1) + _int2bytes(max(0, threshold), count=1)
            return super().write(device, data)

    min_value = rw_class.MIN_VALUE
    max_value = rw_class.MAX_VALUE
    validator_class = _RangeV


class SmartShiftEnhanced(SmartShift):
    feature = _F.SMART_SHIFT_ENHANCED
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}


# the keys for the choice map are Logitech controls (from special_keys)
# each choice value is a NamedInt with the string from a task (to be shown to the user)
# and the integer being the control number for that task (to be written to the device)
# Solaar only remaps keys (controlled by key gmask and group), not other key reprogramming
class ReprogrammableKeys(_Settings):
    name = "reprogrammable-keys"
    label = _("Key/Button Actions")
    description = (
        _("Change the action for the key or button.")
        + "  "
        + _("Overridden by diversion.")
        + "\n"
        + _("Changing important actions (such as for the left mouse button) can result in an unusable system.")
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
            return b"\x00\x00" + _int2bytes(int(key_struct.mapped_to), 2)

        def write(self, device, key, data_bytes):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            key_struct.remap(_special_keys.CONTROL[_bytes2int(data_bytes)])
            return True

    class validator_class(_ChoicesMapV):
        @classmethod
        def build(cls, setting_class, device):
            choices = {}
            if device.keys:
                for k in device.keys:
                    tgts = k.remappable_to
                    if len(tgts) > 1:
                        choices[k.key] = tgts
            return cls(choices, key_byte_count=2, byte_count=2, extra_default=0) if choices else None


class DpiSlidingXY(_RawXYProcessing):
    def activate_action(self):
        self.dpiSetting = next(filter(lambda s: s.name == "dpi" or s.name == "dpi_extended", self.device.settings), None)
        self.dpiChoices = list(self.dpiSetting.choices)
        self.otherDpiIdx = self.device.persister.get("_dpi-sliding", -1) if self.device.persister else -1
        if not isinstance(self.otherDpiIdx, int) or self.otherDpiIdx < 0 or self.otherDpiIdx >= len(self.dpiChoices):
            self.otherDpiIdx = self.dpiChoices.index(self.dpiSetting.read())
        self.fsmState = "idle"
        self.dx = 0.0
        self.movingDpiIdx = None

    def setNewDpi(self, newDpiIdx):
        newDpi = self.dpiChoices[newDpiIdx]
        self.dpiSetting.write(newDpi)
        if self.device.setting_callback:
            self.device.setting_callback(self.device, type(self.dpiSetting), [newDpi])

    def displayNewDpi(self, newDpiIdx):
        if _notify.available:
            selected_dpi = self.dpiChoices[newDpiIdx]
            min_dpi = self.dpiChoices[0]
            max_dpi = self.dpiChoices[-1]
            reason = f"DPI {selected_dpi} [min {min_dpi}, max {max_dpi}]"
            _notify.show(self.device, reason)

    def press_action(self, key):  # start tracking
        self.starting = True
        if self.fsmState == "idle":
            self.fsmState = "pressed"
            self.dx = 0.0
            # While in 'moved' state, the index into 'dpiChoices' of the currently selected DPI setting
            self.movingDpiIdx = None

    def release_action(self):  # adjust DPI and stop tracking
        if self.fsmState == "pressed":  # Swap with other DPI
            thisIdx = self.dpiChoices.index(self.dpiSetting.read())
            newDpiIdx, self.otherDpiIdx = self.otherDpiIdx, thisIdx
            if self.device.persister:
                self.device.persister["_dpi-sliding"] = self.otherDpiIdx
            self.setNewDpi(newDpiIdx)
            self.displayNewDpi(newDpiIdx)
        elif self.fsmState == "moved":  # Set DPI according to displacement
            self.setNewDpi(self.movingDpiIdx)
        self.fsmState = "idle"

    def move_action(self, dx, dy):
        if self.device.features.get_feature_version(_F.REPROG_CONTROLS_V4) >= 5 and self.starting:
            self.starting = False  # hack to ignore strange first movement report from MX Master 3S
            return
        currDpi = self.dpiSetting.read()
        self.dx += float(dx) / float(currDpi) * 15.0  # yields a more-or-less DPI-independent dx of about 5/cm
        if self.fsmState == "pressed":
            if abs(self.dx) >= 1.0:
                self.fsmState = "moved"
                self.movingDpiIdx = self.dpiChoices.index(currDpi)
        elif self.fsmState == "moved":
            currIdx = self.dpiChoices.index(self.dpiSetting.read())
            newMovingDpiIdx = min(max(currIdx + int(self.dx), 0), len(self.dpiChoices) - 1)
            if newMovingDpiIdx != self.movingDpiIdx:
                self.movingDpiIdx = newMovingDpiIdx
                self.displayNewDpi(newMovingDpiIdx)


class MouseGesturesXY(_RawXYProcessing):
    def activate_action(self):
        self.dpiSetting = next(filter(lambda s: s.name == "dpi" or s.name == "dpi_extended", self.device.settings), None)
        self.fsmState = "idle"
        self.initialize_data()

    def initialize_data(self):
        self.dx = 0.0
        self.dy = 0.0
        self.lastEv = None
        self.data = []

    def press_action(self, key):
        self.starting = True
        if self.fsmState == "idle":
            self.fsmState = "pressed"
            self.initialize_data()
            self.data = [key.key]

    def release_action(self):
        if self.fsmState == "pressed":
            # emit mouse gesture notification
            self.push_mouse_event()
            if logger.isEnabledFor(logging.INFO):
                logger.info("mouse gesture notification %s", self.data)
            payload = _pack("!" + (len(self.data) * "h"), *self.data)
            notification = _HIDPP_Notification(0, 0, 0, 0, payload)
            _process_notification(self.device, notification, _F.MOUSE_GESTURE)
            self.fsmState = "idle"

    def move_action(self, dx, dy):
        if self.fsmState == "pressed":
            now = _time() * 1000  # _time_ns() / 1e6
            if self.device.features.get_feature_version(_F.REPROG_CONTROLS_V4) >= 5 and self.starting:
                self.starting = False  # hack to ignore strange first movement report from MX Master 3S
                return
            if self.lastEv is not None and now - self.lastEv > 200.0:
                self.push_mouse_event()
            dpi = self.dpiSetting.read() if self.dpiSetting else 1000
            dx = float(dx) / float(dpi) * 15.0  # This multiplier yields a more-or-less DPI-independent dx of about 5/cm
            self.dx += dx
            dy = float(dy) / float(dpi) * 15.0  # This multiplier yields a more-or-less DPI-independent dx of about 5/cm
            self.dy += dy
            self.lastEv = now

    def key_action(self, key):
        self.push_mouse_event()
        self.data.append(1)
        self.data.append(key)
        self.lastEv = _time() * 1000  # _time_ns() / 1e6
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("mouse gesture key event %d %s", key, self.data)

    def push_mouse_event(self):
        x = int(self.dx)
        y = int(self.dy)
        if x == 0 and y == 0:
            return
        self.data.append(0)
        self.data.append(x)
        self.data.append(y)
        self.dx = 0.0
        self.dy = 0.0
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("mouse gesture move event %d %d %s", x, y, self.data)


class DivertKeys(_Settings):
    name = "divert-keys"
    label = _("Key/Button Diversion")
    description = _("Make the key or button send HID++ notifications (Diverted) or initiate Mouse Gestures or Sliding DPI")
    feature = _F.REPROG_CONTROLS_V4
    keys_universe = _special_keys.CONTROL
    choices_universe = _NamedInts(**{_("Regular"): 0, _("Diverted"): 1, _("Mouse Gestures"): 2, _("Sliding DPI"): 3})
    choices_gesture = _NamedInts(**{_("Regular"): 0, _("Diverted"): 1, _("Mouse Gestures"): 2})
    choices_divert = _NamedInts(**{_("Regular"): 0, _("Diverted"): 1})

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = _FeatureRW.kind

        def read(self, device, key):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            return b"\x00\x00\x01" if "diverted" in key_struct.mapping_flags else b"\x00\x00\x00"

        def write(self, device, key, data_bytes):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            key_struct.set_diverted(_bytes2int(data_bytes) != 0)  # not regular
            return True

    class validator_class(_ChoicesMapV):
        def __init__(self, choices, key_byte_count=2, byte_count=1, mask=0x01):
            super().__init__(choices, key_byte_count, byte_count, mask)

        def prepare_write(self, key, new_value):
            if self.gestures and new_value != 2:  # mouse gestures
                self.gestures.stop(key)
            if self.sliding and new_value != 3:  # sliding DPI
                self.sliding.stop(key)
            if self.gestures and new_value == 2:  # mouse gestures
                self.gestures.start(key)
            if self.sliding and new_value == 3:  # sliding DPI
                self.sliding.start(key)
            return super().prepare_write(key, new_value)

        @classmethod
        def build(cls, setting_class, device):
            sliding = gestures = None
            choices = {}
            if device.keys:
                for k in device.keys:
                    if "divertable" in k.flags and "virtual" not in k.flags:
                        if "raw XY" in k.flags:
                            choices[k.key] = setting_class.choices_gesture
                            if gestures is None:
                                gestures = MouseGesturesXY(device, name="MouseGestures")
                            if _F.ADJUSTABLE_DPI in device.features:
                                choices[k.key] = setting_class.choices_universe
                                if sliding is None:
                                    sliding = DpiSlidingXY(device, name="DpiSlding")
                        else:
                            choices[k.key] = setting_class.choices_divert
            if not choices:
                return None
            validator = cls(choices, key_byte_count=2, byte_count=1, mask=0x01)
            validator.sliding = sliding
            validator.gestures = gestures
            return validator


def produce_dpi_list(feature, function, ignore, device, direction):
    dpi_bytes = b""
    for i in range(0, 0x100):  # there will be only a very few iterations performed
        reply = device.feature_request(feature, function, 0x00, direction, i)
        assert reply, "Oops, DPI list cannot be retrieved!"
        dpi_bytes += reply[ignore:]
        if dpi_bytes[-2:] == b"\x00\x00":
            break
    dpi_list = []
    i = 0
    while i < len(dpi_bytes):
        val = _bytes2int(dpi_bytes[i : i + 2])
        if val == 0:
            break
        if val >> 13 == 0b111:
            step = val & 0x1FFF
            last = _bytes2int(dpi_bytes[i + 2 : i + 4])
            assert len(dpi_list) > 0 and last > dpi_list[-1], f"Invalid DPI list item: {val!r}"
            dpi_list += range(dpi_list[-1] + step, last + 1, step)
            i += 4
        else:
            dpi_list.append(val)
            i += 2
    return dpi_list


class AdjustableDpi(_Setting):
    name = "dpi"
    label = _("Sensitivity (DPI)")
    description = _("Mouse movement sensitivity")
    feature = _F.ADJUSTABLE_DPI
    rw_options = {"read_fnid": 0x20, "write_fnid": 0x30}
    choices_universe = _NamedInts.range(100, 4000, str, 50)

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            dpilist = produce_dpi_list(setting_class.feature, 0x10, 1, device, 0)
            setting = cls(choices=_NamedInts.list(dpilist), byte_count=2, write_prefix_bytes=b"\x00") if dpilist else None
            setting.dpilist = dpilist
            return setting

        def validate_read(self, reply_bytes):  # special validator to use default DPI if needed
            reply_value = _bytes2int(reply_bytes[1:3])
            if reply_value == 0:  # use default value instead
                reply_value = _bytes2int(reply_bytes[3:5])
            valid_value = self.choices[reply_value]
            assert valid_value is not None, f"{self.__class__.__name__}: failed to validate read value {reply_value:02X}"
            return valid_value


class ExtendedAdjustableDpi(_Setting):
    # the extended version allows for two dimensions, longer dpi descriptions, but still assume only one sensor
    name = "dpi_extended"
    label = _("Sensitivity (DPI)")
    description = _("Mouse movement sensitivity") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    feature = _F.EXTENDED_ADJUSTABLE_DPI
    rw_options = {"read_fnid": 0x50, "write_fnid": 0x60}
    keys_universe = _NamedInts(X=0, Y=1, LOD=2)
    choices_universe = _NamedInts.range(100, 4000, str, 50)
    choices_universe[0] = "LOW"
    choices_universe[1] = "MEDIUM"
    choices_universe[2] = "HIGH"
    keys = _NamedInts(X=0, Y=1, LOD=2)

    def write_key_value(self, key, value, save=True):
        if isinstance(self._value, dict):
            self._value[key] = value
        else:
            self._value = {key: value}
        result = self.write(self._value, save)
        return result[key] if isinstance(result, dict) else result

    class validator_class(_ChoicesMapV):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(setting_class.feature, 0x10, 0x00)
            y = bool(reply[2] & 0x01)
            lod = bool(reply[2] & 0x02)
            choices_map = {}
            dpilist_x = produce_dpi_list(setting_class.feature, 0x20, 3, device, 0)
            choices_map[setting_class.keys["X"]] = _NamedInts.list(dpilist_x)
            if y:
                dpilist_y = produce_dpi_list(setting_class.feature, 0x20, 3, device, 1)
                choices_map[setting_class.keys["Y"]] = _NamedInts.list(dpilist_y)
            if lod:
                choices_map[setting_class.keys["LOD"]] = _NamedInts(LOW=0, MEDIUM=1, HIGH=2)
            validator = cls(choices_map=choices_map, byte_count=2, write_prefix_bytes=b"\x00")
            validator.y = y
            validator.lod = lod
            validator.keys = setting_class.keys
            return validator

        def validate_read(self, reply_bytes):  # special validator to read entire setting
            dpi_x = _bytes2int(reply_bytes[3:5]) if reply_bytes[1:3] == 0 else _bytes2int(reply_bytes[1:3])
            assert dpi_x in self.choices[0], f"{self.__class__.__name__}: failed to validate dpi_x value {dpi_x:04X}"
            value = {self.keys["X"]: dpi_x}
            if self.y:
                dpi_y = _bytes2int(reply_bytes[7:9]) if reply_bytes[5:7] == 0 else _bytes2int(reply_bytes[5:7])
                assert dpi_y in self.choices[1], f"{self.__class__.__name__}: failed to validate dpi_y value {dpi_y:04X}"
                value[self.keys["Y"]] = dpi_y
            if self.lod:
                lod = reply_bytes[9]
                assert lod in self.choices[2], f"{self.__class__.__name__}: failed to validate lod value {lod:02X}"
                value[self.keys["LOD"]] = lod
            return value

        def prepare_write(self, new_value, current_value=None):  # special preparer to write entire setting
            data_bytes = self._write_prefix_bytes
            if new_value[self.keys["X"]] not in self.choices[self.keys["X"]]:
                raise ValueError(f"invalid value {new_value!r}")
            data_bytes += _int2bytes(new_value[0], 2)
            if self.y:
                if new_value[self.keys["Y"]] not in self.choices[self.keys["Y"]]:
                    raise ValueError(f"invalid value {new_value!r}")
                data_bytes += _int2bytes(new_value[self.keys["Y"]], 2)
            else:
                data_bytes += b"\x00\x00"
            if self.lod:
                if new_value[self.keys["LOD"]] not in self.choices[self.keys["LOD"]]:
                    raise ValueError(f"invalid value {new_value!r}")
                data_bytes += _int2bytes(new_value[self.keys["LOD"]], 1)
            else:
                data_bytes += b"\x00"
            return data_bytes


class SpeedChange(_Setting):
    """Implements the ability to switch Sensitivity by clicking on the DPI_Change button."""

    name = "speed-change"
    label = _("Sensitivity Switching")
    description = _(
        "Switch the current sensitivity and the remembered sensitivity when the key or button is pressed.\n"
        "If there is no remembered sensitivity, just remember the current sensitivity"
    )
    choices_universe = _special_keys.CONTROL
    choices_extra = _NamedInt(0, _("Off"))
    feature = _F.POINTER_SPEED
    rw_options = {"name": "speed change"}

    class rw_class(_ActionSettingRW):
        def press_action(self):  # switch sensitivity
            currentSpeed = self.device.persister.get("pointer_speed", None) if self.device.persister else None
            newSpeed = self.device.persister.get("_speed-change", None) if self.device.persister else None
            speed_setting = next(filter(lambda s: s.name == "pointer_speed", self.device.settings), None)
            if newSpeed is not None:
                if speed_setting:
                    speed_setting.write(newSpeed)
                    if self.device.setting_callback:
                        self.device.setting_callback(self.device, type(speed_setting), [newSpeed])
                else:
                    logger.error("cannot save sensitivity setting on %s", self.device)
            if self.device.persister:
                self.device.persister["_speed-change"] = currentSpeed

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            key_index = device.keys.index(_special_keys.CONTROL.DPI_Change)
            key = device.keys[key_index] if key_index is not None else None
            if key is not None and "divertable" in key.flags:
                keys = [setting_class.choices_extra, key.key]
                return cls(choices=_NamedInts.list(keys), byte_count=2)


class DisableKeyboardKeys(_BitFieldSetting):
    name = "disable-keyboard-keys"
    label = _("Disable keys")
    description = _("Disable specific keyboard keys.")
    feature = _F.KEYBOARD_DISABLE_KEYS
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    _labels = {k: (None, _("Disables the %s key.") % k) for k in _DKEY}
    choices_universe = _DKEY

    class validator_class(_BitFieldV):
        @classmethod
        def build(cls, setting_class, device):
            mask = device.feature_request(_F.KEYBOARD_DISABLE_KEYS, 0x00)[0]
            options = [_DKEY[1 << i] for i in range(8) if mask & (1 << i)]
            return cls(options) if options else None


class Multiplatform(_Setting):
    name = "multiplatform"
    label = _("Set OS")
    description = _("Change keys to match OS.")
    feature = _F.MULTIPLATFORM
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x30}
    choices_universe = _NamedInts(**{"OS " + str(i + 1): i for i in range(8)})

    # multiplatform OS bits
    OSS = [
        ("Linux", 0x0400),
        ("MacOS", 0x2000),
        ("Windows", 0x0100),
        ("iOS", 0x4000),
        ("Android", 0x1000),
        ("WebOS", 0x8000),
        ("Chrome", 0x0800),
        ("WinEmb", 0x0200),
        ("Tizen", 0x0001),
    ]

    # the problem here is how to construct the right values for the rules Set GUI,
    # as, for example, the integer value for 'Windows' can be different on different devices

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            def _str_os_versions(low, high):
                def _str_os_version(version):
                    if version == 0:
                        return ""
                    elif version & 0xFF:
                        return str(version >> 8) + "." + str(version & 0xFF)
                    else:
                        return str(version >> 8)

                return "" if low == 0 and high == 0 else " " + _str_os_version(low) + "-" + _str_os_version(high)

            infos = device.feature_request(_F.MULTIPLATFORM)
            assert infos, "Oops, multiplatform count cannot be retrieved!"
            flags, _ignore, num_descriptors = _unpack("!BBB", infos[:3])
            if not (flags & 0x02):  # can't set platform so don't create setting
                return []
            descriptors = []
            for index in range(0, num_descriptors):
                descriptor = device.feature_request(_F.MULTIPLATFORM, 0x10, index)
                platform, _ignore, os_flags, low, high = _unpack("!BBHHH", descriptor[:8])
                descriptors.append((platform, os_flags, low, high))
            choices = _NamedInts()
            for os_name, os_bit in setting_class.OSS:
                for platform, os_flags, low, high in descriptors:
                    os = os_name + _str_os_versions(low, high)
                    if os_bit & os_flags and platform not in choices and os not in choices:
                        choices[platform] = os
            return cls(choices=choices, read_skip_byte_count=6, write_prefix_bytes=b"\xff") if choices else None


class DualPlatform(_Setting):
    name = "multiplatform"
    label = _("Set OS")
    description = _("Change keys to match OS.")
    choices_universe = _NamedInts()
    choices_universe[0x00] = "iOS, MacOS"
    choices_universe[0x01] = "Android, Windows"
    feature = _F.DUALPLATFORM
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x20}
    validator_class = _ChoicesV
    validator_options = {"choices": choices_universe}


class ChangeHost(_Setting):
    name = "change-host"
    label = _("Change Host")
    description = _("Switch connection to a different host")
    persist = False  # persisting this setting is harmful
    feature = _F.CHANGE_HOST
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x10, "no_reply": True}
    choices_universe = _NamedInts(**{"Host " + str(i + 1): i for i in range(3)})

    class validator_class(_ChoicesV):
        @classmethod
        def build(cls, setting_class, device):
            infos = device.feature_request(_F.CHANGE_HOST)
            assert infos, "Oops, host count cannot be retrieved!"
            numHosts, currentHost = _unpack("!BB", infos[:2])
            hostNames = _hidpp20.get_host_names(device)
            hostNames = hostNames if hostNames is not None else {}
            if currentHost not in hostNames or hostNames[currentHost][1] == "":
                hostNames[currentHost] = (True, _socket.gethostname().partition(".")[0])
            choices = _NamedInts()
            for host in range(0, numHosts):
                paired, hostName = hostNames.get(host, (True, ""))
                choices[host] = str(host + 1) + ":" + hostName if hostName else str(host + 1)
            return cls(choices=choices, read_skip_byte_count=1) if choices and len(choices) > 1 else None


_GESTURE2_GESTURES_LABELS = {
    _GG["Tap1Finger"]: (_("Single tap"), _("Performs a left click.")),
    _GG["Tap2Finger"]: (_("Single tap with two fingers"), _("Performs a right click.")),
    _GG["Tap3Finger"]: (_("Single tap with three fingers"), None),
    _GG["Click1Finger"]: (None, None),
    _GG["Click2Finger"]: (None, None),
    _GG["Click3Finger"]: (None, None),
    _GG["DoubleTap1Finger"]: (_("Double tap"), _("Performs a double click.")),
    _GG["DoubleTap2Finger"]: (_("Double tap with two fingers"), None),
    _GG["DoubleTap3Finger"]: (_("Double tap with three fingers"), None),
    _GG["Track1Finger"]: (None, None),
    _GG["TrackingAcceleration"]: (None, None),
    _GG["TapDrag1Finger"]: (_("Tap and drag"), _("Drags items by dragging the finger after double tapping.")),
    _GG["TapDrag2Finger"]: (
        _("Tap and drag with two fingers"),
        _("Drags items by dragging the fingers after double tapping."),
    ),
    _GG["Drag3Finger"]: (_("Tap and drag with three fingers"), None),
    _GG["TapGestures"]: (None, None),
    _GG["FnClickGestureSuppression"]: (
        _("Suppress tap and edge gestures"),
        _("Disables tap and edge gestures (equivalent to pressing Fn+LeftClick)."),
    ),
    _GG["Scroll1Finger"]: (_("Scroll with one finger"), _("Scrolls.")),
    _GG["Scroll2Finger"]: (_("Scroll with two fingers"), _("Scrolls.")),
    _GG["Scroll2FingerHoriz"]: (_("Scroll horizontally with two fingers"), _("Scrolls horizontally.")),
    _GG["Scroll2FingerVert"]: (_("Scroll vertically with two fingers"), _("Scrolls vertically.")),
    _GG["Scroll2FingerStateless"]: (_("Scroll with two fingers"), _("Scrolls.")),
    _GG["NaturalScrolling"]: (_("Natural scrolling"), _("Inverts the scrolling direction.")),
    _GG["Thumbwheel"]: (_("Thumbwheel"), _("Enables the thumbwheel.")),
    _GG["VScrollInertia"]: (None, None),
    _GG["VScrollBallistics"]: (None, None),
    _GG["Swipe2FingerHoriz"]: (None, None),
    _GG["Swipe3FingerHoriz"]: (None, None),
    _GG["Swipe4FingerHoriz"]: (None, None),
    _GG["Swipe3FingerVert"]: (None, None),
    _GG["Swipe4FingerVert"]: (None, None),
    _GG["LeftEdgeSwipe1Finger"]: (None, None),
    _GG["RightEdgeSwipe1Finger"]: (None, None),
    _GG["BottomEdgeSwipe1Finger"]: (None, None),
    _GG["TopEdgeSwipe1Finger"]: (_("Swipe from the top edge"), None),
    _GG["LeftEdgeSwipe1Finger2"]: (_("Swipe from the left edge"), None),
    _GG["RightEdgeSwipe1Finger2"]: (_("Swipe from the right edge"), None),
    _GG["BottomEdgeSwipe1Finger2"]: (_("Swipe from the bottom edge"), None),
    _GG["TopEdgeSwipe1Finger2"]: (_("Swipe from the top edge"), None),
    _GG["LeftEdgeSwipe2Finger"]: (_("Swipe two fingers from the left edge"), None),
    _GG["RightEdgeSwipe2Finger"]: (_("Swipe two fingers from the right edge"), None),
    _GG["BottomEdgeSwipe2Finger"]: (_("Swipe two fingers from the bottom edge"), None),
    _GG["TopEdgeSwipe2Finger"]: (_("Swipe two fingers from the top edge"), None),
    _GG["Zoom2Finger"]: (_("Zoom with two fingers."), _("Pinch to zoom out; spread to zoom in.")),
    _GG["Zoom2FingerPinch"]: (_("Pinch to zoom out."), _("Pinch to zoom out.")),
    _GG["Zoom2FingerSpread"]: (_("Spread to zoom in."), _("Spread to zoom in.")),
    _GG["Zoom3Finger"]: (_("Zoom with three fingers."), None),
    _GG["Zoom2FingerStateless"]: (_("Zoom with two fingers"), _("Pinch to zoom out; spread to zoom in.")),
    _GG["TwoFingersPresent"]: (None, None),
    _GG["Rotate2Finger"]: (None, None),
    _GG["Finger1"]: (None, None),
    _GG["Finger2"]: (None, None),
    _GG["Finger3"]: (None, None),
    _GG["Finger4"]: (None, None),
    _GG["Finger5"]: (None, None),
    _GG["Finger6"]: (None, None),
    _GG["Finger7"]: (None, None),
    _GG["Finger8"]: (None, None),
    _GG["Finger9"]: (None, None),
    _GG["Finger10"]: (None, None),
    _GG["DeviceSpecificRawData"]: (None, None),
}

_GESTURE2_PARAMS_LABELS = {
    _GP["ExtraCapabilities"]: (None, None),  # not supported
    _GP["PixelZone"]: (_("Pixel zone"), None),  # TO DO: replace None with a short description
    _GP["RatioZone"]: (_("Ratio zone"), None),  # TO DO: replace None with a short description
    _GP["ScaleFactor"]: (_("Scale factor"), _("Sets the cursor speed.")),
}

_GESTURE2_PARAMS_LABELS_SUB = {
    "left": (_("Left"), _("Left-most coordinate.")),
    "bottom": (_("Bottom"), _("Bottom coordinate.")),
    "width": (_("Width"), _("Width.")),
    "height": (_("Height"), _("Height.")),
    "scale": (_("Scale"), _("Cursor speed.")),
}


class Gesture2Gestures(_BitFieldOMSetting):
    name = "gesture2-gestures"
    label = _("Gestures")
    description = _("Tweak the mouse/touchpad behaviour.")
    feature = _F.GESTURE_2
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"om_method": hidpp20.Gesture.enable_offset_mask}
    choices_universe = _hidpp20_constants.GESTURE
    _labels = _GESTURE2_GESTURES_LABELS

    class validator_class(_BitFieldOMV):
        @classmethod
        def build(cls, setting_class, device, om_method=None):
            options = [g for g in device.gestures.gestures.values() if g.can_be_enabled or g.default_enabled]
            return cls(options, om_method=om_method) if options else None


class Gesture2Divert(_BitFieldOMSetting):
    name = "gesture2-divert"
    label = _("Gestures Diversion")
    description = _("Divert mouse/touchpad gestures.")
    feature = _F.GESTURE_2
    rw_options = {"read_fnid": 0x30, "write_fnid": 0x40}
    validator_options = {"om_method": hidpp20.Gesture.diversion_offset_mask}
    choices_universe = _hidpp20_constants.GESTURE
    _labels = _GESTURE2_GESTURES_LABELS

    class validator_class(_BitFieldOMV):
        @classmethod
        def build(cls, setting_class, device, om_method=None):
            options = [g for g in device.gestures.gestures.values() if g.can_be_diverted]
            return cls(options, om_method=om_method) if options else None


class Gesture2Params(_LongSettings):
    name = "gesture2-params"
    label = _("Gesture params")
    description = _("Change numerical parameters of a mouse/touchpad.")
    feature = _F.GESTURE_2
    rw_options = {"read_fnid": 0x70, "write_fnid": 0x80}
    choices_universe = hidpp20.PARAM
    sub_items_universe = hidpp20.SUB_PARAM
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
    name = "m-key-leds"
    label = _("M-Key LEDs")
    description = (
        _("Control the M-Key LEDs.")
        + "\n"
        + _("May need Onboard Profiles set to Disable to be effective.")
        + "\n"
        + _("May need G Keys diverted to be effective.")
    )
    feature = _F.MKEYS
    choices_universe = _NamedInts()
    for i in range(8):
        choices_universe[1 << i] = "M" + str(i + 1)
    _labels = {k: (None, _("Lights up the %s key.") % k) for k in choices_universe}

    class rw_class(_FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x10)

        def read(self, device):  # no way to read, so just assume off
            return b"\x00"

    class validator_class(_BitFieldV):
        @classmethod
        def build(cls, setting_class, device):
            number = device.feature_request(setting_class.feature, 0x00)[0]
            options = [setting_class.choices_universe[1 << i] for i in range(number)]
            return cls(options) if options else None


class MRKeyLED(_Setting):
    name = "mr-key-led"
    label = _("MR-Key LED")
    description = (
        _("Control the MR-Key LED.")
        + "\n"
        + _("May need Onboard Profiles set to Disable to be effective.")
        + "\n"
        + _("May need G Keys diverted to be effective.")
    )
    feature = _F.MR

    class rw_class(_FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x00)

        def read(self, device):  # no way to read, so just assume off
            return b"\x00"


## Only implemented for devices that can produce Key and Consumer Codes (e.g., Craft)
## and devices that can produce Key, Mouse, and Horizontal Scroll (e.g., M720)
## Only interested in current host, so use 0xFF for it
class PersistentRemappableAction(_Settings):
    name = "persistent-remappable-keys"
    label = _("Persistent Key/Button Mapping")
    description = (
        _("Permanently change the mapping for the key or button.")
        + "\n"
        + _("Changing important keys or buttons (such as for the left mouse button) can result in an unusable system.")
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
            return b"\x00\x00" + ks.data_bytes

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
                if logger.isEnabledFor(_WARN):
                    logger.warning("%s: unimplemented Persistent Remappable capability %s", device.name, hex(capabilities))
                return None
            choices = {}
            for k in remap_keys:
                if k is not None:
                    key = _special_keys.CONTROL[k.key]
                    choices[key] = keys  # TO RECOVER FROM BAD VALUES use _special_keys.KEYS
            return cls(choices, key_byte_count=2, byte_count=4) if choices else None

        def validate_read(self, reply_bytes, key):
            start = self._key_byte_count + self._read_skip_byte_count
            end = start + self._byte_count
            reply_value = _bytes2int(reply_bytes[start:end]) & self.mask
            # Craft keyboard has a value that isn't valid so fudge these values
            if reply_value not in self.choices[key]:
                if logger.isEnabledFor(_WARN):
                    logger.warning("unusual persistent remappable action mapping %x: use Default", reply_value)
                reply_value = _special_keys.KEYS_Default
            return reply_value


class Sidetone(_Setting):
    name = "sidetone"
    label = _("Sidetone")
    description = _("Set sidetone level.")
    feature = _F.SIDETONE
    validator_class = _RangeV
    min_value = 0
    max_value = 100


class Equalizer(_RangeFieldSetting):
    name = "equalizer"
    label = _("Equalizer")
    description = _("Set equalizer levels.")
    feature = _F.EQUALIZER
    rw_options = {"read_fnid": 0x20, "write_fnid": 0x30, "read_prefix": b"\x00"}
    keys_universe = []

    class validator_class(_PackedRangeV):
        @classmethod
        def build(cls, setting_class, device):
            data = device.feature_request(_F.EQUALIZER, 0x00)
            if not data:
                return None
            count, dbRange, _x, dbMin, dbMax = _unpack("!BBBBB", data[:5])
            if dbMin == 0:
                dbMin = -dbRange
            if dbMax == 0:
                dbMax = dbRange
            map = _NamedInts()
            for g in range((count + 6) // 7):
                freqs = device.feature_request(_F.EQUALIZER, 0x10, g * 7)
                for b in range(7):
                    if g * 7 + b >= count:
                        break
                    map[g * 7 + b] = str(int.from_bytes(freqs[2 * b + 1 : 2 * b + 3], "big")) + _("Hz")
            return cls(map, min_value=dbMin, max_value=dbMax, count=count, write_prefix_bytes=b"\x02")


class ADCPower(_Setting):
    name = "adc_power_management"
    label = _("Power Management")
    description = _("Power off in minutes (0 for never).")
    feature = _F.ADC_MEASUREMENT
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_class = _RangeV
    min_value = 0x00
    max_value = 0xFF
    validator_options = {"byte_count": 1}


class BrightnessControl(_Setting):
    name = "brightness_control"
    label = _("Brightness Control")
    description = _("Control overall brightness")
    feature = _F.BRIGHTNESS_CONTROL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_class = _RangeV

    def __init__(self, device, rw, validator):
        super().__init__(device, rw, validator)
        rw.on_off = validator.on_off
        rw.min_nonzero_value = validator.min_value
        validator.min_value = 0 if validator.on_off else validator.min_value

    class rw_class(_FeatureRW):
        def read(self, device, data_bytes=b""):
            if self.on_off:
                reply = device.feature_request(self.feature, 0x30)
                if not reply[0] & 0x01:
                    return b"\x00\x00"
            return super().read(device, data_bytes)

        def write(self, device, data_bytes):
            if self.on_off:
                off = int.from_bytes(data_bytes, byteorder="big") < self.min_nonzero_value
                reply = device.feature_request(self.feature, 0x40, b"\x00" if off else b"\x01", no_reply=False)
                if off:
                    return reply
            return super().write(device, data_bytes)

    class validator_class(_RangeV):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(_F.BRIGHTNESS_CONTROL)
            assert reply, "Oops, brightness range cannot be retrieved!"
            if reply:
                max_value = int.from_bytes(reply[0:2], byteorder="big")
                min_value = int.from_bytes(reply[4:6], byteorder="big")
                on_off = bool(reply[3] & 0x04)  # separate on/off control
                validator = cls(min_value=min_value, max_value=max_value, byte_count=2)
                validator.on_off = on_off
                return validator


class LEDControl(_Setting):
    name = "led_control"
    label = _("LED Control")
    description = _("Switch control of LED zones between device and Solaar")
    feature = _F.COLOR_LED_EFFECTS
    rw_options = {"read_fnid": 0x70, "write_fnid": 0x80}
    choices_universe = _NamedInts(Device=0, Solaar=1)
    validator_class = _ChoicesV
    validator_options = {"choices": choices_universe}


colors = _special_keys.COLORS
_LEDP = hidpp20.LEDParam


# an LED Zone has an index, a set of possible LED effects, and an LED effect setting
class LEDZoneSetting(_Setting):
    name = "led_zone_"
    label = _("LED Zone Effects")
    description = _("Set effect for LED Zone") + "\n" + _("LED Control needs to be set to Solaar to be effective.")
    feature = _F.COLOR_LED_EFFECTS
    color_field = {"name": _LEDP.color, "kind": _KIND.choice, "label": None, "choices": colors}
    speed_field = {"name": _LEDP.speed, "kind": _KIND.range, "label": _("Speed"), "min": 0, "max": 255}
    period_field = {"name": _LEDP.period, "kind": _KIND.range, "label": _("Period"), "min": 100, "max": 5000}
    intensity_field = {"name": _LEDP.intensity, "kind": _KIND.range, "label": _("Intensity"), "min": 0, "max": 100}
    ramp_field = {"name": _LEDP.ramp, "kind": _KIND.choice, "label": _("Ramp"), "choices": hidpp20.LEDRampChoices}
    #    form_field = { 'name': _LEDP.form, 'kind': _KIND.choice, 'label': _('Form'), 'choices': _hidpp20.LEDFormChoices }
    possible_fields = [color_field, speed_field, period_field, intensity_field, ramp_field]

    @classmethod
    def setup(cls, device, read_fnid, write_fnid, suffix):
        infos = device.led_effects
        settings = []
        for zone in infos.zones:
            prefix = _int2bytes(zone.index, 1)
            rw = _FeatureRW(cls.feature, read_fnid, write_fnid, prefix=prefix, suffix=suffix)
            validator = _HeteroV(data_class=hidpp20.LEDEffectSetting, options=zone.effects, readable=infos.readable)
            setting = cls(device, rw, validator)
            setting.name = cls.name + str(int(zone.location))
            setting.label = _("LEDs") + " " + str(hidpp20.LEDZoneLocations[zone.location])
            choices = [hidpp20.LEDEffects[e.ID][0] for e in zone.effects if e.ID in hidpp20.LEDEffects]
            ID_field = {"name": "ID", "kind": _KIND.choice, "label": None, "choices": choices}
            setting.possible_fields = [ID_field] + cls.possible_fields
            setting.fields_map = hidpp20.LEDEffects
            settings.append(setting)
        return settings

    @classmethod
    def build(cls, device):
        return cls.setup(device, 0xE0, 0x30, b"")


class RGBControl(_Setting):
    name = "rgb_control"
    label = _("LED Control")
    description = _("Switch control of LED zones between device and Solaar")
    feature = _F.RGB_EFFECTS
    rw_options = {"read_fnid": 0x50, "write_fnid": 0x50}
    choices_universe = _NamedInts(Device=0, Solaar=1)
    validator_class = _ChoicesV
    validator_options = {"choices": choices_universe, "write_prefix_bytes": b"\x01", "read_skip_byte_count": 1}


class RGBEffectSetting(LEDZoneSetting):
    name = "rgb_zone_"
    label = _("LED Zone Effects")
    description = _("Set effect for LED Zone") + "\n" + _("LED Control needs to be set to Solaar to be effective.")
    feature = _F.RGB_EFFECTS

    @classmethod
    def build(cls, device):
        return cls.setup(device, 0xE0, 0x10, b"\x01")


class PerKeyLighting(_Settings):
    name = "per-key-lighting"
    label = _("Per-key Lighting")
    description = _("Control per-key lighting.")
    feature = _F.PER_KEY_LIGHTING_V2
    keys_universe = _special_keys.KEYCODES
    choices_universe = _special_keys.COLORS

    def read(self, cached=True):
        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value
        reply_map = {}
        for key in self._validator.choices:
            reply_map[int(key)] = 0xFFFFFF  # can't read so fake a value of white
        self._value = reply_map
        return reply_map

    def write(self, map, save=True):
        if self._device.online:
            self.update(map, save)
            data_bytes = b""
            for key, value in map.items():
                data_bytes += key.to_bytes(1, "big") + value.to_bytes(3, "big")
                if len(data_bytes) >= 16:  # up to four values are packed into a request
                    self._device.feature_request(self.feature, 0x10, data_bytes)
                    data_bytes = b""
            if len(data_bytes) > 0:
                self._device.feature_request(self.feature, 0x10, data_bytes)
        self._device.feature_request(self.feature, 0x70, 0x00)  # signal device to make the changes
        return map

    def write_key_value(self, key, value, save=True):
        result = super().write_key_value(int(key), value, save)
        if self._device.online:
            self._device.feature_request(self.feature, 0x70, 0x00)  # signal device to make the change
        return result

    class rw_class(_FeatureRWMap):
        pass

    class validator_class(_ChoicesMapV):
        @classmethod
        def build(cls, setting_class, device):
            choices_map = {}
            key_bitmap = device.feature_request(setting_class.feature, 0x00, 0x00, 0x00)[2:]
            key_bitmap += device.feature_request(setting_class.feature, 0x00, 0x00, 0x01)[2:]
            key_bitmap += device.feature_request(setting_class.feature, 0x00, 0x00, 0x02)[2:]
            for i in range(1, 255):
                if (key_bitmap[i // 8] >> i % 8) & 0x01:
                    key = setting_class.keys_universe[i] if i in setting_class.keys_universe else _NamedInt(i, "KEY " + str(i))
                    choices_map[key] = setting_class.choices_universe
            result = cls(choices_map) if choices_map else None
            return result


SETTINGS = [
    RegisterHandDetection,  # simple
    RegisterSmoothScroll,  # simple
    RegisterSideScroll,  # simple
    RegisterDpi,
    RegisterFnSwap,  # working
    HiResScroll,  # simple
    LowresMode,  # simple
    HiresSmoothInvert,  # working
    HiresSmoothResolution,  # working
    HiresMode,  # simple
    ScrollRatchet,  # simple
    SmartShift,  # working
    SmartShiftEnhanced,  # simple
    ThumbInvert,  # working
    ThumbMode,  # working
    OnboardProfiles,
    ReportRate,  # working
    ExtendedReportRate,
    PointerSpeed,  # simple
    AdjustableDpi,  # working
    ExtendedAdjustableDpi,
    SpeedChange,
    #    Backlight,  # not working - disabled temporarily
    Backlight2,  # working
    Backlight2Level,
    Backlight2DurationHandsOut,
    Backlight2DurationHandsIn,
    Backlight2DurationPowered,
    Backlight3,
    LEDControl,
    LEDZoneSetting,
    RGBControl,
    RGBEffectSetting,
    BrightnessControl,
    PerKeyLighting,
    FnSwap,  # simple
    NewFnSwap,  # simple
    K375sFnSwap,  # working
    ReprogrammableKeys,  # working
    PersistentRemappableAction,
    DivertKeys,  # working
    DisableKeyboardKeys,  # working
    CrownSmooth,  # working
    DivertCrown,  # working
    DivertGkeys,  # working
    MKeyLEDs,  # working
    MRKeyLED,  # working
    Multiplatform,  # working
    DualPlatform,  # simple
    ChangeHost,  # working
    Gesture2Gestures,  # working
    Gesture2Divert,
    Gesture2Params,  # working
    Sidetone,
    Equalizer,
    ADCPower,
]

#
#
#


def check_feature(device, sclass):
    if sclass.feature not in device.features:
        return
    if sclass.min_version > device.features.get_feature_version(sclass.feature):
        return
    try:
        detected = sclass.build(device)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("check_feature %s [%s] detected %s", sclass.name, sclass.feature, detected)
        return detected
    except Exception as e:
        logger.error("check_feature %s [%s] error %s\n%s", sclass.name, sclass.feature, e, _format_exc())
        return False  # differentiate from an error-free determination that the setting is not supported


# Returns True if device was queried to find features, False otherwise
def check_feature_settings(device, already_known):
    """Auto-detect device settings by the HID++ 2.0 features they have."""
    if not device.features or not device.online:
        return False
    if device.protocol and device.protocol < 2.0:
        return False
    absent = device.persister.get("_absent", []) if device.persister else []
    newAbsent = []
    for sclass in SETTINGS:
        if sclass.feature:
            known_present = device.persister and sclass.name in device.persister
            if not any(s.name == sclass.name for s in already_known) and (known_present or sclass.name not in absent):
                setting = check_feature(device, sclass)
                if isinstance(setting, list):
                    for s in setting:
                        already_known.append(s)
                    if sclass.name in newAbsent:
                        newAbsent.remove(sclass.name)
                elif setting:
                    already_known.append(setting)
                    if sclass.name in newAbsent:
                        newAbsent.remove(sclass.name)
                elif setting is None:
                    if sclass.name not in newAbsent and sclass.name not in absent and sclass.name not in device.persister:
                        newAbsent.append(sclass.name)
    if device.persister and newAbsent:
        absent.extend(newAbsent)
        device.persister["_absent"] = absent
    return True


def check_feature_setting(device, setting_name):
    for sclass in SETTINGS:
        if sclass.feature and sclass.name == setting_name and device.features:
            setting = check_feature(device, sclass)
            if setting:
                return setting
