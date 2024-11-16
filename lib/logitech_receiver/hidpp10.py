## Copyright (C) 2012-2013  Daniel Pavel
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

import logging

from typing import Any

from typing_extensions import Protocol

from . import common
from .common import Battery
from .common import BatteryLevelApproximation
from .common import BatteryStatus
from .common import FirmwareKind
from .hidpp10_constants import NotificationFlag
from .hidpp10_constants import Registers

logger = logging.getLogger(__name__)


class Device(Protocol):
    def request(self, request_id, *params):
        ...

    @property
    def kind(self) -> Any:
        ...

    @property
    def online(self) -> bool:
        ...

    @property
    def protocol(self) -> Any:
        ...

    @property
    def registers(self) -> list:
        ...


def read_register(device: Device, register: Registers | int, *params) -> Any:
    assert device is not None, f"tried to read register {register:02X} from invalid device {device}"
    # support long registers by adding a 2 in front of the register number
    request_id = 0x8100 | (int(register) & 0x2FF)
    return device.request(request_id, *params)


def write_register(device: Device, register: Registers | int, *value) -> Any:
    assert device is not None, f"tried to write register {register:02X} to invalid device {device}"
    # support long registers by adding a 2 in front of the register number
    request_id = 0x8000 | (int(register) & 0x2FF)
    return device.request(request_id, *value)


def get_configuration_pending_flags(receiver):
    assert not receiver.isDevice
    result = read_register(receiver, Registers.DEVICES_CONFIGURATION)
    if result is not None:
        return ord(result[:1])


def set_configuration_pending_flags(receiver, devices):
    assert not receiver.isDevice
    result = write_register(receiver, Registers.DEVICES_CONFIGURATION, devices)
    return result is not None


class Hidpp10:
    def get_battery(self, device: Device):
        assert device is not None
        assert device.kind is not None
        if not device.online:
            return
        """Reads a device's battery level, if provided by the HID++ 1.0 protocol."""
        if device.protocol and device.protocol >= 2.0:
            # let's just assume HID++ 2.0 devices do not provide the battery info in a register
            return

        for r in (Registers.BATTERY_STATUS, Registers.BATTERY_CHARGE):
            if r in device.registers:
                reply = read_register(device, r)
                if reply:
                    return parse_battery_status(r, reply)
                return

        # the descriptor does not tell us which register this device has, try them both
        reply = read_register(device, Registers.BATTERY_CHARGE)
        if reply:
            # remember this for the next time
            device.registers.append(Registers.BATTERY_CHARGE)
            return parse_battery_status(Registers.BATTERY_CHARGE, reply)

        reply = read_register(device, Registers.BATTERY_STATUS)
        if reply:
            # remember this for the next time
            device.registers.append(Registers.BATTERY_STATUS)
            return parse_battery_status(Registers.BATTERY_STATUS, reply)

    def get_firmware(self, device: Device) -> tuple[common.FirmwareInfo] | None:
        assert device is not None

        firmware = [None, None, None]

        reply = read_register(device, Registers.FIRMWARE, 0x01)
        if not reply:
            # won't be able to read any of it now...
            return

        fw_version = common.strhex(reply[1:3])
        fw_version = f"{fw_version[0:2]}.{fw_version[2:4]}"
        reply = read_register(device, Registers.FIRMWARE, 0x02)
        if reply:
            fw_version += ".B" + common.strhex(reply[1:3])
        fw = common.FirmwareInfo(FirmwareKind.Firmware, "", fw_version, None)
        firmware[0] = fw

        reply = read_register(device, Registers.FIRMWARE, 0x04)
        if reply:
            bl_version = common.strhex(reply[1:3])
            bl_version = f"{bl_version[0:2]}.{bl_version[2:4]}"
            bl = common.FirmwareInfo(FirmwareKind.Bootloader, "", bl_version, None)
            firmware[1] = bl

        reply = read_register(device, Registers.FIRMWARE, 0x03)
        if reply:
            o_version = common.strhex(reply[1:3])
            o_version = f"{o_version[0:2]}.{o_version[2:4]}"
            o = common.FirmwareInfo(FirmwareKind.Other, "", o_version, None)
            firmware[2] = o

        if any(firmware):
            return tuple(f for f in firmware if f)

    def set_3leds(self, device: Device, battery_level=None, charging=None, warning=None):
        assert device is not None
        assert device.kind is not None
        if not device.online:
            return

        if Registers.THREE_LEDS not in device.registers:
            return

        if battery_level is not None:
            if battery_level < BatteryLevelApproximation.CRITICAL:
                # 1 orange, and force blink
                v1, v2 = 0x22, 0x00
                warning = True
            elif battery_level < BatteryLevelApproximation.LOW:
                # 1 orange
                v1, v2 = 0x22, 0x00
            elif battery_level < BatteryLevelApproximation.GOOD:
                # 1 green
                v1, v2 = 0x20, 0x00
            elif battery_level < BatteryLevelApproximation.FULL:
                # 2 greens
                v1, v2 = 0x20, 0x02
            else:
                # all 3 green
                v1, v2 = 0x20, 0x22
            if warning:
                # set the blinking flag for the leds already set
                v1 |= v1 >> 1
                v2 |= v2 >> 1
        elif charging:
            # blink all green
            v1, v2 = 0x30, 0x33
        elif warning:
            # 1 red
            v1, v2 = 0x02, 0x00
        else:
            # turn off all leds
            v1, v2 = 0x11, 0x11

        write_register(device, Registers.THREE_LEDS, v1, v2)

    def get_notification_flags(self, device: Device):
        return self._get_register(device, Registers.NOTIFICATIONS)

    def set_notification_flags(self, device: Device, *flag_bits: NotificationFlag):
        assert device is not None

        # Avoid a call if the device is not online,
        # or the device does not support registers.
        if device.kind is not None:
            # peripherals with protocol >= 2.0 don't support registers
            if device.protocol and device.protocol >= 2.0:
                return

        flag_bits = sum(int(b.value) for b in flag_bits)
        assert flag_bits & 0x00FFFFFF == flag_bits
        result = write_register(device, Registers.NOTIFICATIONS, common.int2bytes(flag_bits, 3))
        return result is not None

    def get_device_features(self, device: Device):
        return self._get_register(device, Registers.MOUSE_BUTTON_FLAGS)

    def _get_register(self, device: Device, register: Registers | int):
        assert device is not None

        # Avoid a call if the device is not online,
        # or the device does not support registers.
        if device.kind is not None:
            # peripherals with protocol >= 2.0 don't support registers
            if device.protocol and device.protocol >= 2.0:
                return

        flags = read_register(device, register)
        if flags is not None:
            assert len(flags) == 3
            return common.bytes2int(flags)


