from dataclasses import dataclass
from functools import partial
from unittest import mock

import pytest

from logitech_receiver import base
from logitech_receiver import common
from logitech_receiver import exceptions
from logitech_receiver import receiver

from . import fake_hidpp


@pytest.fixture
def nano_recv():
    device_info = DeviceInfo("12", product_id=0xC534)
    mock_low_level = LowLevelInterfaceFake(responses_lacking)
    yield receiver.create_receiver(mock_low_level, device_info, lambda x: x)


class LowLevelInterfaceFake:
    def __init__(self, responses=None):
        self.responses = responses

    def open_path(self, path):
        return fake_hidpp.open_path(path)

    def product_information(self, usb_id: int) -> dict:
        return base.product_information(usb_id)

    def find_paired_node(self, receiver_path: str, index: int, timeout: int):
        return None

    def request(self, response, *args, **kwargs):
        func = partial(fake_hidpp.request, self.responses)
        return func(response, *args, **kwargs)

    def ping(self, response, *args, **kwargs):
        func = partial(fake_hidpp.ping, self.responses)
        return func(response, *args, **kwargs)

    def close(self, *args, **kwargs):
        pass


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


responses_unifying = [
    fake_hidpp.Response("000000", 0x8003, "FF"),
    fake_hidpp.Response("000300", 0x8102),
    fake_hidpp.Response("0316CC9CB40506220000000000000000", 0x83B5, "03"),
    fake_hidpp.Response("20200840820402020700000000000000", 0x83B5, "20"),
    fake_hidpp.Response("21211420110400010D1A000000000000", 0x83B5, "21"),
    fake_hidpp.Response("22220840660402010700000000020000", 0x83B5, "22"),
    fake_hidpp.Response("30198E3EB80600000001000000000000", 0x83B5, "30"),
    fake_hidpp.Response("31811119511A40000002000000000000", 0x83B5, "31"),
    fake_hidpp.Response("32112C46EA1E40000003000000000000", 0x83B5, "32"),
    fake_hidpp.Response("400B4D58204D61737465722033000000", 0x83B5, "40"),
    fake_hidpp.Response("41044B35323020202020202020202020", 0x83B5, "41"),
    fake_hidpp.Response("42054372616674000000000000000000", 0x83B5, "42"),
    fake_hidpp.Response("012411", 0x81F1, "01"),
    fake_hidpp.Response("020036", 0x81F1, "02"),
    fake_hidpp.Response("03AAAC", 0x81F1, "03"),
    fake_hidpp.Response("040209", 0x81F1, "04"),
]
responses_c534 = [
    fake_hidpp.Response("000000", 0x8003, "FF", handle=0x12),
    fake_hidpp.Response("000209", 0x8102, handle=0x12),
    fake_hidpp.Response("0316CC9CB40502220000000000000000", 0x83B5, "03", handle=0x12),
    fake_hidpp.Response("00000445AB", 0x83B5, "04", handle=0x12),
]
responses_unusual = [
    fake_hidpp.Response("000000", 0x8003, "FF", handle=0x13),
    fake_hidpp.Response("000300", 0x8102, handle=0x13),
    fake_hidpp.Response("00000445AB", 0x83B5, "04", handle=0x13),
    fake_hidpp.Response("0326CC9CB40508220000000000000000", 0x83B5, "03", handle=0x13),
]
responses_lacking = [
    fake_hidpp.Response("000000", 0x8003, "FF", handle=0x14),
    fake_hidpp.Response("000300", 0x8102, handle=0x14),
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
        (DeviceInfo(path=None), [], False, None, None),
        (DeviceInfo(path=11), [], None, None, None),
        (DeviceInfo(path="11"), responses_unifying, 0x11, "16CC9CB4", 6),
        (DeviceInfo(path="12", product_id=0xC534), responses_c534, 0x12, "16CC9CB4", 2),
        (DeviceInfo(path="12", product_id=0xC539), responses_c534, 0x12, "16CC9CB4", 2),
        (DeviceInfo(path="13"), responses_unusual, 0x13, "26CC9CB4", 1),
        (DeviceInfo(path="14"), responses_lacking, 0x14, None, 1),
    ],
)
def test_receiver_factory_create_receiver(device_info, responses, handle, serial, max_devices):
    mock_low_level = LowLevelInterfaceFake(responses)

    if handle is False:
        with pytest.raises(Exception):  # noqa: B017
            receiver.create_receiver(mock_low_level, device_info, lambda x: x)
    elif handle is None:
        r = receiver.create_receiver(mock_low_level, device_info, lambda x: x)
        assert r is None
    else:
        r = receiver.create_receiver(mock_low_level, device_info, lambda x: x)
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
def test_receiver_factory_props(device_info, responses, firmware, codename, remaining_pairings, pairing_info, count):
    mock_low_level = LowLevelInterfaceFake(responses)

    r = receiver.create_receiver(mock_low_level, device_info, lambda x: x)

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
def test_receiver_factory_string(device_info, responses, status_str, strng):
    mock_low_level = LowLevelInterfaceFake(responses)

    r = receiver.create_receiver(mock_low_level, device_info, lambda x: x)

    assert r.status_string() == status_str
    assert str(r) == strng


