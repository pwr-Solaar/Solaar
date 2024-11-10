## Copyright (C) Solaar Contributors
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
from enum import Enum
from shlex import quote as shlex_quote

from gi.repository import Gtk
from logitech_receiver import diversion
from logitech_receiver.diversion import CLICK
from logitech_receiver.diversion import DEPRESS
from logitech_receiver.diversion import RELEASE
from logitech_receiver.diversion import XK_KEYS
from logitech_receiver.diversion import buttons

from solaar.i18n import _
from solaar.ui.rule_base import CompletionEntry
from solaar.ui.rule_base import RuleComponentUI


class GtkSignal(Enum):
    CHANGED = "changed"
    CLICKED = "clicked"
    TOGGLED = "toggled"


class ActionUI(RuleComponentUI):
    CLASS = diversion.Action

    @classmethod
    def icon_name(cls):
        return "go-next"


class KeyPressUI(ActionUI):
    CLASS = diversion.KeyPress
    KEY_NAMES = [k[3:] if k.startswith("XK_") else k for k, v in XK_KEYS.items() if isinstance(v, int)]

    def create_widgets(self):
        self.widgets = {}
        self.fields = []
        self.label = Gtk.Label(
            label=_("Simulate a chorded key click or depress or release.\nOn Wayland requires write access to /dev/uinput."),
            halign=Gtk.Align.CENTER,
        )
        self.widgets[self.label] = (0, 0, 5, 1)
        self.del_btns = []
        self.add_btn = Gtk.Button(label=_("Add key"), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
        self.add_btn.connect(GtkSignal.CLICKED.value, self._clicked_add)
        self.widgets[self.add_btn] = (1, 1, 1, 1)
        self.action_clicked_radio = Gtk.RadioButton.new_with_label_from_widget(None, _("Click"))
        self.action_clicked_radio.connect(GtkSignal.TOGGLED.value, self._on_update, CLICK)
        self.widgets[self.action_clicked_radio] = (0, 3, 1, 1)
        self.action_pressed_radio = Gtk.RadioButton.new_with_label_from_widget(self.action_clicked_radio, _("Depress"))
        self.action_pressed_radio.connect(GtkSignal.TOGGLED.value, self._on_update, DEPRESS)
        self.widgets[self.action_pressed_radio] = (1, 3, 1, 1)
        self.action_released_radio = Gtk.RadioButton.new_with_label_from_widget(self.action_pressed_radio, _("Release"))
        self.action_released_radio.connect(GtkSignal.TOGGLED.value, self._on_update, RELEASE)
        self.widgets[self.action_released_radio] = (2, 3, 1, 1)

    def _create_field(self):
        field_entry = CompletionEntry(self.KEY_NAMES, halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
        field_entry.connect(GtkSignal.CHANGED.value, self._on_update)
        self.fields.append(field_entry)
        self.widgets[field_entry] = (len(self.fields) - 1, 1, 1, 1)
        return field_entry

    def _create_del_btn(self):
        btn = Gtk.Button(label=_("Delete"), halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True)
        self.del_btns.append(btn)
        self.widgets[btn] = (len(self.del_btns) - 1, 2, 1, 1)
        btn.connect(GtkSignal.CLICKED.value, self._clicked_del, len(self.del_btns) - 1)
        return btn

    def _clicked_add(self, _btn):
        keys, action = self.component.regularize_args(self.collect_value())
        self.component.__init__([keys + [""], action], warn=False)
        self.show(self.component, editable=True)
        self.fields[len(self.component.key_names) - 1].grab_focus()

    def _clicked_del(self, _btn, pos):
        keys, action = self.component.regularize_args(self.collect_value())
        keys.pop(pos)
        self.component.__init__([keys, action], warn=False)
        self.show(self.component, editable=True)
        self._on_update_callback()

    def _on_update(self, *args):
        super()._on_update(*args)
        for i, f in enumerate(self.fields):
            if f.get_visible():
                icon = (
                    "dialog-warning"
                    if i < len(self.component.key_names) and self.component.key_names[i] not in self.KEY_NAMES
                    else ""
                )
                f.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    def show(self, component, editable=True):
        n = len(component.key_names)
        while len(self.fields) < n:
            self._create_field()
            self._create_del_btn()

        self.widgets[self.add_btn] = (n, 1, 1, 1)
        super().show(component, editable)
        for i in range(n):
            field_entry = self.fields[i]
            with self.ignore_changes():
                field_entry.set_text(component.key_names[i])
            field_entry.set_size_request(int(0.3 * self.panel.get_toplevel().get_size()[0]), 0)
            field_entry.show_all()
            self.del_btns[i].show()
        for i in range(n, len(self.fields)):
            self.fields[i].hide()
            self.del_btns[i].hide()

    def collect_value(self):
        action = (
            CLICK if self.action_clicked_radio.get_active() else DEPRESS if self.action_pressed_radio.get_active() else RELEASE
        )
        return [[f.get_text().strip() for f in self.fields if f.get_visible()], action]

    @classmethod
    def left_label(cls, component):
        return _("Key press")

    @classmethod
    def right_label(cls, component):
        return " + ".join(component.key_names) + ("  (" + component.action + ")" if component.action != CLICK else "")


class MouseScrollUI(ActionUI):
    CLASS = diversion.MouseScroll
    MIN_VALUE = -2000
    MAX_VALUE = 2000

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(
            label=_("Simulate a mouse scroll.\nOn Wayland requires write access to /dev/uinput."), halign=Gtk.Align.CENTER
        )
        self.widgets[self.label] = (0, 0, 4, 1)
        self.label_x = Gtk.Label(label="x", halign=Gtk.Align.END, valign=Gtk.Align.END, hexpand=True)
        self.label_y = Gtk.Label(label="y", halign=Gtk.Align.END, valign=Gtk.Align.END, hexpand=True)
        self.field_x = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        self.field_y = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        for f in [self.field_x, self.field_y]:
            f.set_halign(Gtk.Align.CENTER)
            f.set_valign(Gtk.Align.START)
        self.field_x.connect(GtkSignal.CHANGED.value, self._on_update)
        self.field_y.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.label_x] = (0, 1, 1, 1)
        self.widgets[self.field_x] = (1, 1, 1, 1)
        self.widgets[self.label_y] = (2, 1, 1, 1)
        self.widgets[self.field_y] = (3, 1, 1, 1)

    @classmethod
    def __parse(cls, v):
        try:
            # allow floats, but round them down
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.field_x.set_value(self.__parse(component.amounts[0] if len(component.amounts) >= 1 else 0))
            self.field_y.set_value(self.__parse(component.amounts[1] if len(component.amounts) >= 2 else 0))

    def collect_value(self):
        return [int(self.field_x.get_value()), int(self.field_y.get_value())]

    @classmethod
    def left_label(cls, component):
        return _("Mouse scroll")

    @classmethod
    def right_label(cls, component):
        x = y = 0
        x = cls.__parse(component.amounts[0] if len(component.amounts) >= 1 else 0)
        y = cls.__parse(component.amounts[1] if len(component.amounts) >= 2 else 0)
        return f"{x}, {y}"


class MouseClickUI(ActionUI):
    CLASS = diversion.MouseClick
    MIN_VALUE = 1
    MAX_VALUE = 9
    BUTTONS = list(buttons.keys())
    ACTIONS = [CLICK, DEPRESS, RELEASE]

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(
            label=_("Simulate a mouse click.\nOn Wayland requires write access to /dev/uinput."), halign=Gtk.Align.CENTER
        )
        self.widgets[self.label] = (0, 0, 4, 1)
        self.label_b = Gtk.Label(label=_("Button"), halign=Gtk.Align.END, valign=Gtk.Align.CENTER, hexpand=True)
        self.label_c = Gtk.Label(label=_("Count and Action"), halign=Gtk.Align.END, valign=Gtk.Align.CENTER, hexpand=True)
        self.field_b = CompletionEntry(self.BUTTONS)
        self.field_c = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        self.field_d = CompletionEntry(self.ACTIONS)
        for f in [self.field_b, self.field_c]:
            f.set_halign(Gtk.Align.CENTER)
            f.set_valign(Gtk.Align.START)
        self.field_b.connect(GtkSignal.CHANGED.value, self._on_update)
        self.field_c.connect(GtkSignal.CHANGED.value, self._on_update)
        self.field_d.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.label_b] = (0, 1, 1, 1)
        self.widgets[self.field_b] = (1, 1, 1, 1)
        self.widgets[self.label_c] = (2, 1, 1, 1)
        self.widgets[self.field_c] = (3, 1, 1, 1)
        self.widgets[self.field_d] = (4, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.field_b.set_text(component.button)
            if isinstance(component.count, int):
                self.field_c.set_value(component.count)
                self.field_d.set_text(CLICK)
            else:
                self.field_c.set_value(1)
                self.field_d.set_text(component.count)

    def collect_value(self):
        b, c, d = self.field_b.get_text(), int(self.field_c.get_value()), self.field_d.get_text()
        if b not in self.BUTTONS:
            b = "unknown"
        if d != CLICK:
            c = d
        return [b, c]

    @classmethod
    def left_label(cls, component):
        return _("Mouse click")

    @classmethod
    def right_label(cls, component):
        return f'{component.button} ({"x" if isinstance(component.count, int) else ""}{component.count})'


class ExecuteUI(ActionUI):
    CLASS = diversion.Execute

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(label=_("Execute a command with arguments."), halign=Gtk.Align.CENTER)
        self.widgets[self.label] = (0, 0, 5, 1)
        self.fields = []
        self.add_btn = Gtk.Button(label=_("Add argument"), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
        self.del_btns = []
        self.add_btn.connect(GtkSignal.CLICKED.value, self._clicked_add)
        self.widgets[self.add_btn] = (1, 1, 1, 1)

    def _create_field(self):
        field_entry = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
        field_entry.set_size_request(150, 0)
        field_entry.connect(GtkSignal.CHANGED.value, self._on_update)
        self.fields.append(field_entry)
        self.widgets[field_entry] = (len(self.fields) - 1, 1, 1, 1)
        return field_entry

    def _create_del_btn(self):
        btn = Gtk.Button(label=_("Delete"), halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True)
        btn.set_size_request(150, 0)
        self.del_btns.append(btn)
        self.widgets[btn] = (len(self.del_btns) - 1, 2, 1, 1)
        btn.connect(GtkSignal.CLICKED.value, self._clicked_del, len(self.del_btns) - 1)
        return btn

    def _clicked_add(self, *_args):
        self.component.__init__(self.collect_value() + [""], warn=False)
        self.show(self.component, editable=True)
        self.fields[len(self.component.args) - 1].grab_focus()

    def _clicked_del(self, _btn, pos):
        v = self.collect_value()
        v.pop(pos)
        self.component.__init__(v, warn=False)
        self.show(self.component, editable=True)
        self._on_update_callback()

    def show(self, component, editable=True):
        n = len(component.args)
        while len(self.fields) < n:
            self._create_field()
            self._create_del_btn()
        for i in range(n):
            field_entry = self.fields[i]
            with self.ignore_changes():
                field_entry.set_text(component.args[i])
            self.del_btns[i].show()
        self.widgets[self.add_btn] = (n + 1, 1, 1, 1)
        super().show(component, editable)
        for i in range(n, len(self.fields)):
            self.fields[i].hide()
            self.del_btns[i].hide()
        self.add_btn.set_valign(Gtk.Align.END if n >= 1 else Gtk.Align.CENTER)

    def collect_value(self):
        return [f.get_text() for f in self.fields if f.get_visible()]

    @classmethod
    def left_label(cls, component):
        return _("Execute")

    @classmethod
    def right_label(cls, component):
        return " ".join([shlex_quote(a) for a in component.args])
