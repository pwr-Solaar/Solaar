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

"""Narrow contract between the per-key editor and any color-map setting.

The editor consumes only this protocol, never `lib.logitech_receiver` directly.
This is the seam where a future frontend/backend split would cut cleanly.
"""

from __future__ import annotations

from typing import Callable
from typing import Protocol


class PerKeyColorSink(Protocol):
    """A device's per-key color buffer, exposed without device internals.

    Colors are 24-bit packed RGB ints (0xRRGGBB). The sentinel value -1 means
    "no change" / "unset" (matches `special_keys.COLORSPLUS["No change"]`).
    """

    @property
    def title(self) -> str:
        ...

    @property
    def zones(self) -> list[int]:
        ...

    @property
    def current(self) -> dict[int, int]:
        ...

    def label(self, zone: int) -> str:
        ...

    def write_one(self, zone: int, color: int) -> None:
        ...

    def write_bulk(self, deltas: dict[int, int]) -> None:
        ...

    def subscribe(self, listener: Callable[[dict[int, int]], None]) -> Callable[[], None]:
        """Register a callback for current-value changes; return an unsubscribe handle."""
        ...

    def palette_state(self) -> tuple[int, int] | None:
        """Return the persisted (active_color, previous_color) for this device's palette, or None."""
        ...

    def set_palette_state(self, active: int, previous: int) -> None:
        """Persist the palette's active and previous colors for this device."""
        ...

    def zone_base_color(self) -> int | None:
        """Return the zone base color (what 'no change' cells actually display
        on the keyboard), or None if the device has no zone effect.
        """
        ...
