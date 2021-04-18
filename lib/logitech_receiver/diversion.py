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

import os as _os
import os.path as _path
import sys as _sys

from logging import INFO as _INFO
from logging import getLogger

import _thread
import psutil

from yaml import add_representer as _yaml_add_representer
from yaml import dump_all as _yaml_dump_all
from yaml import safe_load_all as _yaml_safe_load_all

from .common import unpack as _unpack
from .hidpp20 import FEATURE as _F
from .special_keys import CONTROL as _CONTROL

_log = getLogger(__name__)
del getLogger

# many of the rule features require X11 so turn rule processing off if X11 is not available
try:
    import Xlib
    from Xlib import X
    from Xlib.display import Display
    from Xlib.ext import record
    from Xlib.protocol import rq
    from Xlib import XK as _XK
    _XK.load_keysym_group('xf86')
    XK_KEYS = vars(_XK)
    disp_prog = Display()
    x11 = True
except Exception:
    _log.warn('X11 not available - rules will not be activated', exc_info=_sys.exc_info())
    XK_KEYS = {}
    x11 = False

if x11:
    # determine name of active process
    NET_ACTIVE_WINDOW = disp_prog.intern_atom('_NET_ACTIVE_WINDOW')
    NET_WM_PID = disp_prog.intern_atom('_NET_WM_PID')
    WM_CLASS = disp_prog.intern_atom('WM_CLASS')
    root2 = disp_prog.screen().root
    root2.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

active_process_name = None
active_wm_class_name = None


def active_program_name():
    try:
        window_id = root2.get_full_property(NET_ACTIVE_WINDOW, Xlib.X.AnyPropertyType).value[0]
        window = disp_prog.create_resource_object('window', window_id)
        window_pid = window.get_full_property(NET_WM_PID, 0).value[0]
        return psutil.Process(window_pid).name()
    except (Xlib.error.XError, AttributeError):  # simplify dealing with BadWindow
        return None


def active_program_wm_class():
    try:
        window_id = root2.get_full_property(NET_ACTIVE_WINDOW, Xlib.X.AnyPropertyType).value[0]
        window = disp_prog.create_resource_object('window', window_id)
        window_wm_class = window.get_wm_class()[0]
        return window_wm_class
    except (Xlib.error.XError, AttributeError):  # simplify dealing with BadWindow
        return None


def determine_active_program_and_wm_class():
    global active_process_name
    global active_wm_class_name
    active_process_name = active_program_name()
    active_wm_class_name = active_program_wm_class()
    while True:
        event = disp_prog.next_event()
        if event.type == Xlib.X.PropertyNotify and event.atom == NET_ACTIVE_WINDOW:
            active_process_name = active_program_name()
            active_wm_class_name = active_program_wm_class()


if x11:
    _thread.start_new_thread(determine_active_program_and_wm_class, ())

# determine current key modifiers
# there must be a better way to do this

if x11:
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
        elif event.type == X.KeyRelease:
            mod = modifier_code(event.detail)
            current_key_modifiers = event.state & ~(1 << mod) if mod is not None else event.state


if x11:
    _thread.start_new_thread(display.record_enable_context, (context, key_press_handler))
# display.record_free_context(context)  when should this be done??

# See docs/rules.md for documentation

key_down = None


def signed(bytes):
    return int.from_bytes(bytes, 'big', signed=True)


def xy_direction(d):
    x, y = _unpack('!2h', d[:4])
    if x > 0 and x >= abs(y):
        return 'right'
    elif x < 0 and abs(x) >= abs(y):
        return 'left'
    elif y > 0:
        return 'down'
    elif y < 0:
        return 'up'
    else:
        return None


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
    'mouse-down': lambda f, r, d: f == _F.MOUSE_GESTURE and xy_direction(d) == 'down',
    'mouse-up': lambda f, r, d: f == _F.MOUSE_GESTURE and xy_direction(d) == 'up',
    'mouse-left': lambda f, r, d: f == _F.MOUSE_GESTURE and xy_direction(d) == 'left',
    'mouse-right': lambda f, r, d: f == _F.MOUSE_GESTURE and xy_direction(d) == 'right',
    'mouse-noop': lambda f, r, d: f == _F.MOUSE_GESTURE and xy_direction(d) is None,
    'False': lambda f, r, d: False,
    'True': lambda f, r, d: True,
}

