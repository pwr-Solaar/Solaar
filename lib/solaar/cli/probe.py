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

from logitech_receiver import base as _base
from logitech_receiver import hidpp10 as _hidpp10
from logitech_receiver.common import strhex as _strhex
from solaar.cli.show import _print_device, _print_receiver

_R = _hidpp10.REGISTERS


def run(receivers, args, find_receiver, _ignore):
    assert receivers

    if args.receiver:
        receiver_name = args.receiver.lower()
        receiver = find_receiver(receivers, receiver_name)
        if not receiver:
            raise Exception("no receiver found matching '%s'" % receiver_name)
    else:
        receiver = receivers[0]

    assert receiver is not None

    if receiver.isDevice:
        _print_device(receiver, 1)
        return

    _print_receiver(receiver)

    print('')
    print('  Register Dump')
    rgst = receiver.read_register(_R.notifications)
    print('    Notifications         %#04x: %s' % (_R.notifications % 0x100, '0x' + _strhex(rgst) if rgst else 'None'))
    rgst = receiver.read_register(_R.receiver_connection)
    print('    Connection State      %#04x: %s' % (_R.receiver_connection % 0x100, '0x' + _strhex(rgst) if rgst else 'None'))
    rgst = receiver.read_register(_R.devices_activity)
    print('    Device Activity       %#04x: %s' % (_R.devices_activity % 0x100, '0x' + _strhex(rgst) if rgst else 'None'))

    for sub_reg in range(0, 6):
        rgst = receiver.read_register(_R.receiver_info, sub_reg)
        print(
            '    Pairing Register %#04x %#04x: %s' %
            (_R.receiver_info % 0x100, sub_reg, '0x' + _strhex(rgst) if rgst else 'None')
        )
    for device in range(0, 6):
        for sub_reg in [0x10, 0x20, 0x30]:
            rgst = receiver.read_register(_R.receiver_info, sub_reg + device)
            print(
                '    Pairing Register %#04x %#04x: %s' %
                (_R.receiver_info % 0x100, sub_reg + device, '0x' + _strhex(rgst) if rgst else 'None')
            )
        rgst = receiver.read_register(_R.receiver_info, 0x40 + device)
        print(
            '    Pairing Name     %#04x %#02x: %s' %
            (_R.receiver_info % 0x100, 0x40 + device, rgst[2:2 + ord(rgst[1:2])] if rgst else 'None')
        )

    for sub_reg in range(0, 5):
        rgst = receiver.read_register(_R.firmware, sub_reg)
        print(
            '    Firmware         %#04x %#04x: %s' %
            (_R.firmware % 0x100, sub_reg, '0x' + _strhex(rgst) if rgst is not None else 'None')
        )

    print('')
    for reg in range(0, 0xFF):
        last = None
        for sub in range(0, 0xFF):
            rgst = _base.request(receiver.handle, 0xFF, 0x8100 | reg, sub, return_error=True)
            if isinstance(rgst, int) and rgst == _hidpp10.ERROR.invalid_address:
                break
            elif isinstance(rgst, int) and rgst == _hidpp10.ERROR.invalid_value:
                continue
            else:
                if not isinstance(last, bytes) or not isinstance(rgst, bytes) or last != rgst:
                    print(
                        '    Register Short   %#04x %#04x: %s' %
                        (reg, sub, '0x' + _strhex(rgst) if isinstance(rgst, bytes) else str(rgst))
                    )
            last = rgst
        last = None
        for sub in range(0, 0xFF):
            rgst = _base.request(receiver.handle, 0xFF, 0x8100 | (0x200 + reg), sub, return_error=True)
            if isinstance(rgst, int) and rgst == _hidpp10.ERROR.invalid_address:
                break
            elif isinstance(rgst, int) and rgst == _hidpp10.ERROR.invalid_value:
                continue
            else:
                if not isinstance(last, bytes) or not isinstance(rgst, bytes) or last != rgst:
                    print(
                        '    Register Long    %#04x %#04x: %s' %
                        (reg, sub, '0x' + _strhex(rgst) if isinstance(rgst, bytes) else str(rgst))
                    )
            last = rgst
