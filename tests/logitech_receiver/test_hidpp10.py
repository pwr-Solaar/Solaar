from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import List
from typing import Optional

import pytest

from logitech_receiver import common
from logitech_receiver import hidpp10
from logitech_receiver import hidpp10_constants
from logitech_receiver.hidpp10_constants import Registers

_hidpp10 = hidpp10.Hidpp10()


@dataclass
class Response:
    response: Optional[str]
    request_id: int
    params: Any


@dataclass
class Device:
    name: str = "Device"
    online: bool = True
    kind: str = "fake"
    protocol: float = 1.0
    isDevice: bool = False  # incorrect, but useful here
    registers: List[Registers] = field(default_factory=list)
    responses: List[Response] = field(default_factory=list)

    def request(self, id, params=None, no_reply=False):
        if params is None:
            params = []
        print("REQUEST ", self.name, hex(id), params)
        for r in self.responses:
            if id == r.request_id and params == r.params:
                print("RESPONSE", self.name, hex(r.request_id), r.params, r.response)
                return bytes.fromhex(r.response) if r.response is not None else None


device_offline = Device("OFFLINE", False)
device_leds = Device("LEDS", True, registers=[Registers.THREE_LEDS, Registers.BATTERY_STATUS])
device_features = Device("FEATURES", True, protocol=4.5)

registers_standard = [Registers.BATTERY_STATUS, Registers.FIRMWARE]
responses_standard = [
    Response("555555", 0x8100 | Registers.BATTERY_STATUS, 0x00),
    Response("666666", 0x8100 | Registers.BATTERY_STATUS, 0x10),
    Response("777777", 0x8000 | Registers.BATTERY_STATUS, 0x00),
    Response("888888", 0x8000 | Registers.BATTERY_STATUS, 0x10),
    Response("052100", 0x8100 | Registers.BATTERY_STATUS, []),
    Response("ABCDEF", 0x8100 | Registers.FIRMWARE, 0x01),
    Response("ABCDEF", 0x8100 | Registers.FIRMWARE, 0x02),
    Response("ABCDEF", 0x8100 | Registers.FIRMWARE, 0x03),
    Response("ABCDEF", 0x8100 | Registers.FIRMWARE, 0x04),
    Response("000900", 0x8100 | Registers.NOTIFICATIONS, []),
    Response("101010", 0x8100 | Registers.MOUSE_BUTTON_FLAGS, []),
    Response("010101", 0x8100 | Registers.KEYBOARD_FN_SWAP, []),
    Response("020202", 0x8100 | Registers.DEVICES_CONFIGURATION, []),
    Response("030303", 0x8000 | Registers.DEVICES_CONFIGURATION, 0x00),
]
device_standard = Device("STANDARD", True, registers=registers_standard, responses=responses_standard)


@pytest.mark.parametrize(
    "device, register, param, expected_result",
    [
        (device_offline, Registers.THREE_LEDS, 0x00, None),
        (device_standard, Registers.THREE_LEDS, 0x00, None),
        (device_standard, Registers.BATTERY_STATUS, 0x00, "555555"),
        (device_standard, Registers.BATTERY_STATUS, 0x10, "666666"),
    ],
)
def test_read_register(device, register, param, expected_result, mocker):
    spy_request = mocker.spy(device, "request")

    result = hidpp10.read_register(device, register, param)

    assert result == (bytes.fromhex(expected_result) if expected_result else None)
    spy_request.assert_called_once_with(0x8100 | register, param)


@pytest.mark.parametrize(
    "device, register, param, expected_result",
    [
        (device_offline, Registers.THREE_LEDS, 0x00, None),
        (device_standard, Registers.THREE_LEDS, 0x00, None),
        (device_standard, Registers.BATTERY_STATUS, 0x00, "777777"),
        (device_standard, Registers.BATTERY_STATUS, 0x10, "888888"),
    ],
)
def test_write_register(device, register, param, expected_result, mocker):
    spy_request = mocker.spy(device, "request")

    result = hidpp10.write_register(device, register, param)

    assert result == (bytes.fromhex(expected_result) if expected_result else None)
    spy_request.assert_called_once_with(0x8000 | register, param)


