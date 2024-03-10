from dataclasses import dataclass
from functools import partial
from typing import Any, Optional
from unittest import mock

import pytest

from lib.logitech_receiver import hidpp20
from lib.logitech_receiver import hidpp20_constants


@dataclass
class Device:
    name: str = "TEST DEVICE"


DEVICE = Device
_hidpp20 = hidpp20.Hidpp20()


@dataclass
class Response:
    response: Optional[str]
    device: Any
    feature: int
    function: int
    params: Any
    no_reply: bool = False


def feature_request(responses, device, feature, function=0x00, *params, no_reply=False):
    r = responses[0]
    responses.pop(0)
    assert r.device == device
    assert (r.feature, r.function, r.params) == (feature, function, params)
    return bytes.fromhex(r.response) if r.response is not None else None


@pytest.fixture
def mock_feature_request():
    with mock.patch("lib.logitech_receiver.hidpp20.feature_request", return_value=None) as mock_feature_request:
        yield mock_feature_request


def test_get_firmware(mock_feature_request):
    responses = [
        Response("02FFFF", DEVICE, hidpp20_constants.FEATURE.DEVICE_FW_VERSION, 0x00, ()),
        Response("01414243030401000101000102030405", DEVICE, hidpp20_constants.FEATURE.DEVICE_FW_VERSION, 0x10, (0,)),
        Response("02414243030401000101000102030405", DEVICE, hidpp20_constants.FEATURE.DEVICE_FW_VERSION, 0x10, (1,)),
    ]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_firmware(DEVICE)

    assert len(result) == 2
    assert isinstance(result[0], common.FirmwareInfo)
    assert isinstance(result[1], common.FirmwareInfo)


