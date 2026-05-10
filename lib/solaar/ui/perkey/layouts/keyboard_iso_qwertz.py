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

"""ISO QWERTZ layout (DE / CH).

ISO shape plus German label overrides (Y/Z swap, Ü/Ö/Ä/ß placement).
Adapted from OpenRGB.
"""

from __future__ import annotations

from ..layout import Layout
from ._keyboard_base import MAIN_ISO
from ._keyboard_base import build_layout

# zone_id → German label
_OVERRIDES: dict[int, str] = {
    50: "^",  # row 1 col 0 — caret/degree (DE keycap)
    42: "ß",  # row 1 col 11 — eszett
    43: "´",  # row 1 col 12 — acute accent
    25: "Z",  # row 2 col 6 — Y/Z swap
    44: "Ü",  # row 2 col 11
    45: "+",  # row 2 col 12
    48: "Ö",  # row 3 col 10
    49: "Ä",  # row 3 col 11
    26: "Y",  # row 4 col 2 — Y/Z swap
    53: "-",  # row 4 col 11
}


LAYOUT_FULL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=True,
    label_overrides=_OVERRIDES,
    description="ISO QWERTZ (DE/CH) full-size",
)


LAYOUT_TKL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=False,
    label_overrides=_OVERRIDES,
    description="ISO QWERTZ (DE/CH) tenkeyless",
)
