# -*- python-mode -*-

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

from logging import DEBUG as _DEBUG
from logging import INFO as _INFO
from logging import getLogger
from math import sqrt as _sqrt

import keysyms.keysymdef as _keysymdef
import psutil

from gi.repository import Gdk, GLib
from solaar.ui.config_panel import change_setting as _change_setting
from yaml import add_representer as _yaml_add_representer
from yaml import dump_all as _yaml_dump_all
from yaml import safe_load_all as _yaml_safe_load_all

from .common import NamedInt
from .common import unpack as _unpack
from .hidpp20 import FEATURE as _F
from .special_keys import CONTROL as _CONTROL

_log = getLogger(__name__)
del getLogger

#
# See docs/rules.md for documentation
#
# Several capabilities of rules depend on aspects of GDK, X11, or XKB
# As the Solaar GUI uses GTK, Glib and GDK are always available and are obtained from gi.repository
#
# Process condition depends on X11 from python-xlib, and is probably not possible at all in Wayland
# MouseProcess condition depends on X11 from python-xlib, and is probably not possible at all in Wayland
# Modifiers condition depends only on GDK
# KeyPress action currently only works in X11, and is not currently available under Wayland
# KeyPress action determines whether a keysym is a currently-down modifier using get_modifier_mapping from python-xlib;
#   under Wayland no modifier keys are considered down so all modifier keys are pressed, potentially leading to problems
# KeyPress action translates key names to keysysms using the local file described for GUI keyname determination
# KeyPress action gets the current keyboard group using XkbGetState from libX11.so using ctypes definitions
#   under Wayland the keyboard group is None resulting in using the first keyboard group
# KeyPress action translates keysyms to keycodes using the GDK keymap
# KeyPress action simulates keyboard input with X11 XTest from python-xlib
# MouseScroll and MouseClick actions currently only work in X11, and are not currently available under Wayland
# MouseScroll and MouseClick actions simulate mouse input with X11 XTest from python-xlib
#
# Rule GUI keyname determination uses a local file generated
#   from http://cgit.freedesktop.org/xorg/proto/x11proto/plain/keysymdef.h
#   and http://cgit.freedesktop.org/xorg/proto/x11proto/plain/XF86keysym.h
# because there does not seem to be a non-X11 file for this set of key names

XK_KEYS = _keysymdef.keysymdef

try:
    import Xlib
    from Xlib import X
    from Xlib.display import Display
    xdisplay = Display()
    modifier_keycodes = xdisplay.get_modifier_mapping()  # there should be a way to do this in Gdk
    x11 = True

    NET_ACTIVE_WINDOW = xdisplay.intern_atom('_NET_ACTIVE_WINDOW')
    NET_WM_PID = xdisplay.intern_atom('_NET_WM_PID')
    WM_CLASS = xdisplay.intern_atom('WM_CLASS')

    # set up to get keyboard state using ctypes interface to libx11
    import ctypes

    class X11Display(ctypes.Structure):
        """ opaque struct """

    class X11XkbStateRec(ctypes.Structure):
        _fields_ = [('group', ctypes.c_ubyte), ('locked_group', ctypes.c_ubyte), ('base_group', ctypes.c_ushort),
                    ('latched_group', ctypes.c_ushort), ('mods', ctypes.c_ubyte), ('base_mods', ctypes.c_ubyte),
                    ('latched_mods', ctypes.c_ubyte), ('locked_mods', ctypes.c_ubyte), ('compat_state', ctypes.c_ubyte),
                    ('grab_mods', ctypes.c_ubyte), ('compat_grab_mods', ctypes.c_ubyte), ('lookup_mods', ctypes.c_ubyte),
                    ('compat_lookup_mods', ctypes.c_ubyte),
                    ('ptr_buttons', ctypes.c_ushort)]  # something strange is happening here but it is not being used

    X11Lib = ctypes.cdll.LoadLibrary('libX11.so')
    X11Lib.XOpenDisplay.restype = ctypes.POINTER(X11Display)
    X11Lib.XkbGetState.argtypes = [ctypes.POINTER(X11Display), ctypes.c_uint, ctypes.POINTER(X11XkbStateRec)]
    display = X11Lib.XOpenDisplay(None)
