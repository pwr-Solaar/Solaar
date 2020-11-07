# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2020 Peter Patel-Schneider
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

# Map diverted feature notifications to keyboard and mouse input

import os as _os
import os.path as _path

from logging import INFO as _INFO
from logging import getLogger

import _thread
import psutil
import Xlib

from pynput import keyboard as _keyboard
from pynput import mouse as _mouse
from Xlib import X
from Xlib.display import Display
from Xlib.ext import record
from Xlib.protocol import rq
from yaml import safe_load_all as _yaml_safe_load_all

from .common import unpack as _unpack
from .hidpp20 import FEATURE as _F
from .special_keys import CONTROL as _CONTROL

_log = getLogger(__name__)
del getLogger

Xlib.XK.load_keysym_group('xf86')

# determine name of active process

disp_prog = Display()
NET_ACTIVE_WINDOW = disp_prog.intern_atom('_NET_ACTIVE_WINDOW')
NET_WM_PID = disp_prog.intern_atom('_NET_WM_PID')
root2 = disp_prog.screen().root
root2.change_attributes(event_mask=Xlib.X.PropertyChangeMask)
active_process_name = None


def active_program():
    try:
        window_id = root2.get_full_property(NET_ACTIVE_WINDOW, Xlib.X.AnyPropertyType).value[0]
        window = disp_prog.create_resource_object('window', window_id)
        window_pid = window.get_full_property(NET_WM_PID, 0).value[0]
        return psutil.Process(window_pid).name()
    except Xlib.error.XError:  # simplify dealing with BadWindow
        return None


def determine_active_program():
    global active_process_name
    active_process_name = active_program()
    while True:
        event = disp_prog.next_event()
        if event.type == Xlib.X.PropertyNotify and event.atom == NET_ACTIVE_WINDOW:
            active_process_name = active_program()


_thread.start_new_thread(determine_active_program, ())

# determine current key modifiers
# there must be a better way to do this

display = Display()
context = display.record_create_context(
    0, [record.AllClients], [{
        'core_requests': (0, 0),
        'core_replies': (0, 0),
        'ext_requests': (0, 0, 0, 0),
        'ext_replies': (0, 0, 0, 0),
        'delivered_events': (0, 0),
        'device_events': (X.KeyPress, X.KeyRelease),
        'errors': (0, 0),
        'client_started': False,
        'client_died': False,
    }]
)

modifier_keycodes = display.get_modifier_mapping()
current_key_modifiers = 0


def modifier_code(keycode):
    if keycode == 0:
        return None
    for m in range(0, len(modifier_keycodes)):
        if keycode in modifier_keycodes[m]:
            return m


def key_press_handler(reply):
    global current_key_modifiers
    data = reply.data
    while len(data):
        event, data = rq.EventField(None).parse_binary_value(data, display.display, None, None)
        if event.type == X.KeyPress:
            mod = modifier_code(event.detail)
            current_key_modifiers = event.state | 1 << mod if mod is not None else event.state
            # if mod is not None:
            # print("press", event.detail, current_key_modifiers)
        elif event.type == X.KeyRelease:
            mod = modifier_code(event.detail)
            current_key_modifiers = event.state & ~(1 << mod) if mod is not None else event.state
            # if mod is not None:
            # print("release", event.detail, current_key_modifiers)


_thread.start_new_thread(display.record_enable_context, (context, key_press_handler))
# display.record_free_context(context)  when should this be done??

