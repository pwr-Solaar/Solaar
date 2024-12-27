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

from __future__ import annotations

import ctypes
import logging
import math
import numbers
import os
import platform
import socket
import struct
import subprocess
import sys
import time
import typing

from typing import Any
from typing import Dict
from typing import Tuple

import gi
import psutil
import yaml

from keysyms import keysymdef

# There is no evdev on macOS or Windows. Diversion will not work without
# it but other Solaar functionality is available.
if platform.system() in ("Darwin", "Windows"):
    evdev = None
else:
    import evdev

from .common import NamedInt
from .hidpp20 import SupportedFeature
from .special_keys import CONTROL

gi.require_version("Gdk", "3.0")  # isort:skip
from gi.repository import Gdk, GLib  # NOQA: E402 # isort:skip

if typing.TYPE_CHECKING:
    from .base import HIDPPNotification

logger = logging.getLogger(__name__)

#
# See docs/rules.md for documentation
#
# Several capabilities of rules depend on aspects of GDK, X11, or XKB
# As the Solaar GUI uses GTK, Glib and GDK are always available and are obtained from gi.repository
#
# Process condition depends on X11 from python-xlib, and is probably not possible at all in Wayland
# MouseProcess condition depends on X11 from python-xlib, and is probably not possible at all in Wayland
# Modifiers condition depends only on GDK
# KeyPress action determines whether a keysym is a currently-down modifier using get_modifier_mapping from python-xlib;
#   under Wayland no modifier keys are considered down so all modifier keys are pressed, potentially leading to problems
# KeyPress action translates key names to keysysms using the local file described for GUI keyname determination
# KeyPress action gets the current keyboard group using XkbGetState from libX11.so using ctypes definitions
#   under Wayland the keyboard group is None resulting in using the first keyboard group
# KeyPress action translates keysyms to keycodes using the GDK keymap
# KeyPress, MouseScroll, and MouseClick actions use XTest (under X11) or uinput.
# For uinput to work the user must have write access for /dev/uinput.
# To get this access run  sudo setfacl -m u:${user}:rw /dev/uinput
#
# Rule GUI keyname determination uses a local file generated
#   from http://cgit.freedesktop.org/xorg/proto/x11proto/plain/keysymdef.h
#   and http://cgit.freedesktop.org/xorg/proto/x11proto/plain/XF86keysym.h
# because there does not seem to be a non-X11 file for this set of key names

# Setting up is complex because there are several systems that each provide partial facilities:
# GDK - always available (when running with a window system) but only provides access to keymap
# X11 - provides access to active process and process with window under mouse and current modifier keys
# Xtest extension to X11 - provides input simulation, partly works under Wayland
# Wayland - provides input simulation

XK_KEYS: Dict[str, int] = keysymdef.key_symbols

# Event codes - can't use Xlib.X codes because Xlib might not be available
_KEY_RELEASE = 0
_KEY_PRESS = 1
_BUTTON_RELEASE = 2
_BUTTON_PRESS = 3

CLICK, DEPRESS, RELEASE = "click", "depress", "release"

gdisplay = Gdk.Display.get_default()  # can be None if Solaar is run without a full window system
gkeymap = Gdk.Keymap.get_for_display(gdisplay) if gdisplay else None
if logger.isEnabledFor(logging.INFO):
    logger.info("GDK Keymap %sset up", "" if gkeymap else "not ")

wayland = os.getenv("WAYLAND_DISPLAY")  # is this Wayland?
if wayland:
    logger.warning(
        "rules cannot access modifier keys in Wayland, "
        "accessing process only works on GNOME with Solaar Gnome extension installed"
    )

try:
    import Xlib

    _x11 = None  # X11 might be available
except Exception:
    _x11 = False  # X11 is not available

# Globals
xtest_available = True  # Xtest might be available
xdisplay = None


Xkbdisplay = None  # xkb might be available
X11Lib = None

modifier_keycodes = []
XkbUseCoreKbd = 0x100
NET_ACTIVE_WINDOW = None
NET_WM_PID = None
WM_CLASS = None


udevice = None

key_down = None
key_up = None

keys_down = []
g_keys_down = 0
m_keys_down = 0
mr_key_down = False
thumb_wheel_displacement = 0

_dbus_interface = None


class XkbDisplay(ctypes.Structure):
    """opaque struct"""


class XkbStateRec(ctypes.Structure):
    _fields_ = [
        ("group", ctypes.c_ubyte),
        ("locked_group", ctypes.c_ubyte),
        ("base_group", ctypes.c_ushort),
        ("latched_group", ctypes.c_ushort),
        ("mods", ctypes.c_ubyte),
        ("base_mods", ctypes.c_ubyte),
        ("latched_mods", ctypes.c_ubyte),
        ("locked_mods", ctypes.c_ubyte),
        ("compat_state", ctypes.c_ubyte),
        ("grab_mods", ctypes.c_ubyte),
        ("compat_grab_mods", ctypes.c_ubyte),
        ("lookup_mods", ctypes.c_ubyte),
        ("compat_lookup_mods", ctypes.c_ubyte),
        ("ptr_buttons", ctypes.c_ushort),
    ]  # something strange is happening here but it is not being used


def x11_setup():
    global _x11, xdisplay, modifier_keycodes, NET_ACTIVE_WINDOW, NET_WM_PID, WM_CLASS, xtest_available
    if _x11 is not None:
        return _x11
    try:
        from Xlib.display import Display

        xdisplay = Display()
        modifier_keycodes = xdisplay.get_modifier_mapping()  # there should be a way to do this in Gdk
        NET_ACTIVE_WINDOW = xdisplay.intern_atom("_NET_ACTIVE_WINDOW")
        NET_WM_PID = xdisplay.intern_atom("_NET_WM_PID")
        WM_CLASS = xdisplay.intern_atom("WM_CLASS")
        _x11 = True  # X11 available
        if logger.isEnabledFor(logging.INFO):
            logger.info("X11 library loaded and display set up")
    except Exception:
        logger.warning("X11 not available - some rule capabilities inoperable", exc_info=sys.exc_info())
        _x11 = False
        xtest_available = False
    return _x11