except Exception:
    _log.warn(
        'X11 not available - rules cannot access current process or keyboard group and cannot simulate input. %s',
        exc_info=_sys.exc_info()
    )
    modifier_keycodes = []
    x11 = False


def kbdgroup():
    if x11:
        state = X11XkbStateRec()
        X11Lib.XkbGetState(display, 0x100, ctypes.pointer(state))  # 0x100 is core device FIXME
        return state.group
    else:
        return None


def modifier_code(keycode):
    if keycode == 0:
        return None
    for m in range(0, len(modifier_keycodes)):
        if keycode in modifier_keycodes[m]:
            return m


gdisplay = Gdk.Display.get_default()
gkeymap = Gdk.Keymap.get_for_display(gdisplay)

key_down = None
key_up = None


def signed(bytes):
    return int.from_bytes(bytes, 'big', signed=True)


def xy_direction(_x, _y):
    # normalize x and y
    m = _sqrt((_x * _x) + (_y * _y))
    if m == 0:
        return 'noop'
    x = round(_x / m)
    y = round(_y / m)
    if x < 0 and y < 0:
        return 'Mouse Up-left'
    elif x > 0 and y < 0:
        return 'Mouse Up-right'
    elif x < 0 and y > 0:
        return 'Mouse Down-left'
    elif x > 0 and y > 0:
        return 'Mouse Down-right'
    elif x > 0:
        return 'Mouse Right'
    elif x < 0:
        return 'Mouse Left'
    elif y > 0:
        return 'Mouse Down'
    elif y < 0:
        return 'Mouse Up'
    else:
        return 'noop'


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

MOUSE_GESTURE_TESTS = {
    'mouse-down': ['Mouse Down'],
    'mouse-up': ['Mouse Up'],
    'mouse-left': ['Mouse Left'],
    'mouse-right': ['Mouse Right'],
    'mouse-noop': [],
}

COMPONENTS = {}

if x11:
    displayt = Display()
else:
    displayt = None


class RuleComponent:
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


def x11_focus_prog():
    pid = wm_class = None
    window = xdisplay.get_input_focus().focus
    while window:
        pid = window.get_full_property(NET_WM_PID, 0)
        wm_class = window.get_wm_class()
        if wm_class and pid:
            break
        window = window.query_tree().parent
    try:
        name = psutil.Process(pid.value[0]).name() if pid else ''
    except Exception:
        name = ''
    return (wm_class[0], wm_class[1], name) if wm_class else (name, )


def x11_pointer_prog():
    pid = wm_class = None
    window = xdisplay.screen().root.query_pointer().child
    for window in reversed(window.query_tree().children):
        pid = window.get_full_property(NET_WM_PID, 0)
        wm_class = window.get_wm_class()
        if wm_class:
            break
        window = window.query_tree().parent
    name = psutil.Process(pid.value[0]).name() if pid else ''
    return (wm_class[0], wm_class[1], name) if wm_class else (name, )


class Process(Condition):
    def __init__(self, process):
        self.process = process
        if not x11:
            _log.warn('X11 not available - rules cannot access current process - %s', self)
        if not isinstance(process, str):
            _log.warn('rule Process argument not a string: %s', process)
            self.process = str(process)

    def __str__(self):
        return 'Process: ' + str(self.process)

    def evaluate(self, feature, notification, device, status, last_result):
        if not isinstance(self.process, str):
            return False
        focus = x11_focus_prog() if x11 else None
        result = any(bool(s and s.startswith(self.process)) for s in focus) if focus else None
        return result

    def data(self):
        return {'Process': str(self.process)}


class MouseProcess(Condition):
    def __init__(self, process):
        self.process = process
        if not x11:
            _log.warn('X11 not available - rules cannot access current mouse process - %s', self)
        if not isinstance(process, str):
            _log.warn('rule MouseProcess argument not a string: %s', process)
            self.process = str(process)

    def __str__(self):
        return 'MouseProcess: ' + str(self.process)

    def evaluate(self, feature, notification, device, status, last_result):
        if not isinstance(self.process, str):
            return False
        result = any(bool(s and s.startswith(self.process)) for s in x11_pointer_prog()) if x11 else None
        return result

    def data(self):
        return {'MouseProcess': str(self.process)}


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


