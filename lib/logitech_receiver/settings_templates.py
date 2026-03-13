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
from __future__ import annotations

import enum
import logging
import socket
import struct
import traceback

from time import time
from typing import Callable
from typing import Protocol

from solaar.i18n import _

from . import base
from . import common
from . import descriptors
from . import desktop_notifications
from . import diversion
from . import exceptions
from . import hidpp20
from . import hidpp20_constants
from . import settings
from . import settings_new
from . import settings_validator
from . import special_keys
from .hidpp10_constants import Registers
from .hidpp20 import KeyFlag
from .hidpp20 import MappingFlag
from .hidpp20_constants import GestureId
from .hidpp20_constants import ParamId

logger = logging.getLogger(__name__)

try:
    from gi.repository import GLib

    _has_glib = True
except ImportError:
    _has_glib = False

_hidpp20 = hidpp20.Hidpp20()
_F = hidpp20_constants.SupportedFeature


class State(enum.Enum):
    IDLE = "idle"
    PRESSED = "pressed"
    MOVED = "moved"


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
# Setting is for settings with a single value (boolean, number in a range, and symbolic choice).
# Settings is for settings that are maps from keys to values
#    and permit reading or writing the entire map or just one key/value pair.
# The BitFieldSetting class is for settings that have multiple boolean values packed into a bit field.
# BitFieldWithOffsetAndMaskSetting is similar.
# The RangeFieldSetting class is for settings that have multiple ranges packed into a byte string.
# LongSettings is for settings that have an even more complex structure.
#
# When settings are created a reader/writer and a validator are created.

# If the setting class has a value for rw_class then an instance of that class is created.
# Otherwise if the setting has a register then an instance of RegisterRW is created.
# and if the setting has a feature then an instance of FeatureRW is created.
# The instance is created with the register or feature as the first argument and rw_options as keyword arguments.
# RegisterRW doesn't use any options.
# FeatureRW options include
#   read_fnid - the feature function (times 16) to read the value (default 0x00),
#   write_fnid - the feature function (times 16) to write the value (default 0x10),
#   prefix - a prefix to add to the data being written and the read request (default b''), used for features
#     that provide and set multiple settings (e.g., to read and write function key inversion for current host)
#   no_reply - whether to wait for a reply (default false) (USE WITH EXTREME CAUTION).
#
# There are three simple validator classes - BooleanV, RangeValidator, and ChoicesValidator
# BooleanV is for boolean values and is the default.  It takes
#   true_value is the raw value for true (default 0x01), this can be an integer or a byte string,
#   false_value is the raw value for false (default 0x00), this can be an integer or a byte string,
#   mask is used to keep only some bits from a sequence of bits, this can be an integer or a byte string,
#   read_skip_byte_count is the number of bytes to ignore at the beginning of the read value (default 0),
#   write_prefix_bytes is a byte string to write before the value (default empty).

# RangeValidator is for an integer in a range.  It takes
#   byte_count is number of bytes that the value is stored in (defaults to size of max_value).
#   read_skip_byte_count is as for BooleanV
#   write_prefix_bytes is as for BooleanV
# RangeValidator uses min_value and max_value from the setting class as minimum and maximum.

# ChoicesValidator is for symbolic choices.  It takes one positional and three keyword arguments:
#   choices is a list of named integers that are the valid choices,
#   byte_count is the number of bytes for the integer (default size of largest choice integer),
#   read_skip_byte_count is as for BooleanV,
#   write_prefix_bytes is as for BooleanV.
# Settings that use ChoicesValidator should have a choices_universe class variable of the potential choices,
# or None for no limitation and optionally a choices_extra class variable with an extra choice.
# The choices_extra is so that there is no need to specially extend a large existing NamedInts.
# ChoicesMapValidator validator is for map settings that map onto symbolic choices.   It takes
#   choices_map is a map from keys to possible values
#   byte_count is as for ChoicesValidator,
#   read_skip_byte_count is as for ChoicesValidator,
#   write_prefix_bytes is as for ChoicesValidator,
#   key_byte_count is the number of bytes for the key integer (default size of largest key),
#   extra_default is an extra raw value that is used as a default value (default None).
# Settings that use ChoicesValidator should have keys_universe and choices_universe class variable of
# the potential keys and potential choices or None for no limitation.

# BitFieldValidator validator is for bit field settings.  It takes one positional and one keyword argument
#   the positional argument is the number of bits in the bit field
#   byte_count is the size of the bit field (default size of the bit field)
#
# A few settings work very differently.  They divert a key, which is then used to start and stop some special action.
# These settings have reader/writer classes that perform special processing instead of sending commands to the device.


class FnSwapVirtual(settings.Setting):  # virtual setting to hold fn swap strings
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


class RegisterHandDetection(settings.Setting):
    name = "hand-detection"
    label = _("Hand Detection")
    description = _("Turn on illumination when the hands hover over the keyboard.")
    register = Registers.KEYBOARD_HAND_DETECTION
    validator_options = {"true_value": b"\x00\x00\x00", "false_value": b"\x00\x00\x30", "mask": b"\x00\x00\xff"}


class RegisterSmoothScroll(settings.Setting):
    name = "smooth-scroll"
    label = _("Scroll Wheel Smooth Scrolling")
    description = _("High-sensitivity mode for vertical scroll with the wheel.")
    register = Registers.MOUSE_BUTTON_FLAGS
    validator_options = {"true_value": 0x40, "mask": 0x40}


class RegisterSideScroll(settings.Setting):
    name = "side-scroll"
    label = _("Side Scrolling")
    description = _(
        "When disabled, pushing the wheel sideways sends custom button events\n"
        "instead of the standard side-scrolling events."
    )
    register = Registers.MOUSE_BUTTON_FLAGS
    validator_options = {"true_value": 0x02, "mask": 0x02}


# different devices have different sets of permissible dpis, so this should be subclassed
class RegisterDpi(settings.Setting):
    name = "dpi-old"
    label = _("Sensitivity (DPI - older mice)")
    description = _("Mouse movement sensitivity")
    register = Registers.MOUSE_DPI
    choices_universe = common.NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}


class RegisterFnSwap(FnSwapVirtual):
    register = Registers.KEYBOARD_FN_SWAP
    validator_options = {"true_value": b"\x00\x01", "mask": b"\x00\x01"}


class _PerformanceMXDpi(RegisterDpi):
    choices_universe = common.NamedInts.range(0x81, 0x8F, lambda x: str((x - 0x80) * 100))
    validator_options = {"choices": choices_universe}


# set up register settings for devices - this is done here to break up an import loop
descriptors.get_wpid("0060").settings = [RegisterFnSwap]
descriptors.get_wpid("2008").settings = [RegisterFnSwap]
descriptors.get_wpid("2010").settings = [RegisterFnSwap, RegisterHandDetection]
descriptors.get_wpid("2011").settings = [RegisterFnSwap]
descriptors.get_usbid(0xC318).settings = [RegisterFnSwap]
descriptors.get_wpid("C714").settings = [RegisterFnSwap]
descriptors.get_wpid("100B").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("100F").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("1013").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("1014").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("1017").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("1023").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("4004").settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("101A").settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("101B").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("101D").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("101F").settings = [RegisterSideScroll]
descriptors.get_usbid(0xC06B).settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_wpid("1025").settings = [RegisterSideScroll]
descriptors.get_wpid("102A").settings = [RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_usbid(0xC048).settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]
descriptors.get_usbid(0xC066).settings = [_PerformanceMXDpi, RegisterSmoothScroll, RegisterSideScroll]


# ignore the capabilities part of the feature - all devices should be able to swap Fn state
# can't just use the first byte = 0xFF (for current host) because of a bug in the firmware of the MX Keys S
class K375sFnSwap(FnSwapVirtual):
    feature = _F.K375S_FN_INVERSION
    validator_options = {"true_value": b"\x01", "false_value": b"\x00", "read_skip_byte_count": 1}

    class rw_class(settings.FeatureRW):
        def find_current_host(self, device):
            if not self.prefix:
                response = device.feature_request(_F.HOSTS_INFO, 0x00)
                self.prefix = response[3:4] if response else b"\xff"

        def read(self, device, data_bytes=b""):
            self.find_current_host(device)
            return super().read(device, data_bytes)

        def write(self, device, data_bytes):
            self.find_current_host(device)
            return super().write(device, data_bytes)


class FnSwap(FnSwapVirtual):
    feature = _F.FN_INVERSION


class NewFnSwap(FnSwapVirtual):
    feature = _F.NEW_FN_INVERSION


class Backlight(settings.Setting):
    name = "backlight-qualitative"
    label = _("Backlight Timed")
    description = _("Set illumination time for keyboard.")
    feature = _F.BACKLIGHT
    choices_universe = common.NamedInts(Off=0, Varying=2, VeryShort=5, Short=10, Medium=20, Long=60, VeryLong=180)
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}


# MX Keys S requires some extra values, as in 11 02 0c1a 000dff000b000b003c00000000000000
# on/off options (from current) effect (FF-no change) level (from current) durations[6] (from current)
class Backlight2(settings.Setting):
    name = "backlight"
    label = _("Backlight")
    description = _("Illumination level on keyboard.  Changes made are only applied in Manual mode.")
    feature = _F.BACKLIGHT2
    choices_universe = common.NamedInts(Disabled=0xFF, Enabled=0x00, Automatic=0x01, Manual=0x02)
    min_version = 0

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device):
            backlight = device.backlight
            if not backlight.enabled:
                return b"\xff"
            else:
                return common.int2bytes(backlight.mode, 1)

        def write(self, device, data_bytes):
            backlight = device.backlight
            backlight.enabled = data_bytes[0] != 0xFF
            if data_bytes[0] != 0xFF:
                backlight.mode = data_bytes[0]
            backlight.write()
            return True

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            backlight = device.backlight
            choices = common.NamedInts()
            choices[0xFF] = _("Disabled")
            if backlight.auto_supported:
                choices[0x1] = _("Automatic")
            if backlight.perm_supported:
                choices[0x3] = _("Manual")
            if not (backlight.auto_supported or backlight.temp_supported or backlight.perm_supported):
                choices[0x0] = _("Enabled")
            return cls(choices=choices, byte_count=1)


class Backlight2Level(settings.Setting):
    name = "backlight_level"
    label = _("Backlight Level")
    description = _("Illumination level on keyboard when in Manual mode.")
    feature = _F.BACKLIGHT2
    min_version = 3

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device):
            backlight = device.backlight
            return common.int2bytes(backlight.level, 1)

        def write(self, device, data_bytes):
            if device.backlight.level != common.bytes2int(data_bytes):
                device.backlight.level = common.bytes2int(data_bytes)
                device.backlight.write()
            return True

    class validator_class(settings_validator.RangeValidator):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(_F.BACKLIGHT2, 0x20)
            assert reply, "Oops, backlight range cannot be retrieved!"
            if reply[0] > 1:
                return cls(min_value=0, max_value=reply[0] - 1, byte_count=1)


class Backlight2Duration(settings.Setting):
    feature = _F.BACKLIGHT2
    min_version = 3
    validator_class = settings_validator.RangeValidator
    min_value = 1
    max_value = 600  # 10 minutes - actual maximum is 2 hours
    validator_options = {"byte_count": 2}

    class rw_class:
        def __init__(self, feature, field):
            self.feature = feature
            self.kind = settings.FeatureRW.kind
            self.field = field

        def read(self, device):
            backlight = device.backlight
            return common.int2bytes(getattr(backlight, self.field) * 5, 2)  # use seconds instead of 5-second units

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
    validator_class = settings_validator.RangeValidator
    rw_options = {"field": "dho"}


class Backlight2DurationHandsIn(Backlight2Duration):
    name = "backlight_duration_hands_in"
    label = _("Backlight Delay Hands In")
    description = _("Delay in seconds until backlight fades out with hands near keyboard.")
    feature = _F.BACKLIGHT2
    validator_class = settings_validator.RangeValidator
    rw_options = {"field": "dhi"}


class Backlight2DurationPowered(Backlight2Duration):
    name = "backlight_duration_powered"
    label = _("Backlight Delay Powered")
    description = _("Delay in seconds until backlight fades out with external power.")
    feature = _F.BACKLIGHT2
    validator_class = settings_validator.RangeValidator
    rw_options = {"field": "dpow"}


class Backlight3(settings.Setting):
    name = "backlight-timed"
    label = _("Backlight (Seconds)")
    description = _("Set illumination time for keyboard.")
    feature = _F.BACKLIGHT3
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20, "suffix": b"\x09"}
    validator_class = settings_validator.RangeValidator
    min_value = 0
    max_value = 1000
    validator_options = {"byte_count": 2}


class HiResScroll(settings.Setting):
    name = "hi-res-scroll"
    label = _("Scroll Wheel High Resolution")
    description = (
        _("High-sensitivity mode for vertical scroll with the wheel.")
        + "\n"
        + _("Set to ignore if scrolling is abnormally fast or slow")
    )
    feature = _F.HI_RES_SCROLLING


