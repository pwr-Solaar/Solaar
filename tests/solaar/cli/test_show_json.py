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

from __future__ import annotations

import json

from dataclasses import dataclass
from functools import partial

import pytest

from logitech_receiver import base
from logitech_receiver import exceptions
from logitech_receiver import receiver as receiver_mod
from logitech_receiver.common import Battery
from logitech_receiver.common import BatteryLevelApproximation
from logitech_receiver.common import BatteryStatus
from logitech_receiver.common import NamedInt
from logitech_receiver.device import Device
from solaar.cli.show import _battery_json
from solaar.cli.show import _device_json
from solaar.cli.show import _json_output
from solaar.cli.show import _receiver_json

from tests.logitech_receiver import fake_hidpp


class LowLevelInterfaceFake:
    def __init__(self, responses=None):
        self.responses = responses

    def open_path(self, path) -> int:
        return fake_hidpp.open_path(path)

    def find_paired_node(self, receiver_path: str, index: int, timeout: int):
        return None

    def product_information(self, usb_id: int) -> dict:
        return base.product_information(usb_id)

    def request(self, response, *args, **kwargs):
        func = partial(fake_hidpp.request, self.responses)
        return func(response, *args, **kwargs)

    def ping(self, response, *args, **kwargs):
        func = partial(fake_hidpp.ping, self.responses)
        return func(response, *args, **kwargs)

    def close(self, *args, **kwargs):
        pass


class FakeReceiver:
    name = "Nano Receiver"
    serial = "F14890D2"
    path = "/dev/hidraw2"

    def device_codename(self, number):
        return None

    def __contains__(self, dev):
        return True


@dataclass
class DeviceInfo:
    path: str
    vendor_id: int = 1133
    product_id: int = 0xC534


@dataclass
class DeviceInfoStub:
    path: str
    product_id: str
    vendor_id: int = 1133
    hidpp_short: bool = False
    hidpp_long: bool = True
    bus_id: int = 0x0003
    serial: str = "aa:aa:aa;aa"
    centurion: bool = False
    centurion_report_id: int | None = None


pi_4066 = {"wpid": "4066", "kind": NamedInt(1, "keyboard"), "serial": "5678", "polling": "4ms", "power_switch": "left"}

responses_receiver = [
    fake_hidpp.Response("000000", 0x8003, "FF"),
    fake_hidpp.Response("000300", 0x8102),
]


def _keyboard_device():
    responses = fake_hidpp.replace_number(fake_hidpp.r_keyboard_2, 3)
    return Device(LowLevelInterfaceFake(responses), FakeReceiver(), 3, True, pi_4066, handle=0x11)


def _capture_json(mocker, func, *args):
    printed = []
    mocker.patch("solaar.cli.show.print", side_effect=lambda *a, **kw: printed.append(a[0]))
    func(*args)
    return json.loads(printed[-1])


def _battery(level, status=BatteryStatus.DISCHARGING, next_level=None, voltage=None):
    return Battery(level, next_level, status, voltage)


def test_battery_json_none():
    assert _battery_json(None) is None


def test_battery_json_percentage():
    info = _battery_json(_battery(55, voltage=3800))
    assert info == {
        "level": 55,
        "level_kind": "level",
        "next_level": None,
        "status": "DISCHARGING",
        "voltage": 3800,
    }


def test_battery_json_approximation():
    info = _battery_json(_battery(BatteryLevelApproximation.GOOD))
    assert info["level"] == 50
    assert info["level_kind"] == "approximation"


def test_battery_json_full_approximation():
    info = _battery_json(_battery(BatteryLevelApproximation.FULL, next_level=BatteryLevelApproximation.LOW))
    assert info["level"] == 90
    assert info["level_kind"] == "approximation"
    assert info["next_level"] == 20


@pytest.mark.parametrize(
    "status, expected",
    [
        (BatteryStatus.DISCHARGING, "DISCHARGING"),
        (BatteryStatus.RECHARGING, "RECHARGING"),
        (BatteryStatus.ALMOST_FULL, "ALMOST_FULL"),
        (BatteryStatus.SLOW_RECHARGE, "SLOW_RECHARGE"),
    ],
)
def test_battery_json_status_names(status, expected):
    assert _battery_json(_battery(50, status))["status"] == expected


def test_battery_json_no_status():
    assert _battery_json(_battery(50, None))["status"] is None


def test_battery_json_combined_status_flag():
    combined = BatteryStatus(0x07)  # bits from multiple flags (no canonical name on Python < 3.11)
    status = _battery_json(_battery(50, combined))["status"]
    assert status == "RECHARGING|ALMOST_FULL|SLOW_RECHARGE"


def test_receiver_json_none():
    assert _receiver_json(None) is None


def test_receiver_json_info():
    assert _receiver_json(FakeReceiver()) == {
        "name": "Nano Receiver",
        "serial": "F14890D2",
        "path": "/dev/hidraw2",
    }