COMPONENTS = {}

if x11:
    displayt = Display()


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
    def __init__(self, args, source=None):
        self.components = [self.compile(a) for a in args]
        self.source = source

    def __str__(self):
        source = '(' + self.source + ')' if self.source else ''
        return 'Rule%s[%s]' % (source, ', '.join([c.__str__() for c in self.components]))

    def evaluate(self, feature, notification, device, status, last_result):
        result = True
        for component in self.components:
            result = component.evaluate(feature, notification, device, status, result)
            if not isinstance(component, Action) and result is None:
                return None
            if isinstance(component, Condition) and not result:
                return result
        return result

    def data(self):
        return {'Rule': [c.data() for c in self.components]}


class Condition(RuleComponent):
    def __init__(self, *args):
        pass

    def __str__(self):
        return 'CONDITION'

    def evaluate(self, feature, notification, device, status, last_result):
        return False


class Not(Condition):
    def __init__(self, op):
        if isinstance(op, list) and len(op) == 1:
            op = op[0]
        self.op = op
        self.component = self.compile(op)

    def __str__(self):
        return 'Not: ' + str(self.component)

    def evaluate(self, feature, notification, device, status, last_result):
        result = self.component.evaluate(feature, notification, device, status, last_result)
        return None if result is None else not result

    def data(self):
        return {'Not': self.component.data()}


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

    def data(self):
        return {'Or': [c.data() for c in self.components]}


class And(Condition):
    def __init__(self, args):
        self.components = [self.compile(a) for a in args]

    def __str__(self):
        return 'And: [' + ', '.join(str(c) for c in self.components) + ']'

    def evaluate(self, feature, notification, device, status, last_result):
        result = True
        for component in self.components:
            result = component.evaluate(feature, notification, device, status, last_result)
            if not isinstance(component, Action) and result is None:
                return None
            if isinstance(component, Condition) and not result:
                return result
        return result

    def data(self):
        return {'And': [c.data() for c in self.components]}


class Process(Condition):
    def __init__(self, process):
        self.process = process
        if not isinstance(process, str):
            _log.warn('rule Process argument not a string: %s', process)
            self.process = str(process)

    def __str__(self):
        return 'Process: ' + str(self.process)

    def evaluate(self, feature, notification, device, status, last_result):
        if not isinstance(self.process, str):
            return False
        return active_process_name.startswith(self.process) or active_wm_class_name.startswith(self.process)

    def data(self):
        return {'Process': str(self.process)}


class Feature(Condition):
    def __init__(self, feature):
        if not (isinstance(feature, str) and feature in _F):
            _log.warn('rule Feature argument not name of a feature: %s', feature)
            self.feature = None
        self.feature = _F[feature]

    def __str__(self):
        return 'Feature: ' + str(self.feature)

    def evaluate(self, feature, notification, device, status, last_result):
        return feature == self.feature

    def data(self):
        return {'Feature': str(self.feature)}


class Report(Condition):
    def __init__(self, report):
        if not (isinstance(report, int)):
            _log.warn('rule Report argument not an integer: %s', report)
            self.report = -1
        self.report = report

    def __str__(self):
        return 'Report: ' + str(self.report)

    def evaluate(self, report, notification, device, status, last_result):
        return (notification.address >> 4) == self.report

    def data(self):
        return {'Report': self.report}


MODIFIERS = {'Shift': 0x01, 'Control': 0x04, 'Alt': 0x08, 'Super': 0x40}
MODIFIER_MASK = MODIFIERS['Shift'] + MODIFIERS['Control'] + MODIFIERS['Alt'] + MODIFIERS['Super']


