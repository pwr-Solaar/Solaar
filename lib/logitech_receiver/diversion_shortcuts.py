## Copyright (C) 2026  Solaar Contributors
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

import os

from logitech_receiver import diversion
from logitech_receiver.common import NamedInt
from logitech_receiver.special_keys import CONTROL


def normalize_key_name(name):
    cleaned = name.replace("-", " ").replace("_", " ").strip().lower()
    for key in CONTROL:
        if str(key).lower() == cleaned:
            return key
    raise Exception(f"unknown Logitech key/button '{name}'")


def parse_shortcut(shortcut):
    parts = [p.strip() for p in shortcut.replace("+", " ").split() if p.strip()]
    if not parts:
        raise Exception("shortcut must contain at least one X11 keysym")
    return parts[0] if len(parts) == 1 else parts


def key_value(key):
    return int(key) if isinstance(key, NamedInt) else int(CONTROL[key])


def is_shortcut_rule(rule, key):
    if not isinstance(rule, diversion.Rule) or len(rule.components) != 2:
        return False
    condition, action = rule.components
    return (
        isinstance(condition, diversion.Key)
        and condition.key == key
        and condition.action == diversion.Key.DOWN
        and isinstance(action, diversion.KeyPress)
    )


def ensure_user_rule_container():
    diversion.load_config_rule_file()
    if not isinstance(diversion.rules, diversion.Rule):
        diversion.rules = diversion.Rule([])
    for component in diversion.rules.components:
        if isinstance(component, diversion.Rule) and component.source == diversion._file_path:
            return component
    user_rules = diversion.Rule([], source=diversion._file_path)
    diversion.rules.components.insert(0, user_rules)
    return user_rules


def set_shortcut_rule(key, shortcut):
    user_rules = ensure_user_rule_container()
    rule = diversion.Rule(
        [
            {"Key": [str(key), diversion.Key.DOWN]},
            {"KeyPress": [parse_shortcut(shortcut), "click"]},
        ],
        source=diversion._file_path,
    )
    for index, component in enumerate(user_rules.components):
        if is_shortcut_rule(component, key):
            user_rules.components[index] = rule
            break
    else:
        user_rules.components.append(rule)
    os.makedirs(os.path.dirname(diversion._file_path), exist_ok=True)
    if not diversion._save_config_rule_file(diversion._file_path):
        raise Exception(f"failed to save shortcut rule to {diversion._file_path}")
    return rule
