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

"""Collection of known Logitech product IDs.

According to Logitech, they use the following product IDs (as of September 2020)
USB product IDs for receivers: 0xC526 - 0xC5xx
Wireless PIDs for hidpp10 devices: 0x2006 - 0x2019
Wireless PIDs for hidpp20 devices: 0x4002 - 0x4097, 0x4101 - 0x4102
USB product IDs for hidpp20 devices: 0xC07D - 0xC094, 0xC32B - 0xC344
Bluetooth product IDs (for hidpp20 devices): 0xB012 - 0xB0xx, 0xB32A - 0xB3xx

USB ids of Logitech wireless receivers.
Only receivers supporting the HID++ protocol can go in here.
"""

from __future__ import annotations

from typing import Any

from solaar.i18n import _

# max_devices is only used for receivers that do not support reading from Registers.RECEIVER_INFO offset 0x03, default
# to 1.
# may_unpair is only used for receivers that do not support reading from Registers.RECEIVER_INFO offset 0x03,
# default to False.
# unpair is for receivers that do support reading from Registers.RECEIVER_INFO offset 0x03, no default.
## should this last be changed so that may_unpair is used for all receivers? writing to Registers.RECEIVER_PAIRING
## doesn't seem right

LOGITECH_VENDOR_ID = 0x046D


def _bolt_receiver(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 2,
        "name": _("Bolt Receiver"),
        "receiver_kind": "bolt",
        "max_devices": 6,
        "may_unpair": True,
    }


def _unifying_receiver(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 2,
        "name": _("Unifying Receiver"),
        "receiver_kind": "unifying",
        "may_unpair": True,
    }


def _nano_receiver(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 1,
        "name": _("Nano Receiver"),
        "receiver_kind": "nano",
        "may_unpair": False,
        "re_pairs": True,
    }


def _nano_receiver_no_unpair(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 1,
        "name": _("Nano Receiver"),
        "receiver_kind": "nano",
        "may_unpair": False,
        "unpair": False,
        "re_pairs": True,
    }


def _nano_receiver_max2(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 1,
        "name": _("Nano Receiver"),
        "receiver_kind": "nano",
        "max_devices": 2,
        "may_unpair": False,
        "re_pairs": True,
    }


def _lenovo_receiver(product_id: int) -> dict:
    return {
        "vendor_id": 6127,
        "product_id": product_id,
        "usb_interface": 1,
        "name": _("Nano Receiver"),
        "receiver_kind": "nano",
        "may_unpair": False,
    }


def _lightspeed_receiver(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 2,
        "receiver_kind": "lightspeed",
        "name": _("Lightspeed Receiver"),
        "may_unpair": False,
    }


def _ex100_receiver(product_id: int) -> dict:
    return {
        "vendor_id": LOGITECH_VENDOR_ID,
        "product_id": product_id,
        "usb_interface": 1,
        "name": _("EX100 Receiver 27 Mhz"),
        "receiver_kind": "27Mhz",
        "max_devices": 4,
        "may_unpair": False,
        "re_pairs": True,
    }


# Receivers added here should also be listed in
# share/solaar/io.github.pwr_solaar.solaar.meta-info.xml
# Look in https://github.com/torvalds/linux/blob/master/drivers/hid/hid-ids.h

# Bolt receivers (marked with the yellow lightning bolt logo)
BOLT_RECEIVER_C548 = _bolt_receiver(0xC548)

# standard Unifying receivers (marked with the orange Unifying logo)
UNIFYING_RECEIVER_C52B = _unifying_receiver(0xC52B)
UNIFYING_RECEIVER_C532 = _unifying_receiver(0xC532)

# Nano receivers (usually sold with low-end devices)
NANO_RECEIVER_ADVANCED = _nano_receiver_no_unpair(0xC52F)
NANO_RECEIVER_C518 = _nano_receiver(0xC518)
NANO_RECEIVER_C51A = _nano_receiver(0xC51A)
NANO_RECEIVER_C51B = _nano_receiver(0xC51B)
NANO_RECEIVER_C521 = _nano_receiver(0xC521)
NANO_RECEIVER_C525 = _nano_receiver(0xC525)
NANO_RECEIVER_C526 = _nano_receiver(0xC526)
NANO_RECEIVER_C52E = _nano_receiver_no_unpair(0xC52E)
NANO_RECEIVER_C531 = _nano_receiver(0xC531)
NANO_RECEIVER_C534 = _nano_receiver_max2(0xC534)
NANO_RECEIVER_C535 = _nano_receiver(0xC535)  # branded as Dell
NANO_RECEIVER_C537 = _nano_receiver(0xC537)
NANO_RECEIVER_6042 = _lenovo_receiver(0x6042)

# Lightspeed receivers (usually sold with gaming devices)
LIGHTSPEED_RECEIVER_C539 = _lightspeed_receiver(0xC539)
LIGHTSPEED_RECEIVER_C53A = _lightspeed_receiver(0xC53A)
LIGHTSPEED_RECEIVER_C53D = _lightspeed_receiver(0xC53D)
LIGHTSPEED_RECEIVER_C53F = _lightspeed_receiver(0xC53F)
LIGHTSPEED_RECEIVER_C541 = _lightspeed_receiver(0xC541)
LIGHTSPEED_RECEIVER_C545 = _lightspeed_receiver(0xC545)
LIGHTSPEED_RECEIVER_C547 = _lightspeed_receiver(0xC547)

# EX100 old style receiver pre-unifying protocol
EX100_27MHZ_RECEIVER_C517 = _ex100_receiver(0xC517)

KNOWN_RECEIVERS = {
    0xC548: BOLT_RECEIVER_C548,
    0xC52B: UNIFYING_RECEIVER_C52B,
    0xC532: UNIFYING_RECEIVER_C532,
    0xC52F: NANO_RECEIVER_ADVANCED,
    0xC518: NANO_RECEIVER_C518,
    0xC51A: NANO_RECEIVER_C51A,
    0xC51B: NANO_RECEIVER_C51B,
    0xC521: NANO_RECEIVER_C521,
    0xC525: NANO_RECEIVER_C525,
    0xC526: NANO_RECEIVER_C526,
    0xC52E: NANO_RECEIVER_C52E,
    0xC531: NANO_RECEIVER_C531,
    0xC534: NANO_RECEIVER_C534,
    0xC535: NANO_RECEIVER_C535,
    0xC537: NANO_RECEIVER_C537,
    0x6042: NANO_RECEIVER_6042,
    0xC539: LIGHTSPEED_RECEIVER_C539,
    0xC53A: LIGHTSPEED_RECEIVER_C53A,
    0xC53D: LIGHTSPEED_RECEIVER_C53D,
    0xC53F: LIGHTSPEED_RECEIVER_C53F,
    0xC541: LIGHTSPEED_RECEIVER_C541,
    0xC545: LIGHTSPEED_RECEIVER_C545,
    0xC547: LIGHTSPEED_RECEIVER_C547,
    0xC517: EX100_27MHZ_RECEIVER_C517,
}


def get_receiver_info(product_id: int) -> dict[str, Any]:
    """Returns hardcoded information about a Logitech receiver.

    Parameters
    ----------
    product_id
        Product ID (pid) of the receiver, e.g. 0xC548 for a Logitech
        Bolt receiver.

    Returns
    -------
    dict[str, Any]
        Receiver info with mandatory fields:
        - vendor_id
        - product_id

    Raises
    ------
    ValueError
        If the product ID is unknown.
    """
    try:
        return KNOWN_RECEIVERS[product_id]
    except KeyError:
        pass

    raise ValueError(f"Unknown product ID '0x{product_id:02X}'")
