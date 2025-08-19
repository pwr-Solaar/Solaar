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

import yaml

from logitech_receiver import settings
from logitech_receiver import settings_templates
from logitech_receiver.common import NamedInts
from logitech_receiver.settings_templates import SettingsProtocol

from solaar import configuration

APP_ID = "io.github.pwr_solaar.solaar"


def _print_setting(s, verbose=True):
    print("#", s.label)
    if verbose:
        if s.description:
            print("#", s.description.replace("\n", " "))
        if s.kind == settings.Kind.TOGGLE:
            print("#   possible values: on/true/t/yes/y/1 or off/false/f/no/n/0 or Toggle/~")
        elif s.kind == settings.Kind.CHOICE:
            print(
                "#   possible values: one of [",
                ", ".join(str(v) for v in s.choices),
                "], or higher/lower/highest/max/lowest/min",
            )
        else:
            # wtf?
            pass
    value = s.read(cached=False)
    if value is None:
        print(s.name, "= ? (failed to read from device)")
    else:
        print(s.name, "=", s.val_to_string(value))


def _print_setting_keyed(s, key, verbose=True):
    print("#", s.label)
    if verbose:
        if s.description:
            print("#", s.description.replace("\n", " "))
        if s.kind == settings.Kind.MULTIPLE_TOGGLE:
            k = next((k for k in s._labels if key == k), None)
            if k is None:
                print(s.name, "=? (key not found)")
            else:
                print("#   possible values: on/true/t/yes/y/1 or off/false/f/no/n/0 or Toggle/~")
                value = s.read(cached=False)
                if value is None:
                    print(s.name, "= ? (failed to read from device)")
                else:
                    print(s.name, s.val_to_string({k: value[str(int(k))]}))
        elif s.kind == settings.Kind.MAP_CHOICE:
            k = next((k for k in s.choices.keys() if key == k), None)
            if k is None:
                print(s.name, "=? (key not found)")
            else:
                print("#   possible values: one of [", ", ".join(str(v) for v in s.choices[k]), "]")
                value = s.read(cached=False)
                if value is None:
                    print(s.name, "= ? (failed to read from device)")
                else:
                    print(s.name, s.val_to_string({k: value[int(k)]}))


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
    elif ivalue is not None and 1 <= ivalue <= len(choices):
        value = choices[ivalue - 1]
    elif lvalue in ("higher", "lower"):
        old_value = setting.read() if key is None else setting.read_key(key)
        if old_value is None:
            raise Exception(f"{setting.name}: could not read current value")
        if lvalue == "lower":
            lower_values = choices[:old_value]
            value = lower_values[-1] if lower_values else choices[:][0]
        elif lvalue == "higher":
            higher_values = choices[old_value + 1 :]
            value = higher_values[0] if higher_values else choices[:][-1]
    elif lvalue in ("highest", "max", "first"):
        value = choices[:][-1]
    elif lvalue in ("lowest", "min", "last"):
        value = choices[:][0]
    else:
        raise Exception(f"{setting.name}: possible values are [{', '.join(str(v) for v in choices)}]")
    return value


def select_toggle(value, setting, key=None):
    if value.lower() in ("toggle", "~"):
        value = not (setting.read() if key is None else setting.read()[str(int(key))])
    else:
        try:
            value = bool(int(value))
        except Exception as exc:
            if value.lower() in ("true", "yes", "on", "t", "y"):
                value = True
            elif value.lower() in ("false", "no", "off", "f", "n"):
                value = False
            else:
                raise Exception(f"{setting.name}: don't know how to interpret '{value}' as boolean") from exc
    return value


def select_range(value, setting):
    try:
        value = int(value)
    except ValueError as exc:
        raise Exception(f"{setting.name}: can't interpret '{value}' as integer") from exc
    minimum, maximum = setting.range
    if value < minimum or value > maximum:
        raise Exception(f"{setting.name}: value '{value}' out of bounds")
    return value


