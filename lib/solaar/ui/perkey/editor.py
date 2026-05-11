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

"""Editor widget: combines toolbar + palette + canvas into one VBox.

The editor consumes only the PerKeyColorSink protocol — no device imports,
no Setting imports — preserving the FE/BE seam.
"""

from __future__ import annotations

import logging

from enum import Enum
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf  # NOQA: E402
from gi.repository import Gio  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from . import binding  # NOQA: E402
from .canvas import KeyboardCanvas  # NOQA: E402
from .layout import Layout  # NOQA: E402
from .palette import GradientSwatch  # NOQA: E402
from .palette import Palette  # NOQA: E402
from .protocol import PerKeyColorSink  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    COLOR_CHANGED = "color-changed"
    PAINT = "paint"
    TOGGLED = "toggled"


_TOOL_LABELS = {
    "single": (_("Brush"), _("Click or drag to paint individual keys")),
    "rect": (_("Rect"), _("Drag to select a rectangle of keys, painted on release")),
    "bucket": (_("Fill"), _("Flood-fill connected keys of the same color with the active color")),
}
_TOOL_TOOLTIPS = {
    "gradient": _("Drag to fade from previous color to active color"),
}
_TOOL_ICON_NAMES = {
    "single": "solaar-tool-brush-symbolic",
    "rect": "solaar-tool-rect-symbolic",
    "bucket": "solaar-tool-bucket-symbolic",
}
_TOOL_ICON_PIXEL_SIZE = 22

_icon_search_path_added = False


def _ensure_tool_icon_path() -> None:
    """Register share/solaar/icons with the default GtkIconTheme so our
    custom symbolic tool icons resolve by name. Idempotent."""
    global _icon_search_path_added
    if _icon_search_path_added:
        return
    theme = Gtk.IconTheme.get_default()
    existing = set(theme.get_search_path() or [])
    # Source-tree path: lib/solaar/ui/perkey/editor.py -> parents[4] = repo root
    candidates = [
        Path(__file__).resolve().parents[4] / "share" / "solaar" / "icons",
    ]
    for c in candidates:
        if c.is_dir() and str(c) not in existing:
            theme.append_search_path(str(c))
    _icon_search_path_added = True


def _tool_icon_image(icon_name: str, style_widget: Gtk.Widget) -> Gtk.Image | None:
    """Load a Solaar tool icon and recolor it to match the given widget's
    text foreground color, so the icons follow the active GTK theme
    (light / dark / custom). Returns None if the icon can't be loaded.

    GTK's stock symbolic loader (`load_symbolic_for_context`) only recolors
    specific palette stand-ins (e.g. fill="#bebebe"); it ignores
    `stroke="currentColor"`. We bypass it and substitute currentColor
    ourselves so any SVG using the currentColor convention works.
    """
    _ensure_tool_icon_path()
    theme = Gtk.IconTheme.get_default()
    icon_info = theme.lookup_icon(icon_name, _TOOL_ICON_PIXEL_SIZE, Gtk.IconLookupFlags.FORCE_SIZE)
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
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, _TOOL_ICON_PIXEL_SIZE, _TOOL_ICON_PIXEL_SIZE, True)
        return Gtk.Image.new_from_pixbuf(pixbuf)
    except Exception as e:
        logger.debug("recolor failed for %s: %s", icon_name, e)
        return None


