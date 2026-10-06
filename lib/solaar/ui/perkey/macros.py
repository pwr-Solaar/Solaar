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

"""Macro recorder: assign a key sequence to a device G-key (G1-G5).

Records keystrokes (including modifier chords) while the dialog has focus,
then persists a Solaar diversion rule so pressing the chosen G-key replays the
sequence. The rule is written to the ordinary user rules file
(``rules.yaml``) through the existing diversion save path, and the G-key
divert setting is enabled so Solaar receives the key presses.

Because playback uses the core diversion ``KeyPress`` actions, this works the
same way as a hand-written Diversion Rule — no new input simulation path.
"""

from __future__ import annotations

import logging

from enum import Enum

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402
from logitech_receiver import diversion  # NOQA: E402

from solaar.i18n import _  # NOQA: E402

logger = logging.getLogger(__name__)

# Delay inserted between recorded steps (seconds), so sequential keys are
# replayed as a typed sequence rather than one simultaneous chord.
_HOLD = 0.05

# Modifier keyvals as GDK reports them. Canonicalisation to the single X11
# "left" symbols we send is safe because these share a modifier mask.
_MODIFIERS = {
    "Control_L": "Control_L",
    "Control_R": "Control_L",
    "Alt_L": "Alt_L",
    "Alt_R": "Alt_L",
    "Meta_L": "Super_L",
    "Meta_R": "Super_L",
    "Super_L": "Super_L",
    "Super_R": "Super_L",
    "Hyper_L": "Super_L",
    "Hyper_R": "Super_L",
}
# These GDK names differ from the X11 keysym names the KeyPress action uses.
_GDK_TO_X11 = {
    "ISO_Left_Tab": "Tab",
    "backspace": "BackSpace",
    "Delete": "Delete",
    "Insert": "Insert",
    "KP_Enter": "KP_Enter",
    "Escape": "Escape",
}

# Canonical display order used both when showing and when emitting a chord.
_MODIFIER_ORDER = ["Control", "Alt", "Super"]


class GtkSignal(Enum):
    CLICKED = "clicked"
    TOGGLED = "toggled"
    KEY_PRESS_EVENT = "key-press-event"
    KEY_RELEASE_EVENT = "key-release-event"
    DELETE_EVENT = "delete-event"


def _to_x11(gdk_name: str) -> str:
    """Best-effort translation from a GDK keyval name to an X11 keysym name."""
    if gdk_name in diversion.XK_KEYS:
        return gdk_name
    if gdk_name in _GDK_TO_X11:
        candidate = _GDK_TO_X11[gdk_name]
        if candidate in diversion.XK_KEYS:
            return candidate
    return gdk_name


def _modifier_x11(gdk_name: str) -> str | None:
    return _MODIFIERS.get(gdk_name)


def _key_is_modifier(gdk_name: str) -> bool:
    return _modifier_x11(gdk_name) is not None or gdk_name in ("Shift_L", "Shift_R", "ISO_Level3_Shift", "Caps_Lock")


def _format_chord(chord: list[str]) -> str:
    """Human-readable '+' joined display of one recorded step."""
    return "+".join(chord) if len(chord) > 1 else chord[0]