def gnome_dbus_interface_setup():
    global _dbus_interface
    if _dbus_interface is not None:
        return _dbus_interface
    try:
        import dbus

        bus = dbus.SessionBus()
        remote_object = bus.get_object("org.gnome.Shell", "/io/github/pwr_solaar/solaar")
        _dbus_interface = dbus.Interface(remote_object, "io.github.pwr_solaar.solaar")
    except dbus.exceptions.DBusException:
        logger.warning(
            "Solaar Gnome extension not installed - some rule capabilities inoperable",
            exc_info=sys.exc_info(),
        )
        _dbus_interface = False
    return _dbus_interface


def xkb_setup():
    global X11Lib, Xkbdisplay
    if Xkbdisplay is not None:
        return Xkbdisplay
    try:  # set up to get keyboard state using ctypes interface to libx11
        X11Lib = ctypes.cdll.LoadLibrary("libX11.so")
        X11Lib.XOpenDisplay.restype = ctypes.POINTER(XkbDisplay)
        X11Lib.XkbGetState.argtypes = [ctypes.POINTER(XkbDisplay), ctypes.c_uint, ctypes.POINTER(XkbStateRec)]
        Xkbdisplay = X11Lib.XOpenDisplay(None)
        if logger.isEnabledFor(logging.INFO):
            logger.info("XKB display set up")
    except Exception:
        logger.warning("XKB display not available - rules cannot access keyboard group", exc_info=sys.exc_info())
        Xkbdisplay = False
    return Xkbdisplay


if evdev:
    buttons = {
        "unknown": (None, None),
        "left": (1, evdev.ecodes.ecodes["BTN_LEFT"]),
        "middle": (2, evdev.ecodes.ecodes["BTN_MIDDLE"]),
        "right": (3, evdev.ecodes.ecodes["BTN_RIGHT"]),
        "scroll_up": (4, evdev.ecodes.ecodes["BTN_4"]),
        "scroll_down": (5, evdev.ecodes.ecodes["BTN_5"]),
        "scroll_left": (6, evdev.ecodes.ecodes["BTN_6"]),
        "scroll_right": (7, evdev.ecodes.ecodes["BTN_7"]),
        "button8": (8, evdev.ecodes.ecodes["BTN_8"]),
        "button9": (9, evdev.ecodes.ecodes["BTN_9"]),
        "back": (10, evdev.ecodes.ecodes["BTN_SIDE"]),
        "forward": (11, evdev.ecodes.ecodes["BTN_EXTRA"]),
    }

    # uinput capability for keyboard keys, mouse buttons, and scrolling
    key_events = [c for n, c in evdev.ecodes.ecodes.items() if n.startswith("KEY") and n != "KEY_CNT"]
    for _, evcode in buttons.values():
        if evcode:
            key_events.append(evcode)
    devicecap = {
        evdev.ecodes.EV_KEY: key_events,
        evdev.ecodes.EV_REL: [evdev.ecodes.REL_WHEEL, evdev.ecodes.REL_HWHEEL],
    }
else:
    # Just mock these since they won't be useful without evdev anyway
    buttons = {}
    key_events = []
    devicecap = {}


def setup_uinput():
    global udevice
    if udevice is not None:
        return udevice
    try:
        udevice = evdev.uinput.UInput(events=devicecap, name="solaar-keyboard")
        if logger.isEnabledFor(logging.INFO):
            logger.info("uinput device set up")
        return True
    except Exception as e:
        logger.warning("cannot create uinput device: %s", e)


if wayland:  # Wayland can't use xtest so may as well set up uinput now
    setup_uinput()


def kbdgroup():
    if xkb_setup():
        state = XkbStateRec()
        X11Lib.XkbGetState(Xkbdisplay, XkbUseCoreKbd, ctypes.pointer(state))
        return state.group
    else:
        return None


def modifier_code(keycode):
    if wayland or not x11_setup() or keycode == 0:
        return None
    for m in range(0, len(modifier_keycodes)):
        if keycode in modifier_keycodes[m]:
            return m


def signed(bytes_: bytes) -> int:
    return int.from_bytes(bytes_, "big", signed=True)


def xy_direction(_x, _y):
    # normalize x and y
    m = math.sqrt((_x * _x) + (_y * _y))
    if m == 0:
        return "noop"
    x = round(_x / m)
    y = round(_y / m)
    if x < 0 and y < 0:
        return "Mouse Up-left"
    elif x > 0 > y:
        return "Mouse Up-right"
    elif x < 0 < y:
        return "Mouse Down-left"
    elif x > 0 and y > 0:
        return "Mouse Down-right"
    elif x > 0:
        return "Mouse Right"
    elif x < 0:
        return "Mouse Left"
    elif y > 0:
        return "Mouse Down"
    elif y < 0:
        return "Mouse Up"
    else:
        return "noop"


def simulate_xtest(code, event):
    global xtest_available
    if x11_setup() and xtest_available:
        try:
            event = (
                Xlib.X.KeyPress
                if event == _KEY_PRESS
                else Xlib.X.KeyRelease
                if event == _KEY_RELEASE
                else Xlib.X.ButtonPress
                if event == _BUTTON_PRESS
                else Xlib.X.ButtonRelease
                if event == _BUTTON_RELEASE
                else None
            )
            Xlib.ext.xtest.fake_input(xdisplay, event, code)
            xdisplay.sync()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("xtest simulated input %s %s %s", xdisplay, event, code)
            return True
        except Exception as e:
            xtest_available = False
            logger.warning("xtest fake input failed: %s", e)


def simulate_uinput(what, code, arg):
    global udevice
    if setup_uinput():
        try:
            udevice.write(what, code, arg)
            udevice.syn()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("uinput simulated input %s %s %s", what, code, arg)
            return True
        except Exception as e:
            udevice = None
            logger.warning("uinput write failed: %s", e)


def simulate_key(code, event):  # X11 keycode but Solaar event code
    if not wayland and simulate_xtest(code, event):
        return True
    if evdev and simulate_uinput(evdev.ecodes.EV_KEY, code - 8, event):
        return True
    logger.warning("no way to simulate key input")


def click_xtest(button, count):
    if isinstance(count, int):
        for _ in range(count):
            if not simulate_xtest(button[0], _BUTTON_PRESS):
                return False
            if not simulate_xtest(button[0], _BUTTON_RELEASE):
                return False
    else:
        if count != RELEASE:
            if not simulate_xtest(button[0], _BUTTON_PRESS):
                return False
        if count != DEPRESS:
            if not simulate_xtest(button[0], _BUTTON_RELEASE):
                return False
    return True