class LowresMode(settings.Setting):
    name = "lowres-scroll-mode"
    label = _("Scroll Wheel Diversion")
    description = _(
        "Make scroll wheel send LOWRES_WHEEL HID++ notifications (which trigger Solaar rules but are otherwise ignored)."
    )
    feature = _F.LOWRES_WHEEL


class HiresSmoothInvert(settings.Setting):
    name = "hires-smooth-invert"
    label = _("Scroll Wheel Direction")
    description = _("Invert direction for vertical scroll with wheel.")
    feature = _F.HIRES_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x04, "mask": 0x04}


class HiresSmoothResolution(settings.Setting):
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


class HiresMode(settings.Setting):
    name = "hires-scroll-mode"
    label = _("Scroll Wheel Diversion")
    description = _(
        "Make scroll wheel send HIRES_WHEEL HID++ notifications (which trigger Solaar rules but are otherwise ignored)."
    )
    feature = _F.HIRES_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x01, "mask": 0x01}


class PointerSpeed(settings.Setting):
    name = "pointer_speed"
    label = _("Sensitivity (Pointer Speed)")
    description = _("Speed multiplier for mouse (256 is normal multiplier).")
    feature = _F.POINTER_SPEED
    validator_class = settings_validator.RangeValidator
    min_value = 0x002E
    max_value = 0x01FF
    validator_options = {"byte_count": 2}


class ThumbMode(settings.Setting):
    name = "thumb-scroll-mode"
    label = _("Thumb Wheel Diversion")
    description = _(
        "Make thumb wheel send THUMB_WHEEL HID++ notifications (which trigger Solaar rules but are otherwise ignored)."
    )
    feature = _F.THUMB_WHEEL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": b"\x01\x00", "false_value": b"\x00\x00", "mask": b"\x01\x00"}


class ThumbInvert(settings.Setting):
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


class OnboardProfiles(settings.Setting):
    name = "onboard_profiles"
    label = _("Onboard Profiles")
    description = _("Enable an onboard profile, which controls report rate, sensitivity, and button actions")
    feature = _F.ONBOARD_PROFILES
    choices_universe = common.NamedInts(Disabled=0)
    for i in range(1, 16):
        choices_universe[i] = f"Profile {i}"
        choices_universe[i + 0x100] = f"Read-Only Profile {i}"
    validator_class = settings_validator.ChoicesValidator

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

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
                profile_change(device, common.bytes2int(data_bytes))
            return result

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            headers = hidpp20.OnboardProfiles.get_profile_headers(device)
            profiles_list = [setting_class.choices_universe[0]]
            if headers:
                for sector, enabled in headers:
                    if enabled and setting_class.choices_universe[sector]:
                        profiles_list.append(setting_class.choices_universe[sector])
            return cls(choices=common.NamedInts.list(profiles_list), byte_count=2) if len(profiles_list) > 1 else None


class ReportRate(settings.Setting):
    name = "report_rate"
    label = _("Report Rate")
    description = (
        _("Frequency of device movement reports") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    )
    feature = _F.REPORT_RATE
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    choices_universe = common.NamedInts()
    choices_universe[1] = "1ms"
    choices_universe[2] = "2ms"
    choices_universe[3] = "3ms"
    choices_universe[4] = "4ms"
    choices_universe[5] = "5ms"
    choices_universe[6] = "6ms"
    choices_universe[7] = "7ms"
    choices_universe[8] = "8ms"

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            # if device.wpid == '408E':
            #    return None  # host mode borks the function keys on the G915 TKL keyboard
            reply = device.feature_request(_F.REPORT_RATE, 0x00)
            assert reply, "Oops, report rate choices cannot be retrieved!"
            rate_list = []
            rate_flags = common.bytes2int(reply[0:1])
            for i in range(0, 8):
                if (rate_flags >> i) & 0x01:
                    rate_list.append(setting_class.choices_universe[i + 1])
            return cls(choices=common.NamedInts.list(rate_list), byte_count=1) if rate_list else None


class ExtendedReportRate(settings.Setting):
    name = "report_rate_extended"
    label = _("Report Rate")
    description = (
        _("Frequency of device movement reports") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    )
    feature = _F.EXTENDED_ADJUSTABLE_REPORT_RATE
    rw_options = {"read_fnid": 0x20, "write_fnid": 0x30}
    choices_universe = common.NamedInts()
    choices_universe[0] = "8ms"
    choices_universe[1] = "4ms"
    choices_universe[2] = "2ms"
    choices_universe[3] = "1ms"
    choices_universe[4] = "500us"
    choices_universe[5] = "250us"
    choices_universe[6] = "125us"

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(_F.EXTENDED_ADJUSTABLE_REPORT_RATE, 0x10)
            assert reply, "Oops, report rate choices cannot be retrieved!"
            rate_list = []
            rate_flags = common.bytes2int(reply[0:2])
            for i in range(0, 7):
                if rate_flags & (0x01 << i):
                    rate_list.append(setting_class.choices_universe[i])
            return cls(choices=common.NamedInts.list(rate_list), byte_count=1) if rate_list else None


class DivertCrown(settings.Setting):
    name = "divert-crown"
    label = _("Divert crown events")
    description = _("Make crown send CROWN HID++ notifications (which trigger Solaar rules but are otherwise ignored).")
    feature = _F.CROWN
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x02, "false_value": 0x01, "mask": 0xFF}


class CrownSmooth(settings.Setting):
    name = "crown-smooth"
    label = _("Crown smooth scroll")
    description = _("Set crown smooth scroll")
    feature = _F.CROWN
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"true_value": 0x01, "false_value": 0x02, "read_skip_byte_count": 1, "write_prefix_bytes": b"\x00"}


class DivertGkeys(settings.Setting):
    name = "divert-gkeys"
    label = _("Divert G and M Keys")
    description = _("Make G and M keys send HID++ notifications (which trigger Solaar rules but are otherwise ignored).")
    feature = _F.GKEY
    validator_options = {"true_value": 0x01, "false_value": 0x00, "mask": 0xFF}

    class rw_class(settings.FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x20)

        def read(self, device):  # no way to read, so just assume not diverted
            return b"\x00"


class ScrollRatchet(settings.Setting):
    name = "scroll-ratchet"
    label = _("Scroll Wheel Ratcheted")
    description = _("Switch the mouse wheel between speed-controlled ratcheting and always freespin.")
    feature = _F.SMART_SHIFT
    choices_universe = common.NamedInts(**{_("Freespinning"): 1, _("Ratcheted"): 2})
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}


class SmartShift(settings.Setting):
    name = "smart-shift"
    label = _("Scroll Wheel Ratchet Speed")
    description = _(
        "Use the mouse wheel speed to switch between ratcheted and freespinning.\n"
        "The mouse wheel is always ratcheted at 50."
    )
    feature = _F.SMART_SHIFT
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x10}

    class rw_class(settings.FeatureRW):
        MIN_VALUE = 1
        MAX_VALUE = 50

        def __init__(self, feature, read_fnid, write_fnid):
            super().__init__(feature, read_fnid, write_fnid)

        def read(self, device):
            value = super().read(device)
            if common.bytes2int(value[0:1]) == 1:
                # Mode = Freespin, map to minimum
                return common.int2bytes(self.MIN_VALUE, count=1)
            else:
                # Mode = smart shift, map to the value, capped at maximum
                threshold = min(common.bytes2int(value[1:2]), self.MAX_VALUE)
                return common.int2bytes(threshold, count=1)

        def write(self, device, data_bytes):
            threshold = common.bytes2int(data_bytes)
            # Freespin at minimum
            mode = 0  # 1 if threshold <= self.MIN_VALUE else 2
            # Ratchet at maximum
            if threshold >= self.MAX_VALUE:
                threshold = 255
            data = common.int2bytes(mode, count=1) + common.int2bytes(max(0, threshold), count=1)
            return super().write(device, data)

    min_value = rw_class.MIN_VALUE
    max_value = rw_class.MAX_VALUE
    validator_class = settings_validator.RangeValidator


class SmartShiftEnhanced(SmartShift):
    feature = _F.SMART_SHIFT_ENHANCED
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}


class ScrollRatchetEnhanced(ScrollRatchet):
    feature = _F.SMART_SHIFT_ENHANCED
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}


class ScrollRatchetTorque(settings.Setting):
    name = "scroll-ratchet-torque"
    label = _("Scroll Wheel Ratchet Torque")
    description = _("Change the torque needed to overcome the ratchet.")
    feature = _F.SMART_SHIFT_ENHANCED
    min_value = 1
    max_value = 100
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}

    class rw_class(settings.FeatureRW):
        def write(self, device, data_bytes):
            ratchetSetting = next(filter(lambda s: s.name == "scroll-ratchet", device.settings), None)
            if ratchetSetting:  # for MX Master 4, the ratchet setting needs to be written for changes to take effect
                ratchet_value = ratchetSetting.read(True)
                data_bytes = ratchet_value.to_bytes(1, "big") + data_bytes[1:]
            result = super().write(device, data_bytes)
            return result

    class validator_class(settings_validator.RangeValidator):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(_F.SMART_SHIFT_ENHANCED, 0x00)
            if reply[0] & 0x01:  # device supports tunable torque
                return cls(
                    min_value=setting_class.min_value,
                    max_value=setting_class.max_value,
                    byte_count=1,
                    write_prefix_bytes=b"\x00\x00",  # don't change mode or disengage, but see above
                    read_skip_byte_count=2,
                )


# the keys for the choice map are Logitech controls (from special_keys)
# each choice value is a NamedInt with the string from a task (to be shown to the user)
# and the integer being the control number for that task (to be written to the device)
# Solaar only remaps keys (controlled by key gmask and group), not other key reprogramming
class ReprogrammableKeys(settings.Settings):
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
    keys_universe = special_keys.CONTROL
    choices_universe = special_keys.CONTROL

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device, key):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            return b"\x00\x00" + common.int2bytes(int(key_struct.mapped_to), 2)

        def write(self, device, key, data_bytes):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            key_struct.remap(special_keys.CONTROL[common.bytes2int(data_bytes)])
            return True

    class validator_class(settings_validator.ChoicesMapValidator):
        @classmethod
        def build(cls, setting_class, device):
            choices = {}
            if device.keys:
                for k in device.keys:
                    tgts = k.remappable_to
                    if len(tgts) > 1:
                        choices[k.key] = tgts
            return cls(choices, key_byte_count=2, byte_count=2, extra_default=0) if choices else None