def device_charge(name, response):
    responses = [Response(response, 0x8100 | Registers.BATTERY_CHARGE, [])]
    return Device(name, registers=[], responses=responses)


device_charge1 = device_charge("DISCHARGING", "550030")
device_charge2 = device_charge("RECHARGING", "440050")
device_charge3 = device_charge("FULL", "600090")
device_charge4 = device_charge("OTHER", "220000")


def device_status(name, response):
    responses = [Response(response, 0x8100 | Registers.BATTERY_STATUS, [])]
    return Device(name, registers=[], responses=responses)


device_status1 = device_status("FULL", "072200")
device_status2 = device_status("GOOD", "052100")
device_status3 = device_status("LOW", "032200")
device_status4 = device_status("CRITICAL", "010100")
device_status5 = device_status("EMPTY", "000000")
device_status6 = device_status("NOSTATUS", "002200")


@pytest.mark.parametrize(
    "device, expected_result, expected_register",
    [
        (device_offline, None, None),
        (device_features, None, None),
        (device_leds, None, None),
        (
            device_standard,
            common.Battery(common.BatteryLevelApproximation.GOOD, None, common.BatteryStatus.RECHARGING, None),
            Registers.BATTERY_STATUS,
        ),
        (device_charge1, common.Battery(0x55, None, common.BatteryStatus.DISCHARGING, None), Registers.BATTERY_CHARGE),
        (
            device_charge2,
            common.Battery(0x44, None, common.BatteryStatus.RECHARGING, None),
            Registers.BATTERY_CHARGE,
        ),
        (
            device_charge3,
            common.Battery(0x60, None, common.BatteryStatus.FULL, None),
            Registers.BATTERY_CHARGE,
        ),
        (device_charge4, common.Battery(0x22, None, None, None), Registers.BATTERY_CHARGE),
        (
            device_status1,
            common.Battery(common.BatteryLevelApproximation.FULL, None, common.BatteryStatus.FULL, None),
            Registers.BATTERY_STATUS,
        ),
        (
            device_status2,
            common.Battery(common.BatteryLevelApproximation.GOOD, None, common.BatteryStatus.RECHARGING, None),
            Registers.BATTERY_STATUS,
        ),
        (
            device_status3,
            common.Battery(common.BatteryLevelApproximation.LOW, None, common.BatteryStatus.FULL, None),
            Registers.BATTERY_STATUS,
        ),
        (
            device_status4,
            common.Battery(common.BatteryLevelApproximation.CRITICAL, None, None, None),
            Registers.BATTERY_STATUS,
        ),
        (
            device_status5,
            common.Battery(common.BatteryLevelApproximation.EMPTY, None, common.BatteryStatus.DISCHARGING, None),
            Registers.BATTERY_STATUS,
        ),
        (
            device_status6,
            common.Battery(None, None, common.BatteryStatus.FULL, None),
            Registers.BATTERY_STATUS,
        ),
    ],
)
def test_hidpp10_get_battery(device, expected_result, expected_register):
    result = _hidpp10.get_battery(device)

    assert result == expected_result
    if expected_register is not None:
        assert expected_register in device.registers


@pytest.mark.parametrize(
    "device, expected_firmwares",
    [
        (device_offline, []),
        (
            device_standard,
            [
                common.FirmwareKind.Firmware,
                common.FirmwareKind.Bootloader,
                common.FirmwareKind.Other,
            ],
        ),
    ],
)
def test_hidpp10_get_firmware(device, expected_firmwares):
    firmwares = _hidpp10.get_firmware(device)

    if not expected_firmwares:
        assert firmwares is None
    else:
        firmware_types = [firmware.kind for firmware in firmwares]
        assert firmware_types == expected_firmwares
        assert len(firmwares) == len(expected_firmwares)