def click_uinput(button, count):
    if isinstance(count, int):
        for _ in range(count):
            if not simulate_uinput(evdev.ecodes.EV_KEY, button[1], 1):
                return False
            if not simulate_uinput(evdev.ecodes.EV_KEY, button[1], 0):
                return False
    else:
        if count != RELEASE:
            if not simulate_uinput(evdev.ecodes.EV_KEY, button[1], 1):
                return False
        if count != DEPRESS:
            if not simulate_uinput(evdev.ecodes.EV_KEY, button[1], 0):
                return False
    return True


def click(button, count):
    if not wayland and click_xtest(button, count):
        return True
    if click_uinput(button, count):
        return True
    logger.warning("no way to simulate mouse click")
    return False


def simulate_scroll(dx, dy):
    if not wayland and xtest_available:
        success = True
        if dx:
            success = click_xtest(buttons["scroll_right" if dx > 0 else "scroll_left"], count=abs(dx))
        if dy and success:
            success = click_xtest(buttons["scroll_up" if dy > 0 else "scroll_down"], count=abs(dy))
        if success:
            return True
    if setup_uinput():
        success = True
        if dx:
            success = simulate_uinput(evdev.ecodes.EV_REL, evdev.ecodes.REL_HWHEEL, dx)
        if dy and success:
            success = simulate_uinput(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, dy)
        if success:
            return True
    logger.warning("no way to simulate scrolling")


def thumb_wheel_up(f, r, d, a):
    global thumb_wheel_displacement
    if f != SupportedFeature.THUMB_WHEEL or r != 0:
        return False
    if a is None:
        return signed(d[0:2]) < 0 and signed(d[0:2])
    elif thumb_wheel_displacement <= -a:
        thumb_wheel_displacement += a
        return 1
    else:
        return False


def thumb_wheel_down(f, r, d, a):
    global thumb_wheel_displacement
    if f != SupportedFeature.THUMB_WHEEL or r != 0:
        return False
    if a is None:
        return signed(d[0:2]) > 0 and signed(d[0:2])
    elif thumb_wheel_displacement >= a:
        thumb_wheel_displacement -= a
        return 1
    else:
        return False


def charging(f, r, d, _a):
    if (
        (f == SupportedFeature.BATTERY_STATUS and r == 0 and 1 <= d[2] <= 4)
        or (f == SupportedFeature.BATTERY_VOLTAGE and r == 0 and d[2] & (1 << 7))
        or (f == SupportedFeature.UNIFIED_BATTERY and r == 0 and 1 <= d[2] <= 3)
    ):
        return 1
    else:
        return False


TESTS = {
    "crown_right": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[1] < 128 and d[1], False],
    "crown_left": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[1] >= 128 and 256 - d[1], False],
    "crown_right_ratchet": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[2] < 128 and d[2], False],
    "crown_left_ratchet": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[2] >= 128 and 256 - d[2], False],
    "crown_tap": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[5] == 0x01 and d[5], False],
    "crown_start_press": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[6] == 0x01 and d[6], False],
    "crown_end_press": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and d[6] == 0x05 and d[6], False],
    "crown_pressed": [lambda f, r, d, a: f == SupportedFeature.CROWN and r == 0 and 0x01 <= d[6] <= 0x04 and d[6], False],
    "thumb_wheel_up": [thumb_wheel_up, True],
    "thumb_wheel_down": [thumb_wheel_down, True],
    "lowres_wheel_up": [
        lambda f, r, d, a: f == SupportedFeature.LOWRES_WHEEL and r == 0 and signed(d[0:1]) > 0 and signed(d[0:1]),
        False,
    ],
    "lowres_wheel_down": [
        lambda f, r, d, a: f == SupportedFeature.LOWRES_WHEEL and r == 0 and signed(d[0:1]) < 0 and signed(d[0:1]),
        False,
    ],
    "hires_wheel_up": [
        lambda f, r, d, a: f == SupportedFeature.HIRES_WHEEL and r == 0 and signed(d[1:3]) > 0 and signed(d[1:3]),
        False,
    ],
    "hires_wheel_down": [
        lambda f, r, d, a: f == SupportedFeature.HIRES_WHEEL and r == 0 and signed(d[1:3]) < 0 and signed(d[1:3]),
        False,
    ],
    "charging": [charging, False],
    "False": [lambda f, r, d, a: False, False],
    "True": [lambda f, r, d, a: True, False],
}

MOUSE_GESTURE_TESTS = {
    "mouse-down": ["Mouse Down"],
    "mouse-up": ["Mouse Up"],
    "mouse-left": ["Mouse Left"],
    "mouse-right": ["Mouse Right"],
    "mouse-noop": [],
}

# COMPONENTS = {}


class RuleComponent:
    def compile(self, c):
        if isinstance(c, RuleComponent):
            return c
        elif isinstance(c, dict) and len(c) == 1:
            k, v = next(iter(c.items()))
            if k in COMPONENTS:
                return COMPONENTS[k](v)
        logger.warning("illegal component in rule: %s", c)
        return Condition()


def _evaluate(components, feature, notification: HIDPPNotification, device, result) -> Any:
    res = True
    for component in components:
        res = component.evaluate(feature, notification, device, result)
        if not isinstance(component, Action) and res is None:
            return None
        if isinstance(component, Condition) and not res:
            return res
    return res


class Rule(RuleComponent):
    def __init__(self, args, source=None, warn=True):
        self.components = [self.compile(a) for a in args]
        self.source = source

    def __str__(self):
        source = "(" + self.source + ")" if self.source else ""
        return f"Rule{source}[{', '.join([c.__str__() for c in self.components])}]"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate rule: %s", self)
        return _evaluate(self.components, feature, notification, device, True)

    def once(self, feature, notification: HIDPPNotification, device, last_result):
        self.evaluate(feature, notification, device, last_result)
        return False

    def data(self):
        return {"Rule": [c.data() for c in self.components]}


class Condition(RuleComponent):
    def __init__(self, *args):
        pass

    def __str__(self):
        return "CONDITION"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return False


