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

import pytest

from logitech_receiver import common
from logitech_receiver import hidpp20
from logitech_receiver import hidpp20_constants
from logitech_receiver.hidpp20_constants import SupportedFeature

from . import fake_hidpp

_hidpp20 = hidpp20.Hidpp20()


def test_get_firmware():
    responses = [
        fake_hidpp.Response("02FFFF", 0x0400),
        fake_hidpp.Response("01414243030401000101000102030405", 0x0410, "00"),
        fake_hidpp.Response("02414243030401000101000102030405", 0x0410, "01"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.DEVICE_FW_VERSION)

    result = _hidpp20.get_firmware(device)

    assert len(result) == 2
    assert isinstance(result[0], common.FirmwareInfo)
    assert isinstance(result[1], common.FirmwareInfo)


def test_get_ids():
    responses = [fake_hidpp.Response("FF12345678000D123456789ABC", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.DEVICE_FW_VERSION)

    unitId, modelId, tid_map = _hidpp20.get_ids(device)

    assert unitId == "12345678"
    assert modelId == "123456789ABC"
    assert tid_map == {"btid": "1234", "wpid": "5678", "usbid": "9ABC"}


def test_get_kind():
    responses = [fake_hidpp.Response("00", 0x0420)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.DEVICE_NAME)

    result = _hidpp20.get_kind(device)

    assert result == "keyboard"
    assert result == 1


def test_get_name():
    responses = [
        fake_hidpp.Response("12", 0x0400),
        fake_hidpp.Response("4142434445464748494A4B4C4D4E4F", 0x0410, "00"),
        fake_hidpp.Response("505152530000000000000000000000", 0x0410, "0F"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.DEVICE_NAME)

    result = _hidpp20.get_name(device)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_friendly_name():
    responses = [
        fake_hidpp.Response("12", 0x0400),
        fake_hidpp.Response("004142434445464748494A4B4C4D4E", 0x0410, "00"),
        fake_hidpp.Response("0E4F50515253000000000000000000", 0x0410, "0E"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.DEVICE_FRIENDLY_NAME)

    result = _hidpp20.get_friendly_name(device)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_battery_status():
    responses = [fake_hidpp.Response("502000FFFF", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.BATTERY_STATUS)

    feature, battery = _hidpp20.get_battery_status(device)

    assert feature == SupportedFeature.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.BatteryStatus.DISCHARGING


def test_get_battery_voltage():
    responses = [fake_hidpp.Response("1000FFFFFF", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.BATTERY_VOLTAGE)

    feature, battery = _hidpp20.get_battery_voltage(device)

    assert feature == SupportedFeature.BATTERY_VOLTAGE
    assert battery.level == 92
    assert common.BatteryStatus.RECHARGING in battery.status
    assert battery.voltage == 0x1000


def test_get_battery_unified():
    responses = [fake_hidpp.Response("500100FFFF", 0x0410)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.UNIFIED_BATTERY)

    feature, battery = _hidpp20.get_battery_unified(device)

    assert feature == SupportedFeature.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.BatteryStatus.DISCHARGING


def test_get_adc_measurement():
    responses = [fake_hidpp.Response("100003", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.ADC_MEASUREMENT)

    feature, battery = _hidpp20.get_adc_measurement(device)

    assert feature == SupportedFeature.ADC_MEASUREMENT
    assert battery.level == 92
    assert battery.status == common.BatteryStatus.RECHARGING
    assert battery.voltage == 0x1000


def test_get_battery():
    responses = [fake_hidpp.Response("502000FFFF", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.BATTERY_STATUS)

    feature, battery = _hidpp20.get_battery(device, SupportedFeature.BATTERY_STATUS)

    assert feature == SupportedFeature.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.BatteryStatus.DISCHARGING


def test_get_battery_none():
    responses = [
        fake_hidpp.Response(None, 0x0000, f"{int(SupportedFeature.BATTERY_STATUS):0>4X}"),
        fake_hidpp.Response(None, 0x0000, f"{int(SupportedFeature.BATTERY_VOLTAGE):0>4X}"),
        fake_hidpp.Response("500100ffff", 0x0410),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.UNIFIED_BATTERY)

    feature, battery = _hidpp20.get_battery(device, None)

    assert feature == SupportedFeature.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.BatteryStatus.DISCHARGING


# get_keys is in test_hidpp20_complex
# get_remap_keys is in test_hidpp20_complex
# TODO get_gestures is complex
# get_backlight is in test_hidpp20_complex
# get_profiles is in test_hidpp20_complex


def test_get_mouse_pointer_info():
    responses = [fake_hidpp.Response("01000A", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.MOUSE_POINTER)

    result = _hidpp20.get_mouse_pointer_info(device)

    assert result == {
        "dpi": 0x100,
        "acceleration": "med",
        "suggest_os_ballistics": False,
        "suggest_vertical_orientation": True,
    }


def test_get_vertical_scrolling_info():
    responses = [fake_hidpp.Response("01080C", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.VERTICAL_SCROLLING)

    result = _hidpp20.get_vertical_scrolling_info(device)

    assert result == {"roller": "standard", "ratchet": 8, "lines": 12}


def test_get_hi_res_scrolling_info():
    responses = [fake_hidpp.Response("0102", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HI_RES_SCROLLING)

    mode, resolution = _hidpp20.get_hi_res_scrolling_info(device)

    assert mode == 1
    assert resolution == 2


def test_get_pointer_speed_info():
    responses = [fake_hidpp.Response("0102", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.POINTER_SPEED)

    result = _hidpp20.get_pointer_speed_info(device)

    assert result == 0x0102 / 256


def test_get_lowres_wheel_status():
    responses = [fake_hidpp.Response("01", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.LOWRES_WHEEL)

    result = _hidpp20.get_lowres_wheel_status(device)

    assert result == "HID++"


def test_get_hires_wheel():
    responses = [
        fake_hidpp.Response("010C", 0x0400),
        fake_hidpp.Response("05FF", 0x0410),
        fake_hidpp.Response("03FF", 0x0430),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HIRES_WHEEL)

    multi, has_invert, has_ratchet, inv, res, target, ratchet = _hidpp20.get_hires_wheel(device)

    assert multi == 1
    assert has_invert is True
    assert has_ratchet is True
    assert inv is True
    assert res is False
    assert target is True
    assert ratchet is True


def test_get_new_fn_inversion():
    responses = [fake_hidpp.Response("0300", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.NEW_FN_INVERSION)

    result = _hidpp20.get_new_fn_inversion(device)

    assert result == (True, False)


@pytest.fixture
def mock_gethostname(mocker):
    mocker.patch("socket.gethostname", return_value="ABCDEFG.foo.org")


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([fake_hidpp.Response(None, 0x0400)], {}),
        ([fake_hidpp.Response("02000000", 0x0400)], {}),
        (
            [
                fake_hidpp.Response("03000200", 0x0400),
                fake_hidpp.Response("000105010518", 0x0410, "00"),
                fake_hidpp.Response("00004142434445", 0x0430, "0000"),
                fake_hidpp.Response("010105011018", 0x0410, "01"),
                fake_hidpp.Response("01004142434445464748494A4B4C4D4E", 0x0430, "0100"),
                fake_hidpp.Response("010E4F50000000000000000000000000", 0x0430, "010E"),
                fake_hidpp.Response("0007", 0x0440, "000041424344454647"),
            ],
            {0: (True, "ABCDEFG"), 1: (True, "ABCDEFGHIJKLMNOP")},
        ),
        (  # a character split between two parts of a name
            [
                fake_hidpp.Response("03000200", 0x0400),
                fake_hidpp.Response("000105010718", 0x0410, "00"),
                fake_hidpp.Response("000041424344454647", 0x0430, "0000"),
                fake_hidpp.Response("010105011118", 0x0410, "01"),
                fake_hidpp.Response("01004142434445464748494A4B4C4DE2", 0x0430, "0100"),
                fake_hidpp.Response("010E809973", 0x0430, "010E"),
            ],
            {0: (True, "ABCDEFG"), 1: (True, "ABCDEFGHIJKLM’s")},
        ),
    ],
)
def test_get_host_names(responses, expected_result, mock_gethostname):
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)

    result = _hidpp20.get_host_names(device)

    assert result == expected_result


def test_get_host_names_set_current_host_name(mocker):
    """A Bolt slot that the device reset to the name of the receiver gets the name of this computer back"""
    mocker.patch("socket.gethostname", return_value="omarchy-desktop.lan")
    responses = [
        fake_hidpp.Response("13080302", 0x0400),
        fake_hidpp.Response("000105010D18", 0x0410, "00"),
        fake_hidpp.Response("0000574F524B2D4C4150544F502D31", 0x0430, "0000"),
        fake_hidpp.Response("010104011418", 0x0410, "01"),
        fake_hidpp.Response("0100416C6578E2809973204D6163426F", 0x0430, "0100"),
        fake_hidpp.Response("010E6F6B2050726F", 0x0430, "010E"),
        fake_hidpp.Response("020105011618", 0x0410, "02"),
        fake_hidpp.Response("02004C6F67697465636820426F6C7420", 0x0430, "0200"),
        fake_hidpp.Response("020E7265636569766572", 0x0430, "020E"),
        fake_hidpp.Response("020E", 0x0440, "02006F6D61726368792D6465736B746F"),
        fake_hidpp.Response("020F", 0x0440, "020E70"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)
    spy_request = mocker.spy(device, "request")

    result = _hidpp20.get_host_names(device)

    assert result == {0: (True, "WORK-LAPTOP-1"), 1: (True, "Alex’s MacBook Pro"), 2: (True, "omarchy-desktop")}
    spy_request.assert_any_call(0x0440, 2, 0x00, b"omarchy-deskto", no_reply=False)
    spy_request.assert_called_with(0x0440, 2, 0x0E, b"p", no_reply=False)


@pytest.mark.parametrize(
    "responses",
    [
        [  # host index in the reply is wrong
            fake_hidpp.Response("03000200", 0x0400),
            fake_hidpp.Response("010105010718", 0x0410, "00"),
            fake_hidpp.Response("010105010318", 0x0410, "01"),
            fake_hidpp.Response("0100484A4B", 0x0430, "0100"),
        ],
        [  # no reply
            fake_hidpp.Response("03000200", 0x0400),
            fake_hidpp.Response("010105010318", 0x0410, "01"),
            fake_hidpp.Response("0100484A4B", 0x0430, "0100"),
        ],
        [  # offset in the reply is wrong
            fake_hidpp.Response("03000200", 0x0400),
            fake_hidpp.Response("000105010718", 0x0410, "00"),
            fake_hidpp.Response("000E41424344454647", 0x0430, "0000"),
            fake_hidpp.Response("010105010318", 0x0410, "01"),
            fake_hidpp.Response("0100484A4B", 0x0430, "0100"),
        ],
    ],
)
def test_get_host_names_bad_replies(responses, mock_gethostname, mocker):
    """A host whose information is not provided is left out, and the name of the current host is not changed"""
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)
    spy_request = mocker.spy(device, "request")

    result = _hidpp20.get_host_names(device)

    assert result == {1: (True, "HJK")}
    assert all(call.args[0] != 0x0440 for call in spy_request.call_args_list)


def test_get_host_names_reply_to_other_request(mock_gethostname, mocker):
    """A reply to another program's request is ignored and the request is made again"""
    responses = [
        fake_hidpp.Response("01000201", 0x0400),
        fake_hidpp.Response("000105010718", 0x0410, "00"),
        fake_hidpp.Response("000041424344454647", 0x0430, "0000"),
        fake_hidpp.Response("010105010318", 0x0410, "01"),
        fake_hidpp.Response("0100484A4B", 0x0430, "0100"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)
    feature_request = device.feature_request
    other_replies = [bytes.fromhex("0100484A4B")]

    def first_reply_for_other_request(feature, function=0x00, *params, **kwargs):
        if function == 0x30 and other_replies:
            return other_replies.pop()
        return feature_request(feature, function, *params, **kwargs)

    mocker.patch.object(device, "feature_request", side_effect=first_reply_for_other_request)

    result = _hidpp20.get_host_names(device)

    assert result == {0: (True, "ABCDEFG"), 1: (True, "HJK")}


def test_get_host_names_long_hostname(mocker):
    """A host name that has to be shortened to fit is not set again when the shortened name is already there"""
    mocker.patch("socket.gethostname", return_value="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123.foo.org")
    responses = [
        fake_hidpp.Response("03000100", 0x0400),
        fake_hidpp.Response("000105011818", 0x0410, "00"),
        fake_hidpp.Response("00004142434445464748494A4B4C4D4E", 0x0430, "0000"),
        fake_hidpp.Response("000E4F505152535455565758", 0x0430, "000E"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)
    spy_request = mocker.spy(device, "request")

    result = _hidpp20.get_host_names(device)
    _hidpp20.get_host_names(device)

    assert result == {0: (True, "ABCDEFGHIJKLMNOPQRSTUVWX")}
    assert [call.args[0] for call in spy_request.call_args_list].count(0x0400) == 2  # nothing more to check or set
    assert all(call.args[0] != 0x0440 for call in spy_request.call_args_list)


def test_get_host_names_no_hostname(mocker):
    """Without a host name for this computer, nothing is set"""
    mocker.patch("socket.gethostname", return_value="")
    responses = [
        fake_hidpp.Response("03000100", 0x0400),
        fake_hidpp.Response("000105010318", 0x0410, "00"),
        fake_hidpp.Response("0000484A4B", 0x0430, "0000"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)
    spy_request = mocker.spy(device, "request")

    result = _hidpp20.get_host_names(device)

    assert result == {0: (True, "HJK")}
    assert [call.args[0] for call in spy_request.call_args_list].count(0x0400) == 1


@pytest.mark.parametrize(
    "responses, name, current_name, expected_result",
    [
        ([fake_hidpp.Response(None, 0x0400)], "ABCDEFGHIJKLMNOPQRSTUVWX", "", None),
        (
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000008", 0x0410, "02"),
                fake_hidpp.Response("0208", 0x0440, "02004142434445464748"),
            ],
            "ABCDEFGHIJKLMNOPQRSTUVWX",
            "",
            True,
        ),
        (
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000014", 0x0410, "02"),
                fake_hidpp.Response("020E", 0x0440, "02004142434445464748494A4B4C4D4E"),
                fake_hidpp.Response("0214", 0x0440, "020E4F5051525354"),
            ],
            "ABCDEFGHIJKLMNOPQRSTUVWX",
            "",
            True,
        ),
        (  # shortened without splitting a character
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000018", 0x0410, "02"),
                fake_hidpp.Response("020E", 0x0440, "02004142434445464748494A4B4C4D4E"),
                fake_hidpp.Response("0217", 0x0440, "020E4F5051525354555657"),
            ],
            "ABCDEFGHIJKLMNOPQRSTUVW’s",
            "",
            True,
        ),
        (  # the shortened name is already there
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000008", 0x0410, "02"),
            ],
            "ABCDEFGHIJKLMNOPQRSTUVWX",
            "ABCDEFGH",
            True,
        ),
        (  # host index in the reply is wrong
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000008", 0x0410, "02"),
                fake_hidpp.Response("0108", 0x0440, "02004142434445464748"),
            ],
            "ABCDEFGH",
            "",
            False,
        ),
        (  # name length in the reply is wrong
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000008", 0x0410, "02"),
                fake_hidpp.Response("0207", 0x0440, "02004142434445464748"),
            ],
            "ABCDEFGH",
            "",
            False,
        ),
        (
            [
                fake_hidpp.Response("03000002", 0x0400),
                fake_hidpp.Response("020000000008", 0x0410, "02"),
            ],
            "",
            "ABCDEFGH",
            False,
        ),
    ],
)
def test_set_host_name(responses, name, current_name, expected_result):
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.HOSTS_INFO)

    result = _hidpp20.set_host_name(device, name, current_name)

    assert result == expected_result


def test_get_onboard_mode():
    responses = [fake_hidpp.Response("03FFFFFFFF", 0x0420)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.ONBOARD_PROFILES)

    result = _hidpp20.get_onboard_mode(device)

    assert result == 0x3


def test_set_onboard_mode():
    responses = [fake_hidpp.Response("03FFFFFFFF", 0x0410, "03")]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.ONBOARD_PROFILES)

    res = _hidpp20.set_onboard_mode(device, 0x3)

    assert res is not None


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([fake_hidpp.Response("03FFFF", 0x0420)], "1ms"),
        (
            [
                fake_hidpp.Response(None, 0x0000, f"{int(SupportedFeature.REPORT_RATE):04X}"),
                fake_hidpp.Response("04FFFF", 0x0420),
            ],
            "500us",
        ),
    ],
)
def test_get_polling_rate(
    responses,
    expected_result,
):
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.EXTENDED_ADJUSTABLE_REPORT_RATE)

    result = _hidpp20.get_polling_rate(device)

    assert result == expected_result


def test_get_remaining_pairing():
    responses = [fake_hidpp.Response("03FFFF", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.REMAINING_PAIRING)

    result = _hidpp20.get_remaining_pairing(device)

    assert result == 0x03


def test_config_change():
    responses = [fake_hidpp.Response("03FFFF", 0x0410, "02")]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CONFIG_CHANGE)

    result = _hidpp20.config_change(device, 0x2)

    assert result == bytes.fromhex("03FFFF")


def test_get_configuration_cookie():
    responses = [fake_hidpp.Response("12345678", 0x0400)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CONFIG_CHANGE)

    result = _hidpp20.get_configuration_cookie(device)

    assert result == bytes.fromhex("1234")


def test_set_configuration_complete_explicit_cookie():
    # An explicit cookie is sent unchanged.
    responses = [fake_hidpp.Response("00", 0x0410, "1234")]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CONFIG_CHANGE)

    result = _hidpp20.set_configuration_complete(device, cookie=bytes.fromhex("1234"))

    assert result == bytes.fromhex("00")


def test_set_configuration_complete_monotonic_counter():
    # With no cookie, sends a host-side monotonic counter, +1 per call.
    hidpp20.Hidpp20._session_cookie = 0x1233
    responses = [
        fake_hidpp.Response("00", 0x0410, "1234"),
        fake_hidpp.Response("00", 0x0410, "1235"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CONFIG_CHANGE)

    assert _hidpp20.set_configuration_complete(device) == bytes.fromhex("00")
    assert _hidpp20.set_configuration_complete(device) == bytes.fromhex("00")


def test_set_configuration_complete_skips_zero():
    # Counter at 0xFFFF wraps to 1, never 0.
    hidpp20.Hidpp20._session_cookie = 0xFFFF
    responses = [fake_hidpp.Response("00", 0x0410, "0001")]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CONFIG_CHANGE)

    assert _hidpp20.set_configuration_complete(device) == bytes.fromhex("00")


def test_decipher_battery_status():
    report = b"\x50\x20\x00\xff\xff"

    feature, battery = hidpp20.decipher_battery_status(report)

    assert feature == SupportedFeature.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.BatteryStatus.DISCHARGING


def test_decipher_battery_voltage():
    report = b"\x10\x00\xff\xff\xff"

    feature, battery = hidpp20.decipher_battery_voltage(report)

    assert feature == SupportedFeature.BATTERY_VOLTAGE
    assert battery.level == 92
    assert common.BatteryStatus.RECHARGING in battery.status
    assert battery.voltage == 0x1000


def test_decipher_battery_unified():
    report = b"\x50\x01\x00\xff\xff"

    feature, battery = hidpp20.decipher_battery_unified(report)

    assert feature == SupportedFeature.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.BatteryStatus.DISCHARGING


def test_decipher_adc_measurement():
    report = b"\x10\x00\x03"

    feature, battery = hidpp20.decipher_adc_measurement(report)

    assert feature == SupportedFeature.ADC_MEASUREMENT
    assert battery.level == 92
    assert battery.status == common.BatteryStatus.RECHARGING
    assert battery.voltage == 0x1000


@pytest.mark.parametrize(
    "code, expected_flags",
    [
        (0x01, ["unknown:000001"]),
        (0x0F, ["unknown:00000F"]),
        (0xF0, ["internal", "hidden", "obsolete", "unknown:000010"]),
        (0x20, ["internal"]),
        (0x33, ["internal", "unknown:000013"]),
        (0x3F, ["internal", "unknown:00001F"]),
        (0x40, ["hidden"]),
        (0x50, ["hidden", "unknown:000010"]),
        (0x5F, ["hidden", "unknown:00001F"]),
        (0x7F, ["internal", "hidden", "unknown:00001F"]),
        (0x80, ["obsolete"]),
        (0xA0, ["internal", "obsolete"]),
        (0xE0, ["internal", "hidden", "obsolete"]),
        (0xFF, ["internal", "hidden", "obsolete", "unknown:00001F"]),
    ],
)
def test_feature_flag_names(code, expected_flags):
    flags = common.flag_names(hidpp20_constants.FeatureFlag, code)

    assert list(flags) == expected_flags


@pytest.mark.parametrize(
    "code, expected_name",
    [
        (0x00, "Unknown Location"),
        (0x03, "Left Side"),
    ],
)
def test_led_zone_locations(code, expected_name):
    assert hidpp20.LEDZoneLocations[code] == expected_name


@pytest.mark.parametrize(
    "millivolt, expected_percentage",
    [
        (-1234, 0),
        (500, 0),
        (2000, 0),
        (3500, 0),
        (3519, 0),
        (3520, 1),
        (3559, 1),
        (3579, 2),
        (3646, 5),
        (3671, 10),
        (3717, 20),
        (3751, 30),
        (3778, 40),
        (3811, 50),
        (3859, 60),
        (3922, 70),
        (3989, 80),
        (4067, 90),
        (4180, 99),
        (4181, 100),
        (4186, 100),
        (4500, 100),
    ],
)
def test_estimate_battery_level_percentage(millivolt, expected_percentage):
    percentage = hidpp20.estimate_battery_level_percentage(millivolt)

    assert percentage == expected_percentage