# Setting(device, setting, [key], value...)
class Setting(Condition):
    def __init__(self, args):
        if not (isinstance(args, list) and len(args) > 2):
            _log.warn('rule Setting argument not list with minimum length 3: %s', args)
            self.args = []
        else:
            self.args = args

    def __str__(self):
        return 'Setting: ' + ' '.join([str(a) for a in self.args])

    def evaluate(self, report, notification, device, status, last_result):
        import solaar.ui.window as _window
        if len(self.args) < 3:
            return None
        dev = _window.find_device(self.args[0]) if self.args[0] is not None else device
        if dev is None:
            _log.warn('Setting condition: device %s is not known', self.args[0])
            return False
        setting = next((s for s in dev.settings if s.name == self.args[1]), None)
        if setting is None:
            _log.warn('Setting condition: setting %s is not the name of a setting for %s', self.args[1], dev.name)
            return None
        # should the value argument be checked to be sure it is acceptable?? needs to be careful about boolean toggle
        # TODO add compare  methods for more validators
        try:
            result = setting.compare(self.args[2:], setting.read())
        except Exception as e:
            _log.warn('Setting condition: error when checking setting %s: %s', self.args, e)
            result = False
        return result

    def data(self):
        return {'Setting': self.args[:]}


MODIFIERS = {
    'Shift': int(Gdk.ModifierType.SHIFT_MASK),
    'Control': int(Gdk.ModifierType.CONTROL_MASK),
    'Alt': int(Gdk.ModifierType.MOD1_MASK),
    'Super': int(Gdk.ModifierType.MOD4_MASK)
}
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
        current = gkeymap.get_modifier_state()  # get the current keyboard modifier
        return self.desired == (current & MODIFIER_MASK)

    def data(self):
        return {'Modifiers': [str(m) for m in self.modifiers]}


class Key(Condition):
    DOWN = 'pressed'
    UP = 'released'

    def __init__(self, args):
        default_key = 0
        default_action = self.DOWN

        key, action = None, None

        if not args or not isinstance(args, (list, str)):
            _log.warn('rule Key arguments unknown: %s' % args)
            key = default_key
            action = default_action
        elif isinstance(args, str):
            _log.debug('rule Key assuming action "%s" for "%s"' % (default_action, args))
            key = args
            action = default_action
        elif isinstance(args, list):
            if len(args) == 1:
                _log.debug('rule Key assuming action "%s" for "%s"' % (default_action, args))
                key, action = args[0], default_action
            elif len(args) >= 2:
                key, action = args[:2]

        if isinstance(key, str) and key in _CONTROL:
            self.key = _CONTROL[key]
        else:
            _log.warn('rule Key key name not name of a Logitech key: %s' % key)
            self.key = default_key

        if isinstance(action, str) and action in (self.DOWN, self.UP):
            self.action = action
        else:
            _log.warn('rule Key action unknown: %s, assuming %s' % (action, default_action))
            self.action = default_action

    def __str__(self):
        return 'Key: %s (%s)' % ((str(self.key) if self.key else 'None'), self.action)

    def evaluate(self, feature, notification, device, status, last_result):
        return bool(self.key and self.key == (key_down if self.action == self.DOWN else key_up))

    def data(self):
        return {'Key': [str(self.key), self.action]}


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
            if test in MOUSE_GESTURE_TESTS:
                _log.warn('mouse movement test %s deprecated, converting to a MouseGesture', test)
                self.__class__ = MouseGesture
                self.__init__(MOUSE_GESTURE_TESTS[test])
            elif test in TESTS:
                self.function = TESTS[test]
            else:
                _log.warn('rule Test string argument not name of a test: %s', test)
                self.function = TESTS['False']
        elif isinstance(test, list) and all(isinstance(t, int) for t in test):
            _log.warn('Test rules consisting of numbers are deprecated, converting to a TestBytes condition')
            self.__class__ = TestBytes
            self.__init__(test)
        else:
            _log.warn('rule Test argument not valid %s', test)

    def __str__(self):
        return 'Test: ' + str(self.test)

    def evaluate(self, feature, notification, device, status, last_result):
        return self.function(feature, notification.address, notification.data)

    def data(self):
        return {'Test': str(self.test)}


