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

from . import hidpp

_hidpp20 = hidpp20.Hidpp20()


def test_get_firmware():
    responses = [
        hidpp.Response("02FFFF", 0x0400),
        hidpp.Response("01414243030401000101000102030405", 0x0410, "00"),
        hidpp.Response("02414243030401000101000102030405", 0x0410, "01"),
    ]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.DEVICE_FW_VERSION)

    result = _hidpp20.get_firmware(device)

    assert len(result) == 2
    assert isinstance(result[0], common.FirmwareInfo)
    assert isinstance(result[1], common.FirmwareInfo)


def test_get_ids():
    responses = [hidpp.Response("FF12345678000D123456789ABC", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.DEVICE_FW_VERSION)

    unitId, modelId, tid_map = _hidpp20.get_ids(device)

    assert unitId == "12345678"
    assert modelId == "123456789ABC"
    assert tid_map == {"btid": "1234", "wpid": "5678", "usbid": "9ABC"}


def test_get_kind():
    responses = [hidpp.Response("00", 0x0420)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.DEVICE_NAME)

    result = _hidpp20.get_kind(device)

    assert result == "keyboard"
    assert result == 1


def test_get_name():
    responses = [
        hidpp.Response("12", 0x0400),
        hidpp.Response("4142434445464748494A4B4C4D4E4F", 0x0410, "00"),
        hidpp.Response("505152530000000000000000000000", 0x0410, "0F"),
    ]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.DEVICE_NAME)

    result = _hidpp20.get_name(device)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_friendly_name():
    responses = [
        hidpp.Response("12", 0x0400),
        hidpp.Response("004142434445464748494A4B4C4D4E", 0x0410, "00"),
        hidpp.Response("0E4F50515253000000000000000000", 0x0410, "0E"),
    ]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.DEVICE_FRIENDLY_NAME)

    result = _hidpp20.get_friendly_name(device)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_battery_status():
    responses = [hidpp.Response("502000FFFF", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.BATTERY_STATUS)

    feature, battery = _hidpp20.get_battery_status(device)

    assert feature == hidpp20_constants.FEATURE.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.Battery.STATUS.discharging


def test_get_battery_voltage():
    responses = [hidpp.Response("1000FFFFFF", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.BATTERY_VOLTAGE)

    feature, battery = _hidpp20.get_battery_voltage(device)

    assert feature == hidpp20_constants.FEATURE.BATTERY_VOLTAGE
    assert battery.level == 90
    assert battery.status == common.Battery.STATUS.recharging
    assert battery.voltage == 0x1000


def test_get_battery_unified():
    responses = [hidpp.Response("500100FFFF", 0x0410)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.UNIFIED_BATTERY)

    feature, battery = _hidpp20.get_battery_unified(device)

    assert feature == hidpp20_constants.FEATURE.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.Battery.STATUS.discharging


def test_get_adc_measurement():
    responses = [hidpp.Response("100003", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.ADC_MEASUREMENT)

    feature, battery = _hidpp20.get_adc_measurement(device)

    assert feature == hidpp20_constants.FEATURE.ADC_MEASUREMENT
    assert battery.level == 90
    assert battery.status == common.Battery.STATUS.recharging
    assert battery.voltage == 0x1000


def test_get_battery():
    responses = [hidpp.Response("502000FFFF", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.BATTERY_STATUS)

    feature, battery = _hidpp20.get_battery(device, hidpp20_constants.FEATURE.BATTERY_STATUS)

    assert feature == hidpp20_constants.FEATURE.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.Battery.STATUS.discharging


def test_get_battery_none():
    responses = [
        hidpp.Response(None, 0x0000, f"{hidpp20_constants.FEATURE.BATTERY_STATUS:0>4X}"),
        hidpp.Response(None, 0x0000, f"{hidpp20_constants.FEATURE.BATTERY_VOLTAGE:0>4X}"),
        hidpp.Response("500100ffff", 0x0410),
    ]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.UNIFIED_BATTERY)

    feature, battery = _hidpp20.get_battery(device, None)

    assert feature == hidpp20_constants.FEATURE.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.Battery.STATUS.discharging


# get_keys is in test_hidpp20_complex
# get_remap_keys is in test_hidpp20_complex
# TODO get_gestures is complex
# get_backlight is in test_hidpp20_complex
# get_profiles is in test_hidpp20_complex


def test_get_mouse_pointer_info():
    responses = [hidpp.Response("01000A", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.MOUSE_POINTER)

    result = _hidpp20.get_mouse_pointer_info(device)

    assert result == {
        "dpi": 0x100,
        "acceleration": "med",
        "suggest_os_ballistics": False,
        "suggest_vertical_orientation": True,
    }


def test_get_vertical_scrolling_info():
    responses = [hidpp.Response("01080C", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.VERTICAL_SCROLLING)

    result = _hidpp20.get_vertical_scrolling_info(device)

    assert result == {"roller": "standard", "ratchet": 8, "lines": 12}


def test_get_hi_res_scrolling_info():
    responses = [hidpp.Response("0102", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.HI_RES_SCROLLING)

    mode, resolution = _hidpp20.get_hi_res_scrolling_info(device)

    assert mode == 1
    assert resolution == 2


def test_get_pointer_speed_info():
    responses = [hidpp.Response("0102", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.POINTER_SPEED)

    result = _hidpp20.get_pointer_speed_info(device)

    assert result == 0x0102 / 256


def test_get_lowres_wheel_status():
    responses = [hidpp.Response("01", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.LOWRES_WHEEL)

    result = _hidpp20.get_lowres_wheel_status(device)

    assert result == "HID++"


def test_get_hires_wheel():
    responses = [
        hidpp.Response("010C", 0x0400),
        hidpp.Response("05FF", 0x0410),
        hidpp.Response("03FF", 0x0430),
    ]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.HIRES_WHEEL)

    multi, has_invert, has_ratchet, inv, res, target, ratchet = _hidpp20.get_hires_wheel(device)

    assert multi == 1
    assert has_invert is True
    assert has_ratchet is True
    assert inv is True
    assert res is False
    assert target is True
    assert ratchet is True


def test_get_new_fn_inversion():
    responses = [hidpp.Response("0300", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.NEW_FN_INVERSION)

    result = _hidpp20.get_new_fn_inversion(device)

    assert result == (True, False)


@pytest.fixture
def mock_gethostname(mocker):
    mocker.patch("socket.gethostname", return_value="ABCDEFG.foo.org")


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([hidpp.Response(None, 0x0400)], {}),
        ([hidpp.Response("02000000", 0x0400)], {}),
        (
            [
                hidpp.Response("03000200", 0x0400),
                hidpp.Response("FF01FFFF05FFFF", 0x0410, "00"),
                hidpp.Response("0000414243444500FFFFFFFFFF", 0x0430, "0000"),
                hidpp.Response("FF01FFFF10FFFF", 0x0410, "01"),
                hidpp.Response("01004142434445464748494A4B4C4D", 0x0430, "0100"),
                hidpp.Response("01134E4F5000FFFFFFFFFFFFFFFFFF", 0x0430, "010E"),
                hidpp.Response("000000000008", 0x0410, "00"),
                hidpp.Response("0208", 0x0440, "000041424344454647"),
            ],
            {0: (True, "ABCDEFG"), 1: (True, "ABCDEFGHIJKLMNO")},
        ),
    ],
)
def test_get_host_names(responses, expected_result, mock_gethostname):
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.HOSTS_INFO)

    result = _hidpp20.get_host_names(device)

    assert result == expected_result


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([hidpp.Response(None, 0x0400)], None),
        (
            [
                hidpp.Response("03000002", 0x0400),
                hidpp.Response("000000000008", 0x0410, "02"),
                hidpp.Response("020E", 0x0440, "02004142434445464748494A4B4C4D4E"),
            ],
            True,
        ),
        (
            [
                hidpp.Response("03000002", 0x0400),
                hidpp.Response("000000000014", 0x0410, "02"),
                hidpp.Response("020E", 0x0440, "02004142434445464748494A4B4C4D4E"),
                hidpp.Response("0214", 0x0440, "020E4F505152535455565758"),
            ],
            True,
        ),
    ],
)
def test_set_host_name(responses, expected_result):
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.HOSTS_INFO)

    result = _hidpp20.set_host_name(device, "ABCDEFGHIJKLMNOPQRSTUVWX")

    assert result == expected_result


def test_get_onboard_mode():
    responses = [hidpp.Response("03FFFFFFFF", 0x0420)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.ONBOARD_PROFILES)

    result = _hidpp20.get_onboard_mode(device)

    assert result == 0x3


def test_set_onboard_mode():
    responses = [hidpp.Response("03FFFFFFFF", 0x0410, "03")]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.ONBOARD_PROFILES)

    res = _hidpp20.set_onboard_mode(device, 0x3)

    assert res is not None


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([hidpp.Response("03FFFF", 0x0420)], "1ms"),
        (
            [
                hidpp.Response(None, 0x0000, f"{hidpp20_constants.FEATURE.REPORT_RATE:0>4X}"),
                hidpp.Response("04FFFF", 0x0420),
            ],
            "500us",
        ),
    ],
)
def test_get_polling_rate(
    responses,
    expected_result,
):
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.EXTENDED_ADJUSTABLE_REPORT_RATE)

    result = _hidpp20.get_polling_rate(device)

    assert result == expected_result