class DpiSlidingXY(settings.RawXYProcessing):
    def __init__(
        self,
        *args,
        show_notification: Callable[[str, str], bool],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fsmState = None
        self._show_notification = show_notification

    def activate_action(self):
        self.dpiSetting = next(filter(lambda s: s.name == "dpi" or s.name == "dpi_extended", self.device.settings), None)
        self.dpiChoices = list(self.dpiSetting.choices)
        self.otherDpiIdx = self.device.persister.get("_dpi-sliding", -1) if self.device.persister else -1
        if not isinstance(self.otherDpiIdx, int) or self.otherDpiIdx < 0 or self.otherDpiIdx >= len(self.dpiChoices):
            self.otherDpiIdx = self.dpiChoices.index(self.dpiSetting.read())
        self.fsmState = State.IDLE
        self.dx = 0.0
        self.movingDpiIdx = None

    def setNewDpi(self, newDpiIdx):
        newDpi = self.dpiChoices[newDpiIdx]
        self.dpiSetting.write(newDpi)
        if self.device.setting_callback:
            self.device.setting_callback(self.device, type(self.dpiSetting), [newDpi])

    def displayNewDpi(self, newDpiIdx):
        selected_dpi = self.dpiChoices[newDpiIdx]
        min_dpi = self.dpiChoices[0]
        max_dpi = self.dpiChoices[-1]
        reason = f"DPI {selected_dpi} [min {min_dpi}, max {max_dpi}]"
        self._show_notification(self.device, reason)

    def press_action(self, key):  # start tracking
        self.starting = True
        if self.fsmState == State.IDLE:
            self.fsmState = State.PRESSED
            self.dx = 0.0
            # While in 'moved' state, the index into 'dpiChoices' of the currently selected DPI setting
            self.movingDpiIdx = None

    def release_action(self):  # adjust DPI and stop tracking
        if self.fsmState == State.PRESSED:  # Swap with other DPI
            thisIdx = self.dpiChoices.index(self.dpiSetting.read())
            newDpiIdx, self.otherDpiIdx = self.otherDpiIdx, thisIdx
            if self.device.persister:
                self.device.persister["_dpi-sliding"] = self.otherDpiIdx
            self.setNewDpi(newDpiIdx)
            self.displayNewDpi(newDpiIdx)
        elif self.fsmState == State.MOVED:  # Set DPI according to displacement
            self.setNewDpi(self.movingDpiIdx)
        self.fsmState = State.IDLE

    def move_action(self, dx, dy):
        if self.device.features.get_feature_version(_F.REPROG_CONTROLS_V4) >= 5 and self.starting:
            self.starting = False  # hack to ignore strange first movement report from MX Master 3S
            return
        currDpi = self.dpiSetting.read()
        self.dx += float(dx) / float(currDpi) * 15.0  # yields a more-or-less DPI-independent dx of about 5/cm
        if self.fsmState == State.PRESSED:
            if abs(self.dx) >= 1.0:
                self.fsmState = State.MOVED
                self.movingDpiIdx = self.dpiChoices.index(currDpi)
        elif self.fsmState == State.MOVED:
            currIdx = self.dpiChoices.index(self.dpiSetting.read())
            newMovingDpiIdx = min(max(currIdx + int(self.dx), 0), len(self.dpiChoices) - 1)
            if newMovingDpiIdx != self.movingDpiIdx:
                self.movingDpiIdx = newMovingDpiIdx
                self.displayNewDpi(newMovingDpiIdx)


class MouseGesturesXY(settings.RawXYProcessing):
    def activate_action(self):
        self.dpiSetting = next(filter(lambda s: s.name == "dpi" or s.name == "dpi_extended", self.device.settings), None)
        self.fsmState = State.IDLE
        self.initialize_data()

    def initialize_data(self):
        self.dx = 0.0
        self.dy = 0.0
        self.lastEv = None
        self.data = []

    def press_action(self, key):
        self.starting = True
        if self.fsmState == State.IDLE:
            self.fsmState = State.PRESSED
            self.initialize_data()
            self.data = [key.key]

    def release_action(self):
        if self.fsmState == State.PRESSED:
            # emit mouse gesture notification
            self.push_mouse_event()
            if logger.isEnabledFor(logging.INFO):
                logger.info("mouse gesture notification %s", self.data)
            payload = struct.pack("!" + (len(self.data) * "h"), *self.data)
            notification = base.HIDPPNotification(0, 0, 0, 0, payload)
            diversion.process_notification(self.device, notification, _F.MOUSE_GESTURE)
            self.fsmState = State.IDLE

    def move_action(self, dx, dy):
        if self.fsmState == State.PRESSED:
            now = time() * 1000  # time_ns() / 1e6
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
        self.lastEv = time() * 1000  # time_ns() / 1e6
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


class DivertKeys(settings.Settings):
    name = "divert-keys"
    label = _("Key/Button Diversion")
    description = _("Make the key or button send HID++ notifications (Diverted) or initiate Mouse Gestures or Sliding DPI")
    feature = _F.REPROG_CONTROLS_V4
    keys_universe = special_keys.CONTROL
    choices_universe = common.NamedInts(**{_("Regular"): 0, _("Diverted"): 1, _("Mouse Gestures"): 2, _("Sliding DPI"): 3})
    choices_gesture = common.NamedInts(**{_("Regular"): 0, _("Diverted"): 1, _("Mouse Gestures"): 2})
    choices_divert = common.NamedInts(**{_("Regular"): 0, _("Diverted"): 1})

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device, key):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            return b"\x00\x00\x01" if MappingFlag.DIVERTED in key_struct.mapping_flags else b"\x00\x00\x00"

        def write(self, device, key, data_bytes):
            key_index = device.keys.index(key)
            key_struct = device.keys[key_index]
            key_struct.set_diverted(common.bytes2int(data_bytes) != 0)  # not regular
            return True

    class validator_class(settings_validator.ChoicesMapValidator):
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
                for key in device.keys:
                    if KeyFlag.DIVERTABLE in key.flags and KeyFlag.VIRTUAL not in key.flags:
                        if KeyFlag.RAW_XY in key.flags:
                            choices[key.key] = setting_class.choices_gesture
                            if gestures is None:
                                gestures = MouseGesturesXY(device, name="MouseGestures")
                            if _F.ADJUSTABLE_DPI in device.features:
                                choices[key.key] = setting_class.choices_universe
                                if sliding is None:
                                    sliding = DpiSlidingXY(
                                        device, name="DpiSliding", show_notification=desktop_notifications.show
                                    )
                        else:
                            choices[key.key] = setting_class.choices_divert
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
        val = common.bytes2int(dpi_bytes[i : i + 2])
        if val == 0:
            break
        if val >> 13 == 0b111:
            step = val & 0x1FFF
            last = common.bytes2int(dpi_bytes[i + 2 : i + 4])
            assert len(dpi_list) > 0 and last > dpi_list[-1], f"Invalid DPI list item: {val!r}"
            dpi_list += range(dpi_list[-1] + step, last + 1, step)
            i += 4
        else:
            dpi_list.append(val)
            i += 2
    return dpi_list


class AdjustableDpi(settings.Setting):
    name = "dpi"
    label = _("Sensitivity (DPI)")
    description = _("Mouse movement sensitivity") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    feature = _F.ADJUSTABLE_DPI
    rw_options = {"read_fnid": 0x20, "write_fnid": 0x30}
    choices_universe = common.NamedInts.range(100, 4000, str, 50)

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            dpilist = produce_dpi_list(setting_class.feature, 0x10, 1, device, 0)
            setting = (
                cls(choices=common.NamedInts.list(dpilist), byte_count=2, write_prefix_bytes=b"\x00") if dpilist else None
            )
            setting.dpilist = dpilist
            return setting

        def validate_read(self, reply_bytes):  # special validator to use default DPI if needed
            reply_value = common.bytes2int(reply_bytes[1:3])
            if reply_value == 0:  # use default value instead
                reply_value = common.bytes2int(reply_bytes[3:5])
            valid_value = self.choices[reply_value]
            assert valid_value is not None, f"{self.__class__.__name__}: failed to validate read value {reply_value:02X}"
            return valid_value


class ExtendedAdjustableDpi(settings.Setting):
    # the extended version allows for two dimensions, longer dpi descriptions, but still assume only one sensor
    name = "dpi_extended"
    label = _("Sensitivity (DPI)")
    description = _("Mouse movement sensitivity") + "\n" + _("May need Onboard Profiles set to Disable to be effective.")
    feature = _F.EXTENDED_ADJUSTABLE_DPI
    rw_options = {"read_fnid": 0x50, "write_fnid": 0x60}
    keys_universe = common.NamedInts(X=0, Y=1, LOD=2)
    choices_universe = common.NamedInts.range(100, 4000, str, 50)
    choices_universe[1] = "LOW"
    choices_universe[2] = "MEDIUM"
    choices_universe[3] = "HIGH"
    keys = common.NamedInts(X=0, Y=1, LOD=2)

    def write_key_value(self, key, value, save=True):
        if isinstance(self._value, dict):
            self._value[key] = value
        else:
            self._value = {key: value}
        result = self.write(self._value, save)
        return result[key] if isinstance(result, dict) else result

    class validator_class(settings_validator.ChoicesMapValidator):
        @classmethod
        def build(cls, setting_class, device):
            reply = device.feature_request(setting_class.feature, 0x10, 0x00)
            y = bool(reply[2] & 0x01)
            lod = bool(reply[2] & 0x02)
            choices_map = {}
            dpilist_x = produce_dpi_list(setting_class.feature, 0x20, 3, device, 0)
            choices_map[setting_class.keys["X"]] = common.NamedInts.list(dpilist_x)
            if y:
                dpilist_y = produce_dpi_list(setting_class.feature, 0x20, 3, device, 1)
                choices_map[setting_class.keys["Y"]] = common.NamedInts.list(dpilist_y)
            if lod:
                choices_map[setting_class.keys["LOD"]] = common.NamedInts(LOW=0, MEDIUM=1, HIGH=2)
            validator = cls(choices_map=choices_map, byte_count=2, write_prefix_bytes=b"\x00")
            validator.y = y
            validator.lod = lod
            validator.keys = setting_class.keys
            return validator

        def validate_read(self, reply_bytes):  # special validator to read entire setting
            dpi_x = common.bytes2int(reply_bytes[3:5]) if reply_bytes[1:3] == 0 else common.bytes2int(reply_bytes[1:3])
            assert dpi_x in self.choices[0], f"{self.__class__.__name__}: failed to validate dpi_x value {dpi_x:04X}"
            value = {self.keys["X"]: dpi_x}
            if self.y:
                dpi_y = common.bytes2int(reply_bytes[7:9]) if reply_bytes[5:7] == 0 else common.bytes2int(reply_bytes[5:7])
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
            data_bytes += common.int2bytes(new_value[0], 2)
            if self.y:
                if new_value[self.keys["Y"]] not in self.choices[self.keys["Y"]]:
                    raise ValueError(f"invalid value {new_value!r}")
                data_bytes += common.int2bytes(new_value[self.keys["Y"]], 2)
            else:
                data_bytes += b"\x00\x00"
            if self.lod:
                if new_value[self.keys["LOD"]] not in self.choices[self.keys["LOD"]]:
                    raise ValueError(f"invalid value {new_value!r}")
                data_bytes += common.int2bytes(new_value[self.keys["LOD"]], 1)
            else:
                data_bytes += b"\x00"
            return data_bytes


class SpeedChange(settings.Setting):
    """Implements the ability to switch Sensitivity by clicking on the DPI_Change button."""

    name = "speed-change"
    label = _("Sensitivity Switching")
    description = _(
        "Switch the current sensitivity and the remembered sensitivity when the key or button is pressed.\n"
        "If there is no remembered sensitivity, just remember the current sensitivity"
    )
    choices_universe = special_keys.CONTROL
    choices_extra = common.NamedInt(0, _("Off"))
    feature = _F.POINTER_SPEED
    rw_options = {"name": "speed change"}

    class rw_class(settings.ActionSettingRW):
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

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            key_index = device.keys.index(special_keys.CONTROL.DPI_Change)
            key = device.keys[key_index] if key_index is not None else None
            if key is not None and KeyFlag.DIVERTABLE in key.flags:
                keys = [setting_class.choices_extra, key.key]
                return cls(choices=common.NamedInts.list(keys), byte_count=2)


class DisableKeyboardKeys(settings.BitFieldSetting):
    name = "disable-keyboard-keys"
    label = _("Disable keys")
    description = _("Disable specific keyboard keys.")
    feature = _F.KEYBOARD_DISABLE_KEYS
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    _labels = {k: (None, _("Disables the %s key.") % k) for k in special_keys.DISABLE}
    choices_universe = special_keys.DISABLE

    class validator_class(settings_validator.BitFieldValidator):
        @classmethod
        def build(cls, setting_class, device):
            mask = device.feature_request(_F.KEYBOARD_DISABLE_KEYS, 0x00)[0]
            options = [special_keys.DISABLE[1 << i] for i in range(8) if mask & (1 << i)]
            return cls(options) if options else None


class Multiplatform(settings.Setting):
    name = "multiplatform"
    label = _("Set OS")
    description = _("Change keys to match OS.")
    feature = _F.MULTIPLATFORM
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x30}
    choices_universe = common.NamedInts(**{"OS " + str(i + 1): i for i in range(8)})

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

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            def _str_os_versions(low, high):
                def _str_os_version(version):
                    if version == 0:
                        return ""
                    elif version & 0xFF:
                        return f"{str(version >> 8)}.{str(version & 0xFF)}"
                    else:
                        return str(version >> 8)

                return "" if low == 0 and high == 0 else f" {_str_os_version(low)}-{_str_os_version(high)}"

            infos = device.feature_request(_F.MULTIPLATFORM)
            assert infos, "Oops, multiplatform count cannot be retrieved!"
            flags, _ignore, num_descriptors = struct.unpack("!BBB", infos[:3])
            if not (flags & 0x02):  # can't set platform so don't create setting
                return []
            descriptors = []
            for index in range(0, num_descriptors):
                descriptor = device.feature_request(_F.MULTIPLATFORM, 0x10, index)
                platform, _ignore, os_flags, low, high = struct.unpack("!BBHHH", descriptor[:8])
                descriptors.append((platform, os_flags, low, high))
            choices = common.NamedInts()
            for os_name, os_bit in setting_class.OSS:
                for platform, os_flags, low, high in descriptors:
                    os = os_name + _str_os_versions(low, high)
                    if os_bit & os_flags and platform not in choices and os not in choices:
                        choices[platform] = os
            return cls(choices=choices, read_skip_byte_count=6, write_prefix_bytes=b"\xff") if choices else None


class DualPlatform(settings.Setting):
    name = "multiplatform"
    label = _("Set OS")
    description = _("Change keys to match OS.")
    choices_universe = common.NamedInts()
    choices_universe[0x00] = "iOS, MacOS"
    choices_universe[0x01] = "Android, Windows"
    feature = _F.DUALPLATFORM
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x20}
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}