# Solaar processes feature notifications from devices by evaluating a rule (usually consisting of a
# sequence of sub-rules) on them.
#
# A rule is a sequence of conditions, actions, and sub-rules.
#
# Rules are evaluated by evaluating each of their components in order.
# A rule evaluation is terminated early if a condition component evaluates to false or
# the last evaluated sub-component of a component is an action.
# A Rule is false if its last evaluated component evaluates to a false value.
#
# Not conditions are true if their component evaluates to a false value.
# Or conditions are evaluated by evaluating each of their components in order.
# An Or condition is terminated early if a component evaluates to true or
# the last evaluated sub-component of a component is an action.
# A Or condition is true if its last evaluated component evaluates to a true value.
# And conditions are evaluted the same as rules.
#
# Process conditions are true if the name of the active process starts with their argument.
# Feature conditions are if true if the name of the feature of the current notification is their argument.
# Report conditions are if true if the report number in the current notification is their argument.
# Modifiers conditions are true if the current keyboard modifiers are their arguments.
# The permissable modifiers are 'Shift', 'Control', 'Alt', and 'Super'.
# Key conditions are true if the Logitech name of the last key down is their argument.
# Test conditions are true if their test evaluates to true on the feature, report, and data of the current notification.
# Test conditions can return a number instead of a boolean.
#
# Test conditions consisting of a list of three or four integers use the first two to select bytes of the data.
# Three-element test conditions are true if the selected bytes bit-wise anded with its third element is non-zero.
# The value of these test conditions is the result of the and.
# Four-element test conditions are true if the selected bytes form a signed integer between the third and fourth elements.
# The value of test test condition is the signed value of the selected bytes if that is non-zero otherwise True.
#
# The other test conditions are mnemonic shorthands for meaningful feature, report, and data combinations.
# A crown_right test is the rotation amount of a CROWN right rotation.
# A crown_left test is the rotation amount of a CROWN left rotation.
# A crown_right_ratchet test is the ratchet amount of a CROWN right ratchet rotation.
# A crown_left_ratchet test is the ratchet amount of a CROWN left ratchet rotation.
# A crown_tap test is true for a CROWN tap.
# A crown_start_press test is true for the start of a CROWN press.
# A crown_stop_press test is true for the end of a CROWN press.
# A crown_pressed test is true for a CROWN notification with the Crown pressed.
# A thumb_wheel_up test is the rotation amount of a THUMB_WHEEL upward rotation.
# A thumb_wheel_down test is the rotation amount of a THUMB_WHEEL downward rotation.
# lowres_wheel_up, lowres_wheel_down, hires_wheel_up, hires_wheel_down are the same but for LOWRES_WHEEL and HIRES_WHEEL.
# True and False tests return True and False, respectively.
#
# A KeyPress action takes X11 key symbols and simulates a chorded keypress on the keyboard.
# Any key symbols that correspond to modifier keys that are in the current keyboard modifiers are ignored.
# A MouseScroll action takes two numbers and simulates a horizontal and vertical mouse scroll of these amounts.
# If the previous condition in the parent rule returns a number the scroll amounts are multiplied by this number.
# An Execute actions takes a program and arguments and executes it asynchronously.
#
# Solaar reads rules from a configuration file (normally ~/.config/solaar/divert.yaml).
# This file contains zero or more documents, each a rule.
# Rule components are one-element dictionaries with key the component name (with initial Captial letter).
# If a component has multiple arguments they are written as a sequence.
# Solaar constructs the rule that it uses to process feature notifications from these rules (if any)
# followed by some built-in rules.

keyboard = _keyboard.Controller()
mouse = _mouse.Controller()

keys_down = []
key_down = None


def signed(bytes):
    return int.from_bytes(bytes, 'big', signed=True)