class TestBytes(Condition):
    def __init__(self, test):
        self.test = test
        if (
            isinstance(test, list) and 2 < len(test) <= 4 and all(isinstance(t, int) for t in test) and test[0] >= 0
            and test[0] <= 16 and test[1] >= 0 and test[1] <= 16 and test[0] < test[1]
        ):
            self.function = bit_test(*test) if len(test) == 3 else range_test(*test)
        else:
            _log.warn('rule TestBytes argument not valid %s', test)

    def __str__(self):
        return 'TestBytes: ' + str(self.test)

    def evaluate(self, feature, notification, device, status, last_result):
        return self.function(feature, notification.address, notification.data)

    def data(self):
        return {'TestBytes': self.test[:]}


class MouseGesture(Condition):
    MOVEMENTS = [
        'Mouse Up', 'Mouse Down', 'Mouse Left', 'Mouse Right', 'Mouse Up-left', 'Mouse Up-right', 'Mouse Down-left',
        'Mouse Down-right'
    ]

    def __init__(self, movements):
        if isinstance(movements, str):
            movements = [movements]
        for x in movements:
            if x not in self.MOVEMENTS and x not in _CONTROL:
                _log.warn('rule Key argument not name of a Logitech key: %s', x)
        self.movements = movements

    def __str__(self):
        return 'MouseGesture: ' + ' '.join(self.movements)

    def evaluate(self, feature, notification, device, status, last_result):
        if feature == _F.MOUSE_GESTURE:
            d = notification.data
            count = _unpack('!h', d[:2])[0]
            data = _unpack('!' + ((int(len(d) / 2) - 1) * 'h'), d[2:])
            if count != len(self.movements):
                return False
            x = 0
            z = 0
            while x < len(data):
                if data[x] == 0:
                    direction = xy_direction(data[x + 1], data[x + 2])
                    if self.movements[z] != direction:
                        return False
                    x += 3
                elif data[x] == 1:
                    if data[x + 1] not in _CONTROL:
                        return False
                    if self.movements[z] != str(_CONTROL[data[x + 1]]):
                        return False
                    x += 2
                z += 1
            return True
        return False

    def data(self):
        return {'MouseGesture': [str(m) for m in self.movements]}


class Action(RuleComponent):
    def __init__(self, *args):
        pass

    def evaluate(self, feature, notification, device, status, last_result):
        return None


class KeyPress(Action):
    def __init__(self, keys):
        if isinstance(keys, str):
            keys = [keys]
        self.key_names = keys
        self.key_symbols = [XK_KEYS.get(k, None) for k in keys]
        if not all(self.key_symbols):
            _log.warn('rule KeyPress not sequence of key names %s', keys)
            self.key_symbols = []
        if not x11:
            _log.warn('rule KeyPress action only available in X11 %s', keys)
            self.key_symbols = []

    def keysym_to_keycode(self, keysym, modifiers):  # maybe should take shift into account
        group = kbdgroup() or 0
        keycodes = gkeymap.get_entries_for_keyval(keysym)
        if len(keycodes.keys) == 1:
            k = keycodes.keys[0]
            return k.keycode
        else:
            for k in keycodes.keys:
                if group == k.group:
                    return k.keycode
            _log.warn('rule KeyPress key symbol not currently available %s', self)

    def __str__(self):
        return 'KeyPress: ' + ' '.join(self.key_names)

    def needed(self, k, modifiers):
        code = modifier_code(k)
        return not (code is not None and modifiers & (1 << code))

    def keyDown(self, keysyms, modifiers):
        for k in keysyms:
            keycode = self.keysym_to_keycode(k, modifiers)
            if self.needed(keycode, modifiers) and x11 and keycode:
                Xlib.ext.xtest.fake_input(displayt, X.KeyPress, keycode)

    def keyUp(self, keysyms, modifiers):
        for k in keysyms:
            keycode = self.keysym_to_keycode(k, modifiers)
            if self.needed(keycode, modifiers) and x11 and keycode:
                Xlib.ext.xtest.fake_input(displayt, X.KeyRelease, keycode)

    def evaluate(self, feature, notification, device, status, last_result):
        current = gkeymap.get_modifier_state()
        if _log.isEnabledFor(_INFO):
            _log.info('KeyPress action: %s, modifiers %s %s', self.key_symbols, current, [hex(k) for k in self.key_symbols])
        self.keyDown(self.key_symbols, current)
        self.keyUp(reversed(self.key_symbols), current)
        if x11:
            displayt.sync()
        return None

    def data(self):
        return {'KeyPress': [str(k) for k in self.key_names]}


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
    if x11:
        for _ in range(count):
            Xlib.ext.xtest.fake_input(displayt, Xlib.X.ButtonPress, button)
            Xlib.ext.xtest.fake_input(displayt, Xlib.X.ButtonRelease, button)
    else:
        _log.warn('X11 not available - rules cannot simulate mouse clicks')


