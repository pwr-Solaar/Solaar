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

"""Inline placeholder control that opens the onboard-profile button editor.

Mirrors ``solaar.ui.perkey.control.PerKeyControl``: a summary label plus a
button that opens a per-device dialog, wired in via ``Setting.editor_class``
instead of the generic ``MapChoiceControl``.
"""

from __future__ import annotations

import logging

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

from . import dialog as dialog_mod  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    CLICKED = "clicked"


class OnboardButtonsControl(Gtk.Box):
    """Replaces ``MapChoiceControl`` for the ``onboard_profile_buttons`` setting.

    Ducktypes the four ``Control`` methods (``set_sensitive``, ``set_value``,
    ``get_value``, ``layout``) used by ``_create_sbox`` / ``_update_setting_item``.
    """

    def __init__(self, sbox) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.sbox = sbox
        self._setting = sbox.setting
        self._value: dict | None = None

        self._summary = Gtk.Label(label=_("(not loaded)"))
        self._summary.set_xalign(0.0)
        self.pack_start(self._summary, True, True, 0)

        self._open_btn = Gtk.Button(label=_("Edit button mapping…"))
        self._open_btn.set_tooltip_text(_("Assign a keyboard key to each onboard-profile button"))
        self._open_btn.connect(GtkSignal.CLICKED.value, self._on_open)
        self.pack_end(self._open_btn, False, False, 0)

    # ---- Control protocol ----

    def set_sensitive(self, sensitive: bool) -> None:
        super().set_sensitive(bool(sensitive))
        self._open_btn.set_sensitive(bool(sensitive))

    def set_value(self, value) -> None:
        if not isinstance(value, dict):
            return
        self._value = value
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
        if not isinstance(self._value, dict) or not self._value:
            self._summary.set_text(_("(no button slots reported)"))
            return
        assigned = sum(1 for b in self._value.values() if getattr(b, "behavior", 15) != 15)
        self._summary.set_text(_("{assigned} / {total} buttons assigned").format(assigned=assigned, total=len(self._value)))

    def _on_open(self, _btn) -> None:
        device = getattr(self._setting, "_device", None)
        # Same stable-key strategy as the per-key RGB dialog: prefer the
        # firmware unit-id so the same physical device shares one window
        # regardless of which transport (receiver vs direct USB) it's on.
        key = (
            getattr(device, "unitId", None)
            or getattr(device, "serial", None)
            or getattr(device, "hid_serial", None)
            or getattr(device, "codename", None)
            or id(self._setting)
        )
        dlg = dialog_mod.get_dialog(key)
        dlg.present(self._setting, self.sbox)