def parse_battery_status(register: Registers | int, reply) -> Battery | None:
    def status_byte_to_charge(status_byte_: int) -> BatteryLevelApproximation:
        if status_byte_ == 7:
            charge_ = BatteryLevelApproximation.FULL
        elif status_byte_ == 5:
            charge_ = BatteryLevelApproximation.GOOD
        elif status_byte_ == 3:
            charge_ = BatteryLevelApproximation.LOW
        elif status_byte_ == 1:
            charge_ = BatteryLevelApproximation.CRITICAL
        else:
            # pure 'charging' notifications may come without a status
            charge_ = BatteryLevelApproximation.EMPTY
        return charge_

    def status_byte_to_battery_status(status_byte_: int) -> BatteryStatus:
        if status_byte_ == 0x30:
            status_text_ = BatteryStatus.DISCHARGING
        elif status_byte_ == 0x50:
            status_text_ = BatteryStatus.RECHARGING
        elif status_byte_ == 0x90:
            status_text_ = BatteryStatus.FULL
        else:
            status_text_ = None
        return status_text_

    def charging_byte_to_status_text(charging_byte_: int) -> BatteryStatus:
        if charging_byte_ == 0x00:
            status_text_ = BatteryStatus.DISCHARGING
        elif charging_byte_ & 0x21 == 0x21:
            status_text_ = BatteryStatus.RECHARGING
        elif charging_byte_ & 0x22 == 0x22:
            status_text_ = BatteryStatus.FULL
        else:
            logger.warning("could not parse 0x07 battery status: %02X (level %02X)", charging_byte_, status_byte)
            status_text_ = None
        return status_text_

    if register == Registers.BATTERY_CHARGE:
        charge = ord(reply[:1])
        status_byte = ord(reply[2:3]) & 0xF0

        battery_status = status_byte_to_battery_status(status_byte)
        return Battery(charge, None, battery_status, None)

    if register == Registers.BATTERY_STATUS:
        status_byte = ord(reply[:1])
        charging_byte = ord(reply[1:2])

        status_text = charging_byte_to_status_text(charging_byte)
        charge = status_byte_to_charge(status_byte)

        if charging_byte & 0x03 and status_byte == 0:
            # some 'charging' notifications may come with no battery level information
            charge = None

        # Return None for next charge level and voltage as these are not in HID++ 1.0 spec
        return Battery(charge, None, status_text, None)
