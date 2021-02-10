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
    dev = next(find_device(receivers, device_name), None)
    if not dev:
        raise Exception("no device found matching '%s'" % device_name)

    if not dev.receiver.may_unpair:
        print(
            'Receiver with USB id %s for %s [%s:%s] does not unpair, but attempting anyway.' %
            (dev.receiver.product_id, dev.name, dev.wpid, dev.serial)
        )
    try:
        # query these now, it's last chance to get them
        number, codename, wpid, serial = dev.number, dev.codename, dev.wpid, dev.serial
        dev.receiver._unpair_device(number, True)  # force an unpair
        print('Unpaired %d: %s (%s) [%s:%s]' % (number, dev.name, codename, wpid, serial))
    except Exception as e:
        raise e