class MouseScroll(Action):
    def __init__(self, amounts):
        import numbers
        if len(amounts) == 1 and isinstance(amounts[0], list):
            amounts = amounts[0]
        if not (len(amounts) == 2 and all([isinstance(a, numbers.Number) for a in amounts])):
            _log.warn('rule MouseScroll argument not two numbers %s', amounts)
            amounts = [0, 0]
        self.amounts = amounts
        if not x11:
            _log.warn('X11 not available - rules cannot simulate mouse scrolling - %s', self)

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
        if x11:
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
        if not x11:
            _log.warn('X11 not available - rules cannot simulate mouse clicks - %s', self)

    def __str__(self):
        return 'MouseClick: %s (%d)' % (self.button, self.count)

    def evaluate(self, feature, notification, device, status, last_result):
        if _log.isEnabledFor(_INFO):
            _log.info('MouseClick action: %d %s' % (self.count, self.button))
        if self.button and self.count:
            click(buttons[self.button], self.count)
        if x11:
            displayt.sync()
        return None

    def data(self):
        return {'MouseClick': [self.button, self.count]}


class Set(Action):
    def __init__(self, args):
        if not (isinstance(args, list) and len(args) > 2):
            _log.warn('rule Set argument not list with minimum length 3: %s', args)
            self.args = []
        else:
            self.args = args

    def __str__(self):
        return 'Set: ' + ' '.join([str(a) for a in self.args])

    def evaluate(self, feature, notification, device, status, last_result):
        import solaar.ui.window as _window
        # importing here to avoid circular imports

        if len(self.args) < 3:
            return None
        if _log.isEnabledFor(_INFO):
            _log.info('Set action: %s', self.args)
        dev = _window.find_device(self.args[0]) if self.args[0] is not None else device
        if dev is None:
            _log.error('Set action: device %s is not known', self.args[0])
            return None
        setting = next((s for s in dev.settings if s.name == self.args[1]), None)
        if setting is None:
            _log.error('Set action: setting %s is not the name of a setting for %s', self.args[1], dev.name)
            return None
        args = setting.acceptable(self.args[2:], setting.read())
        if args is None:
            _log.error('Set Action: invalid args %s for setting %s of %s', self.args[2:], self.args[1], self.args[0])
            return None
        _change_setting(dev, setting, args)
        return None

    def data(self):
        return {'Set': self.args[:]}


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
    'MouseProcess': MouseProcess,
    'Feature': Feature,
    'Report': Report,
    'Setting': Setting,
    'Modifiers': Modifiers,
    'Key': Key,
    'Test': Test,
    'TestBytes': TestBytes,
    'MouseGesture': MouseGesture,
    'KeyPress': KeyPress,
    'MouseScroll': MouseScroll,
    'MouseClick': MouseClick,
    'Set': Set,
    'Execute': Execute,
}

