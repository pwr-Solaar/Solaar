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
from . import keyboard_ansi
from . import keyboard_iso_azerty
from . import keyboard_iso_qwerty
from . import keyboard_iso_qwertz
from . import keyboard_jis
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
_KEYBOARD_FAMILY_BY_COUNTRY: dict[int, str] = {
    1: "ansi",
    # ISO QWERTY (UK + ES/IT/PT/BE/Nordic — same shape, different keycap legends)
    2: "iso_qwerty",
    5: "iso_qwerty",
    8: "iso_qwerty",
    0x0B: "iso_qwerty",
    0x0D: "iso_qwerty",
    0x0E: "iso_qwerty",
    0x0F: "iso_qwerty",
    0x16: "iso_qwerty",
    0x1D: "iso_qwerty",
    0x21: "iso_qwerty",
    0x24: "iso_qwerty",
    # ISO QWERTZ (DE/Swiss)
    3: "iso_qwertz",
    7: "iso_qwertz",
    # ISO AZERTY (FR)
    4: "iso_azerty",
    # JIS
    9: "jis",
    0x3E: "jis",
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


# PER_KEY_LIGHTING_V2 = 0x8081
for _family, (_full, _tkl) in _FAMILY_LAYOUTS.items():
    register_layout(0x8081, _keyboard_matcher(_family, full_size=True), _full)
    register_layout(0x8081, _keyboard_matcher(_family, full_size=False), _tkl)

register_layout(0x8081, _name_contains("G502 X"), mouse_g502x.LAYOUT)
