## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""The tests work by creating a faked device (from the hidpp module) that uses provided data as responses to HID++ commands.
The device uses some methods from the real device to set up data structures that are needed for some tests.
"""

from dataclasses import dataclass
from typing import Any

import pytest

from logitech_receiver import common
from logitech_receiver import hidpp20
from logitech_receiver import hidpp20_constants
from logitech_receiver import settings_templates
from logitech_receiver import special_keys

from . import fake_hidpp

# TODO action part of DpiSlidingXY, MouseGesturesXY


class Setup:
    def __init__(self, test, *params):
        self.test = test
        self.responses = [r for r in params if isinstance(r, fake_hidpp.Response)]
        self.choices = None if isinstance(params[0], fake_hidpp.Response) else params[0]


@dataclass
class RegisterTest:
    sclass: Any
    initial_value: Any = False
    write_value: Any = True
    write_params: str = "01"


register_tests = [
    Setup(
        RegisterTest(settings_templates.RegisterHandDetection, False, True, [b"\x00\x00\x00"]),
        fake_hidpp.Response("000030", 0x8101),  # keyboard_hand_detection
        fake_hidpp.Response("000000", 0x8001, "000000"),
    ),
    Setup(
        RegisterTest(settings_templates.RegisterHandDetection, True, False, [b"\x00\x00\x30"]),
        fake_hidpp.Response("000000", 0x8101),  # keyboard_hand_detection
        fake_hidpp.Response("000030", 0x8001, "000030"),
    ),
    Setup(
        RegisterTest(settings_templates.RegisterSmoothScroll, False, True, [b"\x40"]),
        fake_hidpp.Response("00", 0x8101),  # mouse_button_flags
        fake_hidpp.Response("40", 0x8001, "40"),
    ),
    Setup(
        RegisterTest(settings_templates.RegisterSideScroll, True, False, [b"\x00"]),
        fake_hidpp.Response("02", 0x8101),  # mouse_button_flags
        fake_hidpp.Response("00", 0x8001, "00"),
    ),
    Setup(
        RegisterTest(settings_templates.RegisterFnSwap, False, True, [b"\x00\x01"]),
        fake_hidpp.Response("0000", 0x8109),  # keyboard_fn_swap
        fake_hidpp.Response("0001", 0x8009, "0001"),
    ),
    Setup(
        RegisterTest(
            settings_templates._PerformanceMXDpi, common.NamedInt(0x88, "800"), common.NamedInt(0x89, "900"), [b"\x89"]
        ),
        fake_hidpp.Response("88", 0x8163),  # mouse_dpi
        fake_hidpp.Response("89", 0x8063, "89"),
    ),
]


@pytest.mark.parametrize("test", register_tests)
def test_register_template(test, mocker):
    device = fake_hidpp.Device(protocol=1.0, responses=test.responses)
    spy_request = mocker.spy(device, "request")

    setting = test.test.sclass.build(device)
    value = setting.read(cached=False)
    cached_value = setting.read(cached=True)
    write_value = setting.write(test.test.write_value)

    assert setting is not None
    assert value == test.test.initial_value
    assert cached_value == test.test.initial_value
    assert write_value == test.test.write_value
    spy_request.assert_called_with(test.test.sclass.register + 0x8000, *test.test.write_params)


@dataclass
class FeatureTest:
    sclass: Any
    initial_value: Any = False
    write_value: Any = True
    matched_calls: int = 1
    offset: int = 0x04
    version: int = 0x00
    rewrite: bool = False


simple_tests = [
    Setup(
        FeatureTest(settings_templates.K375sFnSwap, False, True, offset=0x06),
        fake_hidpp.Response("FF0001", 0x0600, "FF"),
        fake_hidpp.Response("FF0101", 0x0610, "FF01"),
    ),
    Setup(
        FeatureTest(settings_templates.K375sFnSwap, False, True, offset=0x06),
        fake_hidpp.Response("050001", 0x0000, "1815"),  # HOSTS_INFO
        fake_hidpp.Response("FF0001", 0x0600, "FF"),
        fake_hidpp.Response("FF0101", 0x0610, "FF01"),
    ),
    Setup(
        FeatureTest(settings_templates.K375sFnSwap, False, True, offset=0x06),
        fake_hidpp.Response("050001", 0x0000, "1815"),  # HOSTS_INFO
        fake_hidpp.Response("07050301", 0x0500),  # current host is 0x01, i.e., host 2
        fake_hidpp.Response("010001", 0x0600, "01"),
        fake_hidpp.Response("010101", 0x0610, "0101"),
    ),
    Setup(
        FeatureTest(settings_templates.FnSwap, True, False),
        fake_hidpp.Response("01", 0x0400),
        fake_hidpp.Response("00", 0x0410, "00"),
    ),
    Setup(
        FeatureTest(settings_templates.NewFnSwap, True, False),
        fake_hidpp.Response("01", 0x0400),
        fake_hidpp.Response("00", 0x0410, "00"),
    ),
    #    Setup(  # Backlight has caused problems
    #        FeatureTest(settings_templates.Backlight, 0, 5, offset=0x06),
    #        fake_hidpp.Response("00", 0x0600),
    #        fake_hidpp.Response("05", 0x0610, "05"),
    #    ),
    Setup(
        FeatureTest(settings_templates.Backlight2DurationHandsOut, 80, 160, version=0x03),
        fake_hidpp.Response("011830000000100040006000", 0x0400),
        fake_hidpp.Response("0118FF00200040006000", 0x0410, "0118FF00200040006000"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight2DurationHandsIn, 320, 160, version=0x03),
        fake_hidpp.Response("011830000000200040006000", 0x0400),
        fake_hidpp.Response("0118FF00200020006000", 0x0410, "0118FF00200020006000"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight2DurationPowered, 480, 80, version=0x03),
        fake_hidpp.Response("011830000000200040006000", 0x0400),
        fake_hidpp.Response("0118FF00200040001000", 0x0410, "0118FF00200040001000"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight3, 0x50, 0x70),
        fake_hidpp.Response("50", 0x0410),
        fake_hidpp.Response("70", 0x0420, "007009"),
    ),
    Setup(
        FeatureTest(settings_templates.HiResScroll, True, False),
        fake_hidpp.Response("01", 0x0400),
        fake_hidpp.Response("00", 0x0410, "00"),
    ),
    Setup(
        FeatureTest(settings_templates.LowresMode, False, True),
        fake_hidpp.Response("00", 0x0400),
        fake_hidpp.Response("01", 0x0410, "01"),
    ),
    Setup(
        FeatureTest(settings_templates.HiresSmoothInvert, True, False),
        fake_hidpp.Response("06", 0x0410),
        fake_hidpp.Response("02", 0x0420, "02"),
    ),
    Setup(
        FeatureTest(settings_templates.HiresSmoothResolution, True, False),
        fake_hidpp.Response("06", 0x0410),
        fake_hidpp.Response("04", 0x0420, "04"),
    ),
    Setup(
        FeatureTest(settings_templates.HiresMode, False, True),
        fake_hidpp.Response("06", 0x0410),
        fake_hidpp.Response("07", 0x0420, "07"),
    ),
    Setup(
        FeatureTest(settings_templates.PointerSpeed, 0x0100, 0x0120),
        fake_hidpp.Response("0100", 0x0400),
        fake_hidpp.Response("0120", 0x0410, "0120"),
    ),
    Setup(
        FeatureTest(settings_templates.ThumbMode, True, False),
        fake_hidpp.Response("0100", 0x0410),
        fake_hidpp.Response("0000", 0x0420, "0000"),
    ),
    Setup(
        FeatureTest(settings_templates.ThumbInvert, False, True),
        fake_hidpp.Response("0100", 0x0410),
        fake_hidpp.Response("0101", 0x0420, "0101"),
    ),
    Setup(
        FeatureTest(settings_templates.DivertCrown, False, True),
        fake_hidpp.Response("01", 0x0410),
        fake_hidpp.Response("02", 0x0420, "02"),
    ),
    Setup(
        FeatureTest(settings_templates.CrownSmooth, True, False),
        fake_hidpp.Response("0001", 0x0410),
        fake_hidpp.Response("0002", 0x0420, "0002"),
    ),
    Setup(
        FeatureTest(settings_templates.DivertGkeys, False, True),
        fake_hidpp.Response("01", 0x0420, "01"),
    ),
    Setup(
        FeatureTest(settings_templates.ScrollRatchet, 2, 1),
        fake_hidpp.Response("02", 0x0400),
        fake_hidpp.Response("01", 0x0410, "01"),
    ),
    Setup(
        FeatureTest(settings_templates.SmartShift, 1, 10),
        fake_hidpp.Response("0100", 0x0400),
        fake_hidpp.Response("000A", 0x0410, "000A"),
    ),
    Setup(
        FeatureTest(settings_templates.SmartShift, 5, 50),
        fake_hidpp.Response("0005", 0x0400),
        fake_hidpp.Response("00FF", 0x0410, "00FF"),
    ),
    Setup(
        FeatureTest(settings_templates.SmartShiftEnhanced, 5, 50),
        fake_hidpp.Response("0005", 0x0410),
        fake_hidpp.Response("00FF", 0x0420, "00FF"),
    ),
    Setup(
        FeatureTest(settings_templates.DisableKeyboardKeys, {1: True, 8: True}, {1: False, 8: True}),
        fake_hidpp.Response("09", 0x0400),
        fake_hidpp.Response("09", 0x0410),
        fake_hidpp.Response("08", 0x0420, "08"),
    ),
    Setup(
        FeatureTest(settings_templates.DualPlatform, 0, 1),
        fake_hidpp.Response("00", 0x0400),
        fake_hidpp.Response("01", 0x0420, "01"),
    ),
    Setup(
        FeatureTest(settings_templates.MKeyLEDs, {1: False, 2: False, 4: False}, {1: False, 2: True, 4: True}),
        fake_hidpp.Response("03", 0x0400),
        fake_hidpp.Response("06", 0x0410, "06"),
    ),
    Setup(
        FeatureTest(settings_templates.MRKeyLED, False, True),
        fake_hidpp.Response("01", 0x0400, "01"),
    ),
    Setup(
        FeatureTest(settings_templates.Sidetone, 5, 0xA),
        fake_hidpp.Response("05", 0x0400),
        fake_hidpp.Response("0A", 0x0410, "0A"),
    ),
    Setup(
        FeatureTest(settings_templates.ADCPower, 5, 0xA),
        fake_hidpp.Response("05", 0x0410),
        fake_hidpp.Response("0A", 0x0420, "0A"),
    ),
    Setup(
        FeatureTest(settings_templates.LEDControl, 0, 1),
        fake_hidpp.Response("00", 0x0470),
        fake_hidpp.Response("01", 0x0480, "01"),
    ),
    Setup(
        FeatureTest(
            settings_templates.LEDZoneSetting,
            hidpp20.LEDEffectSetting(ID=3, intensity=0x50, period=0x100),
            hidpp20.LEDEffectSetting(ID=3, intensity=0x50, period=0x101),
        ),
        fake_hidpp.Response("0100000001", 0x0400),
        fake_hidpp.Response("00000102", 0x0410, "00FF00"),
        fake_hidpp.Response("0000000300040005", 0x0420, "000000"),
        fake_hidpp.Response("0001000B00080009", 0x0420, "000100"),
        fake_hidpp.Response("000000000000010050", 0x04E0, "00"),
        fake_hidpp.Response("000000000000000101500000", 0x0430, "000000000000000101500000"),
    ),
    Setup(
        FeatureTest(settings_templates.RGBControl, 0, 1),
        fake_hidpp.Response("0000", 0x0450),
        fake_hidpp.Response("010100", 0x0450, "0101"),
    ),
    Setup(
        FeatureTest(
            settings_templates.RGBEffectSetting,
            hidpp20.LEDEffectSetting(ID=3, intensity=0x50, period=0x100),
            hidpp20.LEDEffectSetting(ID=2, color=0x505050, speed=0x50),
        ),
        fake_hidpp.Response("FFFF0100000001", 0x0400, "FFFF00"),
        fake_hidpp.Response("0000000102", 0x0400, "00FF00"),
        fake_hidpp.Response("0000000300040005", 0x0400, "000000"),
        fake_hidpp.Response("0001000200080009", 0x0400, "000100"),
        fake_hidpp.Response("000000000000010050", 0x04E0, "00"),
        fake_hidpp.Response("00015050505000000000000001", 0x0410, "00015050505000000000000001"),
    ),
    Setup(
        FeatureTest(settings_templates.RGBEffectSetting, None, hidpp20.LEDEffectSetting(ID=3, intensity=0x60, period=0x101)),
        fake_hidpp.Response("FFFF0100000001", 0x0400, "FFFF00"),
        fake_hidpp.Response("0000000102", 0x0400, "00FF00"),
        fake_hidpp.Response("0000000300040005", 0x0400, "000000"),
        fake_hidpp.Response("0001000200080009", 0x0400, "000100"),
        fake_hidpp.Response("00000000000000010160000001", 0x0410, "00000000000000010160000001"),
    ),
    Setup(
        FeatureTest(settings_templates.RGBEffectSetting, None, hidpp20.LEDEffectSetting(ID=3, intensity=0x60, period=0x101)),
        fake_hidpp.Response("FF000200020004000000000000000000", 0x0400, "FFFF00"),
        fake_hidpp.Response("00000002040000000000000000000000", 0x0400, "00FF00"),
        fake_hidpp.Response("00000000000000000000000000000000", 0x0400, "000000"),
        fake_hidpp.Response("00010001000000000000000000000000", 0x0400, "000100"),
        fake_hidpp.Response("00020003C00503E00000000000000000", 0x0400, "000200"),
        fake_hidpp.Response("0003000AC0011E0B0000000000000000", 0x0400, "000300"),
        fake_hidpp.Response("01000001070000000000000000000000", 0x0400, "01FF00"),
        fake_hidpp.Response("01000000000000000000000000000000", 0x0400, "010000"),
        fake_hidpp.Response("01010001000000000000000000000000", 0x0400, "010100"),
        fake_hidpp.Response("0102000AC0011E0B0000000000000000", 0x0400, "010200"),
        fake_hidpp.Response("01030003C00503E00000000000000000", 0x0400, "010300"),
        fake_hidpp.Response("01040004DCE1001E0000000000000000", 0x0400, "010400"),
        fake_hidpp.Response("0105000B000000320000000000000000", 0x0400, "010500"),
        fake_hidpp.Response("0106000C001B02340000000000000000", 0x0400, "010600"),
        fake_hidpp.Response("00020000000000010160000001", 0x0410, "00020000000000010160000001"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight2, 0xFF, 0x00),
        common.NamedInts(Disabled=0xFF, Enabled=0x00),
        fake_hidpp.Response("000201000000000000000000", 0x0400),
        fake_hidpp.Response("010201", 0x0410, "0102FF00000000000000"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight2, 0x03, 0xFF),
        common.NamedInts(Disabled=0xFF, Automatic=0x01, Manual=0x03),
        fake_hidpp.Response("011838000000000000000000", 0x0400),
        fake_hidpp.Response("001801", 0x0410, "0018FF00000000000000"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight2Level, 0, 3, version=0x03),
        [0, 4],
        fake_hidpp.Response("011830000000000000000000", 0x0400),
        fake_hidpp.Response("05", 0x0420),
        fake_hidpp.Response("01180103000000000000", 0x0410, "0118FF03000000000000"),
    ),
    Setup(
        FeatureTest(settings_templates.Backlight2Level, 0, 2, version=0x03),
        [0, 4],
        fake_hidpp.Response("011830000000000000000000", 0x0400),
        fake_hidpp.Response("05", 0x0420),
        fake_hidpp.Response("01180102000000000000", 0x0410, "0118FF02000000000000"),
    ),
    Setup(
        FeatureTest(settings_templates.OnboardProfiles, 0, 1, offset=0x0C),
        common.NamedInts(**{"Disabled": 0, "Profile 1": 1, "Profile 2": 2}),
        fake_hidpp.Response("01030001010101000101", 0x0C00),
        fake_hidpp.Response("00010100000201FFFFFFFFFFFFFFFFFF", 0x0C50, "00000000"),
        fake_hidpp.Response("000201FFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000004"),
        fake_hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000008"),
        fake_hidpp.Response("02", 0x0C20),
        fake_hidpp.Response("01", 0x0C10, "01"),
        fake_hidpp.Response("0001", 0x0C30, "0001"),
    ),
    Setup(
        FeatureTest(settings_templates.OnboardProfiles, 1, 0, offset=0x0C),
        common.NamedInts(**{"Disabled": 0, "Profile 1": 1, "Profile 2": 2}),
        fake_hidpp.Response("01030001010101000101", 0x0C00),
        fake_hidpp.Response("00010100000201FFFFFFFFFFFFFFFFFF", 0x0C50, "00000000"),
        fake_hidpp.Response("000201FFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000004"),
        fake_hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000008"),
        fake_hidpp.Response("01", 0x0C20),
        fake_hidpp.Response("0001", 0x0C40),
        fake_hidpp.Response("02", 0x0C10, "02"),
    ),
    Setup(
        FeatureTest(settings_templates.ReportRate, 1, 5, offset=0x0C),
        common.NamedInts(**{"1ms": 1, "2ms": 2, "5ms": 5, "6ms": 6}),
        fake_hidpp.Response("33", 0x0C00),
        fake_hidpp.Response("01", 0x0C10),
        fake_hidpp.Response("05", 0x0C20, "05"),
    ),
    Setup(
        FeatureTest(settings_templates.ExtendedReportRate, 1, 5, offset=0x0C),
        common.NamedInts(**{"8ms": 0, "4ms": 1, "500us": 4, "250us": 5}),
        fake_hidpp.Response("33", 0x0C10),
        fake_hidpp.Response("01", 0x0C20),
        fake_hidpp.Response("05", 0x0C30, "05"),
    ),
    Setup(
        FeatureTest(settings_templates.AdjustableDpi, 800, 400, version=0x03),
        common.NamedInts.list([400, 800, 1600]),
        fake_hidpp.Response("000190032006400000", 0x0410, "000000"),
        fake_hidpp.Response("000320", 0x0420),
        fake_hidpp.Response("000190", 0x0430, "000190"),
    ),
    Setup(
        FeatureTest(settings_templates.AdjustableDpi, 256, 512, version=0x03),
        common.NamedInts.list([256, 512]),
        fake_hidpp.Response("000100e10002000000", 0x0410, "000000"),
        fake_hidpp.Response("000100", 0x0420),
        fake_hidpp.Response("000200", 0x0430, "000200"),
    ),
    Setup(
        FeatureTest(settings_templates.AdjustableDpi, 400, 800, version=0x03),
        common.NamedInts.list([400, 800, 1200, 1600]),
        fake_hidpp.Response("000190E19006400000000000000000", 0x0410, "000000"),
        fake_hidpp.Response("000190", 0x0420),
        fake_hidpp.Response("000320", 0x0430, "000320"),
    ),
    Setup(
        FeatureTest(settings_templates.Multiplatform, 0, 1),
        common.NamedInts(**{"MacOS 0.1-0.5": 0, "iOS 0.1-0.7": 1, "Linux 0.2-0.9": 2, "Windows 0.3-0.9": 3}),
        fake_hidpp.Response("020004000001", 0x0400),
        fake_hidpp.Response("00FF200000010005", 0x0410, "00"),
        fake_hidpp.Response("01FF400000010007", 0x0410, "01"),
        fake_hidpp.Response("02FF040000020009", 0x0410, "02"),
        fake_hidpp.Response("03FF010000030009", 0x0410, "03"),
        fake_hidpp.Response("FF01", 0x0430, "FF01"),
    ),
    Setup(
        FeatureTest(settings_templates.ChangeHost, 1, 0),
        common.NamedInts(**{"1:ABCDEF": 0, "2:GHIJKL": 1}),
        fake_hidpp.Response("050003", 0x0000, "1815"),  # HOSTS_INFO
        fake_hidpp.Response("01000200", 0x0500),
        fake_hidpp.Response("000100000600", 0x0510, "00"),
        fake_hidpp.Response("000041424344454600", 0x0530, "0000"),
        fake_hidpp.Response("000100000600", 0x0510, "01"),
        fake_hidpp.Response("00004748494A4B4C00", 0x0530, "0100"),
        fake_hidpp.Response("0201", 0x0400),
        fake_hidpp.Response(True, 0x0410, "00"),
    ),
    Setup(
        FeatureTest(settings_templates.BrightnessControl, 0x10, 0x20),
        [0, 80],
        fake_hidpp.Response("00505100000000", 0x0400),  # 0 to 80, all acceptable, no separate on/off
        fake_hidpp.Response("10", 0x0410),  # brightness 16
        fake_hidpp.Response("0020", 0x0420, "0020"),  # set brightness 32
    ),
    Setup(
        FeatureTest(settings_templates.BrightnessControl, 0x10, 0x00),
        [0, 80],
        fake_hidpp.Response("00505104000000", 0x0400),  # 0 to 80, all acceptable, separate on/off
        fake_hidpp.Response("10", 0x0410),  # brightness 16
        fake_hidpp.Response("01", 0x0430),  # on
        fake_hidpp.Response("00", 0x0440),  # set off
        fake_hidpp.Response("0000", 0x0420, "0000"),  # set brightness 0
    ),
    Setup(
        FeatureTest(settings_templates.BrightnessControl, 0x00, 0x20),
        [0, 80],
        fake_hidpp.Response("00505104000000", 0x0400),  # 0 to 80, all acceptable, separate on/off
        fake_hidpp.Response("10", 0x0410),  # brightness 16
        fake_hidpp.Response("00", 0x0430),  # off
        fake_hidpp.Response("01", 0x0440),  # set on
        fake_hidpp.Response("0020", 0x0420, "0020"),  # set brightness 32
    ),
    Setup(
        FeatureTest(settings_templates.BrightnessControl, 0x20, 0x08),
        [0, 80],
        fake_hidpp.Response("00504104001000", 0x0400),  # 16 to 80, all acceptable, separate on/off
        fake_hidpp.Response("20", 0x0410),  # brightness 32
        fake_hidpp.Response("01", 0x0430),  # on
        fake_hidpp.Response("00", 0x0440, "00"),  # set off
    ),
    Setup(
        FeatureTest(settings_templates.SpeedChange, 0, None, 0),  # need to set up all settings to successfully write
        common.NamedInts(**{"Off": 0, "DPI Change": 0xED}),
        *fake_hidpp.responses_speedchange,
    ),
]


@pytest.fixture
def mock_gethostname(mocker):
    mocker.patch("socket.gethostname", return_value="ABCDEF.foo.org")


@pytest.mark.parametrize("test", simple_tests)
def test_simple_template(test, mocker, mock_gethostname):
    tst = test.test
    print("TEST", tst.sclass.feature)
    device = fake_hidpp.Device(responses=test.responses, feature=tst.sclass.feature, offset=tst.offset, version=tst.version)
    spy_request = mocker.spy(device, "request")

    setting = settings_templates.check_feature(device, tst.sclass)
    assert setting is not None
    if isinstance(setting, list):
        setting = setting[0]
    if isinstance(test.choices, list):
        assert setting._validator.min_value == test.choices[0]
        assert setting._validator.max_value == test.choices[1]
    elif test.choices is not None:
        assert setting.choices == test.choices

    value = setting.read(cached=False)
    assert value == tst.initial_value

    cached_value = setting.read(cached=True)
    assert cached_value == tst.initial_value

    write_value = setting.write(tst.write_value) if tst.write_value is not None else None
    assert write_value == tst.write_value

    fake_hidpp.match_requests(tst.matched_calls, test.responses, spy_request.call_args_list)


responses_reprog_controls = [
    fake_hidpp.Response("03", 0x0500),
    fake_hidpp.Response("00500038010001010400000000000000", 0x0510, "00"),  # left button
    fake_hidpp.Response("00510039010001010400000000000000", 0x0510, "01"),  # right button
    fake_hidpp.Response("00C4009D310003070500000000000000", 0x0510, "02"),  # smart shift
    fake_hidpp.Response("00500000000000000000000000000000", 0x0520, "0050"),  # left button current
    fake_hidpp.Response("00510000500000000000000000000000", 0x0520, "0051"),  # right button current
    fake_hidpp.Response("00C40000000000000000000000000000", 0x0520, "00C4"),  # smart shift current
    fake_hidpp.Response("00500005000000000000000000000000", 0x0530, "0050000050"),  # left button write
    fake_hidpp.Response("00510005000000000000000000000000", 0x0530, "0051000050"),  # right button write
    fake_hidpp.Response("00C4000C400000000000000000000000", 0x0530, "00C40000C4"),  # smart shift write
]

key_tests = [
    Setup(
        FeatureTest(settings_templates.ReprogrammableKeys, {0x50: 0x50, 0x51: 0x50, 0xC4: 0xC4}, {0x51: 0x51}, 4, offset=0x05),
        {
            common.NamedInt(0x50, "Left Button"): common.UnsortedNamedInts(Left_Click=0x50, Right_Click=0x51),
            common.NamedInt(0x51, "Right Button"): common.UnsortedNamedInts(Right_Click=0x51, Left_Click=0x50),
            common.NamedInt(0xC4, "Smart Shift"): common.UnsortedNamedInts(Smart_Shift=0xC4, Left_Click=80, Right_Click=81),
        },
        *responses_reprog_controls,
        fake_hidpp.Response("0051000051", 0x0530, "0051000051"),  # right button set write
    ),
    Setup(
        FeatureTest(settings_templates.DivertKeys, {0xC4: 0}, {0xC4: 1}, 2, offset=0x05),
        {common.NamedInt(0xC4, "Smart Shift"): common.NamedInts(Regular=0, Diverted=1, Mouse_Gestures=2)},
        *responses_reprog_controls,
        fake_hidpp.Response("00C4020000", 0x0530, "00C4020000"),  # Smart Shift write
        fake_hidpp.Response("00C4030000", 0x0530, "00C4030000"),  # Smart Shift divert write
    ),
    Setup(
        FeatureTest(settings_templates.DivertKeys, {0xC4: 0}, {0xC4: 2}, 2, offset=0x05),
        {common.NamedInt(0xC4, "Smart Shift"): common.NamedInts(Regular=0, Diverted=1, Mouse_Gestures=2, Sliding_DPI=3)},
        *responses_reprog_controls,
        fake_hidpp.Response("0A0001", 0x0000, "2201"),  # ADJUSTABLE_DPI
        fake_hidpp.Response("00C4300000", 0x0530, "00C4300000"),  # Smart Shift write
        fake_hidpp.Response("00C4030000", 0x0530, "00C4030000"),  # Smart Shift divert write
    ),
    Setup(
        FeatureTest(settings_templates.PersistentRemappableAction, {80: 16797696, 81: 16797696}, {0x51: 16797952}, 3),
        {
            common.NamedInt(80, "Left Button"): special_keys.KEYS_KEYS_CONSUMER,
            common.NamedInt(81, "Right Button"): special_keys.KEYS_KEYS_CONSUMER,
        },
        fake_hidpp.Response("050001", 0x0000, "1B04"),  # REPROG_CONTROLS_V4
        *responses_reprog_controls,
        fake_hidpp.Response("0041", 0x0400),
        fake_hidpp.Response("0201", 0x0410),
        fake_hidpp.Response("02", 0x0400),
        fake_hidpp.Response("0050", 0x0420, "00FF"),  # left button
        fake_hidpp.Response("0051", 0x0420, "01FF"),  # right button
        fake_hidpp.Response("0050000100500000", 0x0430, "0050FF"),  # left button current
        fake_hidpp.Response("0051000100500001", 0x0430, "0051FF"),  # right button current
        fake_hidpp.Response("0050FF01005000", 0x0440, "0050FF01005000"),  # left button write
        fake_hidpp.Response("0051FF01005000", 0x0440, "0051FF01005000"),  # right button write
        fake_hidpp.Response("0051FF01005100", 0x0440, "0051FF01005100"),  # right button set write
    ),
    Setup(
        FeatureTest(
            settings_templates.Gesture2Gestures,
            {
                1: True,
                2: True,
                30: True,
                10: True,
                45: False,
                42: True,
                43: True,
                64: False,
                65: False,
                67: False,
                84: True,
                34: False,
            },
            {45: True},
            4,
        ),
        *fake_hidpp.responses_gestures,
        fake_hidpp.Response("0001FF6F", 0x0420, "0001FF6F"),  # write
        fake_hidpp.Response("01010F04", 0x0420, "01010F04"),
        fake_hidpp.Response("0001FF7F", 0x0420, "0001FF7F"),  # write 45
        fake_hidpp.Response("01010F04", 0x0420, "01010F04"),
    ),
    Setup(
        FeatureTest(
            settings_templates.Gesture2Divert,
            {1: False, 2: False, 10: False, 44: False, 64: False, 65: False, 67: False, 84: False, 85: False, 100: False},
            {44: True},
            4,
        ),
        *fake_hidpp.responses_gestures,
        fake_hidpp.Response("0001FF00", 0x0440, "0001FF00"),  # write
        fake_hidpp.Response("01010300", 0x0440, "01010300"),
        fake_hidpp.Response("0001FF08", 0x0440, "0001FF08"),  # write 44
        fake_hidpp.Response("01010300", 0x0440, "01010300"),
    ),
    Setup(
        FeatureTest(settings_templates.Gesture2Params, {4: {"scale": 256}}, {4: {"scale": 128}}, 2),
        *fake_hidpp.responses_gestures,
        fake_hidpp.Response("000100FF000000000000000000000000", 0x0480, "000100FF"),
        fake_hidpp.Response("000080FF000000000000000000000000", 0x0480, "000080FF"),
    ),
    Setup(
        FeatureTest(settings_templates.Equalizer, {0: -0x20, 1: 0x10}, {1: 0x18}, 2),
        [-32, 32],
        fake_hidpp.Response("0220000000", 0x0400),
        fake_hidpp.Response("0000800100000000000000", 0x0410, "00"),
        fake_hidpp.Response("E010", 0x0420, "00"),
        fake_hidpp.Response("E010", 0x0430, "02E010"),
        fake_hidpp.Response("E018", 0x0430, "02E018"),
    ),
    Setup(
        FeatureTest(settings_templates.PerKeyLighting, {1: -1, 2: -1, 9: -1, 10: -1, 113: -1}, {2: 0xFF0000}, 4, 4, 0, 1),
        {
            common.NamedInt(1, "A"): special_keys.COLORSPLUS,
            common.NamedInt(2, "B"): special_keys.COLORSPLUS,
            common.NamedInt(9, "I"): special_keys.COLORSPLUS,
            common.NamedInt(10, "J"): special_keys.COLORSPLUS,
            common.NamedInt(113, "KEY 113"): special_keys.COLORSPLUS,
        },
        fake_hidpp.Response("00000606000000000000000000000000", 0x0400, "0000"),  # first group of keys
        fake_hidpp.Response("00000200000000000000000000000000", 0x0400, "0001"),  # second group of keys
        fake_hidpp.Response("00000000000000000000000000000000", 0x0400, "0002"),  # last group of keys
        fake_hidpp.Response("02FF0000", 0x0410, "02FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("02FF0000", 0x0410, "02FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
    ),
    Setup(
        FeatureTest(
            settings_templates.PerKeyLighting,
            {1: -1, 2: -1, 9: -1, 10: -1, 113: -1},
            {2: 0xFF0000, 9: 0xFF0000, 10: 0xFF0000},
            8,
            4,
            0,
            1,
        ),
        {
            common.NamedInt(1, "A"): special_keys.COLORSPLUS,
            common.NamedInt(2, "B"): special_keys.COLORSPLUS,
            common.NamedInt(9, "I"): special_keys.COLORSPLUS,
            common.NamedInt(10, "J"): special_keys.COLORSPLUS,
            common.NamedInt(113, "KEY 113"): special_keys.COLORSPLUS,
        },
        fake_hidpp.Response("00000606000000000000000000000000", 0x0400, "0000"),  # first group of keys
        fake_hidpp.Response("00000200000000000000000000000000", 0x0400, "0001"),  # second group of keys
        fake_hidpp.Response("00000000000000000000000000000000", 0x0400, "0002"),  # last group of keys
        fake_hidpp.Response("02FF0000", 0x0410, "02FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("09FF0000", 0x0410, "09FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("0AFF0000", 0x0410, "0AFF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("02FF000009FF00000AFF0000", 0x0410, "02FF000009FF00000AFF0000"),  # write three values
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
    ),
    Setup(
        FeatureTest(
            settings_templates.PerKeyLighting,
            {1: -1, 2: -1, 9: -1, 10: -1, 113: -1, 114: -1},
            {1: 0xFF0000, 2: 0xFF0000, 9: 0xFF0000, 10: 0xFF0000, 113: 0x00FF00, 114: 0xFF0000},
            15,
            4,
            0,
            1,
        ),
        {
            common.NamedInt(1, "A"): special_keys.COLORSPLUS,
            common.NamedInt(2, "B"): special_keys.COLORSPLUS,
            common.NamedInt(9, "I"): special_keys.COLORSPLUS,
            common.NamedInt(10, "J"): special_keys.COLORSPLUS,
            common.NamedInt(113, "KEY 113"): special_keys.COLORSPLUS,
            common.NamedInt(114, "KEY 114"): special_keys.COLORSPLUS,
        },
        fake_hidpp.Response("00000606000000000000000000000000", 0x0400, "0000"),  # first group of keys
        fake_hidpp.Response("00000600000000000000000000000000", 0x0400, "0001"),  # second group of keys
        fake_hidpp.Response("00000000000000000000000000000000", 0x0400, "0002"),  # last group of keys
        fake_hidpp.Response("01FF0000", 0x0410, "01FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("02FF0000", 0x0410, "02FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("09FF0000", 0x0410, "09FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("0AFF0000", 0x0410, "0AFF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("7100FF00", 0x0410, "7100FF00"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("72FF0000", 0x0410, "72FF0000"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
        fake_hidpp.Response("FF00000102090A72", 0x460, "FF00000102090A72"),  # write one value for five keys
        fake_hidpp.Response("7100FF00", 0x0410, "7100FF00"),  # write one value
        fake_hidpp.Response("00", 0x0470, "00"),  # finish
    ),
    Setup(
        FeatureTest(settings_templates.ExtendedAdjustableDpi, {0: 256}, {0: 512}, 2, offset=0x9),
        {common.NamedInt(0, "X"): common.NamedInts.list([256, 512])},
        fake_hidpp.Response("000000", 0x0910, "00"),  # no y direction, no lod
        fake_hidpp.Response("0000000100e10002000000", 0x0920, "000000"),
        fake_hidpp.Response("00010000000000000000", 0x0950),
        fake_hidpp.Response("000100000000", 0x0960, "000100000000"),
        fake_hidpp.Response("000200000000", 0x0960, "000200000000"),
    ),
    Setup(
        FeatureTest(settings_templates.ExtendedAdjustableDpi, {0: 0x64, 1: 0xE4}, {0: 0x164}, 2, offset=0x9),
        {
            common.NamedInt(0, "X"): common.NamedInts.list([0x064, 0x074, 0x084, 0x0A4, 0x0C4, 0x0E4, 0x0124, 0x0164, 0x01C4]),
            common.NamedInt(1, "Y"): common.NamedInts.list([0x064, 0x074, 0x084, 0x0A4, 0x0C4, 0x0E4, 0x0124, 0x0164]),
        },
        fake_hidpp.Response("000001", 0x0910, "00"),  # supports y direction, no lod
        fake_hidpp.Response("0000000064E0100084E02000C4E02000", 0x0920, "000000"),
        fake_hidpp.Response("000001E4E0400124E0400164E06001C4", 0x0920, "000001"),
        fake_hidpp.Response("00000000000000000000000000000000", 0x0920, "000002"),
        fake_hidpp.Response("0000000064E0100084E02000C4E02000", 0x0920, "000100"),
        fake_hidpp.Response("000001E4E0400124E040016400000000", 0x0920, "000101"),
        fake_hidpp.Response("000064007400E4007400", 0x0950),
        fake_hidpp.Response("00006400E400", 0x0960, "00006400E400"),
        fake_hidpp.Response("00016400E400", 0x0960, "00016400E400"),
    ),
    Setup(
        FeatureTest(settings_templates.ExtendedAdjustableDpi, {0: 0x64, 1: 0xE4, 2: 1}, {1: 0x164}, 2, offset=0x9),
        {
            common.NamedInt(0, "X"): common.NamedInts.list([0x064, 0x074, 0x084, 0x0A4, 0x0C4, 0x0E4, 0x0124, 0x0164, 0x01C4]),
            common.NamedInt(1, "Y"): common.NamedInts.list([0x064, 0x074, 0x084, 0x0A4, 0x0C4, 0x0E4, 0x0124, 0x0164]),
            common.NamedInt(2, "LOD"): common.NamedInts(LOW=0, MEDIUM=1, HIGH=2),
        },
        fake_hidpp.Response("000003", 0x0910, "00"),  # supports y direction and lod
        fake_hidpp.Response("0000000064E0100084E02000C4E02000", 0x0920, "000000"),
        fake_hidpp.Response("000001E4E0400124E0400164E06001C4", 0x0920, "000001"),
        fake_hidpp.Response("00000000000000000000000000000000", 0x0920, "000002"),
        fake_hidpp.Response("0000000064E0100084E02000C4E02000", 0x0920, "000100"),
        fake_hidpp.Response("000001E4E0400124E040016400000000", 0x0920, "000101"),
        fake_hidpp.Response("000064007400E4007401", 0x0950),
        fake_hidpp.Response("00006400E401", 0x0960, "00006400E401"),
        fake_hidpp.Response("000064016401", 0x0960, "000064016401"),
    ),
]


@pytest.mark.parametrize("test", key_tests)
def test_key_template(test, mocker):
    tst = test.test
    device = fake_hidpp.Device(responses=test.responses, feature=tst.sclass.feature, offset=tst.offset, version=tst.version)
    spy_request = mocker.spy(device, "request")

    print("FEATURE", tst.sclass.feature)
    setting = settings_templates.check_feature(device, tst.sclass)
    assert setting is not None
    if isinstance(setting, list):
        setting = setting[0]
    if isinstance(test.choices, list):
        assert setting._validator.min_value == test.choices[0]
        assert setting._validator.max_value == test.choices[1]
    elif test.choices is not None:
        assert setting.choices == test.choices

    value = setting.read(cached=False)
    assert value == tst.initial_value

    write_value = setting.write(value)
    assert write_value == tst.initial_value

    for key, val in tst.write_value.items():
        write_value = setting.write_key_value(key, val)
        assert write_value == val
        value[key] = val

    if tst.rewrite:
        write_value = setting.write(value)

    fake_hidpp.match_requests(tst.matched_calls, test.responses, spy_request.call_args_list)


@pytest.mark.parametrize(
    "responses, currentSpeed, newSpeed",
    [
        (fake_hidpp.responses_speedchange, 100, 200),
        (fake_hidpp.responses_speedchange, None, 250),
    ],
)
def test_SpeedChange_action(responses, currentSpeed, newSpeed, mocker):
    device = fake_hidpp.Device(responses=responses, feature=hidpp20_constants.SupportedFeature.POINTER_SPEED)
    spy_setting_callback = mocker.spy(device, "setting_callback")
    settings_templates.check_feature_settings(device, device.settings)  # need to set up all the settings
    device.persister = {"pointer_speed": currentSpeed, "_speed-change": newSpeed}
    speed_setting = next(filter(lambda s: s.name == "speed-change", device.settings), None)
    pointer_setting = next(filter(lambda s: s.name == "pointer_speed", device.settings), None)

    speed_setting.write(237)
    speed_setting._rw.press_action()

    if newSpeed is not None and speed_setting is not None:
        spy_setting_callback.assert_any_call(device, type(pointer_setting), [newSpeed])
    assert device.persister["_speed-change"] == currentSpeed
    assert device.persister["pointer_speed"] == newSpeed


@pytest.mark.parametrize("test", simple_tests + key_tests)
def test_check_feature_settings(test, mocker):
    tst = test.test
    device = fake_hidpp.Device(responses=test.responses, feature=tst.sclass.feature, offset=tst.offset, version=tst.version)

    already_known = []
    setting = settings_templates.check_feature_settings(device, already_known)

    assert setting is True
    assert already_known


@pytest.mark.parametrize(
    "test",
    [
        Setup(
            FeatureTest(settings_templates.K375sFnSwap, False, True, offset=0x06),
            fake_hidpp.Response("FF0001", 0x0600, "FF"),
            fake_hidpp.Response("FF0101", 0x0610, "FF01"),
        )
    ],
)
def test_check_feature_setting(test, mocker):
    tst = test.test
    device = fake_hidpp.Device(responses=test.responses, feature=tst.sclass.feature, offset=tst.offset, version=tst.version)

    setting = settings_templates.check_feature_setting(device, tst.sclass.name)

    assert setting