class Not(Condition):
    def __init__(self, op, warn=True):
        if isinstance(op, list) and len(op) == 1:
            op = op[0]
        self.op = op
        self.component = self.compile(op)

    def __str__(self):
        return "Not: " + str(self.component)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        result = self.component.evaluate(feature, notification, device, last_result)
        return None if result is None else not result

    def data(self):
        return {"Not": self.component.data()}


class Or(Condition):
    def __init__(self, args, warn=True):
        self.components = [self.compile(a) for a in args]

    def __str__(self):
        return "Or: [" + ", ".join(str(c) for c in self.components) + "]"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        result = False
        for component in self.components:
            result = component.evaluate(feature, notification, device, last_result)
            if not isinstance(component, Action) and result is None:
                return None
            if isinstance(component, Condition) and result:
                return result
        return result

    def data(self):
        return {"Or": [c.data() for c in self.components]}


class And(Condition):
    def __init__(self, args, warn=True):
        self.components = [self.compile(a) for a in args]

    def __str__(self):
        return "And: [" + ", ".join(str(c) for c in self.components) + "]"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return _evaluate(self.components, feature, notification, device, last_result)

    def data(self):
        return {"And": [c.data() for c in self.components]}


def x11_focus_prog():
    if not x11_setup():
        return None
    pid = wm_class = None
    window = xdisplay.get_input_focus().focus
    while window:
        pid = window.get_full_property(NET_WM_PID, 0)
        wm_class = window.get_wm_class()
        if wm_class and pid:
            break
        window = window.query_tree().parent
    try:
        name = psutil.Process(pid.value[0]).name() if pid else ""
    except Exception:
        name = ""
    return (wm_class[0], wm_class[1], name) if wm_class else (name,)


def x11_pointer_prog():
    if not x11_setup():
        return None
    pid = wm_class = None
    window = xdisplay.screen().root.query_pointer().child
    for child in reversed(window.query_tree().children):
        pid = child.get_full_property(NET_WM_PID, 0)
        wm_class = child.get_wm_class()
        if wm_class:
            break
    name = psutil.Process(pid.value[0]).name() if pid else ""
    return (wm_class[0], wm_class[1], name) if wm_class else (name,)


def gnome_dbus_focus_prog():
    if not gnome_dbus_interface_setup():
        return None
    wm_class = _dbus_interface.ActiveWindow()
    return (wm_class,) if wm_class else None


def gnome_dbus_pointer_prog():
    if not gnome_dbus_interface_setup():
        return None
    wm_class = _dbus_interface.PointerOverWindow()
    return (wm_class,) if wm_class else None


class Process(Condition):
    def __init__(self, process, warn=True):
        self.process = process
        if (not wayland and not x11_setup()) or (wayland and not gnome_dbus_interface_setup()):
            if warn:
                logger.warning(
                    "rules can only access active process in X11 or in Wayland under GNOME with Solaar Gnome "
                    "extension - %s",
                    self,
                )
        if not isinstance(process, str):
            if warn:
                logger.warning("rule Process argument not a string: %s", process)
            self.process = str(process)

    def __str__(self):
        return "Process: " + str(self.process)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        if not isinstance(self.process, str):
            return False
        focus = x11_focus_prog() if not wayland else gnome_dbus_focus_prog()
        result = any(bool(s and s.startswith(self.process)) for s in focus) if focus else None
        return result

    def data(self):
        return {"Process": str(self.process)}


class MouseProcess(Condition):
    def __init__(self, process, warn=True):
        self.process = process
        if (not wayland and not x11_setup()) or (wayland and not gnome_dbus_interface_setup()):
            if warn:
                logger.warning(
                    "rules cannot access active mouse process "
                    "in X11 or in Wayland under GNOME with Solaar Extension for GNOME - %s",
                    self,
                )
        if not isinstance(process, str):
            if warn:
                logger.warning("rule MouseProcess argument not a string: %s", process)
            self.process = str(process)

    def __str__(self):
        return "MouseProcess: " + str(self.process)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        if not isinstance(self.process, str):
            return False
        pointer_focus = x11_pointer_prog() if not wayland else gnome_dbus_pointer_prog()
        result = any(bool(s and s.startswith(self.process)) for s in pointer_focus) if pointer_focus else None
        return result

    def data(self):
        return {"MouseProcess": str(self.process)}


class Feature(Condition):
    def __init__(self, feature: str, warn: bool = True):
        try:
            self.feature = SupportedFeature[feature]
        except KeyError:
            self.feature = None
            if warn:
                logger.warning("rule Feature argument not name of a feature: %s", feature)

    def __str__(self):
        return "Feature: " + str(self.feature)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return feature == self.feature

    def data(self):
        return {"Feature": str(self.feature)}