def test_device_json_online():
    info = _device_json(_keyboard_device())
    assert info["name"] == "Craft Advanced Keyboard"
    assert info["number"] == 3
    assert info["receiver"] == {"name": "Nano Receiver", "serial": "F14890D2", "path": "/dev/hidraw2"}
    assert info["pid"] == "4066"
    assert info["path"] is None
    assert info["bluetooth"] is False
    assert info["mac"] is None
    assert info["serial"] == "5678"
    assert info["unitId"] == "12345678"
    assert info["modelId"] == "1234567890AB"
    assert info["kind"] == "keyboard"
    assert info["protocol"] == 4.5
    assert info["online"] is True
    assert info["battery"] == {"level": 18, "level_kind": "level", "next_level": 52, "status": None, "voltage": None}


def test_device_json_direct_usb_device():
    di = DeviceInfoStub("11", product_id="C318")
    responses = fake_hidpp.replace_number(fake_hidpp.r_keyboard_1, 0x00)
    dev = Device(LowLevelInterfaceFake(responses), None, None, None, handle=0x11, device_info=di)
    info = _device_json(dev)
    assert info["receiver"] is None
    assert info["pid"] == "C318"
    assert info["path"] == "11"
    assert info["bluetooth"] is False
    assert info["mac"] is None
    assert info["protocol"] == 1.0
    assert info["online"] is True
    assert info["battery"]["level"] == 50


def test_device_json_bluetooth_device():
    di = DeviceInfoStub("11", product_id="B350", bus_id=0x0005)
    dev = Device(LowLevelInterfaceFake(fake_hidpp.r_keyboard_1), None, None, None, handle=0x11, device_info=di)
    info = _device_json(dev)
    assert info["receiver"] is None
    assert info["path"] == "11"
    assert info["bluetooth"] is True
    assert info["mac"] == "aa:aa:aa;aa"
    assert info["online"] is True


def test_device_json_approximation_battery(mocker):
    dev = _keyboard_device()
    mocker.patch.object(dev, "battery", return_value=_battery(BatteryLevelApproximation.GOOD))
    info = _device_json(dev)
    assert info["battery"]["level"] == 50
    assert info["battery"]["level_kind"] == "approximation"


def test_device_json_offline_battery_unavailable():
    pi = {"wpid": "4066", "kind": 1, "serial": None, "polling": "4ms", "power_switch": "left"}
    dev = Device(LowLevelInterfaceFake([]), FakeReceiver(), 1, True, pi, handle=0x11)
    info = _device_json(dev)
    assert info["online"] is False
    assert info["battery"] is None


def test_device_json_no_such_device_returns_none(mocker):
    dev = _keyboard_device()
    mocker.patch.object(dev, "ping", side_effect=exceptions.NoSuchDevice())
    assert _device_json(dev) is None


def test_json_output_all_flattens_receiver(mocker):
    dev = _keyboard_device()
    r = receiver_mod.create_receiver(LowLevelInterfaceFake(responses_receiver), DeviceInfo("14"), lambda x: x)
    r._devices[1] = dev
    mocker.patch.object(r, "count", return_value=1)

    output = _capture_json(mocker, _json_output, [r], "all", None, None)

    assert "solaar_version" in output
    assert [d["name"] for d in output["devices"]] == ["Craft Advanced Keyboard"]
    assert output["devices"][0]["number"] == 3


def test_json_output_single_device(mocker):
    dev = _keyboard_device()
    find_receiver = mocker.Mock(return_value=None)
    find_device = mocker.Mock(return_value=iter([dev]))

    output = _capture_json(mocker, _json_output, [dev], "Craft Advanced Keyboard", find_receiver, find_device)

    assert [d["name"] for d in output["devices"]] == ["Craft Advanced Keyboard"]
    assert output["devices"][0]["battery"]["level"] == 18


def test_json_output_single_device_on_receiver(mocker):
    dev = _keyboard_device()
    r = receiver_mod.create_receiver(LowLevelInterfaceFake(responses_receiver), DeviceInfo("14"), lambda x: x)
    r._devices[1] = dev
    mocker.patch.object(r, "count", return_value=1)
    find_receiver = mocker.Mock(return_value=r)

    output = _capture_json(mocker, _json_output, [r], "Craft Advanced Keyboard", find_receiver, None)

    assert [d["name"] for d in output["devices"]] == ["Craft Advanced Keyboard"]


def test_json_output_no_matching_device_raises(mocker):
    find_receiver = mocker.Mock(return_value=None)
    find_device = mocker.Mock(return_value=iter([]))

    with pytest.raises(Exception, match="no device found"):
        _json_output([], "Missing", find_receiver, find_device)


def test_parser_json_flag():
    from solaar import cli

    parser = cli._create_parser()[0]
    args = parser.parse_args(["show", "--json"])
    assert args.json is True
    assert args.device == "all"


def test_run_json_output(mocker):
    from solaar.cli.show import run

    dev = _keyboard_device()
    args = mocker.Mock(json=True, device="all")

    output = _capture_json(mocker, run, [dev], args, None, None)

    assert [d["name"] for d in output["devices"]] == ["Craft Advanced Keyboard"]


def test_run_json_closes_devices_when_output_raises(mocker):
    from solaar.cli.show import Device
    from solaar.cli.show import run

    dev = _keyboard_device()
    args = mocker.Mock(json=True, device="all")
    mocker.patch("solaar.cli.show._json_output", side_effect=RuntimeError("boom"))
    close = mocker.patch.object(Device, "close")

    with pytest.raises(RuntimeError):
        run([dev], args, None, None)

    close.assert_called()
