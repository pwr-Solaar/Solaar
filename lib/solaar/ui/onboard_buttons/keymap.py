## Copyright (C) 2026  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""Translate a chosen or captured key into a Solaar onboard-profile Button.

Onboard profiles store button assignments as USB HID usage codes
(``logitech_receiver.special_keys.USB_HID_KEYCODES``), the same table used
for HID++ diversion rules. There are two ways the dialog lets someone pick
one:

- ``capture()`` resolves a live GDK key event (a physical keypress) to a
  Button. GDK key events carry an X11 keysym (``keyval``), so this needs a
  keyval -> HID usage translation; there's no existing table for the
  specific subset of keys HID++ onboard profiles can express, so this
  module hand-maps the keys people actually rebind: letters, digits, the
  function row including F13-F24, the numpad (both NumLock-on and
  NumLock-off keyvals, since we can't assume the live NumLock state while
  capturing), navigation and editing keys, and the standard modifiers.
  Anything not in the resulting table (dead keys, IME composition keys,
  media keys not in the consumer-key table, ...) is reported as unsupported
  rather than silently mapped to something wrong.
- ``available_keys()`` + ``manual_button()`` instead let someone pick a key
  by name from a list and choose modifiers with checkboxes -- for keys that
  can be captured just fine in principle but that this particular keyboard
  can't physically send (the numpad on a keyboard with no numpad block is
  the case that motivated this: capture cannot solve that, no matter how
  complete the keyval table is, so a name-based picker is the only way in).

The same list also offers a curated set of Consumer-Control keys (browser
back/forward, volume, play/pause, ...) via ``manual_consumer_button()``.
These are a genuinely different Button wire type (behavior SEND, type
CONSUMER_KEY, a 2-byte usage code with no modifiers byte -- see
``hidpp20.Button.to_bytes``), not a keyboard key at all. USB_HID_KEYCODES
does contain a set of "MEDIA_*" entries (MEDIA_BACK, MEDIA_VOLUMEUP, ...)
at codes 0xE8 and up, but those are officially-reserved slots on the real
Keyboard/Keypad usage page (which Solaar's own docs use 0x00-0xE7 for) that
Linux's HID driver happens to special-case for some vendor keyboards --
sending them as a plain MODIFIER_AND_KEY value byte is not part of the USB
HID spec and many systems and compositors don't recognize it (this is why
Browser Back/Forward chosen from an earlier version of this picker did
nothing). The curated list below offers the real Consumer-Control
equivalents instead, which is the standard, portable way to send these.