TESTS = {
    'crown_right': lambda f, r, d: f == _F.CROWN and r == 0 and d[1] < 128 and d[1],
    'crown_left': lambda f, r, d: f == _F.CROWN and r == 0 and d[1] >= 128 and 256 - d[1],
    'crown_right_ratchet': lambda f, r, d: f == _F.CROWN and r == 0 and d[2] < 128 and d[2],
    'crown_left_ratchet': lambda f, r, d: f == _F.CROWN and r == 0 and d[2] >= 128 and 256 - d[2],
    'crown_tap': lambda f, r, d: f == _F.CROWN and r == 0 and d[5] == 0x01 and d[5],
    'crown_start_press': lambda f, r, d: f == _F.CROWN and r == 0 and d[6] == 0x01 and d[6],
    'crown_end_press': lambda f, r, d: f == _F.CROWN and r == 0 and d[6] == 0x05 and d[6],
    'crown_pressed': lambda f, r, d: f == _F.CROWN and r == 0 and d[6] >= 0x01 and d[6] <= 0x04 and d[6],
    'thumb_wheel_up': lambda f, r, d: f == _F.THUMB_WHEEL and r == 0 and signed(d[0:2]) < 0 and signed(d[0:2]),
    'thumb_wheel_down': lambda f, r, d: f == _F.THUMB_WHEEL and r == 0 and signed(d[0:2]) > 0 and signed(d[0:2]),
    'lowres_wheel_up': lambda f, r, d: f == _F.LOWRES_WHEEL and r == 0 and signed(d[0:1]) > 0 and signed(d[0:1]),
    'lowres_wheel_down': lambda f, r, d: f == _F.LOWRES_WHEEL and r == 0 and signed(d[0:1]) < 0 and signed(d[0:1]),
    'hires_wheel_up': lambda f, r, d: f == _F.HIRES_WHEEL and r == 0 and signed(d[1:3]) > 0 and signed(d[1:3]),
    'hires_wheel_down': lambda f, r, d: f == _F.HIRES_WHEEL and r == 0 and signed(d[1:3]) < 0 and signed(d[1:3]),
    'False': lambda f, r, d: False,
    'True': lambda f, r, d: True,
}

COMPONENTS = {}


class RuleComponent(object):
    def compile(self, c):
        if isinstance(c, RuleComponent):
            return c
        elif isinstance(c, dict) and len(c) == 1:
            k, v = next(iter(c.items()))
            if k in COMPONENTS:
                return COMPONENTS[k](v)
        _log.warn('illegal component in rule: %s', c)
        return Condition()


class Rule(RuleComponent):
    def __init__(self, args):
        self.components = [self.compile(a) for a in args]

    def __str__(self):
        return 'Rule[' + ', '.join([c.__str__() for c in self.components]) + ']'

    def evaluate(self, feature, notification, device, status, last_result):
        result = True
        for component in self.components:
            result = component.evaluate(feature, notification, device, status, result)
            if not isinstance(component, Action) and result is None:
                return None
            if isinstance(component, Condition) and not result:
                return result
        return result


class Condition(RuleComponent):
    def __init__(self, *args):
        pass

    def __str__(self):
        return 'CONDITION'

    def evaluate(self, feature, notification, device, status, last_result):
        return False


class Not(Condition):
    def __init__(self, op):
        self.op = op
        self.component = self.compile(op)

    def __str__(self):
        return 'NOT: ' + str(self.component)

    def evaluate(self, feature, notification, device, status, last_result):
        result = self.component.evaluate(feature, notification, device, status, last_result)
        return None if result is None else not result


class Or(Condition):
    def __init__(self, args):
        self.components = [self.compile(a) for a in args]

    def __str__(self):
        return 'Or: [' + ', '.join(str(c) for c in self.components) + ']'

    def evaluate(self, feature, notification, device, status, last_result):
        result = False
        for component in self.components:
            result = component.evaluate(feature, notification, device, status, last_result)
            if not isinstance(component, Action) and result is None:
                return None
            if isinstance(component, Condition) and result:
                return result
        return result


class And(Condition):
    def __init__(self, args):
        self.components = [self.compile(a) for a in args]

    def __str__(self):
        return 'AND: [' + ', '.join(str(c) for c in self.components) + ']'

    def evaluate(self, feature, notification, device, status, last_result):
        result = True
        for component in self.components:
            result = component.evaluate(feature, notification, device, status, last_result)
            if not isinstance(component, Action) and result is None:
                return None
            if isinstance(component, Condition) and not result:
                return result
        return result


class Process(Condition):
    def __init__(self, process):
        self.process = process
        if not isinstance(process, str):
            _log.warn('rule Process argument not a string: %s', process)

    def __str__(self):
        return 'PROCESS: ' + str(self.process)

    def evaluate(self, feature, notification, device, status, last_result):
        return active_process_name.startswith(self.process) if isinstance(self.process, str) else False


