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

import argparse as _argparse
import sys as _sys

from logging import DEBUG as _DEBUG
from logging import getLogger

from solaar import NAME

_log = getLogger(__name__)
del getLogger

#
#
#


def _create_parser():
    parser = _argparse.ArgumentParser(
        prog=NAME.lower(),
        add_help=False,
        epilog='For details on individual actions, run `%s <action> --help`.' % NAME.lower()
    )
    subparsers = parser.add_subparsers(title='actions', help='optional action to perform')

    sp = subparsers.add_parser('show', help='show information about devices')
    sp.add_argument(
        'device',
        nargs='?',
        default='all',
        help='device to show information about; may be a device number (1..6), a serial number, '
        'a substring of a device\'s name, or "all" (the default)'
    )
    sp.set_defaults(action='show')

    sp = subparsers.add_parser('probe', help='probe a receiver (debugging use only)')
    sp.add_argument(
        'receiver', nargs='?', help='select receiver by name substring or serial number when more than one is present'
    )
    sp.set_defaults(action='probe')

    sp = subparsers.add_parser(
        'config',
        help='read/write device-specific settings',
        epilog='Please note that configuration only works on active devices.'
    )
    sp.add_argument(
        'device',
        help='device to configure; may be a device number (1..6), a serial number, '
        'or a substring of a device\'s name'
    )
    sp.add_argument('setting', nargs='?', help='device-specific setting; leave empty to list available settings')
    sp.add_argument('value_key', nargs='?', help='new value for the setting or key for keyed settings')
    sp.add_argument('extra_subkey', nargs='?', help='value for keyed or subkey for subkeyed settings')
    sp.add_argument('extra2', nargs='?', help='value for subkeyed settings')
    sp.set_defaults(action='config')

    sp = subparsers.add_parser(
        'pair',
        help='pair a new device',
        epilog='The Logitech Unifying Receiver supports up to 6 paired devices at the same time.'
    )
    sp.add_argument(
        'receiver', nargs='?', help='select receiver by name substring or serial number when more than one is present'
    )
    sp.set_defaults(action='pair')

    sp = subparsers.add_parser('unpair', help='unpair a device')
    sp.add_argument(
        'device',
        help='device to unpair; may be a device number (1..6), a serial number, '
        'or a substring of a device\'s name.'
    )
    sp.set_defaults(action='unpair')

    return parser, subparsers.choices


_cli_parser, actions = _create_parser()
print_help = _cli_parser.print_help


def _receivers(dev_path=None):
    from logitech_receiver import Receiver
    from logitech_receiver.base import receivers
    for dev_info in receivers():
        if dev_path is not None and dev_path != dev_info.path:
            continue
        try:
            r = Receiver.open(dev_info)
            if _log.isEnabledFor(_DEBUG):
                _log.debug('[%s] => %s', dev_info.path, r)
            if r:
                yield r
        except Exception as e:
            _log.exception('opening ' + str(dev_info))
            _sys.exit('%s: error: %s' % (NAME, str(e)))


def _wired_devices(dev_path=None):
    from logitech_receiver import Device
    from logitech_receiver.base import wired_devices
    for dev_info in wired_devices():
        if dev_path is not None and dev_path != dev_info.path:
            continue
        try:
            d = Device.open(dev_info)
            if _log.isEnabledFor(_DEBUG):
                _log.debug('[%s] => %s', dev_info.path, d)
            if d is not None:
                yield d
        except Exception as e:
            _log.exception('opening ' + str(dev_info))
            _sys.exit('%s: error: %s' % (NAME, str(e)))


def _find_receiver(receivers, name):
    assert receivers
    assert name

    for r in receivers:
        if name in r.name.lower() or (r.serial is not None and name == r.serial.lower()):
            return r


def _find_device(receivers, name):
    assert receivers
    assert name

    number = None
    if len(name) == 1:
        try:
            number = int(name)
        except Exception:
            pass
        else:
            assert not (number < 0)
            if number > 6:
                number = None

    for r in receivers:
        if not r.isDevice:  # look for nth device of receiver
            if number and number <= r.max_devices:
                dev = r[number]
                if dev:
                    yield dev
        else:  # wired device, make a device list from it
            r = [r]

        for dev in r:
            if (
                name == dev.serial.lower() or name == dev.codename.lower() or name == str(dev.kind).lower()
                or name in dev.name.lower()
            ):
                yield dev


#    raise Exception("no device found matching '%s'" % name)


def run(cli_args=None, hidraw_path=None):

    if cli_args:
        action = cli_args[0]
        args = _cli_parser.parse_args(cli_args)
    else:
        args = _cli_parser.parse_args()
        # Python 3 has an undocumented 'feature' that breaks parsing empty args
        # http://bugs.python.org/issue16308
        if 'cmd' not in args:
            _cli_parser.print_usage(_sys.stderr)
            _sys.stderr.write('%s: error: too few arguments\n' % NAME.lower())
            _sys.exit(2)
        action = args.action
    assert action in actions

    try:
        c = list(_receivers(hidraw_path))
        if action == 'show' or action == 'probe' or action == 'config':
            c += list(_wired_devices(hidraw_path))

        if not c:
            raise Exception('No devices found')

        from importlib import import_module
        m = import_module('.' + action, package=__name__)
        m.run(c, args, _find_receiver, _find_device)
    except AssertionError:
        from traceback import extract_tb
        tb_last = extract_tb(_sys.exc_info()[2])[-1]
        _sys.exit('%s: assertion failed: %s line %d' % (NAME.lower(), tb_last[0], tb_last[1]))
    except Exception:
        from traceback import format_exc
        _sys.exit('%s: error: %s' % (NAME.lower(), format_exc()))
