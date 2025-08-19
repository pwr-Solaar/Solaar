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

from dataclasses import dataclass
from functools import partial
from typing import Optional

import pytest

from logitech_receiver import common
from logitech_receiver import device
from logitech_receiver import hidpp20
from logitech_receiver.common import BatteryLevelApproximation
from logitech_receiver.common import BatteryStatus

from . import fake_hidpp


class LowLevelInterfaceFake:
    def __init__(self, responses=None):
        self.responses = responses

    def open_path(self, path) -> int:
        return fake_hidpp.open_path(path)

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


@dataclass
class DeviceInfoStub:
    path: str
    product_id: str
    vendor_id: int = 1133
    hidpp_short: bool = False
    hidpp_long: bool = True
    bus_id: int = 0x0003  # USB
    serial: str = "aa:aa:aa;aa"


di_bad_handle = DeviceInfoStub(None, product_id="CCCC")
di_error = DeviceInfoStub(11, product_id="CCCC")
di_CCCC = DeviceInfoStub("11", product_id="CCCC")
di_C318 = DeviceInfoStub("11", product_id="C318")
di_B530 = DeviceInfoStub("11", product_id="B350", bus_id=0x0005)
di_C068 = DeviceInfoStub("11", product_id="C06B")
di_C08A = DeviceInfoStub("11", product_id="C08A")
di_DDDD = DeviceInfoStub("11", product_id="DDDD")


@pytest.mark.parametrize(
    "device_info, responses, expected_success",
    [
        (di_bad_handle, fake_hidpp.r_empty, None),
        (di_error, fake_hidpp.r_empty, False),
        (di_CCCC, fake_hidpp.r_empty, True),
    ],
)
def test_create_device(device_info, responses, expected_success):
    low_level_mock = LowLevelInterfaceFake(responses)
    if expected_success is None:
        with pytest.raises(PermissionError):
            device.create_device(low_level_mock, device_info)
    elif not expected_success:
        with pytest.raises(TypeError):
            device.create_device(low_level_mock, device_info)
    else:
        test_device = device.create_device(low_level_mock, device_info)
        assert bool(test_device) == expected_success


@pytest.mark.parametrize(
    "device_info, responses, expected_codename, expected_name, expected_kind",
    [(di_CCCC, fake_hidpp.r_empty, "?? (CCCC)", "Unknown device CCCC", "?")],
)
def test_device_name(device_info, responses, expected_codename, expected_name, expected_kind):
    low_level = LowLevelInterfaceFake(responses)

    test_device = device.create_device(low_level, device_info)

    assert test_device.codename == expected_codename
    assert test_device.name == expected_name
    assert test_device.kind == expected_kind


@pytest.mark.parametrize(
    "device_info, responses, handle, _name, _codename, number, protocol, registers",
    zip(
        [di_CCCC, di_C318, di_B530, di_C068, di_C08A, di_DDDD],
        [
            fake_hidpp.r_empty,
            fake_hidpp.r_keyboard_1,
            fake_hidpp.r_keyboard_2,
            fake_hidpp.r_mouse_1,
            fake_hidpp.r_mouse_2,
            fake_hidpp.r_mouse_3,
        ],
        [0x11, 0x11, 0x11, 0x11, 0x11, 0x11],
        [None, "Illuminated Keyboard", "Craft Advanced Keyboard", "G700 Gaming Mouse", "MX Vertical Wireless Mouse", None],
        [None, "Illuminated", "Craft", "G700", "MX Vertical", None],
        [0xFF, 0x0, 0xFF, 0x0, 0xFF, 0xFF],
        [1.0, 1.0, 4.5, 1.0, 4.5, 4.5],
        [[], [], [], (common.NamedInt(7, "battery status"), common.NamedInt(81, "three leds")), [], []],
    ),
)
def test_device_info(device_info, responses, handle, _name, _codename, number, protocol, registers):
    test_device = device.Device(LowLevelInterfaceFake(responses), None, None, None, handle=handle, device_info=device_info)

    assert test_device.handle == handle
    assert test_device._name == _name
    assert test_device._codename == _codename
    assert test_device.number == number
    assert test_device._protocol == protocol
    assert test_device.registers == registers

    assert bool(test_device)

    test_device.__del__()
    assert not bool(test_device)


@dataclass
class FakeReceiver:
    path: str = "11"
    handle: int = 0x11
    codename: Optional[str] = None

    def device_codename(self, number):
        return self.codename

    def __contains__(self, dev):
        return True