class Feature(Condition):
    def __init__(self, feature):
        if not (isinstance(feature, str) and feature in _F):
            _log.warn('rule Feature argument not name of a feature: %s', feature)
            self.feature = None
        self.feature = _F[feature]

    def __str__(self):
        return 'FEATURE: ' + str(self.feature)

    def evaluate(self, feature, notification, device, status, last_result):
        return feature == self.feature


class Report(Condition):
    def __init__(self, report):
        if not (isinstance(report, int)):
            _log.warn('rule Report argument not an integer: %s', report)
            self.report = -1
        self.report = report

    def __str__(self):
        return 'REPORT: ' + str(self.report)

    def evaluate(self, report, notification, device, status, last_result):
        return (notification.address >> 4) == self.report


MODIFIERS = {'Shift': 0x01, 'Control': 0x04, 'Alt': 0x08, 'Super': 0x40}
MODIFIER_MASK = MODIFIERS['Shift'] + MODIFIERS['Control'] + MODIFIERS['Alt'] + MODIFIERS['Super']


class Modifiers(Condition):
    def __init__(self, modifiers):
        modifiers = [modifiers] if isinstance(modifiers, str) else modifiers
        self.desired = 0
        for k in modifiers:
            if k in MODIFIERS:
                self.desired += MODIFIERS.get(k, 0)
            else:
                _log.warn('unknown rule Modifier value: %s', k)

    def __str__(self):
        return 'MODIFIERS: ' + str(self.desired)

    def evaluate(self, feature, notification, device, status, last_result):
        return self.desired == (current_key_modifiers & MODIFIER_MASK)


class Key(Condition):
    def __init__(self, key):
        if isinstance(key, str) and key in _CONTROL:
            self.key = _CONTROL[key]
        else:
            _log.warn('rule Key argument not name of a Logitech key: %s', key)
            self.key = 0

    def __str__(self):
        return 'KEY: ' + (str(self.key) if self.key else 'None')

    def evaluate(self, feature, notification, device, status, last_result):
        return self.key and self.key == key_down


def bit_test(start, end, bits):
    return lambda f, r, d: int.from_bytes(d[start:end], byteorder='big', signed=True) & bits


def range_test(start, end, min, max):
    def range_test_helper(f, r, d):
        value = int.from_bytes(d[start:end], byteorder='big', signed=True)
        return min <= value <= max and (value if value else True)

    return range_test_helper


class Test(Condition):
    def __init__(self, test):
        self.test = test
        if isinstance(test, str):
            if test in TESTS:
                self.function = TESTS[test]
            else:
                _log.warn('rule Test string argument not name of a test: %s', test)
                self.function = TESTS['False']
        elif (
            isinstance(test, list) and 2 < len(test) <= 4 and all(isinstance(t, int) for t in test) and test[0] >= 0
            and test[0] <= 16 and test[1] >= 0 and test[1] <= 16 and test[0] < test[1]
        ):
            self.function = bit_test(*test) if len(test) == 3 else range_test(*test)
        else:
            _log.warn('rule Test argument not valid %s', test)

    def __str__(self):
        return 'TEST: ' + str(self.test)

    def evaluate(self, feature, notification, device, status, last_result):
        return self.function(feature, notification.address, notification.data)


class Action(RuleComponent):
    def __init__(self, *args):
        pass

    def evaluate(self, feature, notification, device, status, last_result):
        return None