def test_get_ids(mock_feature_request):
    responses = [Response("FF12345678000D123456789ABC", DEVICE, hidpp20_constants.FEATURE.DEVICE_FW_VERSION, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    unitId, modelId, tid_map = _hidpp20.get_ids(DEVICE)

    assert unitId == "12345678"
    assert modelId == "123456789ABC"
    assert tid_map == {"btid": "1234", "wpid": "5678", "usbid": "9ABC"}


def test_get_kind(mock_feature_request):
    responses = [Response("00", DEVICE, hidpp20_constants.FEATURE.DEVICE_NAME, 0x20, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_kind(DEVICE)

    assert result == "keyboard"
    assert result == 1


def test_get_name(mock_feature_request):
    responses = [
        Response("12", DEVICE, hidpp20_constants.FEATURE.DEVICE_NAME, 0x00, ()),
        Response("4142434445464748494A4B4C4D4E4F", DEVICE, hidpp20_constants.FEATURE.DEVICE_NAME, 0x10, (0,)),
        Response("505152530000000000000000000000", DEVICE, hidpp20_constants.FEATURE.DEVICE_NAME, 0x10, (15,)),
    ]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_name(DEVICE)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_friendly_name(mock_feature_request):
    responses = [
        Response("12", DEVICE, hidpp20_constants.FEATURE.DEVICE_FRIENDLY_NAME, 0x00, ()),
        Response("004142434445464748494A4B4C4D4E", DEVICE, hidpp20_constants.FEATURE.DEVICE_FRIENDLY_NAME, 0x10, (0,)),
        Response("0E4F50515253000000000000000000", DEVICE, hidpp20_constants.FEATURE.DEVICE_FRIENDLY_NAME, 0x10, (14,)),
    ]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_friendly_name(DEVICE)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_battery_status(mock_feature_request):
    responses = [Response("502000FFFF", DEVICE, hidpp20_constants.FEATURE.BATTERY_STATUS, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    feature, battery = _hidpp20.get_battery_status(DEVICE)

    assert feature == hidpp20_constants.FEATURE.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.Battery.STATUS.discharging


def test_get_battery_voltage(mock_feature_request):
    responses = [Response("1000FFFFFF", DEVICE, hidpp20_constants.FEATURE.BATTERY_VOLTAGE, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    feature, battery = _hidpp20.get_battery_voltage(DEVICE)

    assert feature == hidpp20_constants.FEATURE.BATTERY_VOLTAGE
    assert battery.level == 90
    assert battery.status == common.Battery.STATUS.recharging
    assert battery.voltage == 0x1000


def test_get_battery_unified(mock_feature_request):
    responses = [Response("500100FFFF", DEVICE, hidpp20_constants.FEATURE.UNIFIED_BATTERY, 0x10, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    feature, battery = _hidpp20.get_battery_unified(DEVICE)

    assert feature == hidpp20_constants.FEATURE.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.Battery.STATUS.discharging


def test_get_adc_measurement(mock_feature_request):
    responses = [Response("100003", DEVICE, hidpp20_constants.FEATURE.ADC_MEASUREMENT, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    feature, battery = _hidpp20.get_adc_measurement(DEVICE)

    assert feature == hidpp20_constants.FEATURE.ADC_MEASUREMENT
    assert battery.level == 90
    assert battery.status == common.Battery.STATUS.recharging
    assert battery.voltage == 0x1000


def test_get_battery(mock_feature_request):
    responses = [Response("502000FFFF", DEVICE, hidpp20_constants.FEATURE.BATTERY_STATUS, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    feature, battery = _hidpp20.get_battery(DEVICE, hidpp20_constants.FEATURE.BATTERY_STATUS)

    assert feature == hidpp20_constants.FEATURE.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.Battery.STATUS.discharging


def test_get_battery_none(mock_feature_request):
    responses = [
        Response(None, DEVICE, hidpp20_constants.FEATURE.BATTERY_STATUS, 0x00, ()),
        Response(None, DEVICE, hidpp20_constants.FEATURE.BATTERY_VOLTAGE, 0x00, ()),
        Response("500100ffff", DEVICE, hidpp20_constants.FEATURE.UNIFIED_BATTERY, 0x10, ()),
    ]
    mock_feature_request.side_effect = partial(feature_request, responses)

    feature, battery = _hidpp20.get_battery(DEVICE, None)

    assert feature == hidpp20_constants.FEATURE.UNIFIED_BATTERY
    assert battery.level == 80
    assert battery.status == common.Battery.STATUS.discharging


# get_keys is complex
# get_remap_keys is comples
# get_gestures is complex
# get_backlight is complex
# get_profiles is complex


def test_get_mouse_pointer_info(mock_feature_request):
    responses = [Response("01000A", DEVICE, hidpp20_constants.FEATURE.MOUSE_POINTER, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_mouse_pointer_info(DEVICE)

    assert result == {
        "dpi": 0x100,
        "acceleration": "med",
        "suggest_os_ballistics": False,
        "suggest_vertical_orientation": True,
    }


def test_get_vertical_scrolling_info(mock_feature_request):
    responses = [Response("01080C", DEVICE, hidpp20_constants.FEATURE.VERTICAL_SCROLLING, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_vertical_scrolling_info(DEVICE)

    assert result == {"roller": "standard", "ratchet": 8, "lines": 12}


def test_get_hi_res_scrolling_info(mock_feature_request):
    responses = [Response("0102", DEVICE, hidpp20_constants.FEATURE.HI_RES_SCROLLING, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    mode, resolution = _hidpp20.get_hi_res_scrolling_info(DEVICE)

    assert mode == 1
    assert resolution == 2


def test_get_pointer_speed_info(mock_feature_request):
    responses = [Response("0102", DEVICE, hidpp20_constants.FEATURE.POINTER_SPEED, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_pointer_speed_info(DEVICE)

    assert result == 0x0102 / 256


def test_get_lowres_wheel_status(mock_feature_request):
    responses = [Response("01", DEVICE, hidpp20_constants.FEATURE.LOWRES_WHEEL, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_lowres_wheel_status(DEVICE)

    assert result == "HID++"


def test_get_hires_wheel(mock_feature_request):
    responses = [
        Response("010C", DEVICE, hidpp20_constants.FEATURE.HIRES_WHEEL, 0x00, ()),
        Response("05FF", DEVICE, hidpp20_constants.FEATURE.HIRES_WHEEL, 0x10, ()),
        Response("03FF", DEVICE, hidpp20_constants.FEATURE.HIRES_WHEEL, 0x30, ()),
    ]
    mock_feature_request.side_effect = partial(feature_request, responses)

    multi, has_invert, has_ratchet, inv, res, target, ratchet = _hidpp20.get_hires_wheel(DEVICE)

    assert multi == 1
    assert has_invert is True
    assert has_ratchet is True
    assert inv is True
    assert res is False
    assert target is True
    assert ratchet is True


def test_get_new_fn_inversion(mock_feature_request):
    responses = [Response("0300", DEVICE, hidpp20_constants.FEATURE.NEW_FN_INVERSION, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_new_fn_inversion(DEVICE)

    assert result == (True, False)
    assert mock_feature_request.call_count == 1
    assert len(responses) == 0


@pytest.fixture
def mock_gethostname(mocker):
    mocker.patch("socket.gethostname", return_value="getafix.foo.org")


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([Response(None, DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ())], {}),
        ([Response("02000000", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ())], {}),
        (
            [
                Response("03000200", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ()),
                Response("FF01FFFF05FFFF", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x10, (0x00,)),
                Response("0000414243444500FFFFFFFFFF", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x30, (0x00, 0x00)),
                Response("FF01FFFF10FFFF", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x10, (0x01,)),
                Response("01004142434445464748494A4B4C4D", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x30, (0x01, 0)),
                Response("01134E4F5000FFFFFFFFFFFFFFFFFF", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x30, (0x01, 14)),
                Response("03000200", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ()),
                Response("000000000008", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x10, (0x0,)),
                Response("0208", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x40, (0x0, 0x0, bytearray("getafix", "utf-8"))),
            ],
            {0: (True, "getafix"), 1: (True, "ABCDEFGHIJKLMNO")},
        ),
    ],
)
def test_get_host_names(responses, expected_result, mock_feature_request, mock_gethostname):
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_host_names(DEVICE)

    assert result == expected_result
    assert len(responses) == 0


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([Response(None, DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ())], None),
        (
            [
                Response("03000002", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ()),
                Response("000000000008", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x10, (0x2,)),
                Response("0208", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x40, (0x2, 0x0, bytearray("THIS IS A LONG", "utf-8"))),
            ],
            True,
        ),
        (
            [
                Response("03000002", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ()),
                Response("000000000014", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x10, (0x2,)),
                Response("020E", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x40, (0x2, 0, bytearray("THIS IS A LONG", "utf-8"))),
                Response("0214", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x40, (0x2, 14, bytearray(" HOST NAME", "utf-8"))),
            ],
            True,
        ),
    ],
)
def test_set_host_name(responses, expected_result, mock_feature_request):
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.set_host_name(DEVICE, "THIS IS A LONG HOST NAME")

    assert result == expected_result
    assert len(responses) == 0


def test_get_onboard_mode(mock_feature_request):
    responses = [Response("03FFFFFFFF", DEVICE, hidpp20_constants.FEATURE.ONBOARD_PROFILES, 0x20, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_onboard_mode(DEVICE)

    assert result == 0x3
    assert mock_feature_request.call_count == 1
    assert mock_feature_request.call_args[0] == (DEVICE, hidpp20_constants.FEATURE.ONBOARD_PROFILES, 0x20)


def test_set_onboard_mode(mock_feature_request):
    responses = [Response("03FFFFFFFF", DEVICE, hidpp20_constants.FEATURE.ONBOARD_PROFILES, 0x10, (0x3,))]
    mock_feature_request.side_effect = partial(feature_request, responses)

    res = _hidpp20.set_onboard_mode(DEVICE, 0x3)

    assert mock_feature_request.call_count == 1
    assert res is not None


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([Response("03FFFF", DEVICE, hidpp20.FEATURE.REPORT_RATE, 0x10, ())], "3ms"),
        (
            [
                Response(None, DEVICE, hidpp20.FEATURE.REPORT_RATE, 0x10, ()),
                Response("04FFFF", DEVICE, hidpp20.FEATURE.EXTENDED_ADJUSTABLE_REPORT_RATE, 0x20, ()),
            ],
            "500us",
        ),
    ],
)
def test_get_polling_rate(responses, expected_result, mock_feature_request):
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_polling_rate(DEVICE)

    assert result == expected_result
    assert len(responses) == 0


def test_get_remaining_pairing(mock_feature_request):
    responses = [Response("03FFFF", None, hidpp20.FEATURE.REMAINING_PAIRING, 0x0, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_remaining_pairing(None)

    assert result == 0x03
    assert len(responses) == 0


def test_config_change(mock_feature_request):
    responses = [Response("03FFFF", None, hidpp20.FEATURE.CONFIG_CHANGE, 0x0, (0x2,))]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.config_change(None, 0x2)

    assert result == bytes.fromhex("03FFFF")
    assert len(responses) == 0


def test_decipher_battery_status():
    report = b"\x50\x20\x00\xff\xff"

    feature, battery = hidpp20.decipher_battery_status(report)

    assert feature == hidpp20_constants.FEATURE.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.Battery.STATUS.discharging


def test_decipher_battery_voltage():
    report = b"\x10\x00\xFF\xff\xff"

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
