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

"""Theme-aware loader for Solaar's per-key UI icons.

Loads SVG icons from ``share/solaar/icons/`` and recolors them at load
time to match the active GTK theme's text foreground, by substituting
``currentColor`` in the SVG before passing it to GdkPixbuf. GTK's stock
symbolic loader is bypassed because it only recolors specific palette
fill stand-ins and ignores ``stroke="currentColor"``.
"""

from __future__ import annotations

import logging

from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf  # NOQA: E402
from gi.repository import Gio  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

logger = logging.getLogger(__name__)

ICON_PIXEL_SIZE = 22

_search_path_added = False


def ensure_icon_path() -> None:
    """Register share/solaar/icons with the default GtkIconTheme so our
    custom symbolic tool icons resolve by name. Idempotent."""
    global _search_path_added
    if _search_path_added:
        return
    theme = Gtk.IconTheme.get_default()
    existing = set(theme.get_search_path() or [])
    # _icons.py: lib/solaar/ui/perkey/_icons.py -> parents[4] = repo root
    candidates = [
        Path(__file__).resolve().parents[4] / "share" / "solaar" / "icons",
    ]
    for c in candidates:
        if c.is_dir() and str(c) not in existing:
            theme.append_search_path(str(c))
    _search_path_added = True


def themed_icon_image(icon_name: str, style_widget: Gtk.Widget) -> Gtk.Image | None:
    """Load a Solaar tool icon and recolor it to match the given widget's
    text foreground color, so the icons follow the active GTK theme
    (light / dark / custom). Returns None if the icon can't be loaded.
    """
    ensure_icon_path()
    theme = Gtk.IconTheme.get_default()
    icon_info = theme.lookup_icon(icon_name, ICON_PIXEL_SIZE, Gtk.IconLookupFlags.FORCE_SIZE)
    if icon_info is None:
        return None
    path = icon_info.get_filename()
    if not path:
        return None
    fg = style_widget.get_style_context().get_color(Gtk.StateFlags.NORMAL)
    color = f"#{int(fg.red * 255):02x}{int(fg.green * 255):02x}{int(fg.blue * 255):02x}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            svg = f.read()
        svg = svg.replace("currentColor", color)
        stream = Gio.MemoryInputStream.new_from_data(svg.encode("utf-8"))
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, ICON_PIXEL_SIZE, ICON_PIXEL_SIZE, True)
        return Gtk.Image.new_from_pixbuf(pixbuf)
    except Exception as e:
        logger.debug("recolor failed for %s: %s", icon_name, e)
        return None
