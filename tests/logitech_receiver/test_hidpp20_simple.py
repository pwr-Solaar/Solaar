from dataclasses import dataclass
from functools import partial
from typing import Any
from unittest import mock

import pytest

from lib.logitech_receiver import hidpp20, hidpp20_constants

DEVICE = "test_device"
_hidpp20 = hidpp20.Hidpp20()


@dataclass
class Response:
    response: str
    device: Any
    feature: int
    function: int
    params: Any
    no_reply: bool = False


def feature_request(responses, device, feature, function=0x00, *params, no_reply=False):
    r = responses[0]
    responses.pop(0)
    assert r.device == device
    assert r.feature == feature
    assert r.function == function
    assert r.params == params
    return bytes.fromhex(r.response) if r.response is not None else None


@pytest.fixture
def mock_feature_request():
    with mock.patch("lib.logitech_receiver.hidpp20.feature_request", return_value=None) as mock_feature_request:
        yield mock_feature_request


def test_get_new_fn_inversion(mock_feature_request):
    responses = [Response("0300", DEVICE, hidpp20_constants.FEATURE.NEW_FN_INVERSION, 0x00, ())]
    mock_feature_request.side_effect = partial(feature_request, responses)

    result = _hidpp20.get_new_fn_inversion(DEVICE)

    assert result == (True, False)
    assert mock_feature_request.call_count == 1
    assert len(responses) == 0


@pytest.mark.parametrize(
    "responses, expected_result",
    [
        ([Response(None, DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ())], {}),
        ([Response("02000002", DEVICE, hidpp20.FEATURE.HOSTS_INFO, 0x00, ())], {}),
    ],
)
def test_get_host_names(responses, expected_result, mock_feature_request):
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