class ChangeHost(settings.Setting):
    name = "change-host"
    label = _("Change Host")
    description = _("Switch connection to a different host")
    persist = False  # persisting this setting is harmful
    feature = _F.CHANGE_HOST
    rw_options = {"read_fnid": 0x00, "write_fnid": 0x10, "no_reply": True}
    choices_universe = common.NamedInts(**{"Host " + str(i + 1): i for i in range(3)})

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            infos = device.feature_request(_F.CHANGE_HOST)
            assert infos, "Oops, host count cannot be retrieved!"
            numHosts, currentHost = struct.unpack("!BB", infos[:2])
            hostNames = _hidpp20.get_host_names(device)
            hostNames = hostNames if hostNames is not None else {}
            if currentHost not in hostNames or hostNames[currentHost][1] == "":
                hostNames[currentHost] = (True, socket.gethostname().partition(".")[0])
            choices = common.NamedInts()
            for host in range(0, numHosts):
                paired, hostName = hostNames.get(host, (True, ""))
                choices[host] = f"{str(host + 1)}:{hostName}" if hostName else str(host + 1)
            return cls(choices=choices, read_skip_byte_count=1) if choices and len(choices) > 1 else None


_GESTURE2_GESTURES_LABELS = {
    GestureId.TAP_1_FINGER: (_("Single tap"), _("Performs a left click.")),
    GestureId.TAP_2_FINGER: (_("Single tap with two fingers"), _("Performs a right click.")),
    GestureId.TAP_3_FINGER: (_("Single tap with three fingers"), None),
    GestureId.CLICK_1_FINGER: (None, None),
    GestureId.CLICK_2_FINGER: (None, None),
    GestureId.CLICK_3_FINGER: (None, None),
    GestureId.DOUBLE_TAP_1_FINGER: (_("Double tap"), _("Performs a double click.")),
    GestureId.DOUBLE_TAP_2_FINGER: (_("Double tap with two fingers"), None),
    GestureId.DOUBLE_TAP_3_FINGER: (_("Double tap with three fingers"), None),
    GestureId.TRACK_1_FINGER: (None, None),
    GestureId.TRACKING_ACCELERATION: (None, None),
    GestureId.TAP_DRAG_1_FINGER: (_("Tap and drag"), _("Drags items by dragging the finger after double tapping.")),
    GestureId.TAP_DRAG_2_FINGER: (
        _("Tap and drag with two fingers"),
        _("Drags items by dragging the fingers after double tapping."),
    ),
    GestureId.DRAG_3_FINGER: (_("Tap and drag with three fingers"), None),
    GestureId.TAP_GESTURES: (None, None),
    GestureId.FN_CLICK_GESTURE_SUPPRESSION: (
        _("Suppress tap and edge gestures"),
        _("Disables tap and edge gestures (equivalent to pressing Fn+LeftClick)."),
    ),
    GestureId.SCROLL_1_FINGER: (_("Scroll with one finger"), _("Scrolls.")),
    GestureId.SCROLL_2_FINGER: (_("Scroll with two fingers"), _("Scrolls.")),
    GestureId.SCROLL_2_FINGER_HORIZONTAL: (_("Scroll horizontally with two fingers"), _("Scrolls horizontally.")),
    GestureId.SCROLL_2_FINGER_VERTICAL: (_("Scroll vertically with two fingers"), _("Scrolls vertically.")),
    GestureId.SCROLL_2_FINGER_STATELESS: (_("Scroll with two fingers"), _("Scrolls.")),
    GestureId.NATURAL_SCROLLING: (_("Natural scrolling"), _("Inverts the scrolling direction.")),
    GestureId.THUMBWHEEL: (_("Thumbwheel"), _("Enables the thumbwheel.")),
    GestureId.V_SCROLL_INTERTIA: (None, None),
    GestureId.V_SCROLL_BALLISTICS: (None, None),
    GestureId.SWIPE_2_FINGER_HORIZONTAL: (None, None),
    GestureId.SWIPE_3_FINGER_HORIZONTAL: (None, None),
    GestureId.SWIPE_4_FINGER_HORIZONTAL: (None, None),
    GestureId.SWIPE_3_FINGER_VERTICAL: (None, None),
    GestureId.SWIPE_4_FINGER_VERTICAL: (None, None),
    GestureId.LEFT_EDGE_SWIPE_1_FINGER: (None, None),
    GestureId.RIGHT_EDGE_SWIPE_1_FINGER: (None, None),
    GestureId.BOTTOM_EDGE_SWIPE_1_FINGER: (None, None),
    GestureId.TOP_EDGE_SWIPE_1_FINGER: (_("Swipe from the top edge"), None),
    GestureId.LEFT_EDGE_SWIPE_1_FINGER_2: (_("Swipe from the left edge"), None),
    GestureId.RIGHT_EDGE_SWIPE_1_FINGER_2: (_("Swipe from the right edge"), None),
    GestureId.BOTTOM_EDGE_SWIPE_1_FINGER_2: (_("Swipe from the bottom edge"), None),
    GestureId.TOP_EDGE_SWIPE_1_FINGER_2: (_("Swipe from the top edge"), None),
    GestureId.LEFT_EDGE_SWIPE_2_FINGER: (_("Swipe two fingers from the left edge"), None),
    GestureId.RIGHT_EDGE_SWIPE_2_FINGER: (_("Swipe two fingers from the right edge"), None),
    GestureId.BOTTOM_EDGE_SWIPE_2_FINGER: (_("Swipe two fingers from the bottom edge"), None),
    GestureId.TOP_EDGE_SWIPE_2_FINGER: (_("Swipe two fingers from the top edge"), None),
    GestureId.ZOOM_2_FINGER: (_("Zoom with two fingers."), _("Pinch to zoom out; spread to zoom in.")),
    GestureId.ZOOM_2_FINGER_PINCH: (_("Pinch to zoom out."), _("Pinch to zoom out.")),
    GestureId.ZOOM_2_FINGER_SPREAD: (_("Spread to zoom in."), _("Spread to zoom in.")),
    GestureId.ZOOM_3_FINGER: (_("Zoom with three fingers."), None),
    GestureId.ZOOM_2_FINGER_STATELESS: (_("Zoom with two fingers"), _("Pinch to zoom out; spread to zoom in.")),
    GestureId.TWO_FINGERS_PRESENT: (None, None),
    GestureId.ROTATE_2_FINGER: (None, None),
    GestureId.FINGER_1: (None, None),
    GestureId.FINGER_2: (None, None),
    GestureId.FINGER_3: (None, None),
    GestureId.FINGER_4: (None, None),
    GestureId.FINGER_5: (None, None),
    GestureId.FINGER_6: (None, None),
    GestureId.FINGER_7: (None, None),
    GestureId.FINGER_8: (None, None),
    GestureId.FINGER_9: (None, None),
    GestureId.FINGER_10: (None, None),
    GestureId.DEVICE_SPECIFIC_RAW_DATA: (None, None),
}

_GESTURE2_PARAMS_LABELS = {
    ParamId.EXTRA_CAPABILITIES: (None, None),  # not supported
    ParamId.PIXEL_ZONE: (_("Pixel zone"), None),  # TO DO: replace None with a short description
    ParamId.RATIO_ZONE: (_("Ratio zone"), None),  # TO DO: replace None with a short description
    ParamId.SCALE_FACTOR: (_("Scale factor"), _("Sets the cursor speed.")),
}

_GESTURE2_PARAMS_LABELS_SUB = {
    "left": (_("Left"), _("Left-most coordinate.")),
    "bottom": (_("Bottom"), _("Bottom coordinate.")),
    "width": (_("Width"), _("Width.")),
    "height": (_("Height"), _("Height.")),
    "scale": (_("Scale"), _("Cursor speed.")),
}


class Gesture2Gestures(settings.BitFieldWithOffsetAndMaskSetting):
    name = "gesture2-gestures"
    label = _("Gestures")
    description = _("Tweak the mouse/touchpad behaviour.")
    feature = _F.GESTURE_2
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_options = {"om_method": hidpp20.Gesture.enable_offset_mask}
    choices_universe = hidpp20_constants.GestureId
    _labels = _GESTURE2_GESTURES_LABELS

    class validator_class(settings_validator.BitFieldWithOffsetAndMaskValidator):
        @classmethod
        def build(cls, setting_class, device, om_method=None):
            options = [g for g in device.gestures.gestures.values() if g.can_be_enabled or g.default_enabled]
            return cls(options, om_method=om_method) if options else None


class Gesture2Divert(settings.BitFieldWithOffsetAndMaskSetting):
    name = "gesture2-divert"
    label = _("Gestures Diversion")
    description = _("Divert mouse/touchpad gestures.")
    feature = _F.GESTURE_2
    rw_options = {"read_fnid": 0x30, "write_fnid": 0x40}
    validator_options = {"om_method": hidpp20.Gesture.diversion_offset_mask}
    choices_universe = hidpp20_constants.GestureId
    _labels = _GESTURE2_GESTURES_LABELS

    class validator_class(settings_validator.BitFieldWithOffsetAndMaskValidator):
        @classmethod
        def build(cls, setting_class, device, om_method=None):
            options = [g for g in device.gestures.gestures.values() if g.can_be_diverted]
            return cls(options, om_method=om_method) if options else None


class Gesture2Params(settings.LongSettings):
    name = "gesture2-params"
    label = _("Gesture params")
    description = _("Change numerical parameters of a mouse/touchpad.")
    feature = _F.GESTURE_2
    rw_options = {"read_fnid": 0x70, "write_fnid": 0x80}
    choices_universe = hidpp20_constants.ParamId
    sub_items_universe = hidpp20.SUB_PARAM
    # item (NamedInt) -> list/tuple of objects that have the following attributes
    # .id (sub-item text), .length (in bytes), .minimum and .maximum

    _labels = _GESTURE2_PARAMS_LABELS
    _labels_sub = _GESTURE2_PARAMS_LABELS_SUB

    class validator_class(settings_validator.MultipleRangeValidator):
        @classmethod
        def build(cls, setting_class, device):
            params = _hidpp20.get_gestures(device).params.values()
            items = [i for i in params if i.sub_params]
            if not items:
                return None
            sub_items = {i: i.sub_params for i in items}
            return cls(items, sub_items)


class MKeyLEDs(settings.BitFieldSetting):
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
    choices_universe = common.NamedInts()
    for i in range(8):
        choices_universe[1 << i] = "M" + str(i + 1)
    _labels = {k: (None, _("Lights up the %s key.") % k) for k in choices_universe}

    class rw_class(settings.FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x10)

        def read(self, device):  # no way to read, so just assume off
            return b"\x00"

    class validator_class(settings_validator.BitFieldValidator):
        @classmethod
        def build(cls, setting_class, device):
            number = device.feature_request(setting_class.feature, 0x00)[0]
            options = [setting_class.choices_universe[1 << i] for i in range(number)]
            return cls(options) if options else None


class MRKeyLED(settings.Setting):
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

    class rw_class(settings.FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, write_fnid=0x00)

        def read(self, device):  # no way to read, so just assume off
            return b"\x00"


## Only implemented for devices that can produce Key and Consumer Codes (e.g., Craft)
## and devices that can produce Key, Mouse, and Horizontal Scroll (e.g., M720)
## Only interested in current host, so use 0xFF for it
class PersistentRemappableAction(settings.Settings):
    name = "persistent-remappable-keys"
    label = _("Persistent Key/Button Mapping")
    description = (
        _("Permanently change the mapping for the key or button.")
        + "\n"
        + _("Changing important keys or buttons (such as for the left mouse button) can result in an unusable system.")
    )
    persist = False  # This setting is persistent in the device so no need to persist it here
    feature = _F.PERSISTENT_REMAPPABLE_ACTION
    keys_universe = special_keys.CONTROL
    choices_universe = special_keys.KEYS

    class rw_class:
        def __init__(self, feature):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device, key):
            ks = device.remap_keys[device.remap_keys.index(key)]
            return b"\x00\x00" + ks.data_bytes

        def write(self, device, key, data_bytes):
            ks = device.remap_keys[device.remap_keys.index(key)]
            v = ks.remap(data_bytes)
            return v

    class validator_class(settings_validator.ChoicesMapValidator):
        @classmethod
        def build(cls, setting_class, device):
            remap_keys = device.remap_keys
            if not remap_keys:
                return None
            capabilities = device.remap_keys.capabilities
            if capabilities & 0x0041 == 0x0041:  # Key and Consumer Codes
                keys = special_keys.KEYS_KEYS_CONSUMER
            elif capabilities & 0x0023 == 0x0023:  # Key, Mouse, and HScroll Codes
                keys = special_keys.KEYS_KEYS_MOUSE_HSCROLL
            else:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: unimplemented Persistent Remappable capability %s", device.name, hex(capabilities))
                return None
            choices = {}
            for k in remap_keys:
                if k is not None:
                    key = special_keys.CONTROL[k.key]
                    choices[key] = keys  # TO RECOVER FROM BAD VALUES use special_keys.KEYS
            return cls(choices, key_byte_count=2, byte_count=4) if choices else None

        def validate_read(self, reply_bytes, key):
            start = self._key_byte_count + self._read_skip_byte_count
            end = start + self._byte_count
            reply_value = common.bytes2int(reply_bytes[start:end]) & self.mask
            # Craft keyboard has a value that isn't valid so fudge these values
            if reply_value not in self.choices[key]:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("unusual persistent remappable action mapping %x: use Default", reply_value)
                reply_value = special_keys.KEYS_Default
            return reply_value


