from dataclasses import dataclass
from functools import partial
from struct import pack
from typing import Optional
from unittest import mock

import pytest

from logitech_receiver import common
from logitech_receiver import exceptions
from logitech_receiver import receiver


@pytest.mark.parametrize(
    "index, expected_kind",
    [
        (0, None),
        (1, 2),  # mouse
        (2, 2),  # mouse
        (3, 1),  # keyboard
        (4, 3),  # numpad
        (5, None),
    ],
)
def test_get_kind_from_index(index, expected_kind):
    mock_receiver = mock.Mock()

    if expected_kind:
        assert receiver._get_kind_from_index(mock_receiver, index) == expected_kind
    else:
        with pytest.raises(exceptions.NoSuchDevice):
            receiver._get_kind_from_index(mock_receiver, index)


@dataclass
class DeviceInfo:
    path: str
    vendor_id: int = 1133
    product_id: int = 0xC52B


@dataclass
class Response:
    response: Optional[str]
    handle: int
    devnumber: int
    id: int
    params: str = ""
    no_reply: bool = False


def request(responses, handle, devnumber, id, *params, no_reply=False, return_error=False, long_message=False, protocol=1.0):
    params = b"".join(pack("B", p) if isinstance(p, int) else p for p in params)
    print("REQUEST ", hex(handle), hex(devnumber), hex(id), params.hex())
    for r in responses:
        if handle == r.handle and devnumber == r.devnumber and r.id == id and bytes.fromhex(r.params) == params:
            print("RESPONSE", hex(r.handle), hex(r.devnumber), hex(r.id), r.params, r.response)
            return bytes.fromhex(r.response) if r.response is not None else None


def open_path(path: Optional[str]) -> Optional[int]:
    return int(path, 16) if path is not None else None


@pytest.fixture
def mock_request():
    with mock.patch("logitech_receiver.base.request", return_value=None) as mock_request:
        yield mock_request


@pytest.fixture
def mock_base():
    with mock.patch("logitech_receiver.base.open_path", return_value=None) as mock_open_path:
        with mock.patch("logitech_receiver.base.request", return_value=None) as mock_request:
            yield mock_open_path, mock_request


responses_unifying = [
    Response("000000", 0x11, 0xFF, 0x8003, "FF"),
    Response("000300", 0x11, 0xFF, 0x8102),
    Response("0316CC9CB40506220000000000000000", 0x11, 0xFF, 0x83B5, "03"),
    Response("20200840820402020700000000000000", 0x11, 0xFF, 0x83B5, "20"),
    Response("21211420110400010D1A000000000000", 0x11, 0xFF, 0x83B5, "21"),
    Response("22220840660402010700000000020000", 0x11, 0xFF, 0x83B5, "22"),
    Response("30198E3EB80600000001000000000000", 0x11, 0xFF, 0x83B5, "30"),
    Response("31811119511A40000002000000000000", 0x11, 0xFF, 0x83B5, "31"),
    Response("32112C46EA1E40000003000000000000", 0x11, 0xFF, 0x83B5, "32"),
    Response("400B4D58204D61737465722033000000", 0x11, 0xFF, 0x83B5, "40"),
    Response("41044B35323020202020202020202020", 0x11, 0xFF, 0x83B5, "41"),
    Response("42054372616674000000000000000000", 0x11, 0xFF, 0x83B5, "42"),
    Response("012411", 0x11, 0xFF, 0x81F1, "01"),
    Response("020036", 0x11, 0xFF, 0x81F1, "02"),
    Response("03AAAC", 0x11, 0xFF, 0x81F1, "03"),
    Response("040209", 0x11, 0xFF, 0x81F1, "04"),
]
responses_c534 = [
    Response("000000", 0x12, 0xFF, 0x8003, "FF"),
    Response("000209", 0x12, 0xFF, 0x8102),
    Response("0316CC9CB40502220000000000000000", 0x12, 0xFF, 0x83B5, "03"),
    Response("00000445AB", 0x12, 0xFF, 0x83B5, "04"),
]
responses_unusual = [
    Response("000000", 0x13, 0xFF, 0x8003, "FF"),
    Response("000300", 0x13, 0xFF, 0x8102),
    Response("00000445AB", 0x13, 0xFF, 0x83B5, "04"),
    Response("0326CC9CB40508220000000000000000", 0x13, 0xFF, 0x83B5, "03"),
]
responses_lacking = [
    Response("000000", 0x14, 0xFF, 0x8003, "FF"),
    Response("000300", 0x14, 0xFF, 0x8102),
]

