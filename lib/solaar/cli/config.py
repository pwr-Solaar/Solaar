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
        print(s.name, '= %s' % value)


def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None


def select_choice(value, choices, setting, key):
    lvalue = value.lower()
    ivalue = to_int(value)
    val = None
    for choice in choices:
        if value == str(choice):
            val = choice
            break
    if val is not None:
        value = val
    elif ivalue is not None and ivalue >= 1 and ivalue <= len(choices):
        value = choices[ivalue - 1]
    elif lvalue in ('higher', 'lower'):
        old_value = setting.read() if key is None else setting.read_key(key)
        if old_value is None:
            raise Exception("%s: could not read current value'" % setting.name)
        if lvalue == 'lower':
            lower_values = choices[:old_value]
            value = lower_values[-1] if lower_values else choices[:][0]
        elif lvalue == 'higher':
            higher_values = choices[old_value + 1:]
            value = higher_values[0] if higher_values else choices[:][-1]
    elif lvalue in ('highest', 'max', 'first'):
        value = choices[:][-1]
    elif lvalue in ('lowest', 'min', 'last'):
        value = choices[:][0]
    else:
        raise Exception('%s: possible values are [%s]' % (setting.name, ', '.join(str(v) for v in choices)))
    return value


def select_toggle(value, setting):
    try:
        value = bool(int(value))
    except Exception:
        if value.lower() in ('true', 'yes', 'on', 't', 'y'):
            value = True
        elif value.lower() in ('false', 'no', 'off', 'f', 'n'):
            value = False
        else:
            raise Exception("%s: don't know how to interpret '%s' as boolean" % (setting.name, value))
    return value


def select_range(value, setting):
    try:
        value = int(value)
    except ValueError:
        raise Exception("%s: can't interpret '%s' as integer" % (setting.name, value))
    min, max = setting.range
    if value < min or value > max:
        raise Exception("%s: value '%s' out of bounds" % (setting.name, value))
    return value


def run(receivers, args, find_receiver, find_device):
    assert receivers
    assert args.device

    device_name = args.device.lower()

    dev = None
    for dev in find_device(receivers, device_name):
        if dev.ping():
            break
        dev = None

    if not dev:
        raise Exception("no online device found matching '%s'" % device_name)

    if not args.setting:  # print all settings, so first set them all up
        if not dev.settings:
            raise Exception('no settings for %s' % dev.name)
        _configuration.attach_to(dev)
        _settings.apply_all_settings(dev)
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

    if args.value_key is None:
        setting.apply()
        _print_setting(setting)
        return

    if setting.kind == _settings.KIND.toggle:
        value = select_toggle(args.value_key, setting)
        print('Setting %s of %s to %s' % (setting.name, dev.name, value))
        result = setting.write(value)

    elif setting.kind == _settings.KIND.range:
        value = select_range(args.value_key, setting)
        print('Setting %s of %s to %s' % (setting.name, dev.name, value))
        result = setting.write(value)

    elif setting.kind == _settings.KIND.choice:
        value = select_choice(args.value_key, setting.choices, setting, None)
        print('Setting %s of %s to %s' % (setting.name, dev.name, value))
        result = setting.write(value)

    elif setting.kind == _settings.KIND.map_choice:
        key = args.value_key
        ikey = to_int(key)
        k = next((k for k in setting.choices.keys() if key == k), None)
        if k is None and ikey is not None:
            k = next((k for k in setting.choices.keys() if ikey == k), None)
        if k is not None:
            value = select_choice(args.extra_subkey, setting.choices[k], setting, key)
        else:
            raise Exception("%s: key '%s' not in setting" % (setting.name, key))
        print('Setting %s of %s key %r to %r' % (setting.name, dev.name, k, value))
        result = setting.write_key_value(int(k), value)

    elif setting.kind == _settings.KIND.multiple_toggle:
        key = args.value_key
        ikey = to_int(key)
        k = next((k for k in setting._labels if key == k), None)
        if k is None and ikey is not None:
            k = next((k for k in setting._labels if ikey == k), None)
        if k is not None:
            value = select_toggle(args.extra_subkey, setting)
        else:
            raise Exception("%s: key '%s' not in setting" % (setting.name, key))
        print('Setting %s key %r to %r' % (setting.name, k, value))
        result = setting.write_key_value(int(k), value)

    elif setting.kind == _settings.KIND.multiple_range:
        key = args.value_key
        ikey = to_int(key)
        if args.extra_subkey is None:
            raise Exception('%s: setting needs a subkey' % (setting.name))
        if args.extra2 is None or to_int(args.extra2) is None:
            raise Exception('%s: setting needs an integer value, not %s' % (setting.name, args.extra2))
        if not setting._value:  # ensure that there are values to look through
            setting.read()
        k = next((k for k in setting._value if key == k), None)
        if k is None and ikey is not None:
            k = next((k for k in setting._value if ikey == k), None)
        item = setting._value[k]
        if args.extra_subkey in item.keys():
            item[args.extra_subkey] = to_int(args.extra2)
        else:
            raise Exception("%s: key '%s' not in setting" % (setting.name, key))
        print('Setting %s key %s parameter %s to %r' % (setting.name, k, args.extra_subkey, item[args.extra_subkey]))
        result = setting.write_item_value(int(k), item)


# KIND = _NamedInts(, multiple_toggle=0x10, multiple_range=0x40)
# BitField; MultipleRange
# disable_keyboard_keys, gesture2; gesture2_params
# k400+ / craft, k400+; k400+

    else:
        raise Exception('NotImplemented')

    if result is None:
        raise Exception("%s: failed to set value '%s' [%r]" % (setting.name, str(value), value))