@pytest.mark.parametrize(
    "device, level, charging, warning, p1, p2",
    [
        (device_leds, common.BatteryLevelApproximation.EMPTY, False, False, 0x33, 0x00),
        (device_leds, common.BatteryLevelApproximation.CRITICAL, False, False, 0x22, 0x00),
        (device_leds, common.BatteryLevelApproximation.LOW, False, False, 0x20, 0x00),
        (device_leds, common.BatteryLevelApproximation.GOOD, False, False, 0x20, 0x02),
        (device_leds, common.BatteryLevelApproximation.FULL, False, False, 0x20, 0x22),
        (device_leds, None, True, False, 0x30, 0x33),
        (device_leds, None, False, True, 0x02, 0x00),
        (device_leds, None, False, False, 0x11, 0x11),
    ],
)
def test_set_3leds(device, level, charging, warning, p1, p2, mocker):
    spy_request = mocker.spy(device, "request")

    _hidpp10.set_3leds(device, level, charging, warning)

    spy_request.assert_called_once_with(0x8000 | Registers.THREE_LEDS, p1, p2)


@pytest.mark.parametrize("device", [device_offline, device_features])
def test_set_3leds_missing(device, mocker):
    spy_request = mocker.spy(device, "request")

    _hidpp10.set_3leds(device)

    assert spy_request.call_count == 0


@pytest.mark.parametrize("device", [device_standard])
def test_get_notification_flags(device):
    result = _hidpp10.get_notification_flags(device)

    assert result == int("000900", 16)


def test_set_notification_flags(mocker):
    device = device_standard
    spy_request = mocker.spy(device, "request")

    result = _hidpp10.set_notification_flags(
        device, hidpp10_constants.NotificationFlag.BATTERY_STATUS, hidpp10_constants.NotificationFlag.WIRELESS
    )

    spy_request.assert_called_once_with(0x8000 | Registers.NOTIFICATIONS, b"\x10\x01\x00")
    assert result is not None


def test_set_notification_flags_bad(mocker):
    device = device_features
    spy_request = mocker.spy(device, "request")

    result = _hidpp10.set_notification_flags(
        device, hidpp10_constants.NotificationFlag.BATTERY_STATUS, hidpp10_constants.NotificationFlag.WIRELESS
    )

    assert spy_request.call_count == 0
    assert result is None


@pytest.mark.parametrize(
    "flag_bits, expected_names",
    [
        (None, ""),
        (0x0, "none"),
        (0x009020, "multi touch\n               unknown:008020"),
        (0x080000, "mouse extra buttons"),
        (
            0x080000 + 0x000400,
            ("link quality\n               mouse extra buttons"),
        ),
    ],
)
def test_notification_flag_str(flag_bits, expected_names):
    flag_names = hidpp10_constants.flags_to_str(flag_bits, fallback="none")

    assert flag_names == expected_names


def test_get_device_features():
    result = _hidpp10.get_device_features(device_standard)

    assert result == int("101010", 16)


@pytest.mark.parametrize(
    "device, register, expected_result",
    [
        (device_standard, Registers.BATTERY_STATUS, "052100"),
        (device_standard, Registers.MOUSE_BUTTON_FLAGS, "101010"),
        (device_standard, Registers.KEYBOARD_ILLUMINATION, None),
        (device_features, Registers.KEYBOARD_ILLUMINATION, None),
    ],
)
def test_get_register(device, register, expected_result):
    result = _hidpp10._get_register(device, register)

    assert result == (int(expected_result, 16) if expected_result is not None else None)


@pytest.mark.parametrize(
    "device, expected_result",
    [
        (device_standard, 2),
        (device_features, None),
    ],
)
def test_get_configuration_pending_flags(device, expected_result):
    result = hidpp10.get_configuration_pending_flags(device)

    assert result == expected_result


@pytest.mark.parametrize(
    "device, expected_result",
    [
        (device_standard, True),
        (device_features, False),
    ],
)
def test_set_configuration_pending_flags(device, expected_result):
    result = hidpp10.set_configuration_pending_flags(device, 0x00)

    assert result == expected_result
