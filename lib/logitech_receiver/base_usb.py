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

# USB ids of Logitech wireless receivers.
# Only receivers supporting the HID++ protocol can go in here.

from __future__ import absolute_import, division, print_function, unicode_literals


_UNIFYING_DRIVER = 'logitech-djreceiver'
_GENERIC_DRIVER = ('hid-generic', 'generic-usb')


# each tuple contains (vendor_id, product_id, usb interface number, hid driver)

# standard Unifying receivers (marked with the orange Unifying logo)
UNIFYING_RECEIVER         = (0x046d, 0xc52b, 2, _UNIFYING_DRIVER)
UNIFYING_RECEIVER_2       = (0x046d, 0xc532, 2, _UNIFYING_DRIVER)



# Nano receviers that support the Unifying protocol
NANO_RECEIVER_ADVANCED    = (0x046d, 0xc52f, 1, _GENERIC_DRIVER)

# Nano receivers that don't support the Unifying protocol
NANO_RECEIVER_C517        = (0x046d, 0xc517, 1, _GENERIC_DRIVER)
NANO_RECEIVER_C518        = (0x046d, 0xc518, 1, _GENERIC_DRIVER)
NANO_RECEIVER_C51A        = (0x046d, 0xc51a, 1, _GENERIC_DRIVER)
NANO_RECEIVER_C51B        = (0x046d, 0xc51b, 1, _GENERIC_DRIVER)
NANO_RECEIVER_C521        = (0x046d, 0xc521, 1, _GENERIC_DRIVER)
NANO_RECEIVER_C525        = (0x046d, 0xc525, 1, _GENERIC_DRIVER)
NANO_RECEIVER_C526        = (0x046d, 0xc526, 1, _GENERIC_DRIVER)



ALL = (
		UNIFYING_RECEIVER,
		UNIFYING_RECEIVER_2,
		NANO_RECEIVER_ADVANCED,
		NANO_RECEIVER_C517,
		NANO_RECEIVER_C518,
		NANO_RECEIVER_C51A,
		NANO_RECEIVER_C51B,
		NANO_RECEIVER_C521,
		NANO_RECEIVER_C525,
		NANO_RECEIVER_C526,
	)
