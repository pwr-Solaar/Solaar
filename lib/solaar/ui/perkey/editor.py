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

"""Editor widget: combines toolbar + palette + canvas into one VBox.

The editor consumes only the PerKeyColorSink protocol — no device imports,
no Setting imports — preserving the FE/BE seam.
"""

from __future__ import annotations

import logging

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
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


class PerKeyEditor(Gtk.Box):
    def __init__(self, sink: PerKeyColorSink, layout: Layout | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._sink = sink
        self._layout = layout
        self._unsubscribe = None

        # toolbar row
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._tool_buttons: dict[str, Gtk.RadioButton] = {}
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
                btn = Gtk.RadioButton.new_with_label_from_widget(first, label)
                btn.set_mode(False)  # render as toggle button rather than radio
                btn.set_tooltip_text(tip)
            btn.connect(GtkSignal.TOGGLED.value, self._on_tool_toggled, name)
            if first is None:
                first = btn
            toolbar.pack_start(btn, False, False, 0)
            self._tool_buttons[name] = btn

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
