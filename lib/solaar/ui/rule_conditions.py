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
from dataclasses import dataclass
from enum import Enum

from gi.repository import Gtk
from logitech_receiver import diversion
from logitech_receiver.diversion import Key
from logitech_receiver.hidpp20 import SupportedFeature
from logitech_receiver.special_keys import CONTROL

from solaar.i18n import _
from solaar.ui.rule_base import CompletionEntry
from solaar.ui.rule_base import RuleComponentUI


class GtkSignal(Enum):
    CHANGED = "changed"
    CLICKED = "clicked"
    NOTIFY_ACTIVE = "notify::active"
    TOGGLED = "toggled"
    VALUE_CHANGED = "value-changed"


class ConditionUI(RuleComponentUI):
    CLASS = diversion.Condition

    @classmethod
    def icon_name(cls):
        return "dialog-question"


class ProcessUI(ConditionUI):
    CLASS = diversion.Process

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("X11 active process. For use in X11 only."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.field.set_size_request(600, 0)
        self.field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.field] = (0, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.field.set_text(component.process)

    def collect_value(self):
        return self.field.get_text()

    @classmethod
    def left_label(cls, component):
        return _("Process")

    @classmethod
    def right_label(cls, component):
        return str(component.process)


class MouseProcessUI(ConditionUI):
    CLASS = diversion.MouseProcess

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("X11 mouse process. For use in X11 only."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.field.set_size_request(600, 0)
        self.field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.field] = (0, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.field.set_text(component.process)

    def collect_value(self):
        return self.field.get_text()

    @classmethod
    def left_label(cls, component):
        return _("MouseProcess")

    @classmethod
    def right_label(cls, component):
        return str(component.process)


class FeatureUI(ConditionUI):
    CLASS = diversion.Feature
    FEATURES_WITH_DIVERSION = [
        str(SupportedFeature.CROWN),
        str(SupportedFeature.THUMB_WHEEL),
        str(SupportedFeature.LOWRES_WHEEL),
        str(SupportedFeature.HIRES_WHEEL),
        str(SupportedFeature.GESTURE_2),
        str(SupportedFeature.REPROG_CONTROLS_V4),
        str(SupportedFeature.GKEY),
        str(SupportedFeature.MKEYS),
        str(SupportedFeature.MR),
    ]

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Feature name of notification triggering rule processing."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.ComboBoxText.new_with_entry()
        self.field.append("", "")
        for feature in self.FEATURES_WITH_DIVERSION:
            self.field.append(feature, feature)
        self.field.set_valign(Gtk.Align.CENTER)
        self.field.set_size_request(600, 0)
        self.field.connect(GtkSignal.CHANGED.value, self._on_update)
        all_features = [str(f) for f in SupportedFeature]
        CompletionEntry.add_completion_to_entry(self.field.get_child(), all_features)
        self.widgets[self.field] = (0, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            f = str(component.feature) if component.feature else ""
            self.field.set_active_id(f)
            if f not in self.FEATURES_WITH_DIVERSION:
                self.field.get_child().set_text(f)

    def collect_value(self):
        return (self.field.get_active_text() or "").strip()

    def _on_update(self, *args):
        super()._on_update(*args)
        icon = "dialog-warning" if not self.component.feature else ""
        self.field.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _("Feature")

    @classmethod
    def right_label(cls, component):
        return f"{str(component.feature)} ({int(component.feature or 0):04X})"


class ReportUI(ConditionUI):
    CLASS = diversion.Report
    MIN_VALUE = -1  # for invalid values
    MAX_VALUE = 15

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Report number of notification triggering rule processing."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        self.field.set_halign(Gtk.Align.CENTER)
        self.field.set_valign(Gtk.Align.CENTER)
        self.field.set_hexpand(True)
        self.field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.field] = (0, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.field.set_value(component.report)

    def collect_value(self):
        return int(self.field.get_value())

    @classmethod
    def left_label(cls, component):
        return _("Report")

    @classmethod
    def right_label(cls, component):
        return str(component.report)


class ModifiersUI(ConditionUI):
    CLASS = diversion.Modifiers

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Active keyboard modifiers. Not always available in Wayland."))
        self.widgets[self.label] = (0, 0, 5, 1)
        self.labels = {}
        self.switches = {}
        for i, m in enumerate(diversion.MODIFIERS):
            switch = Gtk.Switch(halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True)
            label = Gtk.Label(label=m, halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
            self.widgets[label] = (i, 1, 1, 1)
            self.widgets[switch] = (i, 2, 1, 1)
            self.labels[m] = label
            self.switches[m] = switch
            switch.connect(GtkSignal.NOTIFY_ACTIVE.value, self._on_update)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            for m in diversion.MODIFIERS:
                self.switches[m].set_active(m in component.modifiers)

    def collect_value(self):
        return [m for m, s in self.switches.items() if s.get_active()]

    @classmethod
    def left_label(cls, component):
        return _("Modifiers")

    @classmethod
    def right_label(cls, component):
        return "+".join(component.modifiers) or "None"


class KeyUI(ConditionUI):
    CLASS = diversion.Key
    KEY_NAMES = map(str, CONTROL)

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(
            _(
                "Diverted key or button depressed or released.\n"
                "Use the Key/Button Diversion and Divert G Keys settings to divert keys and buttons."
            )
        )
        self.widgets[self.label] = (0, 0, 5, 1)
        self.key_field = CompletionEntry(self.KEY_NAMES, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.key_field.set_size_request(600, 0)
        self.key_field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.key_field] = (0, 1, 2, 1)
        self.action_pressed_radio = Gtk.RadioButton.new_with_label_from_widget(None, _("Key down"))
        self.action_pressed_radio.connect(GtkSignal.TOGGLED.value, self._on_update, Key.DOWN)
        self.widgets[self.action_pressed_radio] = (2, 1, 1, 1)
        self.action_released_radio = Gtk.RadioButton.new_with_label_from_widget(self.action_pressed_radio, _("Key up"))
        self.action_released_radio.connect(GtkSignal.TOGGLED.value, self._on_update, Key.UP)
        self.widgets[self.action_released_radio] = (3, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.key_field.set_text(str(component.key) if self.component.key else "")
            if not component.action or component.action == Key.DOWN:
                self.action_pressed_radio.set_active(True)
            else:
                self.action_released_radio.set_active(True)

    def collect_value(self):
        action = Key.UP if self.action_released_radio.get_active() else Key.DOWN
        return [self.key_field.get_text(), action]

    def _on_update(self, *args):
        super()._on_update(*args)
        icon = "dialog-warning" if not self.component.key or not self.component.action else ""
        self.key_field.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _("Key")

    @classmethod
    def right_label(cls, component):
        return f"{str(component.key)} ({int(component.key):04X}) ({_(component.action)})" if component.key else "None"


class KeyIsDownUI(ConditionUI):
    CLASS = diversion.KeyIsDown
    KEY_NAMES = map(str, CONTROL)

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(
            _(
                "Diverted key or button is currently down.\n"
                "Use the Key/Button Diversion and Divert G Keys settings to divert keys and buttons."
            )
        )
        self.widgets[self.label] = (0, 0, 5, 1)
        self.key_field = CompletionEntry(self.KEY_NAMES, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.key_field.set_size_request(600, 0)
        self.key_field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.key_field] = (0, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.key_field.set_text(str(component.key) if self.component.key else "")

    def collect_value(self):
        return self.key_field.get_text()

    def _on_update(self, *args):
        super()._on_update(*args)
        icon = "dialog-warning" if not self.component.key else ""
        self.key_field.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _("KeyIsDown")

    @classmethod
    def right_label(cls, component):
        return f"{str(component.key)} ({int(component.key):04X})" if component.key else "None"


class TestUI(ConditionUI):
    CLASS = diversion.Test

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Test condition on notification triggering rule processing."))
        self.widgets[self.label] = (0, 0, 4, 1)
        lbl = Gtk.Label(label=_("Test"), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=False, vexpand=False)
        self.widgets[lbl] = (0, 1, 1, 1)
        lbl = Gtk.Label(label=_("Parameter"), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=False, vexpand=False)
        self.widgets[lbl] = (2, 1, 1, 1)

        self.test = Gtk.ComboBoxText.new_with_entry()
        self.test.append("", "")
        for t in diversion.TESTS:
            self.test.append(t, t)
        self.test.set_halign(Gtk.Align.END)
        self.test.set_valign(Gtk.Align.CENTER)
        self.test.set_hexpand(False)
        self.test.set_size_request(300, 0)
        CompletionEntry.add_completion_to_entry(self.test.get_child(), diversion.TESTS)
        self.test.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.test] = (1, 1, 1, 1)

        self.parameter = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
        self.parameter.set_size_request(150, 0)
        self.parameter.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.parameter] = (3, 1, 1, 1)

    def show(self, component, editable=True):
        super().show(component, editable)
        with self.ignore_changes():
            self.test.set_active_id(component.test)
            self.parameter.set_text(str(component.parameter) if component.parameter is not None else "")
            if component.test not in diversion.TESTS:
                self.test.get_child().set_text(component.test)
                self._change_status_icon()

    def collect_value(self):
        try:
            param = int(self.parameter.get_text()) if self.parameter.get_text() else None
        except Exception:
            param = self.parameter.get_text()
        test = (self.test.get_active_text() or "").strip()
        return [test, param] if param is not None else [test]

    def _on_update(self, *args):
        super()._on_update(*args)
        self._change_status_icon()

    def _change_status_icon(self):
        icon = "dialog-warning" if (self.test.get_active_text() or "").strip() not in diversion.TESTS else ""
        self.test.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _("Test")

    @classmethod
    def right_label(cls, component):
        return component.test + (" " + repr(component.parameter) if component.parameter is not None else "")


@dataclass
class TestBytesElement:
    id: str
    label: str
    min: int
    max: int


@dataclass
class TestBytesMode:
    label: str
    elements: list
    label_fn: callable


class TestBytesUI(ConditionUI):
    CLASS = diversion.TestBytes

    _common_elements = [
        TestBytesElement("begin", _("begin (inclusive)"), 0, 16),
        TestBytesElement("end", _("end (exclusive)"), 0, 16),
    ]

    _global_min = -(2**31)
    _global_max = 2**31 - 1

    _modes = {
        "range": TestBytesMode(
            _("range"),
            _common_elements
            + [
                TestBytesElement("minimum", _("minimum"), _global_min, _global_max),  # uint32
                TestBytesElement("maximum", _("maximum"), _global_min, _global_max),
            ],
            lambda e: _("bytes %(0)d to %(1)d, ranging from %(2)d to %(3)d" % {str(i): v for i, v in enumerate(e)}),
        ),
        "mask": TestBytesMode(
            _("mask"),
            _common_elements + [TestBytesElement("mask", _("mask"), _global_min, _global_max)],
            lambda e: _("bytes %(0)d to %(1)d, mask %(2)d" % {str(i): v for i, v in enumerate(e)}),
        ),
    }

    def create_widgets(self):
        self.fields = {}
        self.field_labels = {}
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Bit or range test on bytes in notification message triggering rule processing."))
        self.widgets[self.label] = (0, 0, 5, 1)
        col = 0
        mode_col = 2
        self.mode_field = Gtk.ComboBox.new_with_model(Gtk.ListStore(str, str))
        mode_renderer = Gtk.CellRendererText()
        self.mode_field.set_id_column(0)
        self.mode_field.pack_start(mode_renderer, True)
        self.mode_field.add_attribute(mode_renderer, "text", 1)
        self.widgets[self.mode_field] = (mode_col, 2, 1, 1)
        mode_label = Gtk.Label(label=_("type"), margin_top=20)
        self.widgets[mode_label] = (mode_col, 1, 1, 1)
        for mode_id, mode in TestBytesUI._modes.items():
            self.mode_field.get_model().append([mode_id, mode.label])
            for element in mode.elements:
                if element.id not in self.fields:
                    field = Gtk.SpinButton.new_with_range(element.min, element.max, 1)
                    field.set_value(0)
                    field.set_size_request(150, 0)
                    field.connect(GtkSignal.VALUE_CHANGED.value, self._on_update)
                    label = Gtk.Label(label=element.label, margin_top=20)
                    self.fields[element.id] = field
                    self.field_labels[element.id] = label
                    self.widgets[label] = (col, 1, 1, 1)
                    self.widgets[field] = (col, 2, 1, 1)
                    col += 1 if col != mode_col - 1 else 2
        self.mode_field.connect(GtkSignal.CHANGED.value, lambda cb: (self._on_update(), self._only_mode(cb.get_active_id())))
        self.mode_field.set_active_id("range")

    def show(self, component, editable=True):
        super().show(component, editable)

        with self.ignore_changes():
            mode_id = {3: "mask", 4: "range"}.get(len(component.test), None)
            self._only_mode(mode_id)
            if not mode_id:
                return
            self.mode_field.set_active_id(mode_id)
            if mode_id:
                mode = TestBytesUI._modes[mode_id]
                for i, element in enumerate(mode.elements):
                    self.fields[element.id].set_value(component.test[i])

    def collect_value(self):
        mode_id = self.mode_field.get_active_id()
        return [self.fields[element.id].get_value_as_int() for element in TestBytesUI._modes[mode_id].elements]

    def _only_mode(self, mode_id):
        if not mode_id:
            return
        keep = {element.id for element in TestBytesUI._modes[mode_id].elements}
        for element_id, f in self.fields.items():
            visible = element_id in keep
            f.set_visible(visible)
            self.field_labels[element_id].set_visible(visible)

    def _on_update(self, *args):
        super()._on_update(*args)
        if not self.component:
            return
        begin, end, *etc = self.component.test
        icon = "dialog-warning" if end <= begin else ""
        self.fields["end"].set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        if len(self.component.test) == 4:
            *etc, minimum, maximum = self.component.test
            icon = "dialog-warning" if maximum < minimum else ""
            self.fields["maximum"].set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _("Test bytes")

    @classmethod
    def right_label(cls, component):
        mode_id = {3: "mask", 4: "range"}.get(len(component.test), None)
        if not mode_id:
            return str(component.test)
        return TestBytesUI._modes[mode_id].label_fn(component.test)


class MouseGestureUI(ConditionUI):
    CLASS = diversion.MouseGesture
    MOUSE_GESTURE_NAMES = [
        "Mouse Up",
        "Mouse Down",
        "Mouse Left",
        "Mouse Right",
        "Mouse Up-left",
        "Mouse Up-right",
        "Mouse Down-left",
        "Mouse Down-right",
    ]
    MOVE_NAMES = list(map(str, CONTROL)) + MOUSE_GESTURE_NAMES

    def create_widgets(self):
        self.widgets = {}
        self.fields = []
        self.label = Gtk.Label(
            label=_("Mouse gesture with optional initiating button followed by zero or more mouse movements."),
            halign=Gtk.Align.CENTER,
        )
        self.widgets[self.label] = (0, 0, 5, 1)
        self.del_btns = []
        self.add_btn = Gtk.Button(label=_("Add movement"), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True)
        self.add_btn.connect(GtkSignal.CLICKED.value, self._clicked_add)
        self.widgets[self.add_btn] = (1, 1, 1, 1)

    def _create_field(self):
        field = Gtk.ComboBoxText.new_with_entry()
        for g in self.MOUSE_GESTURE_NAMES:
            field.append(g, g)
        CompletionEntry.add_completion_to_entry(field.get_child(), self.MOVE_NAMES)
        field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.fields.append(field)
        self.widgets[field] = (len(self.fields) - 1, 1, 1, 1)
        return field

    def _create_del_btn(self):
        btn = Gtk.Button(label=_("Delete"), halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True)
        self.del_btns.append(btn)
        self.widgets[btn] = (len(self.del_btns) - 1, 2, 1, 1)
        btn.connect(GtkSignal.CLICKED.value, self._clicked_del, len(self.del_btns) - 1)
        return btn

    def _clicked_add(self, _btn):
        self.component.__init__(self.collect_value() + [""], warn=False)
        self.show(self.component, editable=True)
        self.fields[len(self.component.movements) - 1].grab_focus()

    def _clicked_del(self, _btn, pos):
        v = self.collect_value()
        v.pop(pos)
        self.component.__init__(v, warn=False)
        self.show(self.component, editable=True)
        self._on_update_callback()

    def _on_update(self, *args):
        super()._on_update(*args)
        for i, f in enumerate(self.fields):
            if f.get_visible():
                icon = (
                    "dialog-warning"
                    if i < len(self.component.movements) and self.component.movements[i] not in self.MOVE_NAMES
                    else ""
                )
                f.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    def show(self, component, editable=True):
        n = len(component.movements)
        while len(self.fields) < n:
            self._create_field()
            self._create_del_btn()
        self.widgets[self.add_btn] = (n + 1, 1, 1, 1)
        super().show(component, editable)
        for i in range(n):
            field = self.fields[i]
            with self.ignore_changes():
                field.get_child().set_text(component.movements[i])
            field.set_size_request(int(0.3 * self.panel.get_toplevel().get_size()[0]), 0)
            field.show_all()
            self.del_btns[i].show()
        for i in range(n, len(self.fields)):
            self.fields[i].hide()
            self.del_btns[i].hide()
        self.add_btn.set_valign(Gtk.Align.END if n >= 1 else Gtk.Align.CENTER)

    def collect_value(self):
        return [f.get_active_text().strip() for f in self.fields if f.get_visible()]

    @classmethod
    def left_label(cls, component):
        return _("Mouse Gesture")

    @classmethod
    def right_label(cls, component):
        if len(component.movements) == 0:
            return "No-op"
        else:
            return " -> ".join(component.movements)