pi_CCCC = {"wpid": "CCCC", "kind": 0, "serial": None, "polling": "1ms", "power_switch": "top"}
pi_2011 = {"wpid": "2011", "kind": 1, "serial": "1234", "polling": "2ms", "power_switch": "bottom"}
pi_4066 = {"wpid": "4066", "kind": 1, "serial": "5678", "polling": "4ms", "power_switch": "left"}
pi_1007 = {"wpid": "1007", "kind": 2, "serial": "1234", "polling": "8ms", "power_switch": "right"}
pi_407B = {"wpid": "407B", "kind": 2, "serial": "5678", "polling": "1ms", "power_switch": "left"}
pi_DDDD = {"wpid": "DDDD", "kind": 2, "serial": "1234", "polling": "2ms", "power_switch": "top"}


@pytest.mark.parametrize(
    "number, pairing_info, responses, handle, _name, codename, p, p2, name",
    zip(
        range(1, 7),
        [pi_CCCC, pi_2011, pi_4066, pi_1007, pi_407B, pi_DDDD],
        [
            fake_hidpp.r_empty,
            fake_hidpp.r_keyboard_1,
            fake_hidpp.r_keyboard_2,
            fake_hidpp.r_mouse_1,
            fake_hidpp.r_mouse_2,
            fake_hidpp.r_mouse_3,
        ],
        [0x11, 0x11, 0x11, 0x11, 0x11, 0x11],
        [None, "Wireless Keyboard K520", "Craft Advanced Keyboard", "MX Air", "MX Vertical Wireless Mouse", None],
        ["CODE", "K520", "Craft", "MX Air", "MX Vertical", "CODE"],
        [None, 1.0, 4.5, 1.0, 4.5, None],
        [1.0, 1.0, 4.5, 1.0, 4.5, 4.5],
        [
            "CODE",
            "Wireless Keyboard K520",
            "Craft Advanced Keyboard",
            "MX Air",
            "MX Vertical Wireless Mouse",
            "ABABABABABABABADED",
        ],
    ),
)
def test_device_receiver(number, pairing_info, responses, handle, _name, codename, p, p2, name):
    low_level = LowLevelInterfaceFake(responses)
    low_level.request = partial(fake_hidpp.request, fake_hidpp.replace_number(responses, number))
    low_level.ping = partial(fake_hidpp.ping, fake_hidpp.replace_number(responses, number))

    test_device = device.Device(low_level, FakeReceiver(codename="CODE"), number, True, pairing_info, handle=handle)
    test_device.receiver.device = test_device

    assert test_device.handle == handle
    assert test_device._name == _name
    assert test_device.codename == codename
    assert test_device.number == number
    assert test_device._protocol == p
    assert test_device.protocol == p2
    assert test_device.codename == codename
    assert test_device.name == name

    assert test_device == test_device
    assert not (test_device != test_device)
    assert bool(test_device)

    test_device.__del__()


@pytest.mark.parametrize(
    "number, info, responses, handle, unitId, modelId, task_id, kind, firmware, serial, id, psl, rate",
    zip(
        range(1, 7),
        [pi_CCCC, pi_2011, pi_4066, pi_1007, pi_407B, pi_DDDD],
        [
            fake_hidpp.r_empty,
            fake_hidpp.r_keyboard_1,
            fake_hidpp.r_keyboard_2,
            fake_hidpp.r_mouse_1,
            fake_hidpp.r_mouse_2,
            fake_hidpp.r_mouse_3,
        ],
        [None, 0x11, 0x11, 0x11, 0x11, 0x11],
        [None, None, "12345678", None, None, "12345679"],  # unitId
        [None, None, "1234567890AB", None, None, "123456780000"],  # modelId
        [None, None, {"btid": "1234", "wpid": "5678", "usbid": "90AB"}, None, None, {"usbid": "1234"}],  # tid_map
        ["?", 1, 1, 2, 2, 2],  # kind
        [(), True, (), (), (), True],  # firmware
        [None, "1234", "5678", "1234", "5678", "1234"],  # serial
        ["", "1234", "12345678", "1234", "5678", "12345679"],  # id
        ["top", "bottom", "left", "right", "left", "top"],  # power switch location
        ["1ms", "2ms", "4ms", "8ms", "1ms", "9ms"],  # polling rate
    ),
)
def test_device_ids(number, info, responses, handle, unitId, modelId, task_id, kind, firmware, serial, id, psl, rate):
    low_level = LowLevelInterfaceFake(responses)
    low_level.request = partial(fake_hidpp.request, fake_hidpp.replace_number(responses, number))
    low_level.ping = partial(fake_hidpp.ping, fake_hidpp.replace_number(responses, number))

    test_device = device.Device(low_level, FakeReceiver(), number, True, info, handle=handle)

    assert test_device.unitId == unitId
    assert test_device.modelId == modelId
    assert test_device.tid_map == task_id
    assert test_device.kind == kind
    assert test_device.firmware == firmware or len(test_device.firmware) > 0 and firmware is True
    assert test_device.id == id
    assert test_device.power_switch_location == psl
    assert test_device.polling_rate == rate


