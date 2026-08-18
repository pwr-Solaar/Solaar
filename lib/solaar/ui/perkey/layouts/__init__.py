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

"""Registry of per-key layouts, keyed by feature + a device-class match.

Layouts register themselves with a matcher callable. `layout_for(feature, hint)`
returns the first matching layout, or None when no model-specific layout is
known — in which case the editor renders a flat strip of all reported zones.
"""

from __future__ import annotations

from collections.abc import Callable

from ..layout import Layout
from . import headset_g522
from . import keyboard_ansi
from . import keyboard_g512
from . import keyboard_g810_family
from . import keyboard_iso_azerty
from . import keyboard_iso_qwerty
from . import keyboard_iso_qwertz
from . import keyboard_jis
from . import keyboard_pro_x_rapid
from . import mouse_g502x

# (feature_id, matcher, layout). Matcher receives a `hint` dict the editor
# assembles from the device (kind, wpid, codename, name, zones list, etc.).
_REGISTRY: list[tuple[int, Callable[[dict], bool], Layout]] = []


def register_layout(feature: int, matcher: Callable[[dict], bool], layout: Layout) -> None:
    _REGISTRY.append((feature, matcher, layout))


def layout_for(feature: int, hint: dict) -> Layout | None:
    for f, match, layout in _REGISTRY:
        if f == feature and match(hint):
            return layout
    return None


def _name_contains(*needles: str) -> Callable[[dict], bool]:
    """Build a matcher that returns True if any needle is a substring of the
    device's name or codename (case-insensitive). Useful for device-family
    layouts where multiple wpids share an LED arrangement.
    """
    folded = tuple(n.upper() for n in needles)

    def match(hint: dict) -> bool:
        for field in ("codename", "name"):
            value = hint.get(field)
            if not value:
                continue
            up = str(value).upper()
            if any(n in up for n in folded):
                return True
        return False

    return match


# --- Keyboard region routing ---
# Country code → layout family. Codes from HID++ feature 0x4540 KeyboardLayout.
# These are Logitech-private codes taken from the official application's layout
# enum — NOT USB HID HUT country codes (an earlier version of this table assumed
# HUT semantics and routed German boards to AZERTY). 0x38 = Brazilian ABNT2 is
# hardware-confirmed on a G512 ABNT2. Codes absent here fall back to ANSI.
_KEYBOARD_FAMILY_BY_COUNTRY: dict[int, str] = {
    0x01: "ansi",  # US
    # ANSI-framed regional boards (local legends on a US frame)
    0x09: "ansi",  # Korean
    0x0B: "ansi",  # Chinese
    0x3E: "ansi",  # Korean
    # ISO QWERTY (UK/ES/IT/PT/BE... same shape, different keycap legends)
    0x02: "iso_qwerty",  # International
    0x03: "iso_qwerty",  # UK
    0x07: "iso_qwerty",  # Russian
    0x08: "iso_qwerty",  # Nordic
    0x0E: "iso_qwerty",  # Turkish
    0x0F: "iso_qwerty",  # Spanish
    0x10: "iso_qwerty",  # Arabic
    0x16: "iso_qwerty",  # Nordic
    0x1A: "iso_qwerty",  # Italian
    0x1D: "iso_qwerty",  # Nordic
    0x1F: "iso_qwerty",  # Portuguese
    0x21: "iso_qwerty",  # Nordic
    0x24: "iso_qwerty",  # Turkish
    0x28: "iso_qwerty",  # Bulgarian
    0x37: "iso_qwerty",  # International 2
    0x3A: "iso_qwerty",  # Arabic
    # ABNT2 is ISO-framed with an extra slash key; ISO QWERTY is the closest
    # canvas we have (dedicated ABNT2 layout is a possible follow-up).
    0x38: "iso_qwerty",  # Brazilian (ABNT2)
    # ISO QWERTZ
    0x04: "iso_qwertz",  # German
    0x0D: "iso_qwertz",  # Swiss
    0x14: "iso_qwertz",  # Czech
    0x19: "iso_qwertz",  # Hungarian
    0x41: "iso_qwertz",  # Czech
    # ISO AZERTY
    0x05: "iso_azerty",  # French
    0x11: "iso_azerty",  # Belgian
    # JIS
    0x0A: "jis",  # Japanese
}