@pytest.mark.parametrize(
    "device_info, responses",
    [
        (DeviceInfo("14"), responses_lacking),
        (DeviceInfo("14", product_id="C534"), responses_lacking),
    ],
)
def test_receiver_factory_no_device(device_info, responses):
    mock_low_level = LowLevelInterfaceFake(responses)

    r = receiver.create_receiver(mock_low_level, device_info, lambda x: x)

    with pytest.raises(exceptions.NoSuchDevice):
        r.device_pairing_information(1)


@pytest.mark.parametrize(
    "address, data, expected_online, expected_encrypted",
    [
        (0x03, b"\x01\x02\x03", True, False),
        (0x10, b"\x61\x02\x03", False, True),
    ],
)
def test_notification_information_nano_receiver(nano_recv, address, data, expected_online, expected_encrypted):
    _number = 0
    notification = base.HIDPPNotification(
        report_id=0x01,
        devnumber=0x52C,
        sub_id=0,
        address=address,
        data=data,
    )
    online, encrypted, wpid, kind = nano_recv.notification_information(_number, notification)

    assert online == expected_online
    assert encrypted == expected_encrypted
    assert wpid == "0302"
    assert kind == "keyboard"


def test_extract_serial_number():
    response = b'\x03\x16\xcc\x9c\xb4\x05\x06"\x00\x00\x00\x00\x00\x00\x00\x00'

    serial_number = receiver.extract_serial(response[1:5])

    assert serial_number == "16CC9CB4"


def test_extract_max_devices():
    response = b'\x03\x16\xcc\x9c\xb4\x05\x06"\x00\x00\x00\x00\x00\x00\x00\x00'

    max_devices = receiver.extract_max_devices(response)

    assert max_devices == 6


@pytest.mark.parametrize(
    "response, expected_remaining_pairings",
    [
        (b"\x00\x03\x00", -1),
        (b"\x00\x02\t", 4),
    ],
)
def test_extract_remaining_pairings(response, expected_remaining_pairings):
    remaining_pairings = receiver.extract_remaining_pairings(response)

    assert remaining_pairings == expected_remaining_pairings


def test_extract_codename():
    response = b"A\x04K520"

    codename = receiver.extract_codename(response)

    assert codename == "K520"


def test_extract_power_switch_location():
    response = b"0\x19\x8e>\xb8\x06\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"

    ps_location = receiver.extract_power_switch_location(response)

    assert ps_location == "base"


def test_extract_connection_count():
    response = b"\x00\x03\x00"

    connection_count = receiver.extract_connection_count(response)

    assert connection_count == 3


def test_extract_wpid():
    response = b"@\x82"

    res = receiver.extract_wpid(response)

    assert res == "4082"


def test_extract_polling_rate():
    response = b"\x08@\x82\x04\x02\x02\x07\x00\x00\x00\x00\x00\x00\x00"

    polling_rate = receiver.extract_polling_rate(response)

    assert polling_rate == 130


@pytest.mark.parametrize(
    "data, expected_device_kind",
    [
        (0x00, "unknown"),
        (0x03, "numpad"),
    ],
)
def test_extract_device_kind(data, expected_device_kind):
    device_kind = receiver.extract_device_kind(data)

    assert str(device_kind) == expected_device_kind