class Sidetone(settings.Setting):
    name = "sidetone"
    label = _("Sidetone")
    description = _("Set sidetone level.")
    feature = _F.SIDETONE
    validator_class = settings_validator.RangeValidator
    min_value = 0
    max_value = 100


class Equalizer(settings.RangeFieldSetting):
    name = "equalizer"
    label = _("Equalizer")
    description = _("Set equalizer levels.")
    feature = _F.EQUALIZER
    rw_options = {"read_fnid": 0x20, "write_fnid": 0x30, "read_prefix": b"\x00"}
    keys_universe = []

    class validator_class(settings_validator.PackedRangeValidator):
        @classmethod
        def build(cls, setting_class, device):
            data = device.feature_request(_F.EQUALIZER, 0x00)
            if not data:
                return None
            count, dbRange, _x, dbMin, dbMax = struct.unpack("!BBBBB", data[:5])
            if dbMin == 0:
                dbMin = -dbRange
            if dbMax == 0:
                dbMax = dbRange
            map = common.NamedInts()
            for g in range((count + 6) // 7):
                freqs = device.feature_request(_F.EQUALIZER, 0x10, g * 7)
                for b in range(7):
                    if g * 7 + b >= count:
                        break
                    map[g * 7 + b] = str(int.from_bytes(freqs[2 * b + 1 : 2 * b + 3], "big")) + _("Hz")
            return cls(map, min_value=dbMin, max_value=dbMax, count=count, write_prefix_bytes=b"\x02")


class ADCPower(settings.Setting):
    name = "adc_power_management"
    label = _("Power Management")
    description = _("Power off in minutes (0 for never).")
    feature = _F.ADC_MEASUREMENT
    min_version = 2  # documentation for version 1 does not mention this capability
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_class = settings_validator.RangeValidator
    min_value = 0x00
    max_value = 0xFF
    validator_options = {"byte_count": 1}


class BrightnessControl(settings.Setting):
    name = "brightness_control"
    label = _("Brightness Control")
    description = _("Control overall brightness")
    feature = _F.BRIGHTNESS_CONTROL
    rw_options = {"read_fnid": 0x10, "write_fnid": 0x20}
    validator_class = settings_validator.RangeValidator

    def __init__(self, device, rw, validator):
        super().__init__(device, rw, validator)
        rw.on_off = validator.on_off
        rw.min_nonzero_value = validator.min_value
        validator.min_value = 0 if validator.on_off else validator.min_value

    class rw_class(settings.FeatureRW):
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

    class validator_class(settings_validator.RangeValidator):
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


class LEDControl(settings.Setting):
    name = "led_control"
    label = _("LED Control")
    description = _("Switch control of LED zones between device and Solaar")
    feature = _F.COLOR_LED_EFFECTS
    rw_options = {"read_fnid": 0x70, "write_fnid": 0x80}
    choices_universe = common.NamedInts(Device=0, Solaar=1)
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}


colors = special_keys.COLORS
_LEDP = hidpp20.LEDParam


# an LED Zone has an index, a set of possible LED effects, and an LED effect setting
class LEDZoneSetting(settings.Setting):
    name = "led_zone_"  # the trailing underscore signals that this setting creates other settings
    label = _("LED Zone Effects")
    description = _("Set effect for LED Zone") + "\n" + _("LED Control needs to be set to Solaar to be effective.")
    feature = _F.COLOR_LED_EFFECTS
    color_field = {"name": _LEDP.color, "kind": settings.Kind.COLOR, "label": _("Color")}
    speed_field = {"name": _LEDP.speed, "kind": settings.Kind.RANGE, "label": _("Speed"), "min": 0, "max": 255}
    period_field = {"name": _LEDP.period, "kind": settings.Kind.RANGE, "label": _("Period"), "min": 100, "max": 5000}
    intensity_field = {"name": _LEDP.intensity, "kind": settings.Kind.RANGE, "label": _("Intensity"), "min": 0, "max": 100}
    ramp_field = {"name": _LEDP.ramp, "kind": settings.Kind.CHOICE, "label": _("Ramp"), "choices": hidpp20.LedRampChoice}
    possible_fields = [color_field, speed_field, period_field, intensity_field, ramp_field]

    @classmethod
    def setup(cls, device, read_fnid, write_fnid, suffix):
        infos = device.led_effects
        settings_ = []
        for zone in infos.zones:
            prefix = common.int2bytes(zone.index, 1)
            rw = settings.FeatureRW(cls.feature, read_fnid, write_fnid, prefix=prefix, suffix=suffix)
            validator = settings_validator.HeteroValidator(
                data_class=hidpp20.LEDEffectSetting, options=zone.effects, readable=infos.readable and read_fnid is not None
            )
            setting = cls(device, rw, validator)
            setting.name = cls.name + str(int(zone.location))
            setting.label = _("LEDs") + " " + str(hidpp20.LEDZoneLocations[zone.location])
            choices = [hidpp20.LEDEffects[e.ID][0] for e in zone.effects if e.ID in hidpp20.LEDEffects]
            ID_field = {"name": "ID", "kind": settings.Kind.CHOICE, "label": None, "choices": choices}
            setting.possible_fields = [ID_field] + cls.possible_fields
            setting.fields_map = hidpp20.LEDEffects
            settings_.append(setting)
        return settings_

    @classmethod
    def build(cls, device):
        return cls.setup(device, 0xE0, 0x30, b"")


class RGBControl(settings.Setting):
    name = "rgb_control"
    label = _("LED Control")
    description = _("Switch control of LED zones between device and Solaar")
    feature = _F.RGB_EFFECTS
    rw_options = {"read_fnid": 0x50, "write_fnid": 0x50}
    choices_universe = common.NamedInts(Device=0, Solaar=1)
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe, "write_prefix_bytes": b"\x01", "read_skip_byte_count": 1}

    def write(self, value, save=True):
        assert hasattr(self, "_value")
        assert hasattr(self, "_device")
        assert value is not None
        device = self._device
        if not device.online:
            return None
        if self._value != value:
            self.update(value, save)
        claiming = int(value) == 1  # Solaar
        if claiming:
            self._claim_sw_control(device)
        else:
            self._release_sw_control(device)
        return value

    def _claim_sw_control(self, device):
        # Disable firmware power management via profile management or onboard profiles
        if device.features and _F.PROFILE_MANAGEMENT in device.features:
            device.feature_request(_F.PROFILE_MANAGEMENT, 0x60, b"\x05")
        elif device.features and _F.ONBOARD_PROFILES in device.features:
            device.feature_request(_F.ONBOARD_PROFILES, 0x10, b"\x02")
        # Claim LED pipeline: SetSWControl(mode=3, flags=5)
        device.feature_request(_F.RGB_EFFECTS, 0x50, b"\x01\x03\x05")
        # Start software power management
        _rgb_power_manager_start(device)
        # Register cleanup for graceful release on device close
        if _rgb_cleanup not in device.cleanups:
            device.cleanups.append(_rgb_cleanup)

    def _release_sw_control(self, device):
        # Stop software power management
        _rgb_power_manager_stop(device)
        # Release LED pipeline: SetSWControl(mode=0, flags=0)
        device.feature_request(_F.RGB_EFFECTS, 0x50, b"\x01\x00\x00")
        # Restore firmware power management
        if device.features and _F.PROFILE_MANAGEMENT in device.features:
            device.feature_request(_F.PROFILE_MANAGEMENT, 0x60, b"\x03")
        elif device.features and _F.ONBOARD_PROFILES in device.features:
            device.feature_request(_F.ONBOARD_PROFILES, 0x10, b"\x01")
        if _rgb_cleanup in device.cleanups:
            device.cleanups.remove(_rgb_cleanup)


class RGBIdleTimeout(settings.Setting):
    name = "rgb_idle_timeout"
    label = _("LED Idle Timeout")
    description = (
        _("Time without input before LED idle effect starts.")
        + "\n"
        + _("LED Control needs to be set to Solaar to be effective.")
    )
    feature = _F.RGB_EFFECTS
    choices_universe = common.NamedInts(
        **{
            "Disabled": 0,
            "15 Seconds": 15,
            "30 Seconds": 30,
            "1 Minute": 60,
            "2 Minutes": 120,
            "5 Minutes": 300,
        }
    )
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}

    class rw_class:
        def __init__(self, feature, **kwargs):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device):
            return common.int2bytes(60, 2)  # default 1 minute

        def write(self, device, data_bytes):
            timeout = int.from_bytes(data_bytes, byteorder="big")
            mgr = _rgb_power_managers.get(id(device))
            if mgr:
                mgr.set_idle_timeout(timeout)
            return True


class RGBIdleEffect(settings.Setting):
    name = "rgb_idle_effect"
    label = _("LED Idle Effect")
    description = (
        _("What happens to LEDs when idle — dim to a percentage or play an animation.")
        + "\n"
        + _("LED Control needs to be set to Solaar to be effective.")
    )
    feature = _F.RGB_EFFECTS
    validator_class = settings_validator.ChoicesValidator

    class rw_class:
        def __init__(self, feature, **kwargs):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device):
            return common.int2bytes(50, 1)  # default Dim 50%

        def write(self, device, data_bytes):
            effect = int.from_bytes(data_bytes, byteorder="big")
            mgr = _rgb_power_managers.get(id(device))
            if mgr:
                mgr.set_idle_effect(effect)
            return True

    @classmethod
    def build(cls, device):
        rw = cls.rw_class(cls.feature)
        choices = common.NamedInts()
        choices[0] = _("Disabled")
        choices[25] = _("Dim to 25%")
        choices[50] = _("Dim to 50%")
        choices[75] = _("Dim to 75%")
        try:
            infos = device.led_effects
            if infos and infos.zones:
                for e in infos.zones[0].effects:
                    if e.ID == 0x0A and 0x0A not in choices:
                        choices[0x0A] = _("Breathe")
                    elif e.ID == 0x0B and 0x0B not in choices:
                        choices[0x0B] = _("Ripple")
        except Exception:
            pass
        validator = settings_validator.ChoicesValidator(choices=choices)
        return cls(device, rw, validator)


class RGBSleepTimeout(settings.Setting):
    name = "rgb_sleep_timeout"
    label = _("LED Sleep Timeout")
    description = (
        _("Time without input before LEDs fade off completely.")
        + "\n"
        + _("LED Control needs to be set to Solaar to be effective.")
    )
    feature = _F.RGB_EFFECTS
    choices_universe = common.NamedInts(
        **{
            "Disabled": 0,
            "2 Minutes": 120,
            "5 Minutes": 300,
            "10 Minutes": 600,
            "15 Minutes": 900,
            "30 Minutes": 1800,
        }
    )
    validator_class = settings_validator.ChoicesValidator
    validator_options = {"choices": choices_universe}

    class rw_class:
        def __init__(self, feature, **kwargs):
            self.feature = feature
            self.kind = settings.FeatureRW.kind

        def read(self, device):
            return common.int2bytes(300, 2)  # default 5 minutes

        def write(self, device, data_bytes):
            timeout = int.from_bytes(data_bytes, byteorder="big")
            mgr = _rgb_power_managers.get(id(device))
            if mgr:
                mgr.set_sleep_timeout(timeout)
            return True


def _rgb_cleanup(device):
    """Cleanup handler called when device is closed — restores firmware control."""
    _rgb_power_manager_stop(device)
    try:
        device.feature_request(_F.RGB_EFFECTS, 0x50, b"\x01\x00\x00")
        if device.features and _F.PROFILE_MANAGEMENT in device.features:
            device.feature_request(_F.PROFILE_MANAGEMENT, 0x60, b"\x03")
        elif device.features and _F.ONBOARD_PROFILES in device.features:
            device.feature_request(_F.ONBOARD_PROFILES, 0x10, b"\x01")
    except Exception:
        pass  # Device may already be offline


# --- RGB Software Power Management ---

_rgb_power_managers = {}  # keyed by id(device)


def _rgb_on_user_activity(device, activity_type):
    """Dispatch firmware onUserActivity events to the power manager."""
    mgr = _rgb_power_managers.get(id(device))
    if mgr:
        mgr.on_user_activity(activity_type)