def test_get_remaining_pairing():
    responses = [hidpp.Response("03FFFF", 0x0400)]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.REMAINING_PAIRING)

    result = _hidpp20.get_remaining_pairing(device)

    assert result == 0x03


def test_config_change():
    responses = [hidpp.Response("03FFFF", 0x0410, "02")]
    device = hidpp.Device(responses=responses, feature=hidpp20_constants.FEATURE.CONFIG_CHANGE)

    result = _hidpp20.config_change(device, 0x2)

    assert result == bytes.fromhex("03FFFF")


def test_decipher_battery_status():
    report = b"\x50\x20\x00\xff\xff"

    feature, battery = hidpp20.decipher_battery_status(report)

    assert feature == hidpp20_constants.FEATURE.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.Battery.STATUS.discharging


def test_decipher_battery_voltage():
    report = b"\x10\x00\xff\xff\xff"

    feature, battery = hidpp20.decipher_battery_voltage(report)

    assert feature == hidpp20_constants.FEATURE.BATTERY_VOLTAGE
    assert battery.level == 90
    assert battery.status == common.Battery.STATUS.recharging
    assert battery.voltage == 0x1000


def test_decipher_battery_unified():
    report = b"\x50\x01\x00\xff\xff"

    feature, battery = hidpp20.decipher_battery_unified(report)

    assert feature == hidpp20_constants.FEATURE.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.Battery.STATUS.discharging


def test_decipher_adc_measurement():
    report = b"\x10\x00\x03"

    feature, battery = hidpp20.decipher_adc_measurement(report)

    assert feature == hidpp20_constants.FEATURE.ADC_MEASUREMENT
    assert battery.level == 90
    assert battery.status == common.Battery.STATUS.recharging
    assert battery.voltage == 0x1000
