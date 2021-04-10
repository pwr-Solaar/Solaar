# -*- python-mode -*-
# -*- coding: UTF-8 -*-

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

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger  # , DEBUG as _DEBUG

from .common import BATTERY_APPROX as _BATTERY_APPROX
from .common import FirmwareInfo as _FirmwareInfo
from .common import NamedInts as _NamedInts
from .common import bytes2int as _bytes2int
from .common import int2bytes as _int2bytes
from .common import strhex as _strhex
from .hidpp20 import BATTERY_STATUS, FIRMWARE_KIND

_log = getLogger(__name__)
del getLogger

#
# Constants - most of them as defined by the official Logitech HID++ 1.0
# documentation, some of them guessed.
#

DEVICE_KIND = _NamedInts(keyboard=0x01, mouse=0x02, numpad=0x03, presenter=0x04, remote=0x07, trackball=0x08, touchpad=0x09)

POWER_SWITCH_LOCATION = _NamedInts(
    base=0x01,
    top_case=0x02,
    edge_of_top_right_corner=0x03,
    top_left_corner=0x05,
    bottom_left_corner=0x06,
    top_right_corner=0x07,
    bottom_right_corner=0x08,
    top_edge=0x09,
    right_edge=0x0A,
    left_edge=0x0B,
    bottom_edge=0x0C
)

# Some flags are used both by devices and receivers. The Logitech documentation
# mentions that the first and last (third) byte are used for devices while the
# second is used for the receiver. In practise, the second byte is also used for
# some device-specific notifications (keyboard illumination level). Do not
# simply set all notification bits if the software does not support it. For
# example, enabling keyboard_sleep_raw makes the Sleep key a no-operation unless
# the software is updated to handle that event.
# Observations:
# - wireless and software present were seen on receivers, reserved_r1b4 as well
# - the rest work only on devices as far as we can tell right now
# In the future would be useful to have separate enums for receiver and device notification flags,
# but right now we don't know enough.
# additional flags taken from https://drive.google.com/file/d/0BxbRzx7vEV7eNDBheWY0UHM5dEU/view?usp=sharing
NOTIFICATION_FLAG = _NamedInts(
    numpad_numerical_keys=0x800000,
    f_lock_status=0x400000,
    roller_H=0x200000,
    battery_status=0x100000,  # send battery charge notifications (0x07 or 0x0D)
    mouse_extra_buttons=0x080000,
    roller_V=0x040000,
    keyboard_sleep_raw=0x020000,  # system control keys such as Sleep
    keyboard_multimedia_raw=0x010000,  # consumer controls such as Mute and Calculator
    # reserved_r1b4=        0x001000,  # unknown, seen on a unifying receiver
    reserved5=0x008000,
    reserved4=0x004000,
    reserved3=0x002000,
    reserved2=0x001000,
    software_present=0x000800,  # .. no idea
    reserved1=0x000400,
    keyboard_illumination=0x000200,  # illumination brightness level changes (by pressing keys)
    wireless=0x000100,  # notify when the device wireless goes on/off-line
    mx_air_3d_gesture=0x000001,
)

ERROR = _NamedInts(
    invalid_SubID__command=0x01,
    invalid_address=0x02,
    invalid_value=0x03,
    connection_request_failed=0x04,
    too_many_devices=0x05,
    already_exists=0x06,
    busy=0x07,
    unknown_device=0x08,
    resource_error=0x09,
    request_unavailable=0x0A,
    unsupported_parameter_value=0x0B,
    wrong_pin_code=0x0C
)