class FakeDevice(device.Device):  # a fully functional Device but its HID++ functions look at local data
    def __init__(self, responses, *args, **kwargs):
        self.responses = responses
        super().__init__(LowLevelInterfaceFake(responses), *args, **kwargs)

    request = fake_hidpp.Device.request
    ping = fake_hidpp.Device.ping


@pytest.mark.parametrize(
    "device_info, responses, protocol, led, keys, remap, gestures, backlight, profiles",
    [
        (di_CCCC, fake_hidpp.r_empty, 1.0, type(None), None, None, None, None, None),
        (di_C318, fake_hidpp.r_empty, 1.0, type(None), None, None, None, None, None),
        (di_B530, fake_hidpp.r_keyboard_1, 1.0, type(None), None, None, None, None, None),
        (di_B530, fake_hidpp.r_keyboard_2, 2.0, type(None), 4, 0, 0, None, None),
        (di_B530, fake_hidpp.complex_responses_1, 4.5, hidpp20.LEDEffectsInfo, 0, 0, 0, None, None),
        (di_B530, fake_hidpp.complex_responses_2, 4.5, hidpp20.RGBEffectsInfo, 8, 3, 1, True, True),
    ],
)
def test_device_complex(device_info, responses, protocol, led, keys, remap, gestures, backlight, profiles, mocker):
    test_device = FakeDevice(responses, None, None, True, device_info=device_info)
    test_device._name = "TestDevice"
    test_device._protocol = protocol
    spy_request = mocker.spy(test_device, "request")

    assert type(test_device.led_effects) == led
    if keys is None:
        assert test_device.keys == keys
    else:
        assert len(test_device.keys) == keys
    if remap is None:
        assert test_device.remap_keys == remap
    else:
        assert len(test_device.remap_keys) == remap
    assert (test_device.gestures is None) == (gestures is None)
    assert (test_device.backlight is None) == (backlight is None)
    assert (test_device.profiles is None) == (profiles is None)

    test_device.set_configuration(55)
    if protocol > 1.0:
        spy_request.assert_called_with(0x210, 55, no_reply=False)
    test_device.reset()
    if protocol > 1.0:
        spy_request.assert_called_with(0x210, 0, no_reply=False)


@pytest.mark.parametrize(
    "device_info, responses, protocol, p, persister, settings",
    [
        (di_CCCC, fake_hidpp.r_empty, 1.0, None, None, 0),
        (di_C318, fake_hidpp.r_empty, 1.0, {}, {}, 0),
        (di_C318, fake_hidpp.r_keyboard_1, 1.0, {"n": "n"}, {"n": "n"}, 1),
        (di_B530, fake_hidpp.r_keyboard_2, 4.5, {"m": "m"}, {"m": "m"}, 1),
        (di_C068, fake_hidpp.r_mouse_1, 1.0, {"o": "o"}, {"o": "o"}, 2),
        (di_C08A, fake_hidpp.r_mouse_2, 4.5, {"p": "p"}, {"p": "p"}, 0),
    ],
)
def test_device_settings(device_info, responses, protocol, p, persister, settings, mocker):
    mocker.patch("solaar.configuration.persister", return_value=p)
    test_device = FakeDevice(responses, None, None, True, device_info=device_info)
    test_device._name = "TestDevice"
    test_device._protocol = protocol

    assert test_device.persister == persister
    assert len(test_device.settings) == settings


@pytest.mark.parametrize(
    "device_info, responses, protocol, expected_battery, changed",
    [
        (di_C318, fake_hidpp.r_empty, 1.0, None, {"active": True, "alert": 0, "reason": None}),
        (
            di_C318,
            fake_hidpp.r_keyboard_1,
            1.0,
            common.Battery(BatteryLevelApproximation.GOOD.value, None, BatteryStatus.DISCHARGING, None),
            {"active": True, "alert": 0, "reason": None},
        ),
        (
            di_B530,
            fake_hidpp.r_keyboard_2,
            4.5,
            common.Battery(18, 52, None, None),
            {"active": True, "alert": 0, "reason": None},
        ),
    ],
)
def test_device_battery(device_info, responses, protocol, expected_battery, changed, mocker):
    test_device = FakeDevice(responses, None, None, online=True, device_info=device_info)
    test_device._name = "TestDevice"
    test_device._protocol = protocol
    spy_changed = mocker.spy(test_device, "changed")

    assert test_device.battery() == expected_battery
    test_device.read_battery()
    spy_changed.assert_called_with(**changed)
