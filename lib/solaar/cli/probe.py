# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2020
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


from time import time as _timestamp

from logitech_receiver.common import strhex as _strhex

from logitech_receiver import (
				base as _base,
				hidpp10 as _hidpp10,
				status as _status,
				notifications as _notifications,
			)

_R = _hidpp10.REGISTERS

from solaar.cli.show import _print_receiver

def run(receivers, args, find_receiver, _ignore):
	assert receivers

	if args.receiver:
		receiver_name = args.receiver.lower()
		receiver = find_receiver(receiver_name)
		if not receiver:
			raise Exception("no receiver found matching '%s'" % receiver_name)
	else:
		receiver = receivers[0]

	assert receiver

	_print_receiver(receiver)

	print ('  Register Dump')
	register = receiver.read_register(_R.notifications)
	print("    Notification Register %#04x: %s" % (_R.notifications%0x100,'0x'+_strhex(register) if register else "None"))
	register = receiver.read_register(_R.receiver_connection)
	print("    Connection State      %#04x: %s" % (_R.receiver_connection%0x100,'0x'+_strhex(register) if register else "None"))
	register = receiver.read_register(_R.devices_activity)
	print("    Device Activity       %#04x: %s" % (_R.devices_activity%0x100,'0x'+_strhex(register) if register else "None"))

	for device in range(0,6):
		for sub_reg in [ 0x0, 0x10, 0x20, 0x30 ] :
			register = receiver.read_register(_R.receiver_info, sub_reg + device)
			print("    Pairing Register %#04x %#04x: %s" % (_R.receiver_info%0x100,sub_reg + device,'0x'+_strhex(register) if register else "None"))
		register = receiver.read_register(_R.receiver_info, 0x40 + device)
		print("    Pairing Name     %#04x %#02x: %s" % (_R.receiver_info%0x100,0x40 + device,register[2:2+ord(register[1:2])] if register else "None"))

	for sub_reg in range(0,5):
		register = receiver.read_register(_R.firmware, sub_reg)
		print("    Firmware         %#04x %#04x: %s" % (_R.firmware%0x100,sub_reg,'0x'+_strhex(register) if register else "None"))