class KeyPress(Action):
    def __init__(self, keys):
        if isinstance(keys, str):
            keys = [keys]
        self.key_symbols = keys
        key_from_string = lambda s: s if isinstance(s, str) and len(s) == 1 else _keyboard.KeyCode._from_symbol(s)
        self.keys = [isinstance(k, str) and key_from_string(k) for k in keys]
        if not all(self.keys):
            _log.warn('rule KeyPress argument not sequence of key names %s', keys)
            self.keys = []

    def __str__(self):
        return 'KeyPress: ' + ' '.join(self.key_symbols)

    def needed(self, k, current_key_modifiers):
        code = modifier_code(display.keysym_to_keycode(k.vk if isinstance(k, _keyboard.KeyCode) else k))
        return not (code and current_key_modifiers & (1 << code))

    def keyDown(self, keys, modifiers):
        for k in keys:
            if self.needed(k, modifiers):
                keyboard.press(k)

    def keyUp(self, keys, modifiers):
        for k in keys:
            if self.needed(k, modifiers):
                keyboard.release(k)

    def evaluate(self, feature, notification, device, status, last_result):
        current = current_key_modifiers
        # print("KeyPress", self.key_symbols, current)
        if _log.isEnabledFor(_INFO):
            _log.info(
                'KeyPress action: %s, modifiers %s %s', self.key_symbols, current,
                [(hex(k.vk) if isinstance(k, _keyboard.KeyCode) else k) for k in self.keys]
            )
        self.keyDown(self.keys, current)
        import time
        time.sleep(0.1)
        self.keyUp(reversed(self.keys), current)
        return None


# KeyDown is dangerous as the key can auto-repeat and make your system unusable
# class KeyDown(KeyPress):
#    def evaluate(self, feature, notification, device, status, last_result):
#        print('KEYDOWN', [(hex(k.vk) if isinstance(k, _keyboard.KeyCode) else k) for k in self.keys], current_key_modifiers)
#        super().keyDown(self.keys, current_key_modifiers)
# class KeyUp(KeyPress):
#    def evaluate(self, feature, notification, device, status, last_result):
#        print('KEYUP', [(hex(k.vk) if isinstance(k, _keyboard.KeyCode) else k) for k in self.keys], current_key_modifiers)
#        super().keyUp(self.keys, current_key_modifiers)


class MouseScroll(Action):
    def __init__(self, amounts):
        import numbers
        if len(amounts) == 1 and isinstance(amounts[0], list):
            amounts = amounts[0]
        if not (len(amounts) == 2 and all([isinstance(a, numbers.Number) for a in amounts])):
            _log.warn('rule MouseScroll argument not two numbers %s', amounts)
        self.amounts = amounts

    def __str__(self):
        return 'MouseScroll: ' + ' '.join([str(a) for a in self.amounts])

    def evaluate(self, feature, notification, device, status, last_result):
        import math
        import numbers
        amounts = self.amounts
        if isinstance(last_result, numbers.Number):
            amounts = [math.floor(last_result * a) for a in self.amounts]
        # print("MOUSESCROLL", self.amounts, last_result, amounts)
        if _log.isEnabledFor(_INFO):
            _log.info('MouseScroll action: %s %s %s', self.amounts, last_result, amounts)
        mouse.scroll(*amounts)
        return None


class Execute(Action):
    def __init__(self, args):
        if isinstance(args, str):
            args = [args]
        if not (isinstance(args, list) and all(isinstance(arg), str) for arg in args):
            _log.warn('rule Execute argument not list of strings: %s', args)
            self.args = None
        else:
            self.args = args

    def __str__(self):
        return 'Execute: ' + ' '.join([a for a in self.args])

    def evaluate(self, feature, notification, device, status, last_result):
        import subprocess
        if _log.isEnabledFor(_INFO):
            _log.info('Execute action: %s', self.args)
        subprocess.Popen(self.args)
        return None


COMPONENTS = {
    'Rule': Rule,
    'Not': Not,
    'Or': Or,
    'And': And,
    'Process': Process,
    'Feature': Feature,
    'Report': Report,
    'Modifiers': Modifiers,
    'Key': Key,
    'Test': Test,
    'KeyPress': KeyPress,
    'MouseScroll': MouseScroll,
    'Execute': Execute,
}