class MacroEditor(Gtk.Dialog):
    """Modal dialog that records a macro and assigns it to a G-key."""

    def __init__(self, parent: Gtk.Window, device, gkeys: list[str], macro_delay: float = _HOLD) -> None:
        super().__init__(title=_("Macro editor"), transient_for=parent, modal=True)
        self.set_default_size(460, 360)
        self._device = device
        self._gkeys = list(gkeys)
        self._recording: list[list[str]] = []
        self._held_mods: list[str] = []  # canonical X11 modifiers (Control/Alt/Super)
        self._active = False
        self._hold = macro_delay

        # --- content ---
        content = self.get_content_area()
        content.set_spacing(10)

        # G-key target selector
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.attach(Gtk.Label(label=_("Assign to")), 0, 0, 1, 1)
        self._gkey_combo = Gtk.ComboBoxText()
        for g in self._gkeys:
            self._gkey_combo.append_text(g)
        self._gkey_combo.set_active(0)
        grid.attach(self._gkey_combo, 1, 0, 1, 1)
        content.add(grid)

        # Record / clear controls
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._record_btn = Gtk.ToggleButton(label=_("Record"))
        self._record_btn.connect(GtkSignal.TOGGLED.value, self._on_record_toggled)
        controls.pack_start(self._record_btn, False, False, 0)
        self._clear_btn = Gtk.Button(label=_("Clear"))
        self._clear_btn.connect(GtkSignal.CLICKED.value, self._on_clear)
        controls.pack_start(self._clear_btn, False, False, 0)
        self._status = Gtk.Label(label="")
        self._status.set_xalign(0.0)
        controls.pack_start(self._status, True, True, 0)
        content.add(controls)

        # Existing per-G-key macro assignments, so it's visible what's already
        # recorded before (re-)recording one.
        self._existing = Gtk.Label()
        self._existing.set_xalign(0.0)
        self._existing.set_line_wrap(True)
        self._existing.get_style_context().add_class("dim-label")
        content.add(self._existing)
        self._refresh_existing()

        # Recorded steps list
        self._steps = Gtk.Label(label=_("Nothing recorded yet."))
        self._steps.set_xalign(0.0)
        self._steps.set_line_wrap(True)
        self._steps.set_yalign(0.0)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self._steps)
        sw.set_size_request(-1, 160)
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        wrap.pack_start(sw, True, True, 0)
        content.add(wrap)

        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("Apply"), Gtk.ResponseType.OK)

        # Key capture on this dialog window only while recording.
        self.connect(GtkSignal.KEY_PRESS_EVENT.value, self._on_key_press)
        self.connect(GtkSignal.KEY_RELEASE_EVENT.value, self._on_key_release)
        self.connect(GtkSignal.DELETE_EVENT.value, self._on_delete)

    # ---- recording ----

    def _on_delete(self, _w, _e) -> bool:
        self._active = False
        return False

    def _on_record_toggled(self, btn: Gtk.ToggleButton) -> None:
        self._active = bool(btn.get_active())
        self._held_mods = []
        if self._active:
            self._status.set_text(_("Recording… type the macro, then click Record again to stop."))
        else:
            self._status.set_text(_("{n} step(s) recorded.").format(n=len(self._recording)) if self._recording else "")
        self._refresh()

    def _on_clear(self, _btn) -> None:
        self._recording = []
        self._held_mods = []
        self._refresh()

    def _on_key_press(self, _w, event) -> bool:
        if not self._active:
            return False
        name = Gdk.keyval_name(event.keyval)
        if not name:
            return False
        if _key_is_modifier(name):
            x = _modifier_x11(name)
            if x and x not in self._held_mods:
                self._held_mods.append(x)
                self._held_mods = sorted(self._held_mods, key=lambda m: _MODIFIER_ORDER.index(m))
            # Shift / level3 / caps are handled by KeyPress automatically.
            return True
        # A real key: record a chord of the currently held Control/Alt/Super
        # modifiers plus this key.
        chord = list(self._held_mods) + [_to_x11(name)]
        self._recording.append(chord)
        self._refresh()
        return True

    def _on_key_release(self, _w, event) -> bool:
        if not self._active:
            return False
        name = Gdk.keyval_name(event.keyval)
        if not name:
            return False
        x = _modifier_x11(name)
        if x and x in self._held_mods:
            self._held_mods.remove(x)
        return False

    def _refresh(self) -> None:
        if self._recording:
            lines = "\n".join(_format_chord(c) for c in self._recording)
            self._steps.set_text(lines)
        else:
            self._steps.set_text(_("Nothing recorded yet."))

    # ---- save / rule generation ----

    def _selected_gkey(self) -> str:
        return self._gkey_combo.get_active_text() or self._gkeys[0]

    def build_rule(self, gkey: str) -> list:
        """Return the diversion rule components replaying the recorded
        sequence on `gkey`. Empty when nothing was recorded."""
        if not self._recording:
            return []
        components: list = [{"Key": [gkey, "pressed"]}]
        for i, chord in enumerate(self._recording):
            if i > 0:
                components.append({"Later": [self._hold]})
            components.append({"KeyPress": [chord, "click"]})
        return components

    def _ensure_gkey_diverted(self) -> bool:
        """Turn on divert-gkeys if present, so Solaar sees G-key presses."""
        if self._device is None:
            return False
        setting = next((s for s in getattr(self._device, "settings", []) if s.name == "divert-gkeys"), None)
        if setting is None:
            return False
        try:
            setting.write(True)
            return True
        except Exception as e:
            logger.debug("could not enable divert-gkeys: %s", e)
            return False

    @classmethod
    def _existing_macros(cls, gkeys: list[str]) -> dict[str, int | None]:
        """Return {G-key: recorded step count (or None if none)} for every
        G-key in `gkeys`, by scanning the user macro rules already saved."""
        result: dict[str, int | None] = {g: None for g in gkeys}
        group = next(
            (r for r in diversion.rules.components if getattr(r, "source", None) == diversion._file_path),
            None,
        )
        if group is None:
            return result
        for rule in getattr(group, "components", []):
            for g in gkeys:
                if result[g] is None and cls._is_macro_rule(rule, g):
                    comps = getattr(rule, "components", [])
                    result[g] = sum(1 for c in comps[1:] if c.__class__ is diversion.KeyPress)
        return result

    def _refresh_existing(self) -> None:
        existing = self._existing_macros(self._gkeys)
        lines = []
        for g in self._gkeys:
            n = existing.get(g)
            if n is None:
                lines.append(_("{g}: none").format(g=g))
            else:
                lines.append(_("{g}: {n} step(s)").format(g=g, n=n))
        self._existing.set_text(_("Existing macros:") + "\n" + "\n".join(lines))

    @staticmethod
    def _is_macro_rule(rule, gkey: str) -> bool:
        """True when `rule` is a macro rule we generated for this G-key.

        Our rules are a single Rule whose first component is our G-key press
        condition and whose remaining components are only KeyPress / Later.
        """
        components = getattr(rule, "components", [])
        if not components:
            return False
        first = components[0]
        key_arg = getattr(first, "key", None)
        if key_arg is None or str(key_arg) != gkey:
            return False
        if getattr(first, "action", None) != "pressed":
            return False
        for comp in components[1:]:
            if comp.__class__ not in (diversion.KeyPress, diversion.Later):
                return False
        return True

    def apply(self) -> bool:
        gkey = self._selected_gkey()
        components = self.build_rule(gkey)
        if not components:
            return False
        rule = diversion.Rule(components, source=diversion._file_path)
        # Find the user-rules group and replace any previous macro rule we
        # generated for this same G-key, then append the new one.
        group = next(
            (r for r in diversion.rules.components if getattr(r, "source", None) == diversion._file_path),
            None,
        )
        if group is None:
            group = diversion.Rule([], source=diversion._file_path)
            diversion.rules.components = [group] + list(diversion.rules.components)
        kept = [r for r in group.components if not self._is_macro_rule(r, gkey)]
        kept.append(rule)
        group.components = kept
        self._ensure_gkey_diverted()
        try:
            return diversion._save_config_rule_file()
        except Exception as e:
            logger.error("failed to save macro rule: %s", e)
            return False
