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

"""ISO_QWERTY keyboard layouts (UK English ISO + other QWERTY ISO regions).

Same English keycap legends as ANSI; differs only in shape — the row 2 col 13
backslash on ANSI doesn't exist on ISO (that position is the upper half of the
L-shape Enter, addressed by zone 37). Used for UK and any other region whose
country code maps to "iso_qwerty" without a more specific layout (Spanish,
Italian, Portuguese, Belgian, Nordic — those keyboards have the same shape
as UK ISO; only their physical keycap legends differ, which our painter
doesn't reproduce verbatim).
"""

from __future__ import annotations

from ..layout import Layout
from ._keyboard_base import MAIN_ISO
from ._keyboard_base import build_layout

LAYOUT_FULL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=True,
    description="ISO QWERTY 103-key full-size",
)


LAYOUT_TKL: Layout = build_layout(
    MAIN_ISO,
    include_numpad=False,
    description="ISO QWERTY tenkeyless",
)
