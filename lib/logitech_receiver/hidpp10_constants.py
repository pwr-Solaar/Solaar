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
from enum import IntEnum

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
NOTIFICATION_FLAG = NamedInts(
    numpad_numerical_keys=0x800000,
    f_lock_status=0x400000,
    roller_H=0x200000,
    battery_status=0x100000,  # send battery charge notifications (0x07 or 0x0D)
    mouse_extra_buttons=0x080000,
    roller_V=0x040000,
    power_keys=0x020000,  # system control keys such as Sleep
    keyboard_multimedia_raw=0x010000,  # consumer controls such as Mute and Calculator
    multi_touch=0x001000,  # notify on multi-touch changes
    software_present=0x000800,  # software is controlling part of device behaviour
    link_quality=0x000400,  # notify on link quality changes
    ui=0x000200,  # notify on UI changes
    wireless=0x000100,  # notify when the device wireless goes on/off-line
    configuration_complete=0x000004,
    voip_telephony=0x000002,
    threed_gesture=0x000001,
)


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
INFO_SUBREGISTERS = NamedInts(
    serial_number=0x01,  # not found on many receivers
    fw_version=0x02,
    receiver_information=0x03,
    pairing_information=0x20,  # 0x2N, by connected device
    extended_pairing_information=0x30,  # 0x3N, by connected device
    device_name=0x40,  # 0x4N, by connected device
    bolt_pairing_information=0x50,  # 0x5N, by connected device
    bolt_device_name=0x60,  # 0x6N01, by connected device,
)

# Flags taken from https://drive.google.com/file/d/0BxbRzx7vEV7eNDBheWY0UHM5dEU/view?usp=sharing
DEVICE_FEATURES = NamedInts(
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
