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
from unittest import mock

import pytest

from logitech_receiver import device

from . import hidpp


@pytest.fixture
def mock_base():
    with mock.patch("logitech_receiver.base.open_path", return_value=None) as mock_open_path:
        with mock.patch("logitech_receiver.base.request", return_value=None) as mock_request:
            with mock.patch("logitech_receiver.base.ping", return_value=None) as mock_ping:
                yield mock_open_path, mock_request, mock_ping


@dataclass
class DeviceInfo:
    path: str
    vendor_id: int = 1133
    product_id: int = 4066
    hidpp_short: bool = False
    hidpp_long: bool = True
    bus_id: int = 0x0003  # USB


di_bad_handle = DeviceInfo(None, product_id=0xCCCC)
di_error = DeviceInfo(11, product_id=0xCCCC)
di_CCCC = DeviceInfo("11", product_id=0xCCCC)
di_C318 = DeviceInfo("11", product_id=0xC318)
di_B530 = DeviceInfo("11", product_id=0xB350, bus_id=0x0005)
di_C068 = DeviceInfo("11", product_id=0xC06B)
di_C08A = DeviceInfo("11", product_id=0xC08A)
di_DDDD = DeviceInfo("11", product_id=0xDDDD)


@pytest.mark.parametrize(
    "device_info, responses, success",
    [(di_bad_handle, hidpp.r_empty, None), (di_error, hidpp.r_empty, False), (di_CCCC, hidpp.r_empty, True)],
)
def test_DeviceFactory(device_info, responses, success, mock_base):
    mock_base[0].side_effect = hidpp.open_path
    mock_base[1].side_effect = partial(hidpp.request, responses)
    mock_base[2].side_effect = partial(hidpp.ping, responses)

    if success is None:
        with pytest.raises(Exception):  # noqa: B017
            test_device = device.DeviceFactory.create_device(device_info)
    else:
        test_device = device.DeviceFactory.create_device(device_info)
        assert bool(test_device) == success


@pytest.mark.parametrize(
    "device_info, responses, handle, _name, _codename, number, protocol",
    zip(
        [di_CCCC, di_C318, di_B530, di_C068, di_C08A, di_DDDD],
        [hidpp.r_empty, hidpp.r_keyboard_1, hidpp.r_keyboard_2, hidpp.r_mouse_1, hidpp.r_mouse_2, hidpp.r_mouse_3],
        [0x11, 0x11, 0x11, 0x11, 0x11, 0x11],
        [None, "Illuminated Keyboard", "Craft Advanced Keyboard", "G700 Gaming Mouse", "MX Vertical Wireless Mouse", None],
        [None, "Illuminated", "Craft", "G700", "MX Vertical", None],
        [0xFF, 0x0, 0xFF, 0x0, 0xFF, 0xFF],
        [1.0, 1.0, 4.5, 1.0, 4.5, 4.5],
    ),
)
def test_Device_info(device_info, responses, handle, _name, _codename, number, protocol, mock_base):
    mock_base[0].side_effect = hidpp.open_path
    mock_base[1].side_effect = partial(hidpp.request, responses)
    mock_base[2].side_effect = partial(hidpp.ping, responses)

    test_device = device.Device(None, None, None, handle=handle, device_info=device_info)

    assert test_device.handle == handle
    assert test_device._name == _name
    assert test_device._codename == _codename
    assert test_device.number == number
    assert test_device._protocol == protocol

    assert bool(test_device)
    test_device.__del__()
    assert not bool(test_device)


@dataclass
class Receiver:
    path: str = "11"
    handle: int = 0x11
    codename: Optional[str] = None

    def device_codename(self, number):
        return self.codename

    def __contains__(self, dev):
        return True


@pytest.fixture
def mock_hid():
    with mock.patch("hidapi.find_paired_node", return_value=None) as find_paired_node:
        yield find_paired_node


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
        [hidpp.r_empty, hidpp.r_keyboard_1, hidpp.r_keyboard_2, hidpp.r_mouse_1, hidpp.r_mouse_2, hidpp.r_mouse_3],
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
def test_Device_receiver(number, pairing_info, responses, handle, _name, codename, p, p2, name, mock_base, mock_hid):
    mock_base[0].side_effect = hidpp.open_path
    mock_base[1].side_effect = partial(hidpp.request, hidpp.replace_number(responses, number))
    mock_base[2].side_effect = partial(hidpp.ping, hidpp.replace_number(responses, number))
    mock_hid.side_effect = lambda x, y, z: x

    test_device = device.Device(Receiver(codename="CODE"), number, True, pairing_info, handle=handle)
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
    "number, pairing_info, responses, handle, unitId, modelId, tid_map, kind, firmware, serial, id, psl, rate",
    zip(
        range(1, 7),
        [pi_CCCC, pi_2011, pi_4066, pi_1007, pi_407B, pi_DDDD],
        [hidpp.r_empty, hidpp.r_keyboard_1, hidpp.r_keyboard_2, hidpp.r_mouse_1, hidpp.r_mouse_2, hidpp.r_mouse_3],
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
def test_Device_ids(
    number,
    pairing_info,
    responses,
    handle,
    unitId,
    modelId,
    tid_map,
    kind,
    firmware,
    serial,
    id,
    psl,
    rate,
    mock_base,
    mock_hid,
):
    mock_base[0].side_effect = hidpp.open_path
    mock_base[1].side_effect = partial(hidpp.request, hidpp.replace_number(responses, number))
    mock_base[2].side_effect = partial(hidpp.ping, hidpp.replace_number(responses, number))
    mock_hid.side_effect = lambda x, y, z: x

    test_device = device.Device(Receiver(), number, True, pairing_info, handle=handle)

    assert test_device.unitId == unitId
    assert test_device.modelId == modelId
    assert test_device.tid_map == tid_map
    assert test_device.kind == kind

    assert test_device.firmware == firmware or len(test_device.firmware) > 0 and firmware is True
    assert test_device.id == id
    assert test_device.power_switch_location == psl
    assert test_device.polling_rate == rate


""" TODO
302-305	profiles
309-314	registers
318-337 settings
340-341 set configuration
344	reset
348-352	persister
355-368 battery
372-390 set_battery_info
394-396 read_battery
401-420	enable_connection_notifications
425-451	changed
465	add_notification_handler
470-473	remove_notification_handler
476-480	handle_notification
"""

# IMPORTANT TODO - battery