class PerKeyEditor(Gtk.Box):
    def __init__(self, sink: PerKeyColorSink, layout: Layout | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._sink = sink
        self._layout = layout
        self._unsubscribe = None

        # toolbar row
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._tool_buttons: dict[str, Gtk.RadioButton] = {}
        # Track which buttons display a themed icon, so we can re-render them
        # when the active GTK theme switches (light <-> dark, theme name).
        self._themed_icon_buttons: dict[Gtk.RadioButton, str] = {}
        self._gradient_swatch: GradientSwatch | None = None
        first: Gtk.RadioButton | None = None
        supported = layout.supported_tools if layout else ("single", "rect", "bucket", "gradient")
        for name in supported:
            if name == "gradient":
                btn = Gtk.RadioButton.new_from_widget(first)
                btn.set_mode(False)
                self._gradient_swatch = GradientSwatch()
                btn.add(self._gradient_swatch)
                btn.set_tooltip_text(_TOOL_TOOLTIPS["gradient"])
            else:
                label, tip = _TOOL_LABELS.get(name, (name, ""))
                icon_name = _TOOL_ICON_NAMES.get(name)
                btn = Gtk.RadioButton.new_from_widget(first)
                btn.set_mode(False)  # render as toggle button rather than radio
                image = _tool_icon_image(icon_name, btn) if icon_name else None
                if image is not None:
                    btn.add(image)
                    btn.set_tooltip_text(tip or label)
                    btn.get_accessible().set_name(label)
                    self._themed_icon_buttons[btn] = icon_name
                else:
                    btn.set_label(label)
                    btn.set_tooltip_text(tip)
            btn.connect(GtkSignal.TOGGLED.value, self._on_tool_toggled, name)
            if first is None:
                first = btn
            toolbar.pack_start(btn, False, False, 0)
            self._tool_buttons[name] = btn

        # Re-render themed icons when the GTK theme changes at runtime.
        self._theme_signal_handlers: list[tuple[object, int]] = []
        if self._themed_icon_buttons:
            settings = Gtk.Settings.get_default()
            for prop in ("notify::gtk-theme-name", "notify::gtk-application-prefer-dark-theme"):
                hid = settings.connect(prop, self._on_gtk_theme_changed)
                self._theme_signal_handlers.append((settings, hid))

        initial_active, initial_previous = 0xFF0000, 0xFF0000
        try:
            persisted = sink.palette_state()
        except Exception as e:
            logger.debug("palette_state read failed: %s", e)
            persisted = None
        if persisted is not None:
            initial_active, initial_previous = persisted
        self._palette = Palette(active=initial_active, previous=initial_previous)
        self._palette.connect(GtkSignal.COLOR_CHANGED.value, self._on_color_changed)
        toolbar.pack_end(self._palette, False, False, 0)
        if self._gradient_swatch is not None:
            self._gradient_swatch.update(self._palette.get_color(), self._palette.get_last_color())

        self.pack_start(toolbar, False, False, 0)

        # canvas inside a scrolled window so wide layouts can scroll if the
        # window is shrunk below content size. propagate_natural_size lets the
        # window auto-fit small layouts (e.g. an 8-LED mouse) without forcing
        # an oversized minimum.
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_width(True)
        scroll.set_propagate_natural_height(True)
        self._canvas = KeyboardCanvas()
        self._canvas.connect(GtkSignal.PAINT.value, self._on_canvas_paint)
        scroll.add(self._canvas)
        self.pack_start(scroll, True, True, 0)

        self._canvas.set_active_color(self._palette.get_color())
        if self._gradient_swatch is not None:
            self._canvas.set_gradient_colors_source(self._gradient_swatch.get_colors)
        try:
            base = sink.zone_base_color()
        except Exception as e:
            logger.debug("zone_base_color read failed: %s", e)
            base = None
        self._canvas.set_zone_base_color(base)
        self._palette.set_zone_base_color(base)
        self._refresh_layout()
        self._sync_from_sink()
        self._unsubscribe = sink.subscribe(self._on_sink_update)

    def shutdown(self) -> None:
        if self._unsubscribe:
            try:
                self._unsubscribe()
            except Exception as e:
                logger.debug("perkey sink unsubscribe failed: %s", e)
            self._unsubscribe = None
        for obj, hid in self._theme_signal_handlers:
            try:
                obj.disconnect(hid)
            except Exception as e:
                logger.debug("theme signal disconnect failed: %s", e)
        self._theme_signal_handlers = []

    def _on_gtk_theme_changed(self, _settings, _pspec) -> None:
        """Rebuild themed tool icons so they match the new theme's foreground."""
        for btn, icon_name in self._themed_icon_buttons.items():
            old = btn.get_child()
            new_image = _tool_icon_image(icon_name, btn)
            if new_image is None:
                continue
            if old is not None:
                btn.remove(old)
            btn.add(new_image)
            new_image.show()

    def canvas_size(self) -> tuple[int, int]:
        """Return the canvas's pixel size_request — what the dialog should
        size its content area to so the layout fits without scrollbars.
        """
        return self._canvas.get_size_request()

    def _refresh_layout(self) -> None:
        if self._layout is None:
            # No registered layout: lay out all reported zones as a flat strip.
            from .layout import Cell

            zones = list(self._sink.zones)
            cells = tuple(Cell(zone_id=z, row=0, col=i, group="strip", label=self._sink.label(z)) for i, z in enumerate(zones))
            self._layout = Layout(cells=cells, rows=1, cols=max(1, len(zones)), description=f"flat strip ({len(zones)} zones)")
        bound = binding.bind(
            self._layout,
            list(self._sink.zones),
            self._sink.label,
        )
        self._canvas.set_layout(bound)

    def _sync_from_sink(self) -> None:
        self._canvas.set_colors(dict(self._sink.current))

    def _on_sink_update(self, current: dict[int, int]) -> None:
        self._canvas.set_colors(dict(current))

    def _on_color_changed(self, _palette, color: int) -> None:
        self._canvas.set_active_color(color)
        # Gradient swatch tracks only real picker colors; toggling unset
        # leaves it alone so the gradient setup isn't disturbed.
        picker = self._palette.get_picker_color()
        if self._gradient_swatch is not None:
            self._gradient_swatch.update(picker, self._palette.get_last_color())
        try:
            self._sink.set_palette_state(picker, self._palette.get_last_color())
        except Exception as e:
            logger.debug("set_palette_state failed: %s", e)

    def _on_tool_toggled(self, btn: Gtk.RadioButton, name: str) -> None:
        if btn.get_active():
            self._canvas.set_tool(name)

    def _on_canvas_paint(self, _canvas, delta: dict) -> None:
        if not delta:
            return
        if len(delta) == 1:
            zone, color = next(iter(delta.items()))
            self._sink.write_one(int(zone), int(color))
        else:
            self._sink.write_bulk({int(z): int(c) for z, c in delta.items()})
