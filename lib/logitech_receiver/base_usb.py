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


_DRIVER = ('hid-generic', 'generic-usb', 'logitech-djreceiver')

# max_devices is only used for receivers that do not support reading from _R.receiver_info offset 0x03, default to 1
# may_unpair is only used for receivers that do not support reading from _R.receiver_info offset 0x03, default to False
## should this last be changed so that may_unpair is used for all receivers? writing to _R.receiver_pairing doesn't seem right
# re_pairs determines whether a receiver pairs by replacing existing pairings, default to False
## currently only one receiver is so marked - should there be more?

_unifying_receiver = lambda product_id: {
	'vendor_id':0x046d,
	'product_id':product_id, 
	'usb_interface':2,
	'hid_driver':_DRIVER,
	'name':'Unifying Receiver'
}

_nano_receiver = lambda product_id: {
	'vendor_id':0x046d,
	'product_id':product_id,
	'usb_interface':1,
	'hid_driver':_DRIVER,
	'name':'Nano Receiver',
	'may_unpair': False,
	're_pairs': True 
}

_nano_receiver_max2 = lambda product_id: {
	'vendor_id':0x046d,
	'product_id':product_id,
	'usb_interface':1,
	'hid_driver':_DRIVER,
	'name':'Nano Receiver',
	'max_devices': 2,
	'may_unpair': False,
	're_pairs': True 
}

_nano_receiver_maxn = lambda product_id, max: {
	'vendor_id':0x046d,
	'product_id':product_id,
	'usb_interface':1,
	'hid_driver':_DRIVER,
	'name':'Nano Receiver',
	'max_devices': max,
	'may_unpair': False,
	're_pairs': True 
}

_lenovo_receiver = lambda product_id: {
	'vendor_id':0x17ef, 
	'product_id':product_id, 
	'usb_interface':1, 
	'hid_driver':_DRIVER, 
	'name':'Nano Receiver'
}

_lightspeed_receiver = lambda product_id: {
	'vendor_id':0x046d,
	'product_id':product_id,
	'usb_interface':2,
	'hid_driver':_DRIVER,
	'name':'Lightspeed Receiver'
}

# standard Unifying receivers (marked with the orange Unifying logo)
UNIFYING_RECEIVER_C52B    = _unifying_receiver(0xc52b)
UNIFYING_RECEIVER_C532    = _unifying_receiver(0xc532)

# Nano receviers that support the Unifying protocol
NANO_RECEIVER_ADVANCED    = _nano_receiver(0xc52f)

# Nano receivers that don't support the Unifying protocol
NANO_RECEIVER_C517        = _nano_receiver_maxn(0xc517,6)
NANO_RECEIVER_C518        = _nano_receiver(0xc518)
NANO_RECEIVER_C51A        = _nano_receiver(0xc51a)
NANO_RECEIVER_C51B        = _nano_receiver(0xc51b)
NANO_RECEIVER_C521        = _nano_receiver(0xc521)
NANO_RECEIVER_C525        = _nano_receiver(0xc525)
NANO_RECEIVER_C526        = _nano_receiver(0xc526)
NANO_RECEIVER_C52e        = _nano_receiver(0xc52e)
NANO_RECEIVER_C531        = _nano_receiver(0xc531)
NANO_RECEIVER_C534        = _nano_receiver_max2(0xc534)
NANO_RECEIVER_C537        = _nano_receiver(0xc537)
NANO_RECEIVER_6042        = _lenovo_receiver(0x6042)

# Lightspeed receivers
LIGHTSPEED_RECEIVER_C539  = _lightspeed_receiver(0xc539)
LIGHTSPEED_RECEIVER_C53a  = _lightspeed_receiver(0xc53a)
LIGHTSPEED_RECEIVER_C53f  = _lightspeed_receiver(0xc53f)

del _DRIVER, _unifying_receiver, _nano_receiver, _lenovo_receiver, _lightspeed_receiver


ALL = (
		UNIFYING_RECEIVER_C52B,
		UNIFYING_RECEIVER_C532,
		NANO_RECEIVER_ADVANCED,
		NANO_RECEIVER_C517,
		NANO_RECEIVER_C518,
		NANO_RECEIVER_C51A,
		NANO_RECEIVER_C51B,
		NANO_RECEIVER_C521,
		NANO_RECEIVER_C525,
		NANO_RECEIVER_C526,
		NANO_RECEIVER_C52e,
		NANO_RECEIVER_C531,
		NANO_RECEIVER_C534,
		NANO_RECEIVER_C537,
		NANO_RECEIVER_6042,
		LIGHTSPEED_RECEIVER_C539,
		LIGHTSPEED_RECEIVER_C53a,
		LIGHTSPEED_RECEIVER_C53f,
	)

def product_information(usb_id):
	if isinstance(usb_id,str):
		usb_id = int(usb_id,16)
	for r in ALL:
		if usb_id == r.get('product_id'):
			return r
	return { }