A third group offers mouse-click assignments (Left/Right/Middle Click,
Back, Forward) via ``manual_mouse_button()`` -- another distinct Button
wire type (behavior SEND, type BUTTON, a 2-byte code from
``special_keys.MOUSE_BUTTONS``, also with no modifiers byte). This is what
lets someone put a Left Click back on a button after moving it elsewhere,
or add a second button that also sends Left Click -- see ``is_left_click()``,
which the dialog uses to warn before a change would leave no button at all
sending Left Click, since every onboard-profile button slot can hold any
assignment (there's no protocol rule that slot 0/1/2 has to stay
left/right/middle -- that's just each device's factory default).
"""

from __future__ import annotations

from dataclasses import dataclass

import gi

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk  # NOQA: E402
from logitech_receiver import hidpp20  # NOQA: E402
from logitech_receiver import special_keys  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

# GDK keyval -> USB HID usage code (logitech_receiver.special_keys.USB_HID_KEYCODES).
_KEYVAL_TO_HID: dict[int, int] = {}

_HID_NAME_TO_CODE: dict[str, int] = {str(k): int(k) for k in special_keys.USB_HID_KEYCODES}

# The real USB HID Keyboard/Keypad usage page ends at 0xE7 (Right GUI/Meta).
# special_keys.USB_HID_KEYCODES also carries a "MEDIA_*" block above that
# (0xE8-0xFB: MEDIA_BACK, MEDIA_VOLUMEUP, ...) which reuses officially-
# reserved usage IDs for vendor multimedia keys -- not part of the spec, and
# not reliably recognized as a MODIFIER_AND_KEY value byte (see module
# docstring). Exclude that range from the keyboard-key list; the curated
# Consumer-Control list below offers a working equivalent for the ones that
# matter (back/forward, volume, play/pause, ...).
_LAST_STANDARD_KEYBOARD_USAGE = 0xE7

# Named keys within the standard range that still don't belong in the
# picker: Japanese/Korean IME and layout-specific keys (essentially never
# useful on a mouse button, and confusing clutter for anyone else); legacy
# "phantom" application keys that essentially no physical keyboard
# implements and that Consumer-Control's AC_* keys already cover more
# portably; the keyboard-page volume/mute keys, now redundant with their
# Consumer-Control equivalents above (which is the more common way these
# are actually implemented); and ordinary punctuation, which is rarely what
# anyone wants a mouse button to type and was crowding out the keys people
# actually reach for.
_EXCLUDED_KEY_NAMES = frozenset(
    {
        # Japanese / Korean IME and layout-specific keys
        "102ND",
        "HANGEUL",
        "HANJA",
        "HIRAGANA",
        "HENKAN",
        "KATAKANA",
        "KATAKANAHIRAGANA",
        "MUHENKAN",
        "RO",
        "YEN",
        "ZENKAKUHANKAKU",
        "KPJPCOMMA",
        # Legacy "phantom" application keys
        "AGAIN",
        "COPY",
        "CUT",
        "PASTE",
        "UNDO",
        "FIND",
        "HELP",
        "OPEN",
        "PROPS",
        "FRONT",
        "STOP",
        "POWER",
        "COMPOSE",
        "SYSRQ",
        "No Output",
        # Keyboard-page volume/mute (see Consumer-Control group instead)
        "MUTE",
        "VOLUMEUP",
        "VOLUMEDOWN",
        # Ordinary punctuation
        "GRAVE",
        "MINUS",
        "EQUAL",
        "SEMICOLON",
        "APOSTROPHE",
        "COMMA",
        "DOT",
        "SLASH",
        "BACKSLASH",
        "LEFTBRACE",
        "RIGHTBRACE",
        "HASHTILDE",
    }
)

# A hand-picked subset of HID_CONSUMERCODES worth offering in the picker --
# that table has ~330 entries (mostly obscure "Application Control" commands
# like AC_Distribute_Horizontally) and dumping all of them in would bury the
# keys people actually want. Each maps a friendly label to its
# special_keys.HID_CONSUMERCODES attribute name -- NamedInts supports
# indexing by that attribute-style name directly (special_keys.
# HID_CONSUMERCODES["AC_Back"]), which is a different, underscored spelling
# from str(the NamedInt) ("AC Back") used for display and for _HID_NAME_TO_
# CODE above. Order is deliberate (browser keys, then media transport, then
# misc) rather than alphabetical, since this list is short enough to just
# read top to bottom.
_CURATED_CONSUMER_KEYS: dict[str, str] = {
    "Browser Back": "AC_Back",
    "Browser Forward": "AC_Forward",
    "Browser Refresh": "AC_Refresh",
    "Browser Stop": "AC_Stop",
    "Browser Home": "AC_Home",
    "Browser Search": "AC_Find",
    "Launch Browser": "AL_Internet_Browser",
    "Launch Calculator": "AL_Calculator",
    "Play/Pause": "Play__Pause",
    "Stop": "Stop",
    "Previous Track": "Scan_Previous_Track",
    "Next Track": "Scan_Next_Track",
    "Eject": "Eject",
    "Volume Up": "Volume_Up",
    "Volume Down": "Volume_Down",
    "Mute": "Mute",
    "Sleep": "Sleep",
    "Lock Screen": "AL_Terminal_Lock__Screensaver",
    "Scroll Up": "AC_Scroll_Up",
    "Scroll Down": "AC_Scroll_Down",
}

_CONSUMER_CODE_TO_LABEL: dict[int, str] = {
    int(special_keys.HID_CONSUMERCODES[attr]): label for label, attr in _CURATED_CONSUMER_KEYS.items()
}

# Mouse-click assignments -- a third Button wire type alongside keyboard
# keys and Consumer-Control keys (see module docstring). special_keys.
# MOUSE_BUTTONS is a bitmask table (Mouse_Button_Left=0x0001, _Right=0x0002,
# _Middle=0x0004, ...); only the handful someone would actually want to put
# on a button are offered here, in the order people expect to see them.
_CURATED_MOUSE_BUTTONS: dict[str, str] = {
    "Left Click": "Mouse_Button_Left",
    "Right Click": "Mouse_Button_Right",
    "Middle Click": "Mouse_Button_Middle",
    "Mouse Back": "Mouse_Button_Back",
    "Mouse Forward": "Mouse_Button_Forward",
}

_MOUSE_CODE_TO_LABEL: dict[int, str] = {
    int(special_keys.MOUSE_BUTTONS[attr]): label for label, attr in _CURATED_MOUSE_BUTTONS.items()
}

_LEFT_CLICK_CODE: int = int(special_keys.MOUSE_BUTTONS["Mouse_Button_Left"])


def _map_name(gdk_attr: str, hid_name: str) -> None:
    keyval = getattr(Gdk, gdk_attr, None)
    hid_code = _HID_NAME_TO_CODE.get(hid_name)
    if keyval is not None and hid_code is not None:
        _KEYVAL_TO_HID[keyval] = hid_code


for _letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _map_name(f"KEY_{_letter.lower()}", _letter)

# The top-row digit keys: HID usage codes 0x1E-0x27 (1,2,...,9,0). Only 0x1E/0x1F
# are given string names ("1"/"2") in special_keys.py; the rest resolve by raw code.
_DIGIT_HID_CODE = {
    "1": 0x1E,
    "2": 0x1F,
    "3": 0x20,
    "4": 0x21,
    "5": 0x22,
    "6": 0x23,
    "7": 0x24,
    "8": 0x25,
    "9": 0x26,
    "0": 0x27,
}
for _digit, _code in _DIGIT_HID_CODE.items():
    _keyval = getattr(Gdk, f"KEY_{_digit}", None)
    if _keyval is not None:
        _KEYVAL_TO_HID[_keyval] = _code

for _n in range(1, 25):  # F1..F24
    _map_name(f"KEY_F{_n}", f"F{_n}")

_NAMED_KEYS = {
    "KEY_Return": "ENTER",
    "KEY_Escape": "ESC",
    "KEY_BackSpace": "BACKSPACE",
    "KEY_Tab": "TAB",
    "KEY_space": "SPACE",
    "KEY_Caps_Lock": "CAPSLOCK",
    "KEY_Insert": "INSERT",
    "KEY_Delete": "DELETE",
    "KEY_Home": "HOME",
    "KEY_End": "END",
    "KEY_Page_Up": "PAGEUP",
    "KEY_Page_Down": "PAGEDOWN",
    "KEY_Up": "UP",
    "KEY_Down": "DOWN",
    "KEY_Left": "LEFT",
    "KEY_Right": "RIGHT",
    "KEY_Num_Lock": "NUMLOCK",
    "KEY_Scroll_Lock": "SCROLLLOCK",
    "KEY_Pause": "PAUSE",
    "KEY_Menu": "COMPOSE",
    "KEY_KP_Divide": "KPSLASH",
    "KEY_KP_Multiply": "KPASTERISK",
    "KEY_KP_Subtract": "KPMINUS",
    "KEY_KP_Add": "KPPLUS",
    "KEY_KP_Enter": "KPENTER",
    "KEY_KP_Decimal": "KPDOT",
    "KEY_KP_Equal": "KPEQUAL",
}
for _attr, _hid_name in _NAMED_KEYS.items():
    _map_name(_attr, _hid_name)

# Numpad digits: GDK reports a "KP_1".."KP_9"/"KP_0" keyval with NumLock on, and a
# navigation-key keyval (KP_End, KP_Down, ...) with NumLock off for the same physical
# key. Map both spellings to the same HID keypad code so capture works either way.
_KP_DIGIT_ALIASES = {
    "0": ("KP_0", "KP_Insert"),
    "1": ("KP_1", "KP_End"),
    "2": ("KP_2", "KP_Down"),
    "3": ("KP_3", "KP_Page_Down"),
    "4": ("KP_4", "KP_Left"),
    "5": ("KP_5", "KP_Begin"),
    "6": ("KP_6", "KP_Right"),
    "7": ("KP_7", "KP_Home"),
    "8": ("KP_8", "KP_Up"),
    "9": ("KP_9", "KP_Page_Up"),
}
_KP_HID_NAME = {d: f"KP{d}" for d in _KP_DIGIT_ALIASES}
for _digit, _attrs in _KP_DIGIT_ALIASES.items():
    for _attr in _attrs:
        _map_name(f"KEY_{_attr}", _KP_HID_NAME[_digit])

# GDK modifier bits -> the modifier byte Button/hidpp20 expects
# (Ctrl=0x01, Shift=0x02, Alt=0x04, Meta/Super=0x08 -- see special_keys.modifiers).
_MODIFIER_BITS = (
    (Gdk.ModifierType.CONTROL_MASK, 0x01),
    (Gdk.ModifierType.SHIFT_MASK, 0x02),
    (Gdk.ModifierType.MOD1_MASK, 0x04),  # Alt
    (Gdk.ModifierType.SUPER_MASK, 0x08),  # Meta / Super / Windows key
)


@dataclass(frozen=True)
class CapturedKey:
    """A resolved key capture, ready to become an onboard-profile Button."""

    hid_code: int
    modifiers: int
    display_name: str


def capture(keyval: int, state) -> CapturedKey | None:
    """Resolve a GDK (keyval, modifier state) pair to a CapturedKey.

    Returns None if the key isn't one onboard profiles can express (see
    module docstring) -- the caller should ask for a different key rather
    than silently discarding the press.
    """
    hid_code = _KEYVAL_TO_HID.get(keyval)
    if hid_code is None:
        return None
    modifiers = 0
    for bit, value in _MODIFIER_BITS:
        if state & bit:
            modifiers |= value
    key_name = Gdk.keyval_name(keyval) or str(hid_code)
    return CapturedKey(hid_code=hid_code, modifiers=modifiers, display_name=_format_display(key_name, modifiers))


# Composed bit-by-bit rather than looked up in special_keys.modifiers, which only
# spells out 11 of the 16 possible combinations (e.g. Ctrl+Alt+Shift together is
# missing there) -- a modifier byte is a bitmask, so build the label the same way.
_MODIFIER_PREFIX_BITS = (
    (0x01, "Cntrl+"),
    (0x02, "Shift+"),
    (0x04, "Alt+"),
    (0x08, "Meta+"),
)


def _format_display(key_name: str, modifiers: int) -> str:
    prefix = "".join(label for bit, label in _MODIFIER_PREFIX_BITS if modifiers & bit)
    return f"{prefix}{key_name}"


def to_button(captured: CapturedKey) -> hidpp20.Button:
    """Build the onboard-profile Button entry for a captured key."""
    return manual_button(captured.hid_code, captured.modifiers)


def manual_button(hid_code: int, modifiers: int = 0) -> hidpp20.Button:
    """Build the onboard-profile Button entry for an explicitly chosen key.

    Same shape as ``to_button()`` (SEND / MODIFIER_AND_KEY) -- this is the
    "choose from a list" path's counterpart to a physical-key capture.
    """
    return hidpp20.Button(
        behavior=int(hidpp20.ButtonBehavior.SEND),
        type=int(hidpp20.ButtonMappingType.MODIFIER_AND_KEY),
        modifiers=modifiers,
        value=hid_code,
    )


def manual_consumer_button(usage_code: int) -> hidpp20.Button:
    """Build the onboard-profile Button entry for a Consumer-Control key
    chosen from the list (browser back/forward, volume, play/pause, ...).

    A different wire shape from manual_button(): SEND / CONSUMER_KEY, a
    2-byte usage code with no modifiers byte at all (see
    hidpp20.Button.to_bytes) -- "Ctrl+Volume Up" isn't a thing this Button
    type can express, unlike a keyboard key.
    """
    return hidpp20.Button(
        behavior=int(hidpp20.ButtonBehavior.SEND),
        type=int(hidpp20.ButtonMappingType.CONSUMER_KEY),
        value=usage_code,
    )


def manual_mouse_button(code: int) -> hidpp20.Button:
    """Build the onboard-profile Button entry for a mouse-click assignment
    chosen from the list (Left/Right/Middle Click, Back, Forward, ...).

    A third distinct wire shape: SEND / BUTTON, a 2-byte code from
    special_keys.MOUSE_BUTTONS with no modifiers byte, same as
    manual_consumer_button()'s shape but a different code space.
    """
    return hidpp20.Button(
        behavior=int(hidpp20.ButtonBehavior.SEND),
        type=int(hidpp20.ButtonMappingType.BUTTON),
        value=code,
    )


# Standalone modifier keys, in the order the picker should list them (Ctrl,
# then Shift, then Alt, then the Windows/Meta key -- left before right within
# each pair). USB_HID_KEYCODES spells the Windows key two different ways
# depending on side (LEFTWINDOWS / RIGHTMETA) -- both are listed here as-is.
_MODIFIER_KEY_ORDER = (
    "LEFTCTRL",
    "RIGHTCTRL",
    "LEFTSHIFT",
    "RIGHTSHIFT",
    "LEFTALT",
    "RIGHTALT",
    "LEFTWINDOWS",
    "RIGHTMETA",
)

# The top-row digits in the order people actually read them off a keyboard
# (1,2,...,9,0), used to group and order _DIGIT_HID_CODE entries below.
_DIGIT_ORDER = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")


def _sort_group(item: tuple[str, int]) -> tuple[int, object]:
    """Grouping key for available_keys(): letters, then top-row digits, then
    the numpad digits, then the standalone modifier keys, then F-keys, then
    everything else (navigation, editing, media, ...) alphabetically -- the
    order the user asked for rather than a plain alphabetical dump."""
    name, _hid_code = item
    if len(name) == 1 and name.isalpha():
        return (0, name)
    if name in _DIGIT_ORDER:
        return (1, _DIGIT_ORDER.index(name))
    if name.startswith("KP") and name[2:].isdigit():
        return (2, int(name[2:]))
    if name in _MODIFIER_KEY_ORDER:
        return (3, _MODIFIER_KEY_ORDER.index(name))
    if name.startswith("F") and name[1:].isdigit():
        return (4, int(name[1:]))
    return (5, name)


def available_keys() -> list[tuple[str, int, str]]:
    """(display name, code, kind) triples the manual picker can offer.

    ``kind`` is ``"mouse"`` for a mouse-click code -- build its Button with
    manual_mouse_button() --, ``"key"`` for a keyboard usage code -- build
    its Button with manual_button() --, or ``"consumer"`` for a
    Consumer-Control usage code -- build its Button with
    manual_consumer_button() instead, since each is a different wire shape
    (see each function's docstring). The three are never the same code
    space, so a caller can't mix them up by accident.

    The mouse-click group (Left/Right/Middle Click, Back, Forward) comes
    first -- this editor is for mouse buttons, and "put Left Click back on
    this button" is the single most important thing it needs to make easy
    (see is_left_click() and the module docstring). Then the keyboard-key
    group, which merges Solaar's named USB_HID_KEYCODES table (excluding
    the non-standard "MEDIA_*" block -- see _LAST_STANDARD_KEYBOARD_USAGE --
    and the IME/legacy/punctuation clutter in _EXCLUDED_KEY_NAMES) with the
    top-row digit codes 3-9 and 0, which that table leaves unnamed (only "1"
    and "2" are named upstream -- see _DIGIT_HID_CODE above); everything
    else capture can reach (letters, F-keys, numpad, navigation, ...) is
    already named there and needs no patching in, and is grouped for
    readability rather than sorted alphabetically (see _sort_group). The
    curated Consumer-Control keys trail as the last group.
    """
    mouse = [(label, int(special_keys.MOUSE_BUTTONS[attr]), "mouse") for label, attr in _CURATED_MOUSE_BUTTONS.items()]
    combined = dict(_HID_NAME_TO_CODE)
    for _digit, _code in _DIGIT_HID_CODE.items():
        combined.setdefault(_digit, _code)
    combined = {
        name: code
        for name, code in combined.items()
        if code <= _LAST_STANDARD_KEYBOARD_USAGE and name not in _EXCLUDED_KEY_NAMES
    }
    keys = [(name, code, "key") for name, code in sorted(combined.items(), key=_sort_group)]
    consumer = [
        (label, int(special_keys.HID_CONSUMERCODES[attr]), "consumer") for label, attr in _CURATED_CONSUMER_KEYS.items()
    ]
    return mouse + keys + consumer


def unassigned_button() -> hidpp20.Button:
    """The device's native "no action" marker (behavior 15, raw 0xFFFFFFFF)."""
    return hidpp20.Button(behavior=15, bytes=b"\xff\xff\xff\xff")


