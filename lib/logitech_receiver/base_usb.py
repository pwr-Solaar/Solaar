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

## According to Logitech, they use the following product IDs (as of September 2020)
## USB product IDs for receivers: 0xC526 - 0xC5xx
## Wireless PIDs for hidpp10 devices: 0x2006 - 0x2019
## Wireless PIDs for hidpp20 devices: 0x4002 - 0x4097, 0x4101 - 0x4102
## USB product IDs for hidpp20 devices: 0xC07D - 0xC094, 0xC32B - 0xC344
## Bluetooth product IDs (for hidpp20 devices): 0xB012 - 0xB0xx, 0xB32A - 0xB3xx

# USB ids of Logitech wireless receivers.
# Only receivers supporting the HID++ protocol can go in here.

from .descriptors import DEVICES as _DEVICES
from .i18n import _

# max_devices is only used for receivers that do not support reading from _R.receiver_info offset 0x03, default to 1
# may_unpair is only used for receivers that do not support reading from _R.receiver_info offset 0x03, default to False
# unpair is for receivers that do support reading from _R.receiver_info offset 0x03, no default
## should this last be changed so that may_unpair is used for all receivers? writing to _R.receiver_pairing doesn't seem right
# re_pairs determines whether a receiver pairs by replacing existing pairings, default to False
## currently only one receiver is so marked - should there be more?
# ex100_27mhz_wpid_fix enable workarounds for EX100 and possible other old 27Mhz receivers

_DRIVER = ('hid-generic', 'generic-usb', 'logitech-djreceiver')

_bolt_receiver = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 2,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Bolt Receiver'),
    'receiver_kind': 'bolt',
    'max_devices': 6,
    'may_unpair': True
}

_unifying_receiver = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 2,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Unifying Receiver'),
    'receiver_kind': 'unifying'
}

_nano_receiver = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 1,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Nano Receiver'),
    'receiver_kind': 'nano',
    'may_unpair': False,
    're_pairs': True
}

_nano_receiver_no_unpair = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 1,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Nano Receiver'),
    'receiver_kind': 'nano',
    'may_unpair': False,
    'unpair': False,
    're_pairs': True
}

_nano_receiver_max2 = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 1,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Nano Receiver'),
    'receiver_kind': 'nano',
    'max_devices': 2,
    'may_unpair': False,
    're_pairs': True
}

_nano_receiver_maxn = lambda product_id, max: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 1,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Nano Receiver'),
    'receiver_kind': 'nano',
    'max_devices': max,
    'may_unpair': False,
    're_pairs': True
}

_lenovo_receiver = lambda product_id: {
    'vendor_id': 0x17ef,
    'product_id': product_id,
    'usb_interface': 1,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Nano Receiver'),
    'receiver_kind': 'nano'
}

_lightspeed_receiver = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 2,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('Lightspeed Receiver')
}

_ex100_receiver = lambda product_id: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'usb_interface': 1,
    'hid_driver': _DRIVER,  # noqa: F821
    'name': _('EX100 Receiver 27 Mhz'),
    'receiver_kind': '27Mhz',
    'max_devices': 4,
    'may_unpair': False,
    're_pairs': True,
    'ex100_27mhz_wpid_fix': True
}

# Receivers added here should also be listed in
# share/solaar/io.github.pwr_solaar.solaar.metainfo.xml

# Bolt receivers (marked with the yellow lightning bolt logo)
BOLT_RECEIVER_C548 = _bolt_receiver(0xc548)

# standard Unifying receivers (marked with the orange Unifying logo)
UNIFYING_RECEIVER_C52B = _unifying_receiver(0xc52b)
UNIFYING_RECEIVER_C532 = _unifying_receiver(0xc532)