PAIRING_ERRORS = _NamedInts(device_timeout=0x01, device_not_supported=0x02, too_many_devices=0x03, sequence_timeout=0x06)
"""Known registers.
Devices usually have a (small) sub-set of these. Some registers are only
applicable to certain device kinds (e.g. smooth_scroll only applies to mice."""
REGISTERS = _NamedInts(
    # only apply to receivers
    receiver_connection=0x02,
    receiver_pairing=0xB2,
    devices_activity=0x2B3,
    receiver_info=0x2B5,

    # only apply to devices
    mouse_button_flags=0x01,
    keyboard_hand_detection=0x01,
    battery_status=0x07,
    keyboard_fn_swap=0x09,
    battery_charge=0x0D,
    keyboard_illumination=0x17,
    three_leds=0x51,
    mouse_dpi=0x63,

    # apply to both
    notifications=0x00,
    firmware=0xF1,
)
# Subregisters for receiver_info register
INFO_SUBREGISTERS = _NamedInts(
    serial_number=0x01,  # not found on many receivers
    fw_version=0x02,
    receiver_information=0x03,
    pairing_information=0x20,  # 0x2N, by connected device
    extended_pairing_information=0x30,  # 0x3N, by connected device
    device_name=0x40,  # 0x4N, by connected device
)

# Flags taken from https://drive.google.com/file/d/0BxbRzx7vEV7eNDBheWY0UHM5dEU/view?usp=sharing
DEVICE_FEATURES = _NamedInts(
    reserved1=0x010000,
    special_buttons=0x020000,
    enhanced_key_usage=0x040000,
    fast_fw_rev=0x080000,
    reserved2=0x100000,
    reserved3=0x200000,
    scroll_accel=0x400000,
    buttons_control_resolution=0x800000,
    inhibit_lock_key_sound=0x000001,
    reserved4=0x000002,
    mx_air_3d_engine=0x000004,
    host_control_leds=0x000008,
    reserved5=0x000010,
    reserved6=0x000020,
    reserved7=0x000040,
    reserved8=0x000080,
)

#
# functions
#


def read_register(device, register_number, *params):
    assert device is not None, 'tried to read register %02X from invalid device %s' % (register_number, device)
    # support long registers by adding a 2 in front of the register number
    request_id = 0x8100 | (int(register_number) & 0x2FF)
    return device.request(request_id, *params)


def write_register(device, register_number, *value):
    assert device is not None, 'tried to write register %02X to invalid device %s' % (register_number, device)
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
            BATTERY_STATUS.discharging if status_byte == 0x30 else
            BATTERY_STATUS.recharging if status_byte == 0x50 else BATTERY_STATUS.full if status_byte == 0x90 else None
        )
        return charge, status_text, None

    if register == REGISTERS.battery_status:
        status_byte = ord(reply[:1])
        charge = (
            _BATTERY_APPROX.full if status_byte == 7  # full
            else _BATTERY_APPROX.good if status_byte == 5  # good
            else _BATTERY_APPROX.low if status_byte == 3  # low
            else _BATTERY_APPROX.critical if status_byte == 1  # critical
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
            _log.warn('could not parse 0x07 battery status: %02X (level %02X)', charging_byte, status_byte)
            status_text = None

        if charging_byte & 0x03 and status_byte == 0:
            # some 'charging' notifications may come with no battery level information
            charge = None

        # Return None for next charge level as this is not in HID++ 1.0 spec
        return charge, status_text, None


def get_firmware(device):
    assert device is not None

    firmware = [None, None, None]

    reply = read_register(device, REGISTERS.firmware, 0x01)
    if not reply:
        # won't be able to read any of it now...
        return

    fw_version = _strhex(reply[1:3])
    fw_version = '%s.%s' % (fw_version[0:2], fw_version[2:4])
    reply = read_register(device, REGISTERS.firmware, 0x02)
    if reply:
        fw_version += '.B' + _strhex(reply[1:3])
    fw = _FirmwareInfo(FIRMWARE_KIND.Firmware, '', fw_version, None)
    firmware[0] = fw

    reply = read_register(device, REGISTERS.firmware, 0x04)
    if reply:
        bl_version = _strhex(reply[1:3])
        bl_version = '%s.%s' % (bl_version[0:2], bl_version[2:4])
        bl = _FirmwareInfo(FIRMWARE_KIND.Bootloader, '', bl_version, None)
        firmware[1] = bl

    reply = read_register(device, REGISTERS.firmware, 0x03)
    if reply:
        o_version = _strhex(reply[1:3])
        o_version = '%s.%s' % (o_version[0:2], o_version[2:4])
        o = _FirmwareInfo(FIRMWARE_KIND.Other, '', o_version, None)
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
            v1 |= (v1 >> 1)
            v2 |= (v2 >> 1)
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
