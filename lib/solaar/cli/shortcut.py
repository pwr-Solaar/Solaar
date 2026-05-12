## Copyright (C) 2026  Solaar Contributors
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

from argparse import Namespace

from logitech_receiver import diversion
from logitech_receiver import diversion_shortcuts
from logitech_receiver import settings_templates

from solaar.cli import config


def _divert_key(dev, key):
    setting = settings_templates.check_feature_setting(dev, "divert-keys")
    if setting is None:
        raise Exception(f"no key/button diversion setting for {dev.name}")
    result, _message, _value = config.set(
        dev,
        setting,
        # Choices are translated, so select the second choice by 1-based index instead of by label.
        Namespace(value_key=str(diversion_shortcuts.key_value(key)), extra_subkey="2", extra2=None),
        save=False,
    )
    if result is None:
        raise Exception(f"failed to divert {key} on {dev.name}")
    if dev.persister and setting.persist:
        dev.persister[setting.name] = setting._value


def run(receivers, args, _find_receiver, find_device):
    assert receivers
    assert args.device

    key = diversion_shortcuts.normalize_key_name(args.key)
    device_name = args.device.lower()

    dev = None
    for dev in find_device(receivers, device_name):
        if dev.ping():
            break
        dev = None
    if not dev:
        raise Exception(f"no online device found matching '{device_name}'")

    _divert_key(dev, key)
    rule = diversion_shortcuts.set_shortcut_rule(key, args.shortcut)
    print(f"Diverted {key} on {dev.name} and bound it to {args.shortcut!r} via {diversion._file_path}")
    print(rule)
