## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

from enum import Flag
from enum import IntEnum
from typing import List

from .common import NamedInts

"""HID constants for HID++ 1.0.

Most of them as defined by the official Logitech HID++ 1.0
documentation, some of them guessed.
"""

DEVICE_KIND = NamedInts(
    unknown=0x00,
    keyboard=0x01,
    mouse=0x02,
    numpad=0x03,
    presenter=0x04,
    remote=0x07,
    trackball=0x08,
    touchpad=0x09,
    tablet=0x0A,
    gamepad=0x0B,
    joystick=0x0C,
    headset=0x0D,  # not from Logitech documentation
    remote_control=0x0E,  # for compatibility with HID++ 2.0
    receiver=0x0F,  # for compatibility with HID++ 2.0
)


class PowerSwitchLocation(IntEnum):
    BASE = 0x01
    TOP_CASE = 0x02
    EDGE_OF_TOP_RIGHT_CORNER = 0x03
    TOP_LEFT_CORNER = 0x05
    BOTTOM_LEFT_CORNER = 0x06
    TOP_RIGHT_CORNER = 0x07
    BOTTOM_RIGHT_CORNER = 0x08
    TOP_EDGE = 0x09
    RIGHT_EDGE = 0x0A
    LEFT_EDGE = 0x0B
    BOTTOM_EDGE = 0x0C


class NotificationFlag(Flag):
    """Some flags are used both by devices and receivers.

    The Logitech documentation mentions that the first and last (third)
    byte are used for devices while the second is used for the receiver.
    In practise, the second byte is also used for some device-specific
    notifications (keyboard illumination level). Do not simply set all
    notification bits if the software does not support it. For example,
    enabling keyboard_sleep_raw makes the Sleep key a no-operation
    unless the software is updated to handle that event.

    Observations:
    - wireless and software present seen on receivers,
    reserved_r1b4 as well
    - the rest work only on devices as far as we can tell right now
    In the future would be useful to have separate enums for receiver
    and device notification flags, but right now we don't know enough.
    Additional flags taken from https://drive.google.com/file/d/0BxbRzx7vEV7eNDBheWY0UHM5dEU/view?usp=sharing
    """

    @classmethod
    def flag_names(cls, flag_bits: int) -> List[str]:
        """Extract the names of the flags from the integer."""
        indexed = {item.value: item.name for item in cls}

        flag_names = []
        unknown_bits = flag_bits
        for k in indexed:
            # Ensure that the key (flag value) is a power of 2 (a single bit flag)
            assert bin(k).count("1") == 1
            if k & flag_bits == k:
                unknown_bits &= ~k
                flag_names.append(indexed[k].replace("_", " ").lower())

        # Yield any remaining unknown bits
        if unknown_bits != 0:
            flag_names.append(f"unknown:{unknown_bits:06X}")
        return flag_names

    NUMPAD_NUMERICAL_KEYS = 0x800000
    F_LOCK_STATUS = 0x400000
    ROLLER_H = 0x200000
    BATTERY_STATUS = 0x100000  # send battery charge notifications (0x07 or 0x0D)
    MOUSE_EXTRA_BUTTONS = 0x080000
    ROLLER_V = 0x040000
    POWER_KEYS = 0x020000  # system control keys such as Sleep
    KEYBOARD_MULTIMEDIA_RAW = 0x010000  # consumer controls such as Mute and Calculator
    MULTI_TOUCH = 0x001000  # notify on multi-touch changes
    SOFTWARE_PRESENT = 0x000800  # software is controlling part of device behaviour
    LINK_QUALITY = 0x000400  # notify on link quality changes
    UI = 0x000200  # notify on UI changes
    WIRELESS = 0x000100  # notify when the device wireless goes on/off-line
    CONFIGURATION_COMPLETE = 0x000004
    VOIP_TELEPHONY = 0x000002
    THREED_GESTURE = 0x000001


def flags_to_str(flag_bits: int | None, fallback: str) -> str:
    flag_names = []
    if flag_bits is not None:
        if flag_bits == 0:
            flag_names = (fallback,)
        else:
            flag_names = NotificationFlag.flag_names(flag_bits)
    return f"\n{' ':15}".join(sorted(flag_names))