def _rgb_power_manager_start(device):
    if not _has_glib:
        return
    key = id(device)
    if key not in _rgb_power_managers:
        mgr = RGBPowerManager(device)
        _rgb_power_managers[key] = mgr
        mgr.start()
        # Apply persisted settings
        for s in device.settings:
            if s.name == "rgb_idle_timeout":
                val = s._value if s._value is not None else 60
                mgr.set_idle_timeout(int(val))
            elif s.name == "rgb_sleep_timeout":
                val = s._value if s._value is not None else 300
                mgr.set_sleep_timeout(int(val))
            elif s.name == "rgb_idle_effect":
                val = s._value if s._value is not None else 50
                mgr.set_idle_effect(int(val))


def _rgb_power_manager_stop(device):
    key = id(device)
    mgr = _rgb_power_managers.pop(key, None)
    if mgr:
        mgr.stop()


class RGBPowerManager:
    """Manages LED idle/sleep states using firmware onUserActivity events from RGB_EFFECTS (0x8071).

    The firmware handles idle detection via SetSWControl flags:
      - flags=5 (ZONE|EFFECT): firmware monitors for inactivity, sends IDLE event at idle_timeout
      - flags=3 (ZONE|POWER): firmware monitors for activity, sends ACTIVE event on keypress

    Two-stage idle behavior matching LGHUB:
      Stage 1 — Idle Effect: Smooth dim ramp or firmware animation (triggered by firmware IDLE event).
      Stage 2 — Sleep: Firmware fade-to-off (software timer: sleep_timeout - idle_timeout after IDLE).

    State machine: ACTIVE → DIMMING → IDLE → SLEEPING
    """

    ACTIVE = 0
    DIMMING = 1
    IDLE = 2
    SLEEPING = 3

    _DIM_INTERVAL_MS = 200  # milliseconds between dim ramp steps
    _DIM_STEPS = 25  # total steps for ~5s dim ramp

    def __init__(self, device):
        self._device = device
        self._state = self.ACTIVE
        # Settings (overridden from persisted values via _rgb_power_manager_start)
        self._idle_timeout = 60  # seconds — firmware idle detection threshold
        self._sleep_timeout = 300  # seconds — total time before sleep (0=disabled)
        self._idle_effect = 50  # 0=disabled, 25/50/75=dim%, 0x0A/0x0B=animation
        # Timers
        self._sleep_timer_id = None  # software sleep timer (fires sleep_timeout - idle_timeout after IDLE)
        self._dim_timer_id = None  # dim ramp animation timer
        self._dim_step = 0
        self._dim_zones = []  # list of (zone, start_color, target_color)
        self._dim_perkey = None  # dict of {zone_id: (start_color, target_color)} or None

    def start(self):
        self._state = self.ACTIVE
        self._read_firmware_timers()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: RGB power manager started (firmware idle=%ds, sleep=%ds)",
                self._device,
                self._idle_timeout,
                self._sleep_timeout,
            )

    def stop(self):
        self._cancel_dim_timer()
        self._cancel_sleep_timer()
        if self._state != self.ACTIVE:
            try:
                self._wake()
            except Exception:
                pass  # Best effort during shutdown
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB power manager stopped", self._device)

    def set_idle_timeout(self, seconds):
        """Update the idle timeout — also writes to firmware so it fires IDLE at the right time."""
        self._idle_timeout = seconds
        self._cancel_sleep_timer()
        if seconds == 0 and self._state in (self.DIMMING, self.IDLE):
            self._wake()
        self._write_firmware_idle_timeout(seconds)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB idle timeout set to %ss", self._device, seconds)

    def set_sleep_timeout(self, seconds):
        """Update the sleep timeout (stage 2). 0 disables sleep."""
        self._sleep_timeout = seconds
        self._cancel_sleep_timer()
        if seconds == 0 and self._state == self.SLEEPING:
            self._wake()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB sleep timeout set to %ss", self._device, seconds)

    def set_idle_effect(self, effect):
        """Update the idle effect type. 0=disabled, 25/50/75=dim%, 0x0A/0x0B=animation."""
        self._idle_effect = effect
        if effect == 0 and self._state in (self.DIMMING, self.IDLE):
            self._wake()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB idle effect set to %s", self._device, effect)

    # --- Firmware activity events ---

    def on_user_activity(self, activity_type):
        """Handle firmware onUserActivity event from RGB_EFFECTS (0x8071).

        activity_type=0: IDLE — user stopped typing, firmware idle timer expired.
        activity_type!=0: ACTIVE — user resumed typing after being idle.

        The firmware sends a burst of ~8 events with exponential backoff.
        Only the first event matters; subsequent events for the same transition are ignored.
        """
        if not self._device.online:
            return

        if activity_type == 0:
            # IDLE event — firmware detected inactivity at idle_timeout
            if self._state != self.ACTIVE:
                return  # Already idle/dimming/sleeping, ignore burst
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: firmware IDLE event — starting idle sequence", self._device)
            # Start idle effect (dim/animation) if enabled
            idle_enabled = self._idle_effect != 0 and self._idle_timeout > 0
            if idle_enabled:
                self._start_idle_effect()
            else:
                self._state = self.IDLE
            # Schedule software sleep timer
            sleep_enabled = self._sleep_timeout > 0
            if sleep_enabled:
                delay = max(self._sleep_timeout - self._idle_timeout, 0)
                if delay == 0:
                    self._start_sleep()
                else:
                    self._sleep_timer_id = GLib.timeout_add_seconds(delay, self._sleep_timer_fired)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("%s: sleep timer scheduled in %ds", self._device, delay)
        else:
            # ACTIVE event — user resumed typing
            if self._state == self.ACTIVE:
                return  # Already active, ignore burst
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: firmware ACTIVE event — waking", self._device)
            self._cancel_sleep_timer()
            self._wake()

    def _sleep_timer_fired(self):
        """GLib callback — software sleep timer expired after IDLE."""
        self._sleep_timer_id = None
        if self._state in (self.IDLE, self.DIMMING) and self._device.online:
            self._start_sleep()
        return False  # One-shot timer

    def _cancel_sleep_timer(self):
        if self._sleep_timer_id is not None:
            GLib.source_remove(self._sleep_timer_id)
            self._sleep_timer_id = None

    def _read_firmware_timers(self):
        """Read idle/sleep timeouts from firmware via GetRgbPowerModeConfig.

        These serve as defaults; persisted user settings may override them.
        """
        try:
            # GetRgbPowerModeConfig: function 7, sub-function 0x00 (get)
            resp = self._device.feature_request(_F.RGB_EFFECTS, 0x70, b"\x00")
            if resp and len(resp) >= 5:
                # Response: [0]=echo(0x00), [1:3]=idle_timeout_s, [3:5]=sleep_timeout_s
                idle_s = (resp[1] << 8) | resp[2]
                sleep_s = (resp[3] << 8) | resp[4]
                if idle_s > 0:
                    self._idle_timeout = idle_s
                if sleep_s > 0:
                    self._sleep_timeout = sleep_s
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "%s: firmware timers: idle=%ds, sleep=%ds",
                        self._device,
                        idle_s,
                        sleep_s,
                    )
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: could not read firmware timers, using defaults: %s", self._device, e)

    def _write_firmware_idle_timeout(self, seconds):
        """Write idle timeout to firmware so it fires IDLE events at the right time."""
        try:
            idle_hi = (seconds >> 8) & 0xFF
            idle_lo = seconds & 0xFF
            sleep_hi = (self._sleep_timeout >> 8) & 0xFF
            sleep_lo = self._sleep_timeout & 0xFF
            # SetRgbPowerModeConfig: function 7, sub-function 0x01 (set)
            self._device.feature_request(_F.RGB_EFFECTS, 0x70, bytes([0x01, idle_hi, idle_lo, sleep_hi, sleep_lo]))
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: could not write firmware idle timeout: %s", self._device, e)

    # --- Idle effect ---

    def _start_idle_effect(self):
        """Begin the idle effect based on _idle_effect setting."""
        if self._idle_effect in (25, 50, 75):
            self._start_dim_ramp(self._idle_effect)
        elif self._idle_effect in (0x0A, 0x0B):
            self._apply_animation(self._idle_effect)

    def _start_dim_ramp(self, dim_pct):
        """Start a smooth ~5s dim ramp to the target brightness percentage.

        When per-key lighting is active, the per-key layer completely masks zone
        effects (confirmed on G515). In that case, ALL dimming goes through 0x8081
        per-key writes and zone dimming is skipped entirely.
        """
        infos = getattr(self._device, "led_effects", None)
        if not infos or not infos.zones:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: dim ramp skipped — no led_effects/zones", self._device)
            self._state = self.IDLE
            return

        # Check if per-key lighting is active with real colors — it completely masks zone effects
        perkey_setting = self._find_perkey_setting()
        perkey_active = (
            perkey_setting is not None
            and self._has_perkey_zones(perkey_setting)
            and self._has_real_perkey_colors(perkey_setting)
        )

        self._dim_perkey = None
        if perkey_active:
            # Per-key masks zones: dim ALL per-key zones, skip zone dimming
            self._dim_zones = []
            self._dim_perkey = self._build_full_perkey_dim_map(perkey_setting, dim_pct)
            if self._dim_perkey:
                # Push zone base color to unset keys before dimming starts,
                # so they show the correct color instead of white/stale values
                self._init_unset_perkey_zones(perkey_setting)
        else:
            # No per-key active: dim via zone effects (original behavior)
            self._dim_zones = []
            for zone in infos.zones:
                effect_ids = [e.ID for e in zone.effects]
                if 0x01 in effect_ids:  # Zone supports Static
                    start_color = self._get_zone_color(zone)
                    target_color = self._compute_dim_color(start_color, dim_pct)
                    self._dim_zones.append((zone, start_color, target_color))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "%s: dim zone %s (loc %s): start=#%06x target=#%06x, effects=%s",
                            self._device,
                            zone.index,
                            zone.location,
                            start_color,
                            target_color,
                            effect_ids,
                        )
                elif logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "%s: dim zone %s skipped — no Static (0x01) in effects=%s",
                        self._device,
                        zone.index,
                        effect_ids,
                    )

        if not self._dim_zones and not self._dim_perkey:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: dim ramp skipped — no zones or per-key colors to dim", self._device)
            self._state = self.IDLE
            return
        self._dim_step = 0
        self._state = self.DIMMING
        self._dim_timer_id = GLib.timeout_add(self._DIM_INTERVAL_MS, self._dim_ramp_step)
        if logger.isEnabledFor(logging.DEBUG):
            n_zones = len(self._dim_zones)
            n_perkey = len(self._dim_perkey) if self._dim_perkey else 0
            logger.debug(
                "%s: starting dim ramp to %d%% brightness (%d zones, %d per-key%s)",
                self._device,
                dim_pct,
                n_zones,
                n_perkey,
                ", per-key masking zones" if perkey_active else "",
            )

    def _dim_ramp_step(self):
        """GLib callback — one step of the smooth dim animation."""
        if self._state != self.DIMMING or not self._device.online:
            self._dim_timer_id = None
            return False  # Cancelled or device offline
        self._dim_step += 1
        t = self._dim_step / self._DIM_STEPS
        for zone, start_color, target_color in self._dim_zones:
            color = self._interpolate_color(start_color, target_color, t)
            try:
                self._push_static_effect(zone, color)
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: dim ramp step failed for zone %s: %s", self._device, zone.index, e)
        # Also dim per-key colors
        if self._dim_perkey:
            try:
                self._push_perkey_dimmed(t)
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: dim ramp step failed for per-key: %s", self._device, e)
        if self._dim_step >= self._DIM_STEPS:
            # Dim complete — release effect control to firmware to hold the dim level
            try:
                self._device.feature_request(_F.RGB_EFFECTS, 0x50, b"\x01\x03\x03")
            except Exception:
                pass
            self._state = self.IDLE
            self._dim_timer_id = None
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: dim ramp complete, entering idle state", self._device)
            return False  # Stop timer
        return True  # Continue timer

    def _push_static_effect(self, zone, color):
        """Send a non-persistent Static effect with the given color to a zone."""
        # Find the Static effect's device-reported index (not list position)
        static_effect = None
        for e in zone.effects:
            if e.ID == 0x01:
                static_effect = e
                break
        if static_effect is None:
            return
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        # SetEffectByIndex: zone(1) + effect_idx(1) + params(10) + persist(1)
        # Static params: color(3, @0) + ramp(1, @3) + pad(6)
        params = bytes([r, g, b, 0, 0, 0, 0, 0, 0, 0])
        payload = bytes([zone.index, static_effect.index]) + params + b"\x01"
        self._device.feature_request(_F.RGB_EFFECTS, 0x10, payload)

    def _push_perkey_dimmed(self, t):
        """Push interpolated per-key colors for one dim ramp step.

        Groups keys by their interpolated color and uses SetRgbZonesSingleValue
        (0x8081 function 6) for efficient bulk writes — up to 13 zone IDs per
        HID message when multiple keys share the same dimmed color.
        """
        # Build color -> [zone_ids] map for this interpolation step
        color_groups = {}
        for zone_id, (start_color, target_color) in self._dim_perkey.items():
            color = self._interpolate_color(start_color, target_color, t)
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(zone_id)

        feat = _F.PER_KEY_LIGHTING_V2
        for color, zone_ids in color_groups.items():
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            # Function 6: SetRgbZonesSingleValue — color(3) + zone_ids (up to 13 per report)
            while zone_ids:
                batch = zone_ids[:13]
                zone_ids = zone_ids[13:]
                data = bytes([r, g, b]) + bytes(batch)
                self._device.feature_request(feat, 0x60, data)
        # Commit the frame
        self._device.feature_request(feat, 0x70, b"\x00\x00\x00\x00\x00")

    def _apply_animation(self, effect_id):
        """Switch to a firmware-handled animation (Breathe/Ripple) for idle effect."""
        infos = getattr(self._device, "led_effects", None)
        if not infos or not infos.zones:
            self._state = self.IDLE
            return
        for zone in infos.zones:
            color = self._get_zone_color(zone)
            r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
            effect_info = None
            for e in zone.effects:
                if e.ID == effect_id:
                    effect_info = e
                    break
            if effect_info is None:
                continue
            period = effect_info.period or 3000
            period_hi, period_lo = (period >> 8) & 0xFF, period & 0xFF
            if effect_id == 0x0A:  # Breathe: color(3,@0) + period(2,@3) + form(1,@5) + intensity(1,@6)
                params = bytes([r, g, b, period_hi, period_lo, 0, 100, 0, 0, 0])
            elif effect_id == 0x0B:  # Ripple: color(3,@0) + period(2,@4)
                params = bytes([r, g, b, 0, period_hi, period_lo, 0, 0, 0, 0])
            else:
                continue
            payload = bytes([zone.index, effect_info.index]) + params + b"\x01"
            try:
                self._device.feature_request(_F.RGB_EFFECTS, 0x10, payload)
            except Exception as exc:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning(
                        "%s: failed to apply animation 0x%02x to zone %d: %s",
                        self._device,
                        effect_id,
                        zone.index,
                        exc,
                    )
        # Release to firmware for animation playback
        try:
            self._device.feature_request(_F.RGB_EFFECTS, 0x50, b"\x01\x03\x03")
        except Exception:
            pass
        self._state = self.IDLE
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: applied animation idle effect 0x%02x", self._device, effect_id)

    # --- Sleep ---

    def _start_sleep(self):
        """Enter low-power sleep via firmware power mode command.

        The firmware fade handles its own smooth dim from whatever the
        current brightness level is, so no need to snap to zero first.
        """
        self._cancel_dim_timer()
        try:
            self._device.feature_request(_F.RGB_EFFECTS, 0x80, b"\x01\x03\x00")
            self._state = self.SLEEPING
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: RGB entering sleep (firmware power-down)", self._device)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: failed to enter RGB sleep: %s", self._device, e)

    # --- Wake ---

    def _wake(self):
        """Restore full lighting from any non-ACTIVE state."""
        if self._state == self.ACTIVE:
            return
        prev_state = self._state
        self._cancel_dim_timer()
        self._cancel_sleep_timer()
        try:
            if prev_state == self.SLEEPING:
                self._set_power_mode_with_retry(1)
            # Re-claim full LED pipeline control
            self._device.feature_request(_F.RGB_EFFECTS, 0x50, b"\x01\x03\x05")
            self._restore_colors()
            self._state = self.ACTIVE
            if logger.isEnabledFor(logging.DEBUG):
                state_names = {self.DIMMING: "dimming", self.IDLE: "idle", self.SLEEPING: "sleep"}
                logger.debug("%s: RGB woken from %s", self._device, state_names.get(prev_state, "unknown"))
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: failed to wake RGB LEDs: %s", self._device, e)

    # --- Helpers ---

    def _cancel_dim_timer(self):
        """Cancel any in-progress dim ramp timer."""
        if self._dim_timer_id is not None:
            GLib.source_remove(self._dim_timer_id)
            self._dim_timer_id = None

    def _get_zone_color(self, zone):
        """Get the current color for a zone from cached settings."""
        location = int(zone.location)
        setting_name = f"rgb_zone_{location}"
        for s in self._device.settings:
            if s.name == setting_name and s._value is not None:
                return getattr(s._value, "color", 0xFFFFFF)
        return 0xFFFFFF  # fallback to white

    def _get_zone_base_color(self):
        """Get the primary zone effect color (used as base for unset per-key zones)."""
        for s in self._device.settings:
            if s.name.startswith("rgb_zone_") and s._value is not None:
                color = getattr(s._value, "color", None)
                if color is not None:
                    return color
        return 0xFFFFFF  # fallback to white

    def _find_perkey_setting(self):
        """Find the per-key-lighting setting, or None."""
        for s in self._device.settings:
            if s.name == "per-key-lighting" and s._value is not None:
                return s
        return None

    @staticmethod
    def _has_perkey_zones(perkey_setting):
        """Check if the per-key setting has a valid zone map from its validator."""
        return (
            hasattr(perkey_setting, "_validator")
            and perkey_setting._validator is not None
            and hasattr(perkey_setting._validator, "choices")
            and len(perkey_setting._validator.choices) > 0
        )

    @staticmethod
    def _has_real_perkey_colors(perkey_setting):
        """Check if any per-key zones have actual colors (not just 'No change')."""
        if not perkey_setting._value:
            return False
        no_change = special_keys.COLORSPLUS["No change"]
        return any(color != no_change and isinstance(color, int) and color >= 0 for color in perkey_setting._value.values())

    def _build_full_perkey_dim_map(self, perkey_setting, dim_pct):
        """Build a dim map for ALL per-key zones (user-set and unset).

        User-set keys dim from their set color. Unset keys dim from the zone
        base color. Returns dict of {zone_id: (start_color, target_color)}.
        """
        no_change = special_keys.COLORSPLUS["No change"]
        zone_base = self._get_zone_base_color()

        # Build lookup of user-set colors
        user_colors = {}
        for key, color in perkey_setting._value.items():
            if color != no_change and isinstance(color, int) and color >= 0:
                user_colors[int(key)] = color

        # Build dim map for ALL zones
        perkey = {}
        for key in perkey_setting._validator.choices:
            zone_id = int(key)
            start_color = user_colors.get(zone_id, zone_base)
            target = self._compute_dim_color(start_color, dim_pct)
            perkey[zone_id] = (start_color, target)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: per-key dim map: %d total zones (%d user-set, %d zone-base #%06x)",
                self._device,
                len(perkey),
                len(user_colors),
                len(perkey) - len(user_colors),
                zone_base,
            )
        return perkey

    def _init_unset_perkey_zones(self, perkey_setting):
        """Push the zone base color to all per-key zones not explicitly set by the user.

        This fixes the 'white default' problem: when per-key is activated, unset
        zones default to white in the device's frame buffer. This method sets
        them to the zone effect color instead, so the keyboard looks consistent.
        """
        no_change = special_keys.COLORSPLUS["No change"]
        zone_base = self._get_zone_base_color()
        r = (zone_base >> 16) & 0xFF
        g = (zone_base >> 8) & 0xFF
        b = zone_base & 0xFF

        # Collect zone IDs that the user hasn't explicitly set
        user_set = set()
        for key, color in perkey_setting._value.items():
            if color != no_change and isinstance(color, int) and color >= 0:
                user_set.add(int(key))

        unset_zones = [int(k) for k in perkey_setting._validator.choices if int(k) not in user_set]
        if not unset_zones:
            return

        feat = _F.PER_KEY_LIGHTING_V2
        remaining = list(unset_zones)
        while remaining:
            batch = remaining[:13]
            remaining = remaining[13:]
            data = bytes([r, g, b]) + bytes(batch)
            self._device.feature_request(feat, 0x60, data)
        self._device.feature_request(feat, 0x70, b"\x00\x00\x00\x00\x00")

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: initialized %d unset per-key zones to base color #%06x",
                self._device,
                len(unset_zones),
                zone_base,
            )

    @staticmethod
    def _compute_dim_color(color, dim_pct):
        """Compute the dimmed color (dim_pct is target brightness percentage)."""
        r = ((color >> 16) & 0xFF) * dim_pct // 100
        g = ((color >> 8) & 0xFF) * dim_pct // 100
        b = (color & 0xFF) * dim_pct // 100
        return (r << 16) | (g << 8) | b

    @staticmethod
    def _interpolate_color(start, target, t):
        """Linearly interpolate between two RGB colors. t in [0, 1]."""
        r_s, g_s, b_s = (start >> 16) & 0xFF, (start >> 8) & 0xFF, start & 0xFF
        r_t, g_t, b_t = (target >> 16) & 0xFF, (target >> 8) & 0xFF, target & 0xFF
        r = int(r_s + (r_t - r_s) * t)
        g = int(g_s + (g_t - g_s) * t)
        b = int(b_s + (b_t - b_s) * t)
        return (r << 16) | (g << 8) | b

    def _set_power_mode_with_retry(self, mode):
        """Set RGB power mode with retry — first command after wake may fail."""
        params = bytes([0x01, mode, 0x00])
        for attempt in range(3):
            try:
                self._device.feature_request(_F.RGB_EFFECTS, 0x80, params)
                return
            except Exception:
                if attempt == 2:
                    raise
                import time as _time

                _time.sleep(0.1)

    def _restore_colors(self):
        """Re-push cached lighting state after waking.

        When per-key lighting is active, it completely masks zone effects.
        Zone writes via 0x8071 are skipped to avoid a visible flash (the zone
        write would briefly show the base color before per-key overwrites it).
        PerKeyLighting.write() fills unset zones with the zone base color
        before its FrameEnd, so the entire keyboard restores atomically.
        """
        perkey_setting = self._find_perkey_setting()
        has_perkey = (
            perkey_setting is not None
            and self._has_perkey_zones(perkey_setting)
            and self._has_real_perkey_colors(perkey_setting)
        )
        for s in self._device.settings:
            if s._value is None:
                continue
            if s.name == "per-key-lighting":
                pass  # always restore per-key
            elif s.name.startswith("rgb_zone_"):
                if has_perkey:
                    continue  # skip zone writes — invisible and causes flash
            else:
                continue
            try:
                s.write(s._value, save=False)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: restored %s after wake", self._device, s.name)
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: failed to restore %s: %s", self._device, s.name, e)