class Modifiers(Condition):
    def __init__(self, modifiers):
        modifiers = [modifiers] if isinstance(modifiers, str) else modifiers
        self.desired = 0
        self.modifiers = []
        for k in modifiers:
            if k in MODIFIERS:
                self.desired += MODIFIERS.get(k, 0)
                self.modifiers.append(k)
            else:
                _log.warn('unknown rule Modifier value: %s', k)

    def __str__(self):
        return 'Modifiers: ' + str(self.desired)

    def evaluate(self, feature, notification, device, status, last_result):
        return self.desired == (current_key_modifiers & MODIFIER_MASK)

    def data(self):
        return {'Modifiers': [str(m) for m in self.modifiers]}


class Key(Condition):
    def __init__(self, key):
        if isinstance(key, str) and key in _CONTROL:
            self.key = _CONTROL[key]
        else:
            _log.warn('rule Key argument not name of a Logitech key: %s', key)
            self.key = 0

    def __str__(self):
        return 'Key: ' + (str(self.key) if self.key else 'None')

    def evaluate(self, feature, notification, device, status, last_result):
        return self.key and self.key == key_down

    def data(self):
        return {'Key': str(self.key)}


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
        return 'Test: ' + str(self.test)

    def evaluate(self, feature, notification, device, status, last_result):
        return self.function(feature, notification.address, notification.data)

    def data(self):
        return {'Test': str(self.test)}


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
        key_from_string = lambda s: displayt.keysym_to_keycode(Xlib.XK.string_to_keysym(s))
        self.keys = [isinstance(k, str) and key_from_string(k) for k in keys]
        if not all(self.keys):
            _log.warn('rule KeyPress argument not sequence of key names %s', keys)
            self.keys = []

    def __str__(self):
        return 'KeyPress: ' + ' '.join(self.key_symbols)

    def needed(self, k, current_key_modifiers):
        code = modifier_code(k)
        return not (code and current_key_modifiers & (1 << code))

    def keyDown(self, keys, modifiers):
        for k in keys:
            if self.needed(k, modifiers):
                Xlib.ext.xtest.fake_input(displayt, X.KeyPress, k)

    def keyUp(self, keys, modifiers):
        for k in keys:
            if self.needed(k, modifiers):
                Xlib.ext.xtest.fake_input(displayt, X.KeyRelease, k)

    def evaluate(self, feature, notification, device, status, last_result):
        current = current_key_modifiers
        if _log.isEnabledFor(_INFO):
            _log.info('KeyPress action: %s, modifiers %s %s', self.key_symbols, current, [hex(k) for k in self.keys])
        self.keyDown(self.keys, current)
        self.keyUp(reversed(self.keys), current)
        displayt.sync()
        return None

    def data(self):
        return {'KeyPress': [str(k) for k in self.key_symbols]}


# KeyDown is dangerous as the key can auto-repeat and make your system unusable
# class KeyDown(KeyPress):
#    def evaluate(self, feature, notification, device, status, last_result):
#        super().keyDown(self.keys, current_key_modifiers)
# class KeyUp(KeyPress):
#    def evaluate(self, feature, notification, device, status, last_result):
#        super().keyUp(self.keys, current_key_modifiers)

buttons = {
    'unknown': None,
    'left': 1,
    'middle': 2,
    'right': 3,
    'scroll_up': 4,
    'scroll_down': 5,
    'scroll_left': 6,
    'scroll_right': 7
}
for i in range(8, 31):
    buttons['button%d' % i] = i


def click(button, count):
    for _ in range(count):
        Xlib.ext.xtest.fake_input(displayt, Xlib.X.ButtonPress, button)
        Xlib.ext.xtest.fake_input(displayt, Xlib.X.ButtonRelease, button)