def key_and_modifiers(button: hidpp20.Button | None) -> tuple[int | None, int]:
    """The (hid_code, modifiers) a Button holds, if it's a plain key mapping.

    Returns (None, 0) for anything else (unassigned, mouse buttons, consumer
    keys, device functions) -- the single place that decides what counts as
    "a plain key mapping" for this editor, shared by describe() and the
    dialog's "choose from a list" picker so they can't disagree.
    """
    behavior = getattr(button, "behavior", None) if button is not None else None
    is_key_send = behavior == int(hidpp20.ButtonBehavior.SEND)
    is_key_send = is_key_send and getattr(button, "type", None) == int(hidpp20.ButtonMappingType.MODIFIER_AND_KEY)
    if not is_key_send:
        return None, 0
    return getattr(button, "value", None), getattr(button, "modifiers", 0) or 0


def consumer_code(button: hidpp20.Button | None) -> int | None:
    """The Consumer-Control usage code a Button holds, if it's a
    Consumer-Control key mapping (see manual_consumer_button()) -- the
    counterpart to key_and_modifiers() for this Button type, shared by
    describe() and the dialog's "choose from a list" picker.
    """
    behavior = getattr(button, "behavior", None) if button is not None else None
    if behavior != int(hidpp20.ButtonBehavior.SEND):
        return None
    if getattr(button, "type", None) != int(hidpp20.ButtonMappingType.CONSUMER_KEY):
        return None
    return getattr(button, "value", None)