class ErrorCode(IntEnum):
    INVALID_SUB_ID_COMMAND = 0x01
    INVALID_ADDRESS = 0x02
    INVALID_VALUE = 0x03
    CONNECTION_REQUEST_FAILED = 0x04
    TOO_MANY_DEVICES = 0x05
    ALREADY_EXISTS = 0x06
    BUSY = 0x07
    UNKNOWN_DEVICE = 0x08
    RESOURCE_ERROR = 0x09
    REQUEST_UNAVAILABLE = 0x0A
    UNSUPPORTED_PARAMETER_VALUE = 0x0B
    WRONG_PIN_CODE = 0x0C


class PairingError(IntEnum):
    DEVICE_TIMEOUT = 0x01
    DEVICE_NOT_SUPPORTED = 0x02
    TOO_MANY_DEVICES = 0x03
    SEQUENCE_TIMEOUT = 0x06


class BoltPairingError(IntEnum):
    DEVICE_TIMEOUT = 0x01
    FAILED = 0x02


class Registers(IntEnum):
    """Known HID registers.

    Devices usually have a (small) sub-set of these. Some registers are only
    applicable to certain device kinds (e.g. smooth_scroll only applies to mice).
    """

    # Generally applicable
    NOTIFICATIONS = 0x00
    FIRMWARE = 0xF1

    # only apply to receivers
    RECEIVER_CONNECTION = 0x02
    RECEIVER_PAIRING = 0xB2
    DEVICES_ACTIVITY = 0x2B3
    RECEIVER_INFO = 0x2B5
    BOLT_DEVICE_DISCOVERY = 0xC0
    BOLT_PAIRING = 0x2C1
    BOLT_UNIQUE_ID = 0x02FB

    # only apply to devices
    MOUSE_BUTTON_FLAGS = 0x01
    KEYBOARD_HAND_DETECTION = 0x01
    DEVICES_CONFIGURATION = 0x03
    BATTERY_STATUS = 0x07
    KEYBOARD_FN_SWAP = 0x09
    BATTERY_CHARGE = 0x0D
    KEYBOARD_ILLUMINATION = 0x17
    THREE_LEDS = 0x51
    MOUSE_DPI = 0x63

    # notifications
    PASSKEY_REQUEST_NOTIFICATION = 0x4D
    PASSKEY_PRESSED_NOTIFICATION = 0x4E
    DEVICE_DISCOVERY_NOTIFICATION = 0x4F
    DISCOVERY_STATUS_NOTIFICATION = 0x53
    PAIRING_STATUS_NOTIFICATION = 0x54


# Subregisters for receiver_info register
class InfoSubRegisters(IntEnum):
    SERIAL_NUMBER = 0x01  # not found on many receivers
    FW_VERSION = 0x02
    RECEIVER_INFORMATION = 0x03
    PAIRING_INFORMATION = 0x20  # 0x2N, by connected device
    EXTENDED_PAIRING_INFORMATION = 0x30  # 0x3N, by connected device
    DEVICE_NAME = 0x40  # 0x4N, by connected device
    BOLT_PAIRING_INFORMATION = 0x50  # 0x5N, by connected device
    BOLT_DEVICE_NAME = 0x60  # 0x6N01, by connected device


class DeviceFeature(Flag):
    """Features for devices.

    Flags taken from
    https://drive.google.com/file/d/0BxbRzx7vEV7eNDBheWY0UHM5dEU/view?usp=sharing
    """

    RESERVED1 = 0x010000
    SPECIAL_BUTTONS = 0x020000
    ENHANCED_KEY_USAGE = 0x040000
    FAST_FW_REV = 0x080000
    RESERVED2 = 0x100000
    RESERVED3 = 0x200000
    SCROLL_ACCEL = 0x400000
    BUTTONS_CONTROL_RESOLUTION = 0x800000
    INHIBIT_LOCK_KEY_SOUND = 0x000001
    RESERVED4 = 0x000002
    MX_AIR_3D_ENGINE = 0x000004
    HOST_CONTROL_LEDS = 0x000008
    RESERVED5 = 0x000010
    RESERVED6 = 0x000020
    RESERVED7 = 0x000040
    RESERVED8 = 0x000080
