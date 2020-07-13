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

from logitech_receiver import settings as _settings
from logitech_receiver import settings_templates as _settings_templates
from solaar import configuration as _configuration


def _print_setting(s, verbose=True):
    print('#', s.label)
    if verbose:
        if s.description:
            print('#', s.description.replace('\n', ' '))
        if s.kind == _settings.KIND.toggle:
            print('#   possible values: on/true/t/yes/y/1 or off/false/f/no/n/0')
        elif s.kind == _settings.KIND.choice:
            print(
                '#   possible values: one of [', ', '.join(str(v) for v in s.choices),
                '], or higher/lower/highest/max/lowest/min'
            )
        else:
            # wtf?
            pass
    value = s.read(cached=False)
    if value is None:
        print(s.name, '= ? (failed to read from device)')
    else:
        print(s.name, '= %r' % value)


def run(receivers, args, find_receiver, find_device):
    assert receivers
    assert args.device

    device_name = args.device.lower()
    dev = find_device(receivers, device_name)

    if not dev.ping():
        raise Exception('%s is offline' % dev.name)

    if not args.setting:  # print all settings, so first set them all up
        if not dev.settings:
            raise Exception('no settings for %s' % dev.name)
        _configuration.attach_to(dev)
        for s in dev.settings:
            s.apply()
        print(dev.name, '(%s) [%s:%s]' % (dev.codename, dev.wpid, dev.serial))
        for s in dev.settings:
            print('')
            _print_setting(s)
        return

    setting_name = args.setting.lower()
    setting = _settings_templates.check_feature_setting(dev, setting_name)
    if setting is None:
        raise Exception("no setting '%s' for %s" % (args.setting, dev.name))
    _configuration.attach_to(dev)

    if args.value is None:
        setting.apply()
        _print_setting(setting)
        return

    if setting.kind == _settings.KIND.toggle:
        value = args.value
        try:
            value = bool(int(value))
        except Exception:
            if value.lower() in ('true', 'yes', 'on', 't', 'y'):
                value = True
            elif value.lower() in ('false', 'no', 'off', 'f', 'n'):
                value = False
            else:
                raise Exception("%s: don't know how to interpret '%s' as boolean" % (setting.name, value))
        print('Setting %s to %s' % (setting.name, value))

    elif setting.kind == _settings.KIND.range:
        try:
            value = int(args.value)
        except ValueError:
            raise Exception("%s: can't interpret '%s' as integer" % (setting.name, args.value))
        min, max = setting.range
        if value < min or value > max:
            raise Exception("%s: value '%s' out of bounds" % (setting.name, args.value))
        print('Setting %s to %s' % (setting.name, value))

    elif setting.kind == _settings.KIND.choice:
        value = args.value
        lvalue = value.lower()
        try:
            ivalue = int(value)
        except ValueError:
            ivalue = None
        if value in setting.choices:
            value = setting.choices[value]
        elif ivalue is not None and ivalue >= 0 and ivalue < len(setting.choices):
            value = setting.choices[ivalue]
        elif lvalue in ('higher', 'lower'):
            old_value = setting.read()
            if old_value is None:
                raise Exception("%s: could not read current value'" % setting.name)
            if lvalue == 'lower':
                lower_values = setting.choices[:old_value]
                value = lower_values[-1] if lower_values else setting.choices[:][0]
            elif lvalue == 'higher':
                higher_values = setting.choices[old_value + 1:]
                value = higher_values[0] if higher_values else setting.choices[:][-1]
        elif lvalue in ('highest', 'max', 'first'):
            value = setting.choices[:][-1]
        elif lvalue in ('lowest', 'min', 'last'):
            value = setting.choices[:][0]
        else:
            raise Exception('%s: possible values are [%s]' % (setting.name, ', '.join(str(v) for v in setting.choices)))
        print('Setting %s to %r' % (setting.name, value))

    else:
        raise Exception('NotImplemented')

    result = setting.write(value)
    if result is None:
        raise Exception("%s: failed to set value '%s' [%r]" % (setting.name, str(value), value))