def mouse_button_code(button: hidpp20.Button | None) -> int | None:
    """The special_keys.MOUSE_BUTTONS code a Button holds, if it's a
    mouse-click mapping (see manual_mouse_button()) -- the third
    counterpart to key_and_modifiers()/consumer_code(), shared by
    describe(), is_left_click(), and the dialog's picker.
    """
    behavior = getattr(button, "behavior", None) if button is not None else None
    if behavior != int(hidpp20.ButtonBehavior.SEND):
        return None
    if getattr(button, "type", None) != int(hidpp20.ButtonMappingType.BUTTON):
        return None
    return getattr(button, "value", None)


def is_left_click(button: hidpp20.Button | None) -> bool:
    """Whether a Button is specifically a Left Click mouse-button mapping.

    Used by the dialog to warn before a change would leave no button
    anywhere sending Left Click -- there's no protocol rule that any
    particular button slot has to be Left Click, so the only reliable check
    is scanning actual assignments rather than trusting a slot index.
    """
    return mouse_button_code(button) == _LEFT_CLICK_CODE


def describe(button: hidpp20.Button | None) -> str:
    """Human-readable summary of a button's current assignment, for its row label."""
    behavior = getattr(button, "behavior", None) if button is not None else None
    if behavior is None or behavior == 15:
        return _("(unassigned)")
    hid_code, modifiers = key_and_modifiers(button)
    if hid_code is not None:
        if hid_code in special_keys.USB_HID_KEYCODES:
            key_name = str(special_keys.USB_HID_KEYCODES[hid_code])
        else:
            key_name = str(hid_code)
        return _format_display(key_name, modifiers)
    usage_code = consumer_code(button)
    if usage_code is not None:
        if usage_code in _CONSUMER_CODE_TO_LABEL:
            return _CONSUMER_CODE_TO_LABEL[usage_code]
        if usage_code in special_keys.HID_CONSUMERCODES:
            return str(special_keys.HID_CONSUMERCODES[usage_code])
        return str(usage_code)
    mouse_code = mouse_button_code(button)
    if mouse_code is not None:
        if mouse_code in _MOUSE_CODE_TO_LABEL:
            return _MOUSE_CODE_TO_LABEL[mouse_code]
        if mouse_code in special_keys.MOUSE_BUTTONS:
            return str(special_keys.MOUSE_BUTTONS[mouse_code])
        return str(mouse_code)
    # Device functions (DPI cycle, profile switch, G-Shift, ...) and macros
    # are out of scope for this editor (v1) -- show that something is set
    # without offering to edit it.
    return _("(set via CLI -- not a plain key mapping)")