class RGBEffectSetting(LEDZoneSetting):
    name = "rgb_zone_"  # the trailing underscore signals that this setting creates other settings
    label = _("LED Zone Effects")
    description = _("Set effect for LED Zone") + "\n" + _("LED Control needs to be set to Solaar to be effective.")
    feature = _F.RGB_EFFECTS

    @classmethod
    def build(cls, device):
        return cls.setup(device, None, 0x10, b"\x01")


class PerKeyLighting(settings.Settings):
    name = "per-key-lighting"
    label = _("Per-key Lighting")
    description = _("Control per-key lighting.")
    feature = _F.PER_KEY_LIGHTING_V2
    keys_universe = special_keys.KEYCODES
    choices_universe = special_keys.COLORSPLUS

    def _ensure_sw_control(self):
        """Ensure SW control is claimed before writing per-key colors."""
        if getattr(self, "_has_rgb_effects", None) is None:
            self._has_rgb_effects = bool(self._device.features and _F.RGB_EFFECTS in self._device.features)
        if not self._has_rgb_effects:
            return  # No autonomous effect engine, no claim needed
        for s in self._device.settings:
            if s.name == "rgb_control":
                if s._value != 1:  # Not already claimed by Solaar
                    s.write(1)  # Triggers full claim sequence in RGBControl
                return

    def _fill_unset_zones_with_base_color(self):
        """Set all unset per-key zones to the zone effect base color.

        The per-key layer completely masks zone effects on devices like the G515.
        When per-key is activated, unset zones default to white (0xFF,0xFF,0xFF)
        in the device's frame buffer. This pushes the zone base color to all
        zones not explicitly set by the user, so the keyboard looks consistent.

        Called after writing per-key colors. Skips the FrameEnd — the caller's
        FrameEnd commits both the user's colors and these base fills together.
        """
        if not self._has_rgb_effects:
            return  # No zone effects, nothing to fill from
        no_change = special_keys.COLORSPLUS["No change"]
        # Get zone base color from rgb_zone_* settings
        zone_base = 0xFFFFFF
        for s in self._device.settings:
            if s.name.startswith("rgb_zone_") and s._value is not None:
                color = getattr(s._value, "color", None)
                if color is not None:
                    zone_base = color
                    break
        r = (zone_base >> 16) & 0xFF
        g = (zone_base >> 8) & 0xFF
        b = zone_base & 0xFF
        # Collect unset zone IDs
        user_set = set()
        if self._value:
            for key, color in self._value.items():
                if color != no_change and isinstance(color, int) and color >= 0:
                    user_set.add(int(key))
        unset_zones = [int(k) for k in self._validator.choices if int(k) not in user_set]
        if not unset_zones:
            return
        # Bulk write using SetRgbZonesSingleValue (function 6)
        remaining = list(unset_zones)
        while remaining:
            batch = remaining[:13]
            remaining = remaining[13:]
            data = bytes([r, g, b]) + bytes(batch)
            self._device.feature_request(self.feature, 0x60, data)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: filled %d unset per-key zones with base color #%06x",
                self._device,
                len(unset_zones),
                zone_base,
            )

    def read(self, cached=True):
        self._pre_read(cached)
        if cached and self._value is not None:
            return self._value
        reply_map = {}
        for key in self._validator.choices:
            reply_map[int(key)] = special_keys.COLORSPLUS["No change"]  # this signals no change
        self._value = reply_map
        return reply_map

    def write(self, map, save=True):
        if self._device.online:
            self._ensure_sw_control()
            self.update(map, save)
            table = {}
            for key, value in map.items():
                if value in table:
                    table[value].append(key)  # keys will be in order from small to large
                else:
                    table[value] = [key]
            if len(table) == 1:  # use range update
                for value, keys in table.items():  # only one, of course
                    if value != special_keys.COLORSPLUS["No change"]:  # this signals no change, so don't update at all
                        data_bytes = keys[0].to_bytes(1, "big") + keys[-1].to_bytes(1, "big") + value.to_bytes(3, "big")
                        self._device.feature_request(self.feature, 0x50, data_bytes)  # range update command to update all keys
            else:
                data_bytes = b""
                for value, keys in table.items():  # only one, of course
                    if value != special_keys.COLORSPLUS["No change"]:  # this signals no change, so ignore it
                        while len(keys) > 3:  # use an optimized update command that can update up to 13 keys
                            data = value.to_bytes(3, "big") + b"".join([key.to_bytes(1, "big") for key in keys[0:13]])
                            self._device.feature_request(self.feature, 0x60, data)  # single-value multiple-keys update
                            keys = keys[13:]
                        for key in keys:
                            data_bytes += key.to_bytes(1, "big") + value.to_bytes(3, "big")
                            if len(data_bytes) >= 16:  # up to four values are packed into a regular update
                                self._device.feature_request(self.feature, 0x10, data_bytes)
                                data_bytes = b""
                if len(data_bytes) > 0:  # update any remaining keys
                    self._device.feature_request(self.feature, 0x10, data_bytes)
            # Fill unset zones with zone base color before committing the frame,
            # so the entire keyboard updates atomically (no white flash)
            self._fill_unset_zones_with_base_color()
            self._device.feature_request(self.feature, 0x70, 0x00)  # signal device to make the changes
        return map

    def write_key_value(self, key, value, save=True):
        self._ensure_sw_control()
        no_change = special_keys.COLORSPLUS["No change"]
        if value != no_change:
            result = super().write_key_value(int(key), value, save)
            if self._device.online:
                # Fill unset zones on first per-key write (avoids white default)
                if not getattr(self, "_base_filled", False):
                    self._fill_unset_zones_with_base_color()
                    self._base_filled = True
                self._device.feature_request(self.feature, 0x70, 0x00)  # signal device to make the change
            return result
        else:
            # Un-set this key: store "No change", push zone base color to device
            self.update_key_value(int(key), no_change, save)
            if self._device.online:
                zone_base = 0xFFFFFF
                for s in self._device.settings:
                    if s.name.startswith("rgb_zone_") and s._value is not None:
                        color = getattr(s._value, "color", None)
                        if color is not None:
                            zone_base = color
                            break
                r = (zone_base >> 16) & 0xFF
                g = (zone_base >> 8) & 0xFF
                b = zone_base & 0xFF
                zone_id = int(key)
                self._device.feature_request(self.feature, 0x10, bytes([zone_id, r, g, b]))
                self._device.feature_request(self.feature, 0x70, 0x00)
            return no_change

    class rw_class(settings.FeatureRWMap):
        pass

    class validator_class(settings_validator.ChoicesMapValidator):
        @classmethod
        def build(cls, setting_class, device):
            choices_map = {}
            key_bitmap = device.feature_request(setting_class.feature, 0x00, 0x00, 0x00)[2:]
            key_bitmap += device.feature_request(setting_class.feature, 0x00, 0x00, 0x01)[2:]
            key_bitmap += device.feature_request(setting_class.feature, 0x00, 0x00, 0x02)[2:]
            for i in range(1, 255):
                if (key_bitmap[i // 8] >> i % 8) & 0x01:
                    key = (
                        setting_class.keys_universe[i]
                        if i in setting_class.keys_universe
                        else common.NamedInt(i, f"KEY {str(i)}")
                    )
                    choices_map[key] = setting_class.choices_universe
            result = cls(choices_map) if choices_map else None
            return result


# Allow changes to force sensing buttons
class ForceSensing(settings_new.Settings):
    name = "force-sensing"
    label = _("Force Sensing Buttons")
    description = _("Change the force required to activate button.")
    feature = _F.FORCE_SENSING_BUTTON
    setup = "force_buttons"
    get = "get_current"
    set = "set_current"
    acceptable = "acceptable_current_key"
    choices_universe = list(range(0, 256))
    kind = settings.Kind.MAP_RANGE

    @classmethod
    def build(cls, device):
        cls.check_properties(cls)
        device_object = getattr(device, cls.setup)()
        if device_object:
            setting = cls(device, device_object)
            if setting and len(device_object) == 1:
                ## If there is only one force button a simpler interface can be used
                setting.label = _("Force Sensing Button")
                setting.acceptable = "acceptable_current"
                setting.min_value = device_object[0].min_value
                setting.max_value = device_object[0].max_value
                setting.kind = settings.Kind.RANGE
            return setting


class HapticLevel(settings.Setting):
    name = "haptic-level"
    label = _("Haptic Feedback Level")
    description = _("Change power of haptic feedback.  (Zero to turn off.)")
    feature = _F.HAPTIC
    choices_universe = common.NamedInts(Off=0, Low=25, Medium=50, High=75, Maximum=100)
    min_value = 0
    max_value = 100

    class rw_class(settings.FeatureRW):
        def __init__(self, feature):
            super().__init__(feature, read_fnid=0x10, write_fnid=0x20)

        def read(self, device, data_bytes=b""):
            result = device.feature_request(self.feature, 0x10)
            if result[0] & 0x01 == 0:  # disabled, return 0
                return b"\x00"
            else:  # enabled, return second byte
                return result[1:2]

        def write(self, device, data_bytes):
            if data_bytes == b"\x00":
                write_bytes = b"\x00\x32"  # disable, at 50 percent
            else:
                write_bytes = b"\x01" + data_bytes
            reply = device.feature_request(self.feature, 0x20, write_bytes)
            return reply

    @classmethod
    def build(cls, device):
        response = device.feature_request(cls.feature, 0x10)
        if response:
            rw = cls.rw_class(cls.feature)
            levels = response[2] & 0x01
            if levels:  # device only has four levels
                validator = settings_validator.ChoicesValidator(choices=cls.choices_universe)
            else:  # device has all levels
                validator = settings_validator.RangeValidator(min_value=cls.min_value, max_value=cls.max_value)
            return cls(device, rw, validator)


# This setting is not displayed in the UI
# Use `solaar config <device> haptic-play <form>` to play a haptic form
class PlayHapticWaveForm(settings.Setting):
    name = "haptic-play"
    label = _("Play Haptic Waveform")
    description = _("Tell device to play a haptic waveform.")
    feature = _F.HAPTIC
    choices_universe = hidpp20_constants.HapticWaveForms
    rw_options = {"read_fnid": None, "write_fnid": 0x40}  # nothing to read
    persist = False  # persisting this setting is useless
    display = False  # don't display in UI, interact using `solaar config ...`

    class validator_class(settings_validator.ChoicesValidator):
        @classmethod
        def build(cls, setting_class, device):
            response = device.feature_request(_F.HAPTIC, 0x00)
            if response:
                waves = common.NamedInts()
                waveforms = int.from_bytes(response[4:8])
                for waveform in hidpp20_constants.HapticWaveForms:
                    if (1 << int(waveform)) & waveforms:
                        waves[int(waveform)] = str(waveform)
            return cls(choices=waves, byte_count=1)


SETTINGS: list[settings.Setting] = [
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
    ScrollRatchetTorque,
    SmartShift,  # working
    ScrollRatchetEnhanced,
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
    RGBIdleEffect,
    RGBIdleTimeout,
    RGBSleepTimeout,
    FnSwap,  # simple
    NewFnSwap,  # simple
    K375sFnSwap,  # working
    ReprogrammableKeys,  # working
    PersistentRemappableAction,
    DivertKeys,  # working
    DisableKeyboardKeys,  # working
    ForceSensing,
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
    HapticLevel,
    PlayHapticWaveForm,
    Sidetone,
    Equalizer,
    ADCPower,
]


class SettingsProtocol(Protocol):
    @property
    def name(self):
        ...

    @property
    def label(self):
        ...

    @property
    def description(self):
        ...

    @property
    def feature(self):
        ...

    @property
    def register(self):
        ...

    @property
    def kind(self):
        ...

    @property
    def min_version(self):
        ...

    @property
    def persist(self):
        ...

    @property
    def rw_options(self):
        ...

    @property
    def validator_class(self):
        ...

    @property
    def validator_options(self):
        ...

    @classmethod
    def build(cls, device):
        ...

    def val_to_string(self, value):
        ...

    @property
    def choices(self):
        ...

    @property
    def range(self):
        ...

    def _pre_read(self, cached, key=None):
        ...

    def read(self, cached=True):
        ...

    def _pre_write(self, save=True):
        ...

    def update(self, value, save=True):
        ...

    def write(self, value, save=True):
        ...

    def acceptable(self, args, current):
        ...

    def compare(self, args, current):
        ...

    def apply(self):
        ...

    def __str__(self):
        ...


def check_feature(device, settings_class: SettingsProtocol) -> None | bool | SettingsProtocol:
    if settings_class.feature not in device.features:
        return
    if settings_class.min_version > device.features.get_feature_version(settings_class.feature):
        return
    if device.features.get_hidden(settings_class.feature):
        return
    try:
        detected = settings_class.build(device)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("check_feature %s [%s] detected", settings_class.name, settings_class.feature)
        return detected
    except Exception as e:
        logger.error(
            "check_feature %s [%s] error %s\n%s", settings_class.name, settings_class.feature, e, traceback.format_exc()
        )
        raise e  # differentiate from an error-free determination that the setting is not supported


def check_feature_settings(device, already_known) -> bool:
    """Auto-detect device settings by the HID++ 2.0 features they have.

    Returns
    -------
    bool
        True, if device was fully queried to find features, False otherwise.
    """
    if not device.features or not device.online:
        return False
    if device.protocol and device.protocol < 2.0:
        return False
    absent = device.persister.get("_absent", []) if device.persister else []
    new_absent = []
    for sclass in SETTINGS:
        if sclass.feature:
            known_present = device.persister and sclass.name in device.persister
            if not any(s.name == sclass.name for s in already_known) and (known_present or sclass.name not in absent):
                try:
                    setting = check_feature(device, sclass)
                except Exception as err:
                    # on an internal HID++ error, assume offline and stop further checking
                    if (
                        isinstance(err, exceptions.FeatureCallError)
                        and err.error == hidpp20_constants.ErrorCode.LOGITECH_ERROR
                    ):
                        logger.warning(f"HID++ internal error checking feature {sclass.name}: make device not present")
                        device.online = False
                        device.present = False
                        return False
                    else:
                        logger.warning(f"ignore feature {sclass.name} because of error {err}")

                if isinstance(setting, list):
                    for s in setting:
                        already_known.append(s)
                    if sclass.name in new_absent:
                        new_absent.remove(sclass.name)
                elif setting:
                    already_known.append(setting)
                    if sclass.name in new_absent:
                        new_absent.remove(sclass.name)
                elif setting is None:
                    if sclass.name not in new_absent and sclass.name not in absent and sclass.name not in device.persister:
                        new_absent.append(sclass.name)
    if device.persister and new_absent:
        absent.extend(new_absent)
        device.persister["_absent"] = absent
    return True


def check_feature_setting(device, setting_name: str) -> settings.Setting | None:
    for sclass in SETTINGS:
        if (
            sclass.feature
            and device.features
            and (sclass.name == setting_name or sclass.name.endswith("_") and setting_name.startswith(sclass.name))
        ):
            try:
                setting = check_feature(device, sclass)
            except Exception:
                return None
            if isinstance(setting, list):
                for s in setting:
                    if s.name == setting_name:
                        return s
            elif setting:
                return setting