class MouseScroll(Action):
    def __init__(self, amounts):
        import numbers
        if len(amounts) == 1 and isinstance(amounts[0], list):
            amounts = amounts[0]
        if not (len(amounts) == 2 and all([isinstance(a, numbers.Number) for a in amounts])):
            _log.warn('rule MouseScroll argument not two numbers %s', amounts)
            amounts = [0, 0]
        self.amounts = amounts

    def __str__(self):
        return 'MouseScroll: ' + ' '.join([str(a) for a in self.amounts])

    def evaluate(self, feature, notification, device, status, last_result):
        import math
        import numbers
        amounts = self.amounts
        if isinstance(last_result, numbers.Number):
            amounts = [math.floor(last_result * a) for a in self.amounts]
        if _log.isEnabledFor(_INFO):
            _log.info('MouseScroll action: %s %s %s', self.amounts, last_result, amounts)
        dx, dy = amounts
        if dx:
            click(button=buttons['scroll_right'] if dx > 0 else buttons['scroll_left'], count=abs(dx))
        if dy:
            click(button=buttons['scroll_up'] if dy > 0 else buttons['scroll_down'], count=abs(dy))
        displayt.sync()
        return None

    def data(self):
        return {'MouseScroll': self.amounts[:]}


class MouseClick(Action):
    def __init__(self, args):
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]
        if not isinstance(args, list):
            args = [args]
        self.button = str(args[0]) if len(args) >= 0 else None
        if self.button not in buttons:
            _log.warn('rule MouseClick action: button %s not known', self.button)
            self.button = None
        count = args[1] if len(args) >= 2 else 1
        try:
            self.count = int(count)
        except (ValueError, TypeError):
            _log.warn('rule MouseClick action: count %s should be an integer', count)
            self.count = 1

    def __str__(self):
        return 'MouseClick: %s (%d)' % (self.button, self.count)

    def evaluate(self, feature, notification, device, status, last_result):
        if _log.isEnabledFor(_INFO):
            _log.info('MouseClick action: %d %s' % (self.count, self.button))
        if self.button and self.count:
            click(buttons[self.button], self.count)
        displayt.sync()
        return None

    def data(self):
        return {'MouseClick': [self.button, self.count]}


class Execute(Action):
    def __init__(self, args):
        if isinstance(args, str):
            args = [args]
        if not (isinstance(args, list) and all(isinstance(arg), str) for arg in args):
            _log.warn('rule Execute argument not list of strings: %s', args)
            self.args = []
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

    def data(self):
        return {'Execute': self.args[:]}


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
    'MouseClick': MouseClick,
    'Execute': Execute,
}