# Nano receivers (usually sold with low-end devices)
NANO_RECEIVER_ADVANCED = _nano_receiver_no_unpair(0xc52f)
NANO_RECEIVER_C518 = _nano_receiver(0xc518)
NANO_RECEIVER_C51A = _nano_receiver(0xc51a)
NANO_RECEIVER_C51B = _nano_receiver(0xc51b)
NANO_RECEIVER_C521 = _nano_receiver(0xc521)
NANO_RECEIVER_C525 = _nano_receiver(0xc525)
NANO_RECEIVER_C526 = _nano_receiver(0xc526)
NANO_RECEIVER_C52E = _nano_receiver_no_unpair(0xc52e)
NANO_RECEIVER_C531 = _nano_receiver(0xc531)
NANO_RECEIVER_C534 = _nano_receiver_max2(0xc534)
NANO_RECEIVER_C537 = _nano_receiver(0xc537)
NANO_RECEIVER_6042 = _lenovo_receiver(0x6042)

# Lightspeed receivers (usually sold with gaming devices)
LIGHTSPEED_RECEIVER_C539 = _lightspeed_receiver(0xc539)
LIGHTSPEED_RECEIVER_C53A = _lightspeed_receiver(0xc53a)
LIGHTSPEED_RECEIVER_C53D = _lightspeed_receiver(0xc53d)
LIGHTSPEED_RECEIVER_C53F = _lightspeed_receiver(0xc53f)
LIGHTSPEED_RECEIVER_C541 = _lightspeed_receiver(0xc541)
LIGHTSPEED_RECEIVER_C545 = _lightspeed_receiver(0xc545)
LIGHTSPEED_RECEIVER_C547 = _lightspeed_receiver(0xc547)

# EX100 old style receiver pre-unifying protocol
EX100_27MHZ_RECEIVER_C517 = _ex100_receiver(0xc517)

ALL = (
    BOLT_RECEIVER_C548,
    UNIFYING_RECEIVER_C52B,
    UNIFYING_RECEIVER_C532,
    NANO_RECEIVER_ADVANCED,
    NANO_RECEIVER_C518,
    NANO_RECEIVER_C51A,
    NANO_RECEIVER_C51B,
    NANO_RECEIVER_C521,
    NANO_RECEIVER_C525,
    NANO_RECEIVER_C526,
    NANO_RECEIVER_C52E,
    NANO_RECEIVER_C531,
    NANO_RECEIVER_C534,
    NANO_RECEIVER_C537,
    NANO_RECEIVER_6042,
    LIGHTSPEED_RECEIVER_C539,
    LIGHTSPEED_RECEIVER_C53A,
    LIGHTSPEED_RECEIVER_C53D,
    LIGHTSPEED_RECEIVER_C53F,
    LIGHTSPEED_RECEIVER_C541,
    LIGHTSPEED_RECEIVER_C545,
    LIGHTSPEED_RECEIVER_C547,
    EX100_27MHZ_RECEIVER_C517,
)

_wired_device = lambda product_id, interface: {
    'vendor_id': 0x046d,
    'product_id': product_id,
    'bus_id': 0x3,
    'usb_interface': interface,
    'isDevice': True
}

_bt_device = lambda product_id: {'vendor_id': 0x046d, 'product_id': product_id, 'bus_id': 0x5, 'isDevice': True}

DEVICES = []

for _ignore, d in _DEVICES.items():
    if d.usbid:
        DEVICES.append(_wired_device(d.usbid, d.interface if d.interface else 2))
    if d.btid:
        DEVICES.append(_bt_device(d.btid))


def other_device_check(bus_id, vendor_id, product_id):
    """Check whether product is a Logitech USB-connected or Bluetooth device based on bus, vendor, and product IDs
    This allows Solaar to support receiverless HID++ 2.0 devices that it knows nothing about"""
    if vendor_id != 0x46d:  # Logitech
        return
    if bus_id == 0x3:  # USB
        if (product_id >= 0xC07D and product_id <= 0xC094 or product_id >= 0xC32B and product_id <= 0xC344):
            return _wired_device(product_id, 2)
    elif bus_id == 0x5:  # Bluetooth
        if (product_id >= 0xB012 and product_id <= 0xB0FF or product_id >= 0xB32A and product_id <= 0xB3FF):
            return _bt_device(product_id)


def product_information(usb_id):
    if isinstance(usb_id, str):
        usb_id = int(usb_id, 16)
    for r in ALL:
        if usb_id == r.get('product_id'):
            return r
    return {}


del _DRIVER, _unifying_receiver, _nano_receiver, _lenovo_receiver, _lightspeed_receiver
