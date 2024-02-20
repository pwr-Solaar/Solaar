# -*- python-mode -*-

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

import logging

from .common import BATTERY_APPROX as _BATTERY_APPROX
from .common import FirmwareInfo as _FirmwareInfo
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes
from .common import strhex as _strhex
from .hidpp10_constants import REGISTERS
from .hidpp20_constants import BATTERY_STATUS, FIRMWARE_KIND

logger = logging.getLogger(__name__)

#
# functions
#


def read_register(device, register_number, *params):
    assert device is not None, "tried to read register %02X from invalid device %s" % (register_number, device)
    # support long registers by adding a 2 in front of the register number
    request_id = 0x8100 | (int(register_number) & 0x2FF)
    return device.request(request_id, *params)


def write_register(device, register_number, *value):
    assert device is not None, "tried to write register %02X to invalid device %s" % (register_number, device)
    # support long registers by adding a 2 in front of the register number
    request_id = 0x8000 | (int(register_number) & 0x2FF)
    return device.request(request_id, *value)


def get_battery(device):
    assert device is not None
    assert device.kind is not None
    if not device.online:
        return
    """Reads a device's battery level, if provided by the HID++ 1.0 protocol."""
    if device.protocol and device.protocol >= 2.0:
        # let's just assume HID++ 2.0 devices do not provide the battery info in a register
        return

    for r in (REGISTERS.battery_status, REGISTERS.battery_charge):
        if r in device.registers:
            reply = read_register(device, r)
            if reply:
                return parse_battery_status(r, reply)
            return

    # the descriptor does not tell us which register this device has, try them both
    reply = read_register(device, REGISTERS.battery_charge)
    if reply:
        # remember this for the next time
        device.registers.append(REGISTERS.battery_charge)
        return parse_battery_status(REGISTERS.battery_charge, reply)

    reply = read_register(device, REGISTERS.battery_status)
    if reply:
        # remember this for the next time
        device.registers.append(REGISTERS.battery_status)
        return parse_battery_status(REGISTERS.battery_status, reply)


def parse_battery_status(register, reply):
    if register == REGISTERS.battery_charge:
        charge = ord(reply[:1])
        status_byte = ord(reply[2:3]) & 0xF0
        status_text = (
            BATTERY_STATUS.discharging
            if status_byte == 0x30
            else BATTERY_STATUS.recharging
            if status_byte == 0x50
            else BATTERY_STATUS.full
            if status_byte == 0x90
            else None
        )
        return charge, None, status_text, None

    if register == REGISTERS.battery_status:
        status_byte = ord(reply[:1])
        charge = (
            _BATTERY_APPROX.full
            if status_byte == 7  # full
            else _BATTERY_APPROX.good
            if status_byte == 5  # good
            else _BATTERY_APPROX.low
            if status_byte == 3  # low
            else _BATTERY_APPROX.critical
            if status_byte == 1  # critical
            # pure 'charging' notifications may come without a status
            else _BATTERY_APPROX.empty
        )

        charging_byte = ord(reply[1:2])
        if charging_byte == 0x00:
            status_text = BATTERY_STATUS.discharging
        elif charging_byte & 0x21 == 0x21:
            status_text = BATTERY_STATUS.recharging
        elif charging_byte & 0x22 == 0x22:
            status_text = BATTERY_STATUS.full
        else:
            logger.warning("could not parse 0x07 battery status: %02X (level %02X)", charging_byte, status_byte)
            status_text = None

        if charging_byte & 0x03 and status_byte == 0:
            # some 'charging' notifications may come with no battery level information
            charge = None

        # Return None for next charge level and voltage as these are not in HID++ 1.0 spec
        return charge, None, status_text, None


def get_firmware(device):
    assert device is not None

    firmware = [None, None, None]

    reply = read_register(device, REGISTERS.firmware, 0x01)
    if not reply:
        # won't be able to read any of it now...
        return

    fw_version = _strhex(reply[1:3])
    fw_version = "%s.%s" % (fw_version[0:2], fw_version[2:4])
    reply = read_register(device, REGISTERS.firmware, 0x02)
    if reply:
        fw_version += ".B" + _strhex(reply[1:3])
    fw = _FirmwareInfo(FIRMWARE_KIND.Firmware, "", fw_version, None)
    firmware[0] = fw

    reply = read_register(device, REGISTERS.firmware, 0x04)
    if reply:
        bl_version = _strhex(reply[1:3])
        bl_version = "%s.%s" % (bl_version[0:2], bl_version[2:4])
        bl = _FirmwareInfo(FIRMWARE_KIND.Bootloader, "", bl_version, None)
        firmware[1] = bl

    reply = read_register(device, REGISTERS.firmware, 0x03)
    if reply:
        o_version = _strhex(reply[1:3])
        o_version = "%s.%s" % (o_version[0:2], o_version[2:4])
        o = _FirmwareInfo(FIRMWARE_KIND.Other, "", o_version, None)
        firmware[2] = o

    if any(firmware):
        return tuple(f for f in firmware if f)


def set_3leds(device, battery_level=None, charging=None, warning=None):
    assert device is not None
    assert device.kind is not None
    if not device.online:
        return

    if REGISTERS.three_leds not in device.registers:
        return

    if battery_level is not None:
        if battery_level < _BATTERY_APPROX.critical:
            # 1 orange, and force blink
            v1, v2 = 0x22, 0x00
            warning = True
        elif battery_level < _BATTERY_APPROX.low:
            # 1 orange
            v1, v2 = 0x22, 0x00
        elif battery_level < _BATTERY_APPROX.good:
            # 1 green
            v1, v2 = 0x20, 0x00
        elif battery_level < _BATTERY_APPROX.full:
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

    write_register(device, REGISTERS.three_leds, v1, v2)


def get_notification_flags(device):
    assert device is not None

    # Avoid a call if the device is not online,
    # or the device does not support registers.
    if device.kind is not None:
        # peripherals with protocol >= 2.0 don't support registers
        if device.protocol and device.protocol >= 2.0:
            return

    flags = read_register(device, REGISTERS.notifications)
    if flags is not None:
        assert len(flags) == 3
        return _bytes2int(flags)


def set_notification_flags(device, *flag_bits):
    assert device is not None

    # Avoid a call if the device is not online,
    # or the device does not support registers.
    if device.kind is not None:
        # peripherals with protocol >= 2.0 don't support registers
        if device.protocol and device.protocol >= 2.0:
            return

    flag_bits = sum(int(b) for b in flag_bits)
    assert flag_bits & 0x00FFFFFF == flag_bits
    result = write_register(device, REGISTERS.notifications, _int2bytes(flag_bits, 3))
    return result is not None


def get_device_features(device):
    assert device is not None

    # Avoid a call if the device is not online,
    # or the device does not support registers.
    if device.kind is not None:
        # peripherals with protocol >= 2.0 don't support registers
        if device.protocol and device.protocol >= 2.0:
            return

    flags = read_register(device, REGISTERS.mouse_button_flags)
    if flags is not None:
        assert len(flags) == 3
        return _bytes2int(flags)
