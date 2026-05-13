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

"""Inline placeholder control replacing MapChoiceControl for opted-in settings.

Renders a summary line + button. Click opens the per-key editor dialog,
backed by a SettingSink adapter that bridges the editor protocol to the
Solaar Setting object. The editor never touches the Setting directly.
"""

from __future__ import annotations

import logging

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from . import dialog as dialog_mod  # NOQA: E402
from .layouts import layout_for  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    CLICKED = "clicked"


# Sentinel matching special_keys.COLORSPLUS["No change"].
NO_CHANGE = -1


class _SettingSink:
    """Bridge between a Solaar Setting and the editor's PerKeyColorSink protocol."""

    def __init__(self, setting, sbox) -> None:
        self._setting = setting
        self._sbox = sbox
        self._listeners: list = []

    @property
    def title(self) -> str:
        device = getattr(self._setting, "_device", None)
        name = getattr(device, "name", None) or getattr(device, "codename", None) or ""
        return name or self._setting.label

    @property
    def zones(self) -> list[int]:
        return [int(k) for k in self._setting.choices]

    @property
    def current(self) -> dict[int, int]:
        return dict(self._setting._value or {})

    def label(self, zone: int) -> str:
        for k in self._setting.choices:
            if int(k) == int(zone):
                return str(k)
        return f"KEY {zone}"

    def write_one(self, zone: int, color: int) -> None:
        if self._setting._value is None:
            self._setting._value = {}
        self._setting._value[int(zone)] = int(color)
        # Lazy import to avoid a circular module-load between config_panel and perkey.
        from solaar.ui.config_panel import _write_async

        _write_async(self._setting, int(color), self._sbox, key=int(zone))
        self._notify()

    def write_bulk(self, deltas: dict[int, int]) -> None:
        if not deltas:
            return
        if self._setting._value is None:
            self._setting._value = {}
        merged = dict(self._setting._value)
        merged.update({int(k): int(v) for k, v in deltas.items()})
        self._setting._value = merged
        from solaar.ui.config_panel import _write_async

        _write_async(self._setting, merged, self._sbox, key=None)
        self._notify()

    def subscribe(self, listener):
        self._listeners.append(listener)

        def unsubscribe() -> None:
            # Idempotent: the editor calls this on shutdown, but the listener
            # may already be gone if the sink itself was torn down first.
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    def _palette_key(self) -> str:
        return f"_palette:{self._setting.name}"

    def palette_state(self) -> tuple[int, int] | None:
        device = getattr(self._setting, "_device", None)
        persister = getattr(device, "persister", None)
        if persister is None:
            return None
        entry = persister.get(self._palette_key())
        if not isinstance(entry, dict):
            return None
        active = entry.get("active")
        previous = entry.get("previous", active)
        if not isinstance(active, int) or not isinstance(previous, int):
            return None
        return (int(active), int(previous))

    def set_palette_state(self, active: int, previous: int) -> None:
        device = getattr(self._setting, "_device", None)
        persister = getattr(device, "persister", None)
        if persister is None:
            return
        persister[self._palette_key()] = {"active": int(active), "previous": int(previous)}

    def zone_base_color(self) -> int | None:
        """Color used to render per-key unset cells in the editor. Matches
        rgb_power.effective_zone_base_color: black when zone is ignored,
        the saved zone color otherwise."""
        device = getattr(self._setting, "_device", None)
        if device is None:
            return None
        from logitech_receiver import rgb_power

        return int(rgb_power.effective_zone_base_color(device))

    def _notify(self) -> None:
        snapshot = self.current
        for cb in list(self._listeners):
            try:
                cb(snapshot)
            except Exception as e:
                logger.warning("perkey listener raised: %s", e)

    def push_external_value(self, value) -> None:
        """Called from the inline control when the framework reports a value change."""
        if isinstance(value, dict):
            self._notify()