built_in_rules = Rule([])
if True:  # x11
    built_in_rules = Rule([
        {'Rule': [  # Implement problematic keys for Craft and MX Master
            {'Rule': [{'Key': ['Brightness Down', 'pressed']}, {'KeyPress': 'XF86_MonBrightnessDown'}]},
            {'Rule': [{'Key': ['Brightness Up', 'pressed']}, {'KeyPress': 'XF86_MonBrightnessUp'}]},
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
g_keys_down = [0, 0, 0, 0]
m_keys_down = 0
mr_key_down = False


# process a notification
def process_notification(device, status, notification, feature):
    if False:  # not x11
        return
    global keys_down, g_keys_down, m_keys_down, mr_key_down, key_down, key_up
    key_down, key_up = None, None
    # need to keep track of keys that are down to find a new key down
    if feature == _F.REPROG_CONTROLS_V4 and notification.address == 0x00:
        new_keys_down = _unpack('!4H', notification.data[:8])
        for key in new_keys_down:
            if key and key not in keys_down:
                key_down = key
        for key in keys_down:
            if key and key not in new_keys_down:
                key_up = key
        keys_down = new_keys_down
    # and also G keys down
    elif feature == _F.GKEY and notification.address == 0x00:
        new_g_keys_down = _unpack('!4B', notification.data[:4])
        # process 32 bits, byte by byte
        for byte_idx in range(4):
            new_byte, old_byte = new_g_keys_down[byte_idx], g_keys_down[byte_idx]
            for i in range(1, 9):
                if new_byte & (0x01 << (i - 1)) and not old_byte & (0x01 << (i - 1)):
                    key_down = _CONTROL['G' + str(i + 8 * byte_idx)]
                if old_byte & (0x01 << (i - 1)) and not new_byte & (0x01 << (i - 1)):
                    key_up = _CONTROL['G' + str(i + 8 * byte_idx)]
        g_keys_down = new_g_keys_down
    # and also M keys down
    elif feature == _F.MKEYS and notification.address == 0x00:
        new_m_keys_down = _unpack('!1B', notification.data[:1])[0]
        for i in range(1, 9):
            if new_m_keys_down & (0x01 << (i - 1)) and not m_keys_down & (0x01 << (i - 1)):
                key_down = _CONTROL['M' + str(i)]
            if m_keys_down & (0x01 << (i - 1)) and not new_m_keys_down & (0x01 << (i - 1)):
                key_up = _CONTROL['M' + str(i)]
        m_keys_down = new_m_keys_down
    # and also MR key
    elif feature == _F.MR and notification.address == 0x00:
        new_mr_key_down = _unpack('!1B', notification.data[:1])[0]
        if not mr_key_down and new_mr_key_down:
            key_down = _CONTROL['MR']
        if mr_key_down and not new_mr_key_down:
            key_up = _CONTROL['MR']
        mr_key_down = new_mr_key_down
    GLib.idle_add(rules.evaluate, feature, notification, device, status, True)


_XDG_CONFIG_HOME = _os.environ.get('XDG_CONFIG_HOME') or _path.expanduser(_path.join('~', '.config'))
_file_path = _path.join(_XDG_CONFIG_HOME, 'solaar', 'rules.yaml')

rules = built_in_rules


def _save_config_rule_file(file_name=_file_path):
    # This is a trick to show str/float/int lists in-line (inspired by https://stackoverflow.com/a/14001707)
    class inline_list(list):
        pass

    def blockseq_rep(dumper, data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

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
        if isinstance(elem, NamedInt):
            return int(elem)
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
    rules_to_save = sum((r.data()['Rule'] for r in rules.components if r.source == file_name), [])
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
            with open(_file_path) as config_file:
                loaded_rules = []
                for loaded_rule in _yaml_safe_load_all(config_file):
                    rule = Rule(loaded_rule, source=_file_path)
                    if _log.isEnabledFor(_DEBUG):
                        _log.debug('load rule: %s', rule)
                    loaded_rules.append(rule)
                if _log.isEnabledFor(_INFO):
                    _log.info('loaded %d rules from %s', len(loaded_rules), config_file.name)
        except Exception as e:
            _log.error('failed to load from %s\n%s', _file_path, e)
    rules = Rule([Rule(loaded_rules, source=_file_path), built_in_rules])


if True:  # x11
    _load_config_rule_file()