mouse_info = {
    "kind": common.NamedInt(2, "mouse"),
    "polling": "8ms",
    "power_switch": common.NamedInt(1, "base"),
    "serial": "198E3EB8",
    "wpid": "4082",
}
c534_info = {"kind": common.NamedInt(0, "unknown"), "polling": "", "power_switch": "(unknown)", "serial": None, "wpid": "45AB"}


@pytest.mark.parametrize(
    "device_info, responses, handle, serial, max_devices, ",
    [
        (DeviceInfo(None), [], None, None, None),
        (DeviceInfo(None), [], None, None, None),
        (DeviceInfo("11"), responses_unifying, 0x11, "16CC9CB4", 6),
        (DeviceInfo("12", product_id=0xC534), responses_c534, 0x12, "16CC9CB4", 2),
        (DeviceInfo("12", product_id=0xC539), responses_c534, 0x12, "16CC9CB4", 2),
        (DeviceInfo("13"), responses_unusual, 0x13, "26CC9CB4", 1),
        (DeviceInfo("14"), responses_lacking, 0x14, None, 1),
    ],
)
def test_ReceiverFactory_create_receiver(device_info, responses, handle, serial, max_devices, mock_base):
    mock_base[0].side_effect = open_path
    mock_base[1].side_effect = partial(request, responses)

    r = receiver.ReceiverFactory.create_receiver(device_info, lambda x: x)

    if handle is None:
        assert r is None
    else:
        assert r.handle == handle
        assert r.serial == serial
        assert r.max_devices == max_devices


@pytest.mark.parametrize(
    "device_info, responses, firmware, codename, remaining_pairings, pairing_info, count",
    [
        (DeviceInfo("11"), responses_unifying, 3, "K520", -1, mouse_info, 3),
        (DeviceInfo("12", product_id=0xC534), responses_c534, None, None, 4, c534_info, 2),
        (DeviceInfo("13", product_id=0xCCCC), responses_unusual, None, None, -1, c534_info, 3),
    ],
)
def test_ReceiverFactory_props(device_info, responses, firmware, codename, remaining_pairings, pairing_info, count, mock_base):
    mock_base[0].side_effect = open_path
    mock_base[1].side_effect = partial(request, responses)

    r = receiver.ReceiverFactory.create_receiver(device_info, lambda x: x)

    assert len(r.firmware) == firmware if firmware is not None else firmware is None
    assert r.device_codename(2) == codename
    assert r.remaining_pairings() == remaining_pairings
    assert r.device_pairing_information(1) == pairing_info
    assert r.count() == count


@pytest.mark.parametrize(
    "device_info, responses, status_str, strng",
    [
        (DeviceInfo("11"), responses_unifying, "No paired devices.", "<UnifyingReceiver(11,17)>"),
        (DeviceInfo("12", product_id=0xC534), responses_c534, "No paired devices.", "<NanoReceiver(12,18)>"),
        (DeviceInfo("13", product_id=0xCCCC), responses_unusual, "No paired devices.", "<Receiver(13,19)>"),
    ],
)
def test_ReceiverFactory_string(device_info, responses, status_str, strng, mock_base):
    mock_base[0].side_effect = open_path
    mock_base[1].side_effect = partial(request, responses)

    r = receiver.ReceiverFactory.create_receiver(device_info, lambda x: x)

    assert r.status_string() == status_str
    assert str(r) == strng


@pytest.mark.parametrize(
    "device_info, responses",
    [
        (DeviceInfo("14"), responses_lacking),
        (DeviceInfo("14", product_id="C534"), responses_lacking),
    ],
)
def test_ReceiverFactory_nodevice(device_info, responses, mock_base):
    mock_base[0].side_effect = open_path
    mock_base[1].side_effect = partial(request, responses)

    r = receiver.ReceiverFactory.create_receiver(device_info, lambda x: x)

    with pytest.raises(exceptions.NoSuchDevice):
        r.device_pairing_information(1)