built_in_rules = Rule([])
if x11:
    built_in_rules = Rule([
        {'Rule': [  # Implement problematic keys for Craft and MX Master
            {'Rule': [{'Key': 'Brightness Down'}, {'KeyPress': 'XF86_MonBrightnessDown'}]},
            {'Rule': [{'Key': 'Brightness Up'}, {'KeyPress': 'XF86_MonBrightnessUp'}]},
        ]},
        {'Rule': [  # In firefox, crown emits keys that move up and down if not pressed, rotate through tabs otherwise
            {'Process': 'firefox'},
            {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_right_ratchet'}, {'KeyPress': ['Control_R', 'Tab']}]},
            {'Rule': [{'Test': 'crown_pressed'},
                      {'Test': 'crown_left_ratchet'},
                      {'KeyPress': ['Control_R', 'Shift_R', 'Tab']}]},
            {'Rule': [{'Test': 'crown_right_ratchet'}, {'KeyPress': 'Down'}]},
            {'Rule': [{'Test': 'crown_left_ratchet'}, {'KeyPress': 'Up'}]},
        ]},
        {'Rule': [  # Otherwise, crown movements emit keys that modify volume if not pressed, move between tracks otherwise
            {'Feature': 'CROWN'}, {'Report': 0x0},
            {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_right_ratchet'}, {'KeyPress': 'XF86_AudioNext'}]},
            {'Rule': [{'Test': 'crown_pressed'}, {'Test': 'crown_left_ratchet'}, {'KeyPress': 'XF86_AudioPrev'}]},
            {'Rule': [{'Test': 'crown_right_ratchet'}, {'KeyPress': 'XF86_AudioRaiseVolume'}]},
            {'Rule': [{'Test': 'crown_left_ratchet'}, {'KeyPress': 'XF86_AudioLowerVolume'}]}
        ]},
        {'Rule': [  # Thumb wheel does horizontal movement, doubled if control key not pressed
            {'Feature': 'THUMB WHEEL'},  # with control modifier on mouse scrolling sometimes does something different!
            {'Rule': [{'Modifiers': 'Control'}, {'Test': 'thumb_wheel_up'}, {'MouseScroll': [-1, 0]}]},
            {'Rule': [{'Modifiers': 'Control'}, {'Test': 'thumb_wheel_down'}, {'MouseScroll': [-1, 0]}]},
            {'Rule': [{'Or': [{'Test': 'thumb_wheel_up'}, {'Test': 'thumb_wheel_down'}]}, {'MouseScroll': [-2, 0]}]}
        ]}
    ])

keys_down = []
g_keys_down = 0x00


# process a notification
def process_notification(device, status, notification, feature):
    if not x11:
        return
    global keys_down, g_keys_down, key_down
    key_down = None
    # need to keep track of keys that are down to find a new key down
    if feature == _F.REPROG_CONTROLS_V4 and notification.address == 0x00:
        new_keys_down = _unpack('!4H', notification.data[:8])
        for key in new_keys_down:
            if key and key not in keys_down:
                key_down = key
        keys_down = new_keys_down
    # and also G keys down
    elif feature == _F.GKEY and notification.address == 0x00:
        new_g_keys_down, = _unpack('!B', notification.data[:1])
        for i in range(1, 9):
            if new_g_keys_down & (0x01 << (i - 1)) and not g_keys_down & (0x01 << (i - 1)):
                key_down = _CONTROL['G' + str(i)]
        g_keys_down = new_g_keys_down
    rules.evaluate(feature, notification, device, status, True)


_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.expanduser(_path.join('~', '.config'))
_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'rules.yaml')

rules = built_in_rules


def _save_config_rule_file(file_name=_file_path):
    # This is a trick to show str/float/int lists in-line (inspired by https://stackoverflow.com/a/14001707)
    class inline_list(list):
        pass

    def blockseq_rep(dumper, data):
        return dumper.represent_sequence(u'tag:yaml.org,2002:seq', data, flow_style=True)

    _yaml_add_representer(inline_list, blockseq_rep)

    def convert(elem):
        if isinstance(elem, list):
            if len(elem) == 1 and isinstance(elem[0], (int, str, float)):
                # All diversion classes that expect a list of scalars also support a single scalar without a list
                return elem[0]
            if all(isinstance(c, (int, str, float)) for c in elem):
                return inline_list([convert(c) for c in elem])
            return [convert(c) for c in elem]
        if isinstance(elem, dict):
            return {k: convert(v) for k, v in elem.items()}
        return elem

    # YAML format settings
    dump_settings = {
        'encoding': 'utf-8',
        'explicit_start': True,
        'explicit_end': True,
        'default_flow_style': False
        # 'version': (1, 3),  # it would be printed for every rule
    }
    # Save only user-defined rules
    rules_to_save = sum([r.data()['Rule'] for r in rules.components if r.source == file_name], [])
    if rules_to_save:
        if _log.isEnabledFor(_INFO):
            _log.info('saving %d rule(s) to %s', len(rules_to_save), file_name)
        try:
            with open(file_name, 'w') as f:
                f.write('%YAML 1.3\n')  # Write version manually
                _yaml_dump_all(convert([r['Rule'] for r in rules_to_save]), f, **dump_settings)
        except Exception as e:
            _log.error('failed to save to %s\n%s', file_name, e)
            return False
    return True


def _load_config_rule_file():
    global rules
    loaded_rules = []
    if _path.isfile(_file_path):
        try:
            with open(_file_path, 'r') as config_file:
                loaded_rules = []
                for loaded_rule in _yaml_safe_load_all(config_file):
                    rule = Rule(loaded_rule, source=_file_path)
                    if _log.isEnabledFor(_INFO):
                        _log.info('load rule: %s', rule)
                    loaded_rules.append(rule)
                if _log.isEnabledFor(_INFO):
                    _log.info('loaded %d rules from %s', len(loaded_rules), config_file.name)
        except Exception as e:
            _log.error('failed to load from %s\n%s', _file_path, e)
    rules = Rule([Rule(loaded_rules, source=_file_path), built_in_rules])


if x11:
    _load_config_rule_file()
