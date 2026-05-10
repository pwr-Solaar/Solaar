## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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


# --- Keyboards: distinguish full-size from TKL by presence of a numpad zone.
# Counting zones is unreliable (G515 reports phantom zones 47, 97, 99-103, 254
# that diverge from the keycap count).
def _has_numpad(hint: dict) -> bool:
    zones = set(hint.get("zones", ()))
    return 80 in zones or 95 in zones


def _is_full_keyboard(hint: dict) -> bool:
    return hint.get("kind") == "keyboard" and _has_numpad(hint)


def _is_tkl_keyboard(hint: dict) -> bool:
    return hint.get("kind") == "keyboard" and not _has_numpad(hint)


# PER_KEY_LIGHTING_V2 = 0x8081
register_layout(0x8081, _is_full_keyboard, keyboard_ansi.LAYOUT_FULL)
register_layout(0x8081, _is_tkl_keyboard, keyboard_ansi.LAYOUT_TKL)
register_layout(0x8081, _name_contains("G502 X"), mouse_g502x.LAYOUT)