rules = Rule([
    ## Some malformed Rules for testing
    ##    Rule([Process(0), Feature(0), Modifiers(['XX', 0]), Modifiers('XXX'), Modifiers([0]),
    ##         KeyPress(['XXXXX', 0]), KeyPress(['XXXXXX']), KeyPress(0),
    ##         MouseScroll(0), MouseScroll([0, 0, 0]), MouseScroll(['a', 0]),
    ##         Rule(["XXXXXXX"])]),
    ##    Rule([Feature(0)]),
    ##    Rule([Modifiers(['XXXXXXXXX', 0])]),
    ##    Rule([KeyPress(['XXXXXSSSSS', 0])]),
    {'Rule': [  # Implement problematic keys for Craft and MX Master
        {'Feature': 'REPROG_CONTROLS_V4'},
        {'Report': 0x0},
        {'Rule': [{'Key': 'Brightness Down'}, {'KeyPress': 'XF86_MonBrightnessDown'}]},
        {'Rule': [{'Key': 'Brightness Up'}, {'KeyPress': 'XF86_MonBrightnessUp'}]},
    ]},
    {'Rule': [  # In firefox, crown movements emits keys that move up and down if not pressed, rotate through tabs otherwise
        {'Process': 'firefox'},
        {'Feature': 'CROWN'},
        {'Report': 0x0},
        {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_right_ratchet'}, {'KeyPress': ['Control_R', 'Tab']}]},
        {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_left_ratchet'}, {'KeyPress': ['Control_R', 'Shift_R', 'Tab']}]},
        {'Rule': [{'Test': 'crown_right_ratchet'}, {'KeyPress': 'Down'}]},
        Rule([Test('crown_left_ratchet'), KeyPress(['Up'])]),
    ]},
    {'Rule': [  # Otherwise, crown movements emit keys that modify volume if not pressed, move between tracks otherwise
        {'Feature': 'CROWN'}, {'Report': 0x0},
        {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_right_ratchet'}, {'KeyPress': 'XF86_AudioNext'}]},
        {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_left_ratchet'}, {'KeyPress': 'XF86_AudioPrev'}]},
        {'Rule': [{'Test': 'crown_right_ratchet'}, {'KeyPress': 'XF86_AudioRaiseVolume'}]},
        {'Rule': [{'Test': 'crown_left_ratchet'}, {'KeyPress': 'XF86_AudioLowerVolume'}]}
    ]},
    {'Rule': [  # Thumb wheel does horizontal movement, doubled if control key not pressed
        {'Feature': 'THUMB_WHEEL'},  # with control modifier on mouse scrolling sometimes does something different!
        {'Rule': [{'Modifiers': 'Control'}, {'Test': 'thumb_wheel_up'}, {'MouseScroll': [-1, 0]}]},
        {'Rule': [{'Modifiers': 'Control'}, {'Test': 'thumb_wheel_down'}, {'MouseScroll': [-1, 0]}]},
        {'Rule': [{'Or': [{'Test': 'thumb_wheel_up'}, {'Test': 'thumb_wheel_down'}]}, {'MouseScroll': [-2, 0]}]}
    ]}
])


# process a notification
def process_notification(device, status, notification, feature):
    global keys_down, key_down
    key_down = None
    # need to keep track of keys that are down to find a new key down
    if feature == _F.REPROG_CONTROLS_V4 and notification.address == 0x00:
        new_keys_down = _unpack('!4H', notification.data[:8])
        for key in new_keys_down:
            if key and key not in keys_down:
                key_down = key
        keys_down = new_keys_down
    rules.evaluate(feature, notification, device, status, True)


_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.expanduser(_path.join('~', '.config'))
_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'divert.yaml')


def _load_config_rule_file():
    global rules
    if _path.isfile(_file_path):
        try:
            with open(_file_path, 'r') as config_file:
                loaded_rules = []
                for loaded_rule in _yaml_safe_load_all(config_file):
                    rule = Rule(loaded_rule)
                    if _log.isEnabledFor(_INFO):
                        _log.info('load rule: %s', rule)
                    loaded_rules.append(rule)
                if _log.isEnabledFor(_INFO):
                    _log.info('loaded %d rules from %s', len(loaded_rules), config_file)
                loaded_rules.extend(rules.components)
                rules = Rule(loaded_rules)
        except Exception as e:
            _log.error('failed to load from %s\n%s', _file_path, e)


_load_config_rule_file()