class PerKeyControl(Gtk.Box):
    """Replaces MapChoiceControl for per-key color settings.

    Ducktypes the four `Control` methods (`set_sensitive`, `set_value`,
    `get_value`, `layout`) used by `_create_sbox` / `_update_setting_item`.
    """

    def __init__(self, sbox) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sbox = sbox
        self._setting = sbox.setting
        self._value: dict | None = None
        self._sink = _SettingSink(self._setting, sbox)

        self._summary = Gtk.Label(label=_("(not loaded)"))
        self._summary.set_xalign(0.0)
        self.pack_start(self._summary, True, True, 0)

        self._open_btn = Gtk.Button(label=_("Open editor…"))
        self._open_btn.set_tooltip_text(_("Paint key colors on a keyboard layout"))
        self._open_btn.connect(GtkSignal.CLICKED.value, self._on_open)
        self.pack_end(self._open_btn, False, False, 0)

    # ---- Control protocol ----

    def set_sensitive(self, sensitive: bool) -> None:
        super().set_sensitive(bool(sensitive))
        self._open_btn.set_sensitive(bool(sensitive))

    def set_value(self, value) -> None:
        if value is None:
            return
        if not isinstance(value, dict):
            return
        # _write_async wraps single-key writes as `{key: written_value}` so
        # MapChoiceControl can update one combo cell. We need to keep the
        # full picture for the summary count, so merge instead of replace
        # when a partial dict comes in.
        existing = self._setting._value if isinstance(self._setting._value, dict) else None
        if existing and len(value) < len(existing):
            merged = dict(existing)
            merged.update(value)
            self._value = merged
        else:
            self._value = value
        self._sink.push_external_value(self._value)
        self._refresh_summary()

    def get_value(self):
        return self._value

    def layout(self, sbox, label, change, spinner, failed) -> bool:
        # Match the standard Control packing order so our button sits where
        # every other setting's widget sits, just left of spinner/change-icon.
        sbox.pack_start(label, False, False, 0)
        sbox.pack_end(change, False, False, 0)
        sbox.pack_end(self, False, False, 0)
        sbox.pack_end(spinner, False, False, 0)
        sbox.pack_end(failed, False, False, 0)
        return self

    # ---- internal ----

    def _refresh_summary(self) -> None:
        if not isinstance(self._value, dict):
            self._summary.set_text(_("(no zones)"))
            return
        total = len(self._value)
        painted = sum(1 for v in self._value.values() if isinstance(v, int) and v != NO_CHANGE and v >= 0)
        self._summary.set_text(_("{painted} / {total} keys painted").format(painted=painted, total=total))

    def _on_open(self, _btn) -> None:
        feature = getattr(self._setting, "feature", None)
        feature_int = int(feature) if feature is not None else 0
        device = getattr(self._setting, "_device", None)
        kind_obj = getattr(device, "kind", None)
        kind_str = str(kind_obj).lower() if kind_obj is not None else ""
        hint = {
            "kind": kind_str if kind_str else None,
            "wpid": getattr(device, "wpid", None),
            "codename": getattr(device, "codename", None),
            "name": getattr(device, "name", None),
            "keyboard_layout": getattr(device, "keyboard_layout", None),
            "zones": list(self._sink.zones),
            "zone_count": len(self._sink.zones),
        }
        layout = layout_for(feature_int, hint)
        # Stable per-device key so the same physical device on USB and on
        # the receiver shares a single dialog. unitId is read from the
        # device firmware (via DeviceInformation) and is the same across
        # transports; serial is per-pairing-slot. id(self._sink) is a
        # last-resort fallback that should never be hit in practice.
        key = (
            getattr(device, "unitId", None)
            or getattr(device, "serial", None)
            or getattr(device, "hid_serial", None)
            or getattr(device, "codename", None)
            or id(self._sink)
        )
        dlg = dialog_mod.get_dialog(key)
        dlg.present(self._sink, layout)
