# -*- python-mode -*-
# -*- coding: UTF-8 -*-

# Copyright (C) 2012-2013  Daniel Pavel
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import sys
import time

import hidapi as _hid
import pyautogui

from logitech_receiver.base import filter_receivers


def _error(text, scroll=False):
    print('!!', text, scroll)


def _continuous_read(handle, sens, timeout=2000):
    pyautogui.PAUSE = 0
    while True:
        try:
            reply = _hid.read(handle, 128, timeout)
        except OSError as e:
            _error('Read failed, aborting: ' + str(e), True)
            break
        assert reply is not None
        if reply:
            if reply[:1] == b'\x11' and reply[2:4] == b'\x0f\x00':
                thumb = round(int.from_bytes(reply[5:6], 'big', signed=True) * sens)
                if thumb != 0:
                    pyautogui.hscroll(thumb)


def _open():
    device = None
    for d in _hid.enumerate(filter_receivers):
        if d.driver == 'logitech-djreceiver':
            device = d.path
            break
    if not device:
        sys.exit('!! No HID++ receiver found.')

    print('.. Opening device', device)
    handle = _hid.open_path(device)
    if not handle:
        sys.exit('!! Failed to open %s, aborting.' % device)

    print(
        '.. Opened handle %r, vendor %r product %r serial %r.' %
        (handle, _hid.get_manufacturer(handle), _hid.get_product(handle), _hid.get_serial(handle))
    )

    if _hid.get_manufacturer(handle) != b'Logitech':
        sys.exit('!! Only Logitech devices support the HID++ protocol.')

    print('.. HID++ validation enabled.')
    return handle


def _restricted_float(x):
    try:
        x = float(x)
    except ValueError:
        raise argparse.ArgumentTypeError('%r not a floating-point literal' % (x, ))
    return x


def _parse_arguments():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        '--sens',
        type=_restricted_float,
        dest='sens',
        action='store',
        default=1,
        help='hscroll sensitivity (float). default=1'
    )
    return arg_parser.parse_args()


def main():
    args = _parse_arguments()
    handle = _open()

    print('Start with sensitivity = %f' % args.sens)

    try:
        from threading import Thread
        t = Thread(target=_continuous_read, args=(handle, args.sens))
        t.daemon = True
        t.start()

        while t.is_alive():
            time.sleep(1)

    except EOFError:
        pass

    finally:
        print('.. Closing handle %r' % handle)
        _hid.close(handle)


if __name__ == '__main__':
    main()
