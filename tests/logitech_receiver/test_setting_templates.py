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
from struct import pack
from typing import Any
from typing import Optional

import pytest

from logitech_receiver import common
from logitech_receiver import hidpp20
from logitech_receiver import settings_templates
from logitech_receiver import special_keys
from solaar import configuration

from . import hidpp

# TODO DpiSlidingXY, MouseGesturesXY, SpeedChange
# TODO Gesture2Gestures, Gesture2Divert, Gesture2Params, MKeyLEDs, Equalizer, LEDZoneSetting
# TODO future RGB..., RGB..., BrightnessControl


@dataclass
class RegisterTest:
    sclass: Any
    initial_value: Any = False
    write_value: Any = True
    write_params: str = ""


tests = [
    [
        RegisterTest(settings_templates.RegisterHandDetection, False, True, [b"\x00\x00\x00"]),
        hidpp.Response("000030", 0x8101),  # keyboard_hand_detection
        hidpp.Response("000000", 0x8001, "000000"),
    ],
    [
        RegisterTest(settings_templates.RegisterHandDetection, True, False, [b"\x00\x00\x30"]),
        hidpp.Response("000000", 0x8101),  # keyboard_hand_detection
        hidpp.Response("000030", 0x8001, "000030"),
    ],
    [
        RegisterTest(settings_templates.RegisterSmoothScroll, False, True, [b"\x40"]),
        hidpp.Response("00", 0x8101),  # mouse_button_flags
        hidpp.Response("40", 0x8001, "40"),
    ],
    [
        RegisterTest(settings_templates.RegisterSideScroll, True, False, [b"\x00"]),
        hidpp.Response("02", 0x8101),  # mouse_button_flags
        hidpp.Response("00", 0x8001, "00"),
    ],
    [
        RegisterTest(settings_templates.RegisterFnSwap, False, True, [b"\x00\x01"]),
        hidpp.Response("0000", 0x8109),  # keyboard_fn_swap
        hidpp.Response("0001", 0x8009, "0001"),
    ],
    [
        RegisterTest(
            settings_templates._PerformanceMXDpi, common.NamedInt(0x88, "800"), common.NamedInt(0x89, "900"), [b"\x89"]
        ),
        hidpp.Response("88", 0x8163),  # mouse_dpi
        hidpp.Response("89", 0x8063, "89"),
    ],
]


@pytest.mark.parametrize("test", tests)
def test_register_template(test, mocker):
    device = hidpp.Device(responses=test[1:])
    device.persister = configuration._DeviceEntry()
    device.protocol = 1.0
    spy_request = mocker.spy(device, "request")

    setting = test[0].sclass.build(device)
    value = setting.read(cached=False)
    cached_value = setting.read(cached=True)
    write_value = setting.write(test[0].write_value)

    assert setting is not None
    assert value == test[0].initial_value
    assert cached_value == test[0].initial_value
    assert write_value == test[0].write_value
    spy_request.assert_called_with(test[0].sclass.register + 0x8000, *test[0].write_params)


@dataclass
class FeatureTest:
    sclass: Any
    initial_value: Any = False
    write_value: Any = True
    write_fnid: int = 0x10
    write_params: str = ""
    no_reply: Optional[bool] = False


