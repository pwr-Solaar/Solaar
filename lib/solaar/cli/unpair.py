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


def run(receivers, args, find_receiver, find_device):
	assert receivers
	assert args.device

	device_name = args.device.lower()
	dev = find_device(receivers, device_name)

	# query these now, it's last chance to get them
	try:
		number, codename, wpid, serial  = dev.number, dev.codename, dev.wpid, dev.serial
		del dev.receiver[number]
		print ('Unpaired %d: %s (%s) [%s:%s]' % (number, dev.name, codename, wpid, serial))
	except Exception as e:
		raise Exception('failed to unpair device %s: %s' % (dev.name, e))