def run(receivers, args, _find_receiver, find_device):
    assert receivers
    assert args.device

    device_name = args.device.lower()

    dev = None
    for dev in find_device(receivers, device_name):
        if dev.ping():
            break
        dev = None

    if not dev:
        raise Exception(f"no online device found matching '{device_name}'")

    if not args.setting:  # print all settings, so first set them all up
        if not dev.settings:
            raise Exception(f"no settings for {dev.name}")
        configuration.attach_to(dev)
        print(dev.name, f"({dev.codename}) [{dev.wpid}:{dev.serial}]")
        for s in dev.settings:
            print("")
            _print_setting(s)
        return

    setting_name = args.setting.lower()
    setting = settings_templates.check_feature_setting(dev, setting_name)
    if not setting and dev.descriptor and dev.descriptor.settings:
        for sclass in dev.descriptor.settings:
            if sclass.register and sclass.name == setting_name:
                try:
                    setting = sclass.build(dev)
                except Exception:
                    setting = None
    if setting is None:
        raise Exception(f"no setting '{args.setting}' for {dev.name}")

    if args.value_key is None:
        _print_setting(setting)
        return

    remote = False
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gio
        from gi.repository import Gtk

        if Gtk.init_check()[0]:  # can Gtk be initialized?
            application = Gtk.Application.new(APP_ID, Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
            application.register()
            remote = application.get_is_remote()
    except Exception:
        pass

    # don't save configuration here because we might want the Solaar GUI to make the change
    result, message, value = set(dev, setting, args, False)
    if message is not None:
        print(message)
        if result is None:
            raise Exception(f"{setting.name}: failed to set value '{str(value)}' [{value!r}]")

    # if the Solaar UI is running tell it to also perform the set, otherwise save the change in the configuration file
    if remote:
        argl = ["config", dev.serial or dev.unitId, setting.name]
        argl.extend([a for a in [args.value_key, args.extra_subkey, args.extra2] if a is not None])
        application.run(yaml.safe_dump(argl))
    else:
        if dev.persister and setting.persist:
            dev.persister[setting.name] = setting._value


def set(dev, setting: SettingsProtocol, args, save):
    if setting.kind == settings.Kind.TOGGLE:
        value = select_toggle(args.value_key, setting)
        args.value_key = value
        message = f"Setting {setting.name} of {dev.name} to {value}"
        result = setting.write(value, save=save)

    elif setting.kind == settings.Kind.RANGE:
        value = select_range(args.value_key, setting)
        args.value_key = value
        message = f"Setting {setting.name} of {dev.name} to {value}"
        result = setting.write(value, save=save)

    elif setting.kind == settings.Kind.CHOICE:
        value = select_choice(args.value_key, setting.choices, setting, None)
        args.value_key = int(value)
        message = f"Setting {setting.name} of {dev.name} to {value}"
        result = setting.write(value, save=save)

    elif setting.kind == settings.Kind.MAP_CHOICE:
        if args.extra_subkey is None:
            _print_setting_keyed(setting, args.value_key)
            return None, None, None
        key = args.value_key
        ikey = to_int(key)
        k = next((k for k in setting.choices.keys() if key == k), None)
        if k is None and ikey is not None:
            k = next((k for k in setting.choices.keys() if ikey == k), None)
        if k is not None:
            value = select_choice(args.extra_subkey, setting.choices[k], setting, key)
            args.extra_subkey = int(value)
            args.value_key = str(int(k))
        else:
            raise Exception(f"{setting.name}: key '{key}' not in setting")
        message = f"Setting {setting.name} of {dev.name} key {k!r} to {value!r}"
        result = setting.write_key_value(int(k), value, save=save)

    elif setting.kind == settings.Kind.MULTIPLE_TOGGLE:
        if args.extra_subkey is None:
            _print_setting_keyed(setting, args.value_key)
            return None, None, None
        key = args.value_key
        all_keys = getattr(setting, "choices_universe", None)
        ikey = all_keys[int(key) if key.isdigit() else key] if isinstance(all_keys, NamedInts) else to_int(key)
        k = next((k for k in setting._labels if key == k), None)
        if k is None and ikey is not None:
            k = next((k for k in setting._labels if ikey == k), None)
        if k is not None:
            value = select_toggle(args.extra_subkey, setting, key=k)
            args.extra_subkey = value
            args.value_key = str(int(k))
        else:
            raise Exception(f"{setting.name}: key '{key}' not in setting")
        message = f"Setting {setting.name} key {k!r} to {value!r}"
        result = setting.write_key_value(str(int(k)), value, save=save)

    elif setting.kind == settings.Kind.MULTIPLE_RANGE:
        if args.extra_subkey is None:
            raise Exception(f"{setting.name}: setting needs both key and value to set")
        key = args.value_key
        all_keys = getattr(setting, "choices_universe", None)
        ikey = all_keys[int(key) if key.isdigit() else key] if isinstance(all_keys, NamedInts) else to_int(key)
        if args.extra2 is None or to_int(args.extra2) is None:
            raise Exception(f"{setting.name}: setting needs an integer value, not {args.extra2}")
        if not setting._value:  # ensure that there are values to look through
            setting.read()
        k = next((k for k in setting._value if key == ikey or key.isdigit() and ikey == int(key)), None)
        if k is None and ikey is not None:
            k = next((k for k in setting._value if ikey == k), None)
        item = setting._value[k]
        if args.extra_subkey in item.keys():
            item[args.extra_subkey] = to_int(args.extra2)
            args.value_key = str(int(k))
        else:
            raise Exception(f"{setting.name}: key '{key}' not in setting")
        message = f"Setting {setting.name} key {k} parameter {args.extra_subkey} to {item[args.extra_subkey]!r}"
        result = setting.write_key_value(int(k), item, save=save)
        value = item

    else:
        raise Exception("NotImplemented")

    return result, message, value