class Report(Condition):
    def __init__(self, report, warn=True):
        if not (isinstance(report, int)):
            if warn:
                logger.warning("rule Report argument not an integer: %s", report)
            self.report = -1
        else:
            self.report = report

    def __str__(self):
        return "Report: " + str(self.report)

    def evaluate(self, report, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return (notification.address >> 4) == self.report

    def data(self):
        return {"Report": self.report}


# Setting(device, setting, [key], value...)
class Setting(Condition):
    def __init__(self, args, warn=True):
        if not (isinstance(args, list) and len(args) > 2):
            if warn:
                logger.warning("rule Setting argument not list with minimum length 3: %s", args)
            self.args = []
        else:
            self.args = args

    def __str__(self):
        return "Setting: " + " ".join([str(a) for a in self.args])

    def evaluate(self, report, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        if len(self.args) < 3:
            return None
        dev = device.find(self.args[0]) if self.args[0] is not None else device
        if dev is None:
            logger.warning("Setting condition: device %s is not known", self.args[0])
            return False
        setting = next((s for s in dev.settings if s.name == self.args[1]), None)
        if setting is None:
            logger.warning("Setting condition: setting %s is not the name of a setting for %s", self.args[1], dev.name)
            return None
        # should the value argument be checked to be sure it is acceptable?? needs to be careful about boolean toggle
        # TODO add compare  methods for more validators
        try:
            result = setting.compare(self.args[2:], setting.read())
        except Exception as e:
            logger.warning("Setting condition: error when checking setting %s: %s", self.args, e)
            result = False
        return result

    def data(self):
        return {"Setting": self.args[:]}


MODIFIERS = {
    "Shift": int(Gdk.ModifierType.SHIFT_MASK),
    "Control": int(Gdk.ModifierType.CONTROL_MASK),
    "Alt": int(Gdk.ModifierType.MOD1_MASK),
    "Super": int(Gdk.ModifierType.MOD4_MASK),
}
MODIFIER_MASK = MODIFIERS["Shift"] + MODIFIERS["Control"] + MODIFIERS["Alt"] + MODIFIERS["Super"]


class Modifiers(Condition):
    def __init__(self, modifiers, warn=True):
        modifiers = [modifiers] if isinstance(modifiers, str) else modifiers
        self.desired = 0
        self.modifiers = []
        for k in modifiers:
            if k in MODIFIERS:
                self.desired += MODIFIERS.get(k, 0)
                self.modifiers.append(k)
            else:
                if warn:
                    logger.warning("unknown rule Modifier value: %s", k)

    def __str__(self):
        return "Modifiers: " + str(self.desired)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        if gkeymap:
            current = gkeymap.get_modifier_state()  # get the current keyboard modifier
            return self.desired == (current & MODIFIER_MASK)
        else:
            logger.warning("no keymap so cannot determine modifier keys")
            return False

    def data(self):
        return {"Modifiers": [str(m) for m in self.modifiers]}


class Key(Condition):
    DOWN = "pressed"
    UP = "released"

    def __init__(self, args, warn=True):
        default_key = 0
        default_action = self.DOWN

        key, action = None, None

        if not args or not isinstance(args, (list, str)):
            if warn:
                logger.warning(f"rule Key arguments unknown: {args}")
            key = default_key
            action = default_action
        elif isinstance(args, str):
            logger.debug(f'rule Key assuming action "{default_action}" for "{args}"')
            key = args
            action = default_action
        elif isinstance(args, list):
            if len(args) == 1:
                logger.debug(f'rule Key assuming action "{default_action}" for "{args}"')
                key, action = args[0], default_action
            elif len(args) >= 2:
                key, action = args[:2]

        if isinstance(key, str) and key in CONTROL:
            self.key = CONTROL[key]
        elif isinstance(key, str) and key.startswith("unknown:"):
            logger.info(f"rule Key key name currently unknown: {key}")
            self.key = CONTROL[int(key[-4:], 16)]
        else:
            if warn:
                logger.warning(f"rule Key key name not name of a Logitech key: {key}")
            self.key = default_key

        if isinstance(action, str) and action in (self.DOWN, self.UP):
            self.action = action
        else:
            if warn:
                logger.warning(f"rule Key action unknown: {action}, assuming {default_action}")
            self.action = default_action

    def __str__(self):
        return f"Key: {str(self.key) if self.key else 'None'} ({self.action})"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return bool(self.key and self.key == (key_down if self.action == self.DOWN else key_up))

    def data(self):
        return {"Key": [str(self.key), self.action]}


class KeyIsDown(Condition):
    def __init__(self, args, warn=True):
        default_key = 0

        key = None

        if not args or not isinstance(args, str):
            if warn:
                logger.warning(f"rule KeyDown arguments unknown: {args}")
            key = default_key
        elif isinstance(args, str):
            key = args

        if isinstance(key, str) and key in CONTROL:
            self.key = CONTROL[key]
        else:
            if warn:
                logger.warning(f"rule Key key name not name of a Logitech key: {key}")
            self.key = default_key

    def __str__(self):
        return f"KeyIsDown: {str(self.key) if self.key else 'None'}"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return key_is_down(self.key)

    def data(self):
        return {"KeyIsDown": str(self.key)}


def bit_test(start, end, bits):
    return lambda f, r, d: int.from_bytes(d[start:end], byteorder="big", signed=True) & bits


def range_test(start, end, min, max):
    def range_test_helper(_f, _r, d):
        value = int.from_bytes(d[start:end], byteorder="big", signed=True)
        return min <= value <= max and (value if value else True)

    return range_test_helper


class Test(Condition):
    def __init__(self, test, warn=True):
        self.test = ""
        self.parameter = None
        if isinstance(test, str):
            test = [test]
        if isinstance(test, list) and all(isinstance(t, int) for t in test):
            if warn:
                logger.warning("Test rules consisting of numbers are deprecated, converting to a TestBytes condition")
            self.__class__ = TestBytes
            self.__init__(test, warn=warn)
        elif isinstance(test, list):
            if test[0] in MOUSE_GESTURE_TESTS:
                if warn:
                    logger.warning("mouse movement test %s deprecated, converting to a MouseGesture", test)
                self.__class__ = MouseGesture
                self.__init__(MOUSE_GESTURE_TESTS[0][test], warn=warn)
            elif test[0] in TESTS:
                self.test = test[0]
                self.function = TESTS[test[0]][0]
                self.parameter = test[1] if len(test) > 1 else None
            else:
                if warn:
                    logger.warning("rule Test name not name of a test: %s", test)
                self.test = "False"
                self.function = TESTS["False"][0]
        else:
            if warn:
                logger.warning("rule Test argument not valid %s", test)

    def __str__(self):
        return "Test: " + str(self.test)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return self.function(feature, notification.address, notification.data, self.parameter)

    def data(self):
        return {"Test": ([self.test, self.parameter] if self.parameter is not None else [self.test])}


class TestBytes(Condition):
    def __init__(self, test, warn=True):
        self.test = test
        if (
            isinstance(test, list)
            and 2 < len(test) <= 4
            and all(isinstance(t, int) for t in test)
            and 0 <= test[0] <= 16
            and 0 <= test[1] <= 16
            and test[0] < test[1]
        ):
            self.function = bit_test(*test) if len(test) == 3 else range_test(*test)
        else:
            if warn:
                logger.warning("rule TestBytes argument not valid %s", test)

    def __str__(self):
        return "TestBytes: " + str(self.test)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return self.function(feature, notification.address, notification.data)

    def data(self):
        return {"TestBytes": self.test[:]}


class MouseGesture(Condition):
    MOVEMENTS = [
        "Mouse Up",
        "Mouse Down",
        "Mouse Left",
        "Mouse Right",
        "Mouse Up-left",
        "Mouse Up-right",
        "Mouse Down-left",
        "Mouse Down-right",
    ]

    def __init__(self, movements, warn=True):
        if isinstance(movements, str):
            movements = [movements]
        for x in movements:
            if x not in self.MOVEMENTS and x not in CONTROL:
                if warn:
                    logger.warning("rule Mouse Gesture argument not direction or name of a Logitech key: %s", x)
        self.movements = movements

    def __str__(self):
        return "MouseGesture: " + " ".join(self.movements)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        if feature == SupportedFeature.MOUSE_GESTURE:
            d = notification.data
            data = struct.unpack("!" + (int(len(d) / 2) * "h"), d)
            data_offset = 1
            movement_offset = 0
            if self.movements and self.movements[0] not in self.MOVEMENTS:  # matching against initiating key
                movement_offset = 1
                if self.movements[0] != str(CONTROL[data[0]]):
                    return False
            for m in self.movements[movement_offset:]:
                if data_offset >= len(data):
                    return False
                if data[data_offset] == 0:
                    direction = xy_direction(data[data_offset + 1], data[data_offset + 2])
                    if m != direction:
                        return False
                    data_offset += 3
                elif data[data_offset] == 1:
                    if m != str(CONTROL[data[data_offset + 1]]):
                        return False
                    data_offset += 2
            return data_offset == len(data)
        return False

    def data(self):
        return {"MouseGesture": [str(m) for m in self.movements]}


class Active(Condition):
    def __init__(self, devID, warn=True):
        if not (isinstance(devID, str)):
            if warn:
                logger.warning("rule Active argument not a string: %s", devID)
            self.devID = ""
        self.devID = devID

    def __str__(self):
        return "Active: " + str(self.devID)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        dev = device.find(self.devID)
        return bool(dev and dev.ping())

    def data(self):
        return {"Active": self.devID}


class Device(Condition):
    def __init__(self, devID, warn=True):
        if not (isinstance(devID, str)):
            if warn:
                logger.warning("rule Device argument not a string: %s", devID)
            self.devID = ""
        self.devID = devID

    def __str__(self):
        return "Device: " + str(self.devID)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        return device.unitId == self.devID or device.serial == self.devID

    def data(self):
        return {"Device": self.devID}


class Host(Condition):
    def __init__(self, host, warn=True):
        if not (isinstance(host, str)):
            if warn:
                logger.warning("rule Host Name argument not a string: %s", host)
            self.host = ""
        self.host = host

    def __str__(self):
        return "Host: " + str(self.host)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("evaluate condition: %s", self)
        hostname = socket.getfqdn()
        return hostname.startswith(self.host)

    def data(self):
        return {"Host": self.host}


class Action(RuleComponent):
    def __init__(self, *args):
        pass

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        return None


def keysym_to_keycode(keysym, _modifiers) -> Tuple[int, int]:  # maybe should take shift into account
    """Reverse the keycode to keysym mapping.

    Warning:
    This is an attempt to reverse the keycode to keysym mappping in XKB.
    It may not be completely general.
    """
    group = kbdgroup() or 0
    keycodes = gkeymap.get_entries_for_keyval(keysym)
    (keycode, level) = (None, None)
    for k in keycodes.keys:  # mappings that have the correct group
        if group == k.group and k.keycode < 256 and (level is None or k.level < level):
            keycode = k.keycode
            level = k.level
    if keycode or group == 0:
        return keycode, level

    for k in keycodes.keys:  # mappings for group 0 where keycode only has group 0 mappings
        if 0 == k.group and k.keycode < 256 and (level is None or k.level < level):
            (a, m, vs) = gkeymap.get_entries_for_keycode(k.keycode)
            if a and all(mk.group == 0 for mk in m):
                keycode = k.keycode
                level = k.level
    return keycode, level


class KeyPress(Action):
    def __init__(self, args, warn=True):
        self.key_names, self.action = self.regularize_args(args)
        if not isinstance(self.key_names, list):
            if warn:
                logger.warning("rule KeyPress keys not key names %s", self.keys_names)
            self.key_symbols = []
        else:
            self.key_symbols = [XK_KEYS.get(k, None) for k in self.key_names]
        if not all(self.key_symbols):
            if warn:
                logger.warning("rule KeyPress keys not key names %s", self.key_names)
            self.key_symbols = []

    def regularize_args(self, args):
        action = CLICK
        if not isinstance(args, list):
            args = [args]
        keys = args
        if len(args) == 2 and args[1] in [CLICK, DEPRESS, RELEASE]:
            keys = [args[0]] if isinstance(args[0], str) else args[0]
            action = args[1]
        return keys, action

    def __str__(self):
        return "KeyPress: " + " ".join(self.key_names) + " " + self.action

    def needed(self, k, modifiers):
        code = modifier_code(k)
        return not (code is not None and modifiers & (1 << code))

    def mods(self, level, modifiers, direction):
        if level == 2 or level == 3:
            (sk, _) = keysym_to_keycode(XK_KEYS.get("ISO_Level3_Shift", None), modifiers)
            if sk and self.needed(sk, modifiers):
                simulate_key(sk, direction)
        if level == 1 or level == 3:
            (sk, _) = keysym_to_keycode(XK_KEYS.get("Shift_L", None), modifiers)
            if sk and self.needed(sk, modifiers):
                simulate_key(sk, direction)

    def keyDown(self, keysyms_, modifiers):
        for k in keysyms_:
            (keycode, level) = keysym_to_keycode(k, modifiers)
            if keycode is None:
                logger.warning("rule KeyPress key symbol not currently available %s", self)
            elif self.action != CLICK or self.needed(keycode, modifiers):  # only check needed when clicking
                self.mods(level, modifiers, _KEY_PRESS)
                simulate_key(keycode, _KEY_PRESS)

    def keyUp(self, keysyms_, modifiers):
        for k in keysyms_:
            (keycode, level) = keysym_to_keycode(k, modifiers)
            if keycode and (self.action != CLICK or self.needed(keycode, modifiers)):  # only check needed when clicking
                simulate_key(keycode, _KEY_RELEASE)
                self.mods(level, modifiers, _KEY_RELEASE)

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if gkeymap:
            current = gkeymap.get_modifier_state()
            if logger.isEnabledFor(logging.INFO):
                logger.info(
                    "KeyPress action: %s %s, group %s, modifiers %s",
                    self.key_names,
                    self.action,
                    kbdgroup(),
                    current,
                )
            if self.action != RELEASE:
                self.keyDown(self.key_symbols, current)
            if self.action != DEPRESS:
                self.keyUp(reversed(self.key_symbols), current)
            time.sleep(0.01)
        else:
            logger.warning("no keymap so cannot determine which keycode to send")
        return None

    def data(self):
        return {"KeyPress": [[str(k) for k in self.key_names], self.action]}


# KeyDown is dangerous as the key can auto-repeat and make your system unusable
# class KeyDown(KeyPress):
#    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
#        super().keyDown(self.keys, current_key_modifiers)
# class KeyUp(KeyPress):
#    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
#        super().keyUp(self.keys, current_key_modifiers)


class MouseScroll(Action):
    def __init__(self, amounts, warn=True):
        if len(amounts) == 1 and isinstance(amounts[0], list):
            amounts = amounts[0]
        if not (len(amounts) == 2 and all([isinstance(a, numbers.Number) for a in amounts])):
            if warn:
                logger.warning("rule MouseScroll argument not two numbers %s", amounts)
            amounts = [0, 0]
        self.amounts = amounts

    def __str__(self):
        return "MouseScroll: " + " ".join([str(a) for a in self.amounts])

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        amounts = self.amounts
        if isinstance(last_result, numbers.Number):
            amounts = [math.floor(last_result * a) for a in self.amounts]
        if logger.isEnabledFor(logging.INFO):
            logger.info("MouseScroll action: %s %s %s", self.amounts, last_result, amounts)
        dx, dy = amounts
        simulate_scroll(dx, dy)
        time.sleep(0.01)
        return None

    def data(self):
        return {"MouseScroll": self.amounts[:]}


class MouseClick(Action):
    def __init__(self, args, warn=True):
        if len(args) == 1 and isinstance(args[0], list):
            args = args[0]
        if not isinstance(args, list):
            args = [args]
        self.button = str(args[0]) if len(args) >= 0 else None
        if self.button not in buttons:
            if warn:
                logger.warning("rule MouseClick action: button %s not known", self.button)
            self.button = None
        count = args[1] if len(args) >= 2 else 1
        try:
            self.count = int(count)
        except (ValueError, TypeError):
            if count in [CLICK, DEPRESS, RELEASE]:
                self.count = count
            elif warn:
                logger.warning(
                    "rule MouseClick action: argument %s should be an integer or CLICK, PRESS, or RELEASE",
                    count,
                )
                self.count = 1

    def __str__(self):
        return f"MouseClick: {self.button} ({int(self.count)})"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.INFO):
            logger.info(f"MouseClick action: {int(self.count)} {self.button}")
        if self.button and self.count:
            click(buttons[self.button], self.count)
        time.sleep(0.01)
        return None

    def data(self):
        return {"MouseClick": [self.button, self.count]}


class Set(Action):
    def __init__(self, args, warn=True):
        if not (isinstance(args, list) and len(args) > 2):
            if warn:
                logger.warning("rule Set argument not list with minimum length 3: %s", args)
            self.args = []
        else:
            self.args = args

    def __str__(self):
        return "Set: " + " ".join([str(a) for a in self.args])

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if len(self.args) < 3:
            return None
        if logger.isEnabledFor(logging.INFO):
            logger.info("Set action: %s", self.args)
        dev = device.find(self.args[0]) if self.args[0] is not None else device
        if dev is None:
            logger.warning("Set action: device %s is not known", self.args[0])
            return None
        setting = next((s for s in dev.settings if s.name == self.args[1]), None)
        if setting is None:
            logger.warning("Set action: setting %s is not the name of a setting for %s", self.args[1], dev.name)
            return None
        args = setting.acceptable(self.args[2:], setting.read())
        if args is None:
            logger.warning(
                "Set Action: invalid args %s for setting %s of %s",
                self.args[2:],
                self.args[1],
                self.args[0],
            )
            return None
        if len(args) > 1:
            setting.write_key_value(args[0], args[1])
        else:
            setting.write(args[0])
        if device.setting_callback:
            device.setting_callback(device, type(setting), args)
        return None

    def data(self):
        return {"Set": self.args[:]}


class Execute(Action):
    def __init__(self, args, warn=True):
        if isinstance(args, str):
            args = [args]
        if not (isinstance(args, list) and all(isinstance(arg), str) for arg in args):
            if warn:
                logger.warning("rule Execute argument not list of strings: %s", args)
            self.args = []
        else:
            self.args = args

    def __str__(self):
        return "Execute: " + " ".join([a for a in self.args])

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if logger.isEnabledFor(logging.INFO):
            logger.info("Execute action: %s", self.args)
        subprocess.Popen(self.args)
        return None

    def data(self):
        return {"Execute": self.args[:]}


class Later(Action):
    def __init__(self, args, warn=True):
        self.delay = 0
        self.rule = Rule([])
        self.components = []
        if not (isinstance(args, list)):
            args = [args]
        if not (isinstance(args, list) and len(args) >= 1):
            if warn:
                logger.warning("rule Later argument not list with minimum length 1: %s", args)
        elif not (isinstance(args[0], (int, float))) or not 0.01 <= args[0] <= 100:
            if warn:
                logger.warning("rule Later delay not between 0.01 and 100: %s", args)
        else:
            self.delay = args[0]
            self.rule = Rule(args[1:], warn=warn)
            self.components = self.rule.components

    def __str__(self):
        return "Later: [" + str(self.delay) + ", " + ", ".join(str(c) for c in self.components) + "]"

    def evaluate(self, feature, notification: HIDPPNotification, device, last_result):
        if self.delay and self.rule:
            if self.delay >= 1:
                GLib.timeout_add_seconds(int(self.delay), Rule.once, self.rule, feature, notification, device, last_result)
            else:
                GLib.timeout_add(int(self.delay * 1000), Rule.once, self.rule, feature, notification, device, last_result)
        return None

    def data(self):
        data = [c.data() for c in self.components]
        data.insert(0, self.delay)
        return {"Later": data}


COMPONENTS = {
    "Rule": Rule,
    "Not": Not,
    "Or": Or,
    "And": And,
    "Process": Process,
    "MouseProcess": MouseProcess,
    "Feature": Feature,
    "Report": Report,
    "Setting": Setting,
    "Modifiers": Modifiers,
    "Key": Key,
    "KeyIsDown": KeyIsDown,
    "Test": Test,
    "TestBytes": TestBytes,
    "MouseGesture": MouseGesture,
    "Active": Active,
    "Device": Device,
    "Host": Host,
    "KeyPress": KeyPress,
    "MouseScroll": MouseScroll,
    "MouseClick": MouseClick,
    "Set": Set,
    "Execute": Execute,
    "Later": Later,
}


built_in_rules = Rule(
    [
        {
            "Rule": [  # Implement problematic keys for Craft and MX Master
                {"Rule": [{"Key": ["Brightness Down", "pressed"]}, {"KeyPress": "XF86_MonBrightnessDown"}]},
                {"Rule": [{"Key": ["Brightness Up", "pressed"]}, {"KeyPress": "XF86_MonBrightnessUp"}]},
            ]
        },
    ]
)


def key_is_down(key: NamedInt) -> bool:
    """Checks if given key is pressed or not."""
    if key == CONTROL.MR:
        return mr_key_down
    elif CONTROL.M1 <= key <= CONTROL.M8:
        return bool(m_keys_down & (0x01 << (key - CONTROL.M1)))
    elif CONTROL.G1 <= key <= CONTROL.G32:
        return bool(g_keys_down & (0x01 << (key - CONTROL.G1)))
    return key in keys_down


def evaluate_rules(feature, notification: HIDPPNotification, device):
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("evaluating rules on %s", notification)
    rules.evaluate(feature, notification, device, True)


def process_notification(device, notification: HIDPPNotification, feature) -> None:
    """Processes HID++ notifications."""
    global keys_down, g_keys_down, m_keys_down, mr_key_down, key_down, key_up, thumb_wheel_displacement
    key_down, key_up = None, None
    # need to keep track of keys that are down to find a new key down
    if notification.address == 0x00:
        if feature == SupportedFeature.REPROG_CONTROLS_V4:
            new_keys_down = struct.unpack("!4H", notification.data[:8])
            for key in new_keys_down:
                if key and key not in keys_down:
                    key_down = key
            for key in keys_down:
                if key and key not in new_keys_down:
                    key_up = key
            keys_down = new_keys_down
        # and also G keys down
        elif feature == SupportedFeature.GKEY:
            new_g_keys_down = struct.unpack("<I", notification.data[:4])[0]
            for i in range(32):
                if new_g_keys_down & (0x01 << i) and not g_keys_down & (0x01 << i):
                    key_down = CONTROL["G" + str(i + 1)]
                if g_keys_down & (0x01 << i) and not new_g_keys_down & (0x01 << i):
                    key_up = CONTROL["G" + str(i + 1)]
            g_keys_down = new_g_keys_down
        # and also M keys down
        elif feature == SupportedFeature.MKEYS:
            new_m_keys_down = struct.unpack("!1B", notification.data[:1])[0]
            for i in range(1, 9):
                if new_m_keys_down & (0x01 << (i - 1)) and not m_keys_down & (0x01 << (i - 1)):
                    key_down = CONTROL["M" + str(i)]
                if m_keys_down & (0x01 << (i - 1)) and not new_m_keys_down & (0x01 << (i - 1)):
                    key_up = CONTROL["M" + str(i)]
            m_keys_down = new_m_keys_down
        # and also MR key
        elif feature == SupportedFeature.MR:
            new_mr_key_down = struct.unpack("!1B", notification.data[:1])[0]
            if not mr_key_down and new_mr_key_down:
                key_down = CONTROL["MR"]
            if mr_key_down and not new_mr_key_down:
                key_up = CONTROL["MR"]
            mr_key_down = new_mr_key_down
        # keep track of thumb wheel movement
        elif feature == SupportedFeature.THUMB_WHEEL:
            if notification.data[4] <= 0x01:  # when wheel starts, zero out last movement
                thumb_wheel_displacement = 0
            thumb_wheel_displacement += signed(notification.data[0:2])

    GLib.idle_add(evaluate_rules, feature, notification, device)


_XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser(os.path.join("~", ".config"))
_file_path = os.path.join(_XDG_CONFIG_HOME, "solaar", "rules.yaml")

rules = built_in_rules


def _save_config_rule_file(file_name: str = _file_path):
    # This is a trick to show str/float/int lists in-line (inspired by https://stackoverflow.com/a/14001707)
    class inline_list(list):
        pass

    def blockseq_rep(dumper, data):
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)

    yaml.add_representer(inline_list, blockseq_rep)

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
        "encoding": "utf-8",
        "explicit_start": True,
        "explicit_end": True,
        "default_flow_style": False,
        # 'version': (1, 3),  # it would be printed for every rule
    }
    # Save only user-defined rules
    rules_to_save = sum((r.data()["Rule"] for r in rules.components if r.source == file_name), [])
    if logger.isEnabledFor(logging.INFO):
        logger.info("saving %d rule(s) to %s", len(rules_to_save), file_name)
    try:
        with open(file_name, "w") as f:
            if rules_to_save:
                f.write("%YAML 1.3\n")  # Write version manually
            dump_data = [r["Rule"] for r in rules_to_save]
            yaml.dump_all(convert(dump_data), f, **dump_settings)
    except Exception as e:
        logger.error("failed to save to %s\n%s", file_name, e)
        return False
    return True


def load_config_rule_file():
    """Loads user configured rules."""
    global rules

    if os.path.isfile(_file_path):
        rules = _load_rule_config(_file_path)


def _load_rule_config(file_path: str) -> Rule:
    loaded_rules = []
    try:
        with open(file_path) as config_file:
            loaded_rules = []
            for loaded_rule in yaml.safe_load_all(config_file):
                rule = Rule(loaded_rule, source=file_path)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("load rule: %s", rule)
                loaded_rules.append(rule)
            if logger.isEnabledFor(logging.INFO):
                logger.info("loaded %d rules from %s", len(loaded_rules), config_file.name)
    except Exception as e:
        logger.error("failed to load from %s\n%s", file_path, e)
    return Rule([Rule(loaded_rules, source=file_path), built_in_rules])


load_config_rule_file()