_FAMILY_LAYOUTS = {
    "ansi": (keyboard_ansi.LAYOUT_FULL, keyboard_ansi.LAYOUT_TKL),
    "iso_qwerty": (keyboard_iso_qwerty.LAYOUT_FULL, keyboard_iso_qwerty.LAYOUT_TKL),
    "iso_qwertz": (keyboard_iso_qwertz.LAYOUT_FULL, keyboard_iso_qwertz.LAYOUT_TKL),
    "iso_azerty": (keyboard_iso_azerty.LAYOUT_FULL, keyboard_iso_azerty.LAYOUT_TKL),
    "jis": (keyboard_jis.LAYOUT_FULL, keyboard_jis.LAYOUT_TKL),
}


def _has_numpad(hint: dict) -> bool:
    """Numpad presence is read from the device's reported zone bitmap rather
    than counting zones — G515 reports phantom zones (47, 97, 99-103, 254)
    that diverge from the keycap count.
    """
    zones = set(hint.get("zones", ()))
    return 80 in zones or 95 in zones


def _keyboard_family(hint: dict) -> str:
    """Pick a layout family from the device's HID++ keyboard layout country
    code. Defaults to "ansi" when the code is missing or unknown.
    """
    code = hint.get("keyboard_layout")
    if code is None:
        return "ansi"
    return _KEYBOARD_FAMILY_BY_COUNTRY.get(int(code), "ansi")


def _keyboard_matcher(family: str, full_size: bool) -> Callable[[dict], bool]:
    def match(hint: dict) -> bool:
        if hint.get("kind") != "keyboard":
            return False
        if _has_numpad(hint) != full_size:
            return False
        return _keyboard_family(hint) == family

    return match


def _pro_x_rapid_matcher(family: str) -> Callable[[dict], bool]:
    """Match the PRO X RAPID (reported as "PRO X RAPID", TKL) for one region.
    Same country-code family routing as the generic keyboards; only the media
    top row differs."""
    named = _name_contains("PRO X RAPID")

    def match(hint: dict) -> bool:
        if hint.get("kind") != "keyboard":
            return False
        if not named(hint):
            return False
        if _has_numpad(hint):  # PRO X RAPID is TKL
            return False
        return _keyboard_family(hint) == family

    return match


# PRO X RAPID — regional generated base + a customized media top row.
# Registered ahead of the generic family matchers so it wins for this model.
for _family, (_full, _tkl) in _FAMILY_LAYOUTS.items():
    register_layout(0x8081, _pro_x_rapid_matcher(_family), keyboard_pro_x_rapid.with_media_top_row(_tkl))


def _named_keyboard_matcher(needles: tuple[str, ...], family: str, full_size: bool) -> Callable[[dict], bool]:
    """Model-specific keyboard matcher: name/codename substring + frame size
    + regional family. Extras wiring is per-model on the 0x8080 family (G512
    two indicators, G810 media cluster, G910 G-keys/nameplate), so each known
    model registers its own variant ahead of the generic family matchers."""
    named = _name_contains(*needles)

    def match(hint: dict) -> bool:
        if hint.get("kind") != "keyboard":
            return False
        if not named(hint):
            return False
        if _has_numpad(hint) != full_size:
            return False
        return _keyboard_family(hint) == family

    return match


# 0x8080 model variants — regional base + the model's special-key strip.
# Registered ahead of the generic family matchers so they win for these
# models. "PRO" alone is safe here: within the 0x8080 family the wired
# G Pro is the only TKL board.
for _family, (_full, _tkl) in _FAMILY_LAYOUTS.items():
    register_layout(0x8080, _named_keyboard_matcher(("G512", "G513"), _family, True), keyboard_g512.with_indicators(_full))
    register_layout(0x8080, _named_keyboard_matcher(("G810", "G610"), _family, True), keyboard_g810_family.g810_layout(_full))
    register_layout(0x8080, _named_keyboard_matcher(("G910",), _family, True), keyboard_g810_family.g910_layout(_full))
    register_layout(0x8080, _named_keyboard_matcher(("PRO",), _family, False), keyboard_g810_family.gpro_layout(_tkl))

# PER_KEY_LIGHTING = 0x8080 (G810 family) and PER_KEY_LIGHTING_V2 = 0x8081
# share Solaar's per-key zone numbering (0x8080 wire addressing is translated
# in settings_templates), so both use the same regional layouts.
for _family, (_full, _tkl) in _FAMILY_LAYOUTS.items():
    for _feature in (0x8080, 0x8081):
        register_layout(_feature, _keyboard_matcher(_family, full_size=True), _full)
        register_layout(_feature, _keyboard_matcher(_family, full_size=False), _tkl)

register_layout(0x8081, _name_contains("G502 X"), mouse_g502x.LAYOUT)
# HEADSET_RGB_HOSTMODE = 0x0620
register_layout(0x0620, _name_contains("G522"), headset_g522.LAYOUT)