tests = [
    [
        FeatureTest(settings_templates.K375sFnSwap, False, True, 0x10, "FF01"),
        hidpp.Response("060001", 0x0000, "40A3"),  # K375_FN_INVERSION
        hidpp.Response("FF0001", 0x0600, "FF"),
        hidpp.Response("FF0101", 0x0610, "FF01"),
    ],
    [
        FeatureTest(settings_templates.FnSwap, True, False, 0x10, "00"),
        hidpp.Response("040001", 0x0000, "40A0"),  # FN_INVERSION
        hidpp.Response("01", 0x0400),
        hidpp.Response("00", 0x0410, "00"),
    ],
    [
        FeatureTest(settings_templates.NewFnSwap, True, False, 0x10, "00"),
        hidpp.Response("040001", 0x0000, "40A2"),  # NEW_FN_INVERSION
        hidpp.Response("01", 0x0400),
        hidpp.Response("00", 0x0410, "00"),
    ],
    [
        FeatureTest(settings_templates.Backlight, 0, 5, 0x10, "05"),
        hidpp.Response("060001", 0x0000, "1981"),  # BACKLIGHT
        hidpp.Response("00", 0x0600),
        hidpp.Response("05", 0x0610, "05"),
    ],
    [
        FeatureTest(settings_templates.Backlight2DurationHandsOut, 80, 160, 0x10, "0118FF00200040006000", None),
        hidpp.Response("040003", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("011830000000100040006000", 0x0400),
        hidpp.Response("0118FF00200040006000", 0x0410, "0118FF00200040006000"),
    ],
    [
        FeatureTest(settings_templates.Backlight2DurationHandsIn, 320, 160, 0x10, "0118FF00200020006000", None),
        hidpp.Response("040003", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("011830000000200040006000", 0x0400),
        hidpp.Response("0118FF00200020006000", 0x0410, "0118FF00200020006000"),
    ],
    [
        FeatureTest(settings_templates.Backlight2DurationPowered, 480, 80, 0x10, "0118FF00200040001000", None),
        hidpp.Response("040003", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("011830000000200040006000", 0x0400),
        hidpp.Response("0118FF00200040001000", 0x0410, "0118FF00200040001000"),
    ],
    [
        FeatureTest(settings_templates.Backlight3, 0x50, 0x70, 0x20, "007009"),
        hidpp.Response("040001", 0x0000, "1983"),  # BACKLIGHT3
        hidpp.Response("50", 0x0410),
        hidpp.Response("70", 0x0420, "007009"),
    ],
    [
        FeatureTest(settings_templates.HiResScroll, True, False, 0x10, "00"),
        hidpp.Response("040001", 0x0000, "2120"),  # HI_RES_SCROLLING
        hidpp.Response("01", 0x0400),
        hidpp.Response("00", 0x0410, "00"),
    ],
    [
        FeatureTest(settings_templates.LowresMode, False, True, 0x10, "01"),
        hidpp.Response("040001", 0x0000, "2130"),  # LOWRES_WHEEL
        hidpp.Response("00", 0x0400),
        hidpp.Response("01", 0x0410, "01"),
    ],
    [
        FeatureTest(settings_templates.HiresSmoothInvert, True, False, 0x20, "02"),
        hidpp.Response("040001", 0x0000, "2121"),  # HIRES_WHEEL
        hidpp.Response("06", 0x0410),
        hidpp.Response("02", 0x0420, "02"),
    ],
    [
        FeatureTest(settings_templates.HiresSmoothResolution, True, False, 0x20, "04"),
        hidpp.Response("040001", 0x0000, "2121"),  # HIRES_WHEEL
        hidpp.Response("06", 0x0410),
        hidpp.Response("04", 0x0420, "04"),
    ],
    [
        FeatureTest(settings_templates.HiresMode, False, True, 0x20, "07"),
        hidpp.Response("040001", 0x0000, "2121"),  # HIRES_WHEEL
        hidpp.Response("06", 0x0410),
        hidpp.Response("07", 0x0420, "07"),
    ],
    [
        FeatureTest(settings_templates.PointerSpeed, 0x0100, 0x0120, 0x10, "0120"),
        hidpp.Response("040001", 0x0000, "2205"),  # POINTER_SPEED
        hidpp.Response("0100", 0x0400),
        hidpp.Response("0120", 0x0410, "0120"),
    ],
    [
        FeatureTest(settings_templates.ThumbMode, True, False, 0x20, "0000"),
        hidpp.Response("040001", 0x0000, "2150"),  # THUMB_WHEEL
        hidpp.Response("0100", 0x0410),
        hidpp.Response("0000", 0x0420, "0000"),
    ],
    [
        FeatureTest(settings_templates.ThumbInvert, False, True, 0x20, "0101"),
        hidpp.Response("040001", 0x0000, "2150"),  # THUMB_WHEEL
        hidpp.Response("0100", 0x0410),
        hidpp.Response("0101", 0x0420, "0101"),
    ],
    [
        FeatureTest(settings_templates.DivertCrown, False, True, 0x20, "02"),
        hidpp.Response("040001", 0x0000, "4600"),  # CROWN
        hidpp.Response("01", 0x0410),
        hidpp.Response("02", 0x0420, "02"),
    ],
    [
        FeatureTest(settings_templates.CrownSmooth, True, False, 0x20, "0002"),
        hidpp.Response("040001", 0x0000, "4600"),  # CROWN
        hidpp.Response("0001", 0x0410),
        hidpp.Response("0002", 0x0420, "0002"),
    ],
    [
        FeatureTest(settings_templates.DivertGkeys, False, True, 0x20, "01"),
        hidpp.Response("040001", 0x0000, "8010"),  # GKEY
        hidpp.Response("01", 0x0420, "01"),
    ],
    [
        FeatureTest(settings_templates.ScrollRatchet, 2, 1, 0x10, "01"),
        hidpp.Response("040001", 0x0000, "2110"),  # SMART_SHIFT
        hidpp.Response("02", 0x0400),
        hidpp.Response("01", 0x0410, "01"),
    ],
    [
        FeatureTest(settings_templates.SmartShift, 1, 10, 0x10, "000A"),
        hidpp.Response("040001", 0x0000, "2110"),  # SMART_SHIFT
        hidpp.Response("0100", 0x0400),
        hidpp.Response("000A", 0x0410, "000A"),
    ],
    [
        FeatureTest(settings_templates.SmartShift, 5, 50, 0x10, "00FF"),
        hidpp.Response("040001", 0x0000, "2110"),  # SMART_SHIFT
        hidpp.Response("0005", 0x0400),
        hidpp.Response("00FF", 0x0410, "00FF"),
    ],
    [
        FeatureTest(settings_templates.SmartShiftEnhanced, 5, 50, 0x20, "00FF"),
        hidpp.Response("040001", 0x0000, "2111"),  # SMART_SHIFT_ENHANCED
        hidpp.Response("0005", 0x0410),
        hidpp.Response("00FF", 0x0420, "00FF"),
    ],
    [
        FeatureTest(settings_templates.DisableKeyboardKeys, {1: True, 8: True}, {1: False, 8: True}, 0x20, "08"),
        hidpp.Response("040003", 0x0000, "4521"),  # KEYBOARD_DISABLE_KEYS
        hidpp.Response("09", 0x0400),
        hidpp.Response("09", 0x0410),
        hidpp.Response("08", 0x0420, "08"),
    ],
    [
        FeatureTest(settings_templates.DualPlatform, 0, 1, 0x20, "01"),
        hidpp.Response("040003", 0x0000, "4530"),  # DUALPLATFORM
        hidpp.Response("00", 0x0400),
        hidpp.Response("01", 0x0420, "01"),
    ],
    [
        FeatureTest(settings_templates.MRKeyLED, False, True, 0x00, "01"),
        hidpp.Response("040003", 0x0000, "8030"),  # MR
        hidpp.Response("01", 0x0400, "01"),
    ],
    [
        FeatureTest(settings_templates.Sidetone, 5, 0xA, 0x10, "0A"),
        hidpp.Response("040003", 0x0000, "8300"),  # SIDETONE
        hidpp.Response("05", 0x0400),
        hidpp.Response("0A", 0x0410, "0A"),
    ],
    [
        FeatureTest(settings_templates.ADCPower, 5, 0xA, 0x20, "0A"),
        hidpp.Response("040003", 0x0000, "1F20"),  # ADC_MEASUREMENT
        hidpp.Response("05", 0x0410),
        hidpp.Response("0A", 0x0420, "0A"),
    ],
    [
        FeatureTest(settings_templates.LEDControl, 0, 1, 0x80, "01"),
        hidpp.Response("040003", 0x0000, "8070"),  # COLOR_LED_EFFECTS
        hidpp.Response("00", 0x0470),
        hidpp.Response("01", 0x0480, "01"),
    ],
]


@pytest.mark.parametrize("test", tests)
def test_simple_template(test, mocker):
    setup_responses = [hidpp.Response("010001", 0x0000, "0001"), hidpp.Response("20", 0x0100)]
    device = hidpp.Device(responses=test[1:] + setup_responses)
    device.persister = configuration._DeviceEntry()
    device.features = hidpp20.FeaturesArray(device)
    spy_feature_request = mocker.spy(device, "feature_request")

    setting = settings_templates.check_feature(device, test[0].sclass)
    value = setting.read(cached=False)
    cached_value = setting.read(cached=True)
    write_value = setting.write(test[0].write_value)

    assert setting is not None
    assert value == test[0].initial_value
    assert cached_value == test[0].initial_value
    assert write_value == test[0].write_value
    params = bytes.fromhex(test[0].write_params)
    no_reply = {"no_reply": test[0].no_reply} if test[0].no_reply is not None else {}
    spy_feature_request.assert_called_with(test[0].sclass.feature, test[0].write_fnid, params, **no_reply)


@pytest.fixture
def mock_gethostname(mocker):
    mocker.patch("socket.gethostname", return_value="ABCDEF.foo.org")


tests = [
    [
        FeatureTest(settings_templates.Backlight2, 0xFF, 0x00, 0x10, "0102ff00000000000000", None),
        common.NamedInts(Disabled=0xFF, Enabled=0x00),
        hidpp.Response("040001", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("000201000000000000000000", 0x0400),
        hidpp.Response("010201", 0x0410, "0102ff00000000000000"),
    ],
    [
        FeatureTest(settings_templates.Backlight2, 0x03, 0xFF, 0x10, "0018ff00000000000000", None),
        common.NamedInts(Disabled=0xFF, Automatic=0x01, Manual=0x03),
        hidpp.Response("040001", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("011838000000000000000000", 0x0400),
        hidpp.Response("001801", 0x0410, "0018ff00000000000000"),
    ],
    [
        FeatureTest(settings_templates.Backlight2Level, 0, 3, 0x10, "0118ff03000000000000", None),
        [0, 4],
        hidpp.Response("040003", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("011830000000000000000000", 0x0400),
        hidpp.Response("01180103000000000000", 0x0410, "0118ff03000000000000"),
        hidpp.Response("05", 0x0420),
    ],
    [
        FeatureTest(settings_templates.Backlight2Level, 0, 2, 0x10, "0118ff02000000000000", None),
        [0, 4],
        hidpp.Response("040003", 0x0000, "1982"),  # BACKLIGHT2
        hidpp.Response("011830000000000000000000", 0x0400),
        hidpp.Response("01180102000000000000", 0x0410, "0118ff02000000000000"),
        hidpp.Response("05", 0x0420),
    ],
    [
        FeatureTest(settings_templates.OnboardProfiles, 2, 1, 0x30, "0001", None),
        common.NamedInts(**{"Disabled": 0, "Profile 1": 1, "Profile 2": 2}),
        hidpp.Response("0C0003", 0x0000, "8100"),  # ONBOARD_PROFILES
        hidpp.Response("00010100000201FFFFFFFFFFFFFFFFFF", 0x0C50, "00000000"),
        hidpp.Response("000201FFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000004"),
        hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000008"),
        hidpp.Response("01", 0x0C20),
        hidpp.Response("0002", 0x0C40),
        hidpp.Response("01", 0x0C10, "01"),
        hidpp.Response("0001", 0x0C30, "0001"),
    ],
    [
        FeatureTest(settings_templates.OnboardProfiles, 1, 0, 0x10, "02", None),
        common.NamedInts(**{"Disabled": 0, "Profile 1": 1, "Profile 2": 2}),
        hidpp.Response("0C0003", 0x0000, "8100"),  # ONBOARD_PROFILES
        hidpp.Response("00010100000201FFFFFFFFFFFFFFFFFF", 0x0C50, "00000000"),
        hidpp.Response("000201FFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000004"),
        hidpp.Response("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 0x0C50, "00000008"),
        hidpp.Response("01", 0x0C20),
        hidpp.Response("0001", 0x0C40),
        hidpp.Response("02", 0x0C10, "02"),
    ],
    [
        FeatureTest(settings_templates.ReportRate, 1, 5, 0x20, "05"),
        common.NamedInts(**{"1ms": 1, "2ms": 2, "5ms": 5, "6ms": 6}),
        hidpp.Response("0C0003", 0x0000, "8060"),  # REPORT_RATE
        hidpp.Response("33", 0x0C00),
        hidpp.Response("01", 0x0C10),
        hidpp.Response("05", 0x0C20, "05"),
    ],
    [
        FeatureTest(settings_templates.ExtendedReportRate, 1, 5, 0x30, "05"),
        common.NamedInts(**{"8ms": 0, "4ms": 1, "500us": 4, "250us": 5}),
        hidpp.Response("0C0003", 0x0000, "8061"),  # EXTENDED_REPORT_RATE
        hidpp.Response("33", 0x0C10),
        hidpp.Response("01", 0x0C20),
        hidpp.Response("05", 0x0C30, "05"),
    ],
    #    [
    #        FeatureTest(settings_templates.AdjustableDpi, 800, 400, 0x30, "000190"),
    #        common.NamedInts.list([400, 800, 1600]),
    #        hidpp.Response("040003", 0x0000, "2201"),  # ADJUSTABLE_DPI
    #        hidpp.Response("000190032006400000", 0x0410, "000000"),
    #        hidpp.Response("000320", 0x0420),
    #        hidpp.Response("000190", 0x0430, "000190"),
    #    ],
    #    [
    #        FeatureTest(settings_templates.AdjustableDpi, 256, 512, 0x30, "000200"),
    #        common.NamedInts.list([256, 512]),
    #        hidpp.Response("040003", 0x0000, "2201"),  # ADJUSTABLE_DPI
    #        hidpp.Response("000100e10002000000", 0x0410, "000000"),
    #        hidpp.Response("000100", 0x0420),
    #        hidpp.Response("000200", 0x0430, "000200"),
    #    ],
    #    [
    #        FeatureTest(settings_templates.ExtendedAdjustableDpi, 256, 512, 0x60, "000200"),
    #        common.NamedInts.list([256, 512]),
    #        hidpp.Response("090000", 0x0000, "2202"),  # EXTENDED_ADJUSTABLE_DPI
    #        hidpp.Response("000000", 0x0910, "00"),  # no y direction
    #        hidpp.Response("0000000100e10002000000", 0x0920, "000000"),
    #        hidpp.Response("000100", 0x0950),
    #        hidpp.Response("000200", 0x0960, "000200"),
    #    ],
    #    [
    #        FeatureTest(settings_templates.ExtendedAdjustableDpi, 0x64, 0x164, 0x60, "0001640164"),
    #        common.NamedInts.list([0x064, 0x074, 0x084, 0x0A4, 0x0C4, 0x0E4, 0x0124, 0x0164, 0x01C4]),
    #        hidpp.Response("090000", 0x0000, "2202"),  # EXTENDED_ADJUSTABLE_DPI
    #        hidpp.Response("000001", 0x0910, "00"),  # supports y direction
    #        hidpp.Response("0000000064E0100084E02000C4E02000", 0x0920, "000000"),
    #        hidpp.Response("000001E4E0400124E0400164E06001C4", 0x0920, "000001"),
    #        hidpp.Response("00000000000000000000000000000000", 0x0920, "000002"),
    #        hidpp.Response("000064", 0x0950),
    #        hidpp.Response("0001640164", 0x0960, "0001640164"),
    #    ],
    [
        FeatureTest(settings_templates.Multiplatform, 0, 1, 0x30, "FF01"),
        common.NamedInts(**{"MacOS 0.1-0.5": 0, "iOS 0.1-0.7": 1, "Linux 0.2-0.9": 2, "Windows 0.3-0.9": 3}),
        hidpp.Response("040003", 0x0000, "4531"),  # MULTIPLATFORM
        hidpp.Response("020004000001", 0x0400),
        hidpp.Response("00FF200000010005", 0x0410, "00"),
        hidpp.Response("01FF400000010007", 0x0410, "01"),
        hidpp.Response("02FF040000020009", 0x0410, "02"),
        hidpp.Response("03FF010000030009", 0x0410, "03"),
        hidpp.Response("FF01", 0x0430, "FF01"),
    ],
    [
        FeatureTest(settings_templates.ChangeHost, 1, 0, 0x10, "00", True),
        common.NamedInts(**{"1:ABCDEF": 0, "2:GHIJKL": 1}),
        hidpp.Response("040003", 0x0000, "1814"),  # CHANGE_HOST
        hidpp.Response("050003", 0x0000, "1815"),  # HOSTS_INFO
        hidpp.Response("01000200", 0x0500),
        hidpp.Response("000100000600", 0x0510, "00"),
        hidpp.Response("000041424344454600", 0x0530, "0000"),
        hidpp.Response("000100000600", 0x0510, "01"),
        hidpp.Response("00004748494A4B4C00", 0x0530, "0100"),
        hidpp.Response("0201", 0x0400),
        hidpp.Response(True, 0x0410, "00"),
    ],
]


@pytest.mark.parametrize("test", tests)
def test_variable_template(test, mocker, mock_gethostname):
    setup_responses = [hidpp.Response("010001", 0x0000, "0001"), hidpp.Response("20", 0x0100)]
    device = hidpp.Device(responses=test[2:] + setup_responses)
    device.persister = configuration._DeviceEntry()
    device.features = hidpp20.FeaturesArray(device)
    spy_feature_request = mocker.spy(device, "feature_request")

    setting = settings_templates.check_feature(device, test[0].sclass)
    print("CH", setting)
    print("CH", setting.choices)
    value = setting.read(cached=False)
    print("CV", value)
    cached_value = setting.read(cached=True)
    write_value = setting.write(test[0].write_value)

    assert setting is not None
    if isinstance(test[1], common.NamedInts):
        assert len(setting.choices) == len(test[1])
        for setting_choice, expected_choice in zip(setting.choices, test[1]):
            assert setting_choice == expected_choice
    if isinstance(test[1], list):
        assert setting._validator.min_value == test[1][0]
        assert setting._validator.max_value == test[1][1]
    print("VALYE", value, test[0].initial_value)
    assert value == test[0].initial_value
    assert cached_value == test[0].initial_value
    assert write_value == test[0].write_value

    params = bytes.fromhex(test[0].write_params)
    no_reply = {"no_reply": test[0].no_reply} if test[0].no_reply is not None else {}
    spy_feature_request.assert_called_with(test[0].sclass.feature, test[0].write_fnid, params, **no_reply)


responses_reprog_controls = [
    hidpp.Response("050001", 0x0000, "1B04"),  # REPROG_CONTROLS_V4
    hidpp.Response("03", 0x0500),
    hidpp.Response("00500038010001010400000000000000", 0x0510, "00"),  # left button
    hidpp.Response("00510039010001010400000000000000", 0x0510, "01"),  # right button
    hidpp.Response("00C4009D310003070500000000000000", 0x0510, "02"),  # smart shift
    hidpp.Response("00500000000000000000000000000000", 0x0520, "0050"),  # left button current
    hidpp.Response("00510000500000000000000000000000", 0x0520, "0051"),  # right button current
    hidpp.Response("00C40000000000000000000000000000", 0x0520, "00C4"),  # smart shift current
    hidpp.Response("0051000051", 0x0530, "0051000051"),  # right button set
]

responses_remappable_action = responses_reprog_controls + [
    hidpp.Response("040001", 0x0000, "1C00"),  # PERSISTENT_REMAPPABLE_ACTION
    hidpp.Response("0041", 0x0400),
    hidpp.Response("0201", 0x0410),
    hidpp.Response("02", 0x0400),
    hidpp.Response("0050", 0x0420, "00FF"),  # left button
    hidpp.Response("0051", 0x0420, "01FF"),  # right button
    hidpp.Response("0050000100500000", 0x0430, "0050FF"),  # left button current
    hidpp.Response("0051000100500001", 0x0430, "0051FF"),  # right button current
    hidpp.Response("0051FF01005100", 0x0440, "0051FF01005100"),  # right button set
]

tests = [
    [
        FeatureTest(
            settings_templates.ReprogrammableKeys, {0x50: 0x50, 0x51: 0x50, 0xC4: 0xC4}, {0x51: 0x51}, 0x30, "0051000051"
        ),
        {
            common.NamedInt(0x50, "Left Button"): [0x50, 0x51],
            common.NamedInt(0x51, "Right Button"): [0x51, 0x50],
            common.NamedInt(0xC4, "Smart Shift"): [0xC4, 0x50, 0x51],
        },
    ]
    + responses_reprog_controls,
    [
        FeatureTest(settings_templates.DivertKeys, {0xC4: 0}, {0xC4: 1}, 0x30, "00C4030000"),
        {common.NamedInt(0xC4, "Smart Shift"): [0, 1, 2]},
    ]
    + responses_reprog_controls
    + [hidpp.Response("00C4030000", 0x0530, "00C4030000")],
    [
        FeatureTest(
            settings_templates.PersistentRemappableAction,
            {80: 16797696, 81: 16797696},
            {0x51: 16797952},
            0x40,
            "0051FF01005100",
        ),
        {
            common.NamedInt(80, "Left Button"): special_keys.KEYS_KEYS_CONSUMER,
            common.NamedInt(81, "Right Button"): special_keys.KEYS_KEYS_CONSUMER,
        },
    ]
    + responses_remappable_action,
]


@pytest.mark.parametrize("test", tests)
def test_key_template(test, mocker):
    setup_responses = [hidpp.Response("010001", 0x0000, "0001"), hidpp.Response("20", 0x0100)]
    device = hidpp.Device(responses=test[2:] + setup_responses)
    device.persister = configuration._DeviceEntry()
    device.features = hidpp20.FeaturesArray(device)
    spy_feature_request = mocker.spy(device, "feature_request")

    setting = settings_templates.check_feature(device, test[0].sclass)
    assert setting is not None
    assert len(setting.choices) == len(test[1])
    for k, v in setting.choices.items():
        assert len(v) == len(test[1][k])
        for setting_key, test_key in zip(v, test[1][k]):
            assert setting_key == test_key

    value = setting.read(cached=False)
    for k, v in test[0].initial_value.items():
        assert value[k] == v

    for key, value in test[0].write_value.items():
        write_value = setting.write_key_value(key, value)
        assert write_value == value

    assert spy_feature_request.call_args_list[-1][0][0] == test[0].sclass.feature
    assert spy_feature_request.call_args_list[-1][0][1] == test[0].write_fnid
    param = b"".join(pack("B", p) if isinstance(p, int) else p for p in spy_feature_request.call_args_list[-1][0][2:])
    assert param == bytes.fromhex(test[0].write_params)


tests = [  # needs settings to be set up!!
    [
        FeatureTest(settings_templates.SpeedChange, 0, 0xED, 0x60, "000200"),
        common.NamedInts(**{"Off": 0, "DPI Change": 0xED}),
        hidpp.Response("040001", 0x0000, "2205"),  # POINTER_SPEED
        hidpp.Response("0100", 0x0400),
        hidpp.Response("0120", 0x0410, "0120"),
        hidpp.Response("050001", 0x0000, "1B04"),  # REPROG_CONTROLS_V4
        hidpp.Response("01", 0x0500),
        hidpp.Response("00ED009D310003070500000000000000", 0x0510, "00"),  # DPI Change
        hidpp.Response("00ED0000000000000000000000000000", 0x0520, "00ED"),  # DPI Change current
    ],
]


@pytest.mark.parametrize("test", tests)
def XX_action_template(test, mocker):  # needs settings to be set up!!
    setup_responses = [hidpp.Response("010001", 0x0000, "0001"), hidpp.Response("20", 0x0100)]
    device = hidpp.Device(responses=test[2:] + setup_responses)
    device.persister = configuration._DeviceEntry()
    device.features = hidpp20.FeaturesArray(device)
    spy_feature_request = mocker.spy(device, "feature_request")

    setting = settings_templates.check_feature(device, test[0].sclass)
    value = setting.read(cached=False)
    cached_value = setting.read(cached=True)
    write_value = setting.write(test[0].write_value)

    assert setting is not None
    if isinstance(test[1], common.NamedInts):
        assert len(setting.choices) == len(test[1])
        for setting_choice, expected_choice in zip(setting.choices, test[1]):
            assert setting_choice == expected_choice
    if isinstance(test[1], list):
        assert setting._validator.min_value == test[1][0]
        assert setting._validator.max_value == test[1][1]
    assert value == test[0].initial_value
    assert cached_value == test[0].initial_value
    assert write_value == test[0].write_value

    params = bytes.fromhex(test[0].write_params)
    no_reply = {"no_reply": test[0].no_reply} if test[0].no_reply is not None else {}
    spy_feature_request.assert_called_with(test[0].sclass.feature, test[0].write_fnid, params, **no_reply)
