## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

import logging
import traceback

from enum import Enum
from threading import Timer

import gi

from logitech_receiver import hidpp20
from logitech_receiver import settings

from solaar.i18n import _
from solaar.i18n import ngettext

from .common import ui_async

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk  # NOQA: E402
from gi.repository import GLib  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

logger = logging.getLogger(__name__)


class GtkSignal(Enum):
    ACTIVATE = "activate"
    CHANGED = "changed"
    CLICKED = "clicked"
    MATCH_SELECTED = "match_selected"
    NOTIFY_ACTIVE = "notify::active"
    TOGGLED = "toggled"
    VALUE_CHANGED = "value-changed"


def _read_async(setting, force_read, sbox, device_is_online, sensitive):
    def _do_read(s, force, sb, online, sensitive):
        try:
            v = s.read(not force)
        except Exception as e:
            v = None
            logger.warning("%s: error reading so use None (%s): %s", s.name, s._device, repr(e))
        GLib.idle_add(_update_setting_item, sb, v, online, sensitive, True, priority=99)

    ui_async(_do_read, setting, force_read, sbox, device_is_online, sensitive)


def _write_async(setting, value, sbox, sensitive=True, key=None):
    def _do_write(_s, v, sb, key):
        try:
            if key is None:
                v = setting.write(v)
            else:
                v = setting.write_key_value(key, v)
                v = {key: v}
        except Exception:
            traceback.print_exc()
            v = None
        if sb:
            GLib.idle_add(_update_setting_item, sb, v, True, sensitive, priority=99)

    if sbox:
        sbox._control.set_sensitive(False)
        sbox._failed.set_visible(False)
        sbox._spinner.set_visible(True)
        sbox._spinner.start()
    ui_async(_do_write, setting, value, sbox, key)


class ComboBoxText(Gtk.ComboBoxText):
    def get_value(self):
        return int(self.get_active_id())

    def set_value(self, value):
        return self.set_active_id(str(int(value)))


class Scale(Gtk.Scale):
    def get_value(self):
        return int(super().get_value())


class Control:
    def __init__(self, **kwargs):
        self.sbox = None
        self.delegate = None

    def init(self, sbox, delegate):
        self.sbox = sbox
        self.delegate = delegate if delegate else self

    def changed(self, *args):
        if self.get_sensitive():
            self.delegate.update()

    def update(self):
        _write_async(self.sbox.setting, self.get_value(), self.sbox)

    def layout(self, sbox, label, change, spinner, failed):
        sbox.pack_start(label, False, False, 0)
        sbox.pack_end(change, False, False, 0)
        fill = sbox.setting.kind == settings.Kind.RANGE or sbox.setting.kind == settings.Kind.HETERO
        sbox.pack_end(self, fill, fill, 0)
        sbox.pack_end(spinner, False, False, 0)
        sbox.pack_end(failed, False, False, 0)
        return self


class ToggleControl(Gtk.Switch, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.init(sbox, delegate)
        self.connect(GtkSignal.NOTIFY_ACTIVE.value, self.changed)

    def set_value(self, value):
        if value is not None:
            self.set_state(value)

    def get_value(self):
        return self.get_state()


class SliderControl(Gtk.Scale, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.init(sbox, delegate)
        self.timer = None
        self.set_range(*self.sbox.setting.range)
        self.set_round_digits(0)
        self.set_digits(0)
        self.set_increments(1, 5)
        self.connect(GtkSignal.VALUE_CHANGED.value, self.changed)

    def get_value(self):
        return int(super().get_value())

    def changed(self, *args):
        if self.get_sensitive():
            if self.timer:
                self.timer.cancel()
            self.timer = Timer(0.5, lambda: GLib.idle_add(self.do_change))
            self.timer.start()

    def do_change(self):
        self.timer.cancel()
        self.update()


def _create_choice_control(sbox, delegate=None, choices=None):
    if 50 > len(choices if choices else sbox.setting.choices):
        return ChoiceControlLittle(sbox, choices=choices, delegate=delegate)
    else:
        return ChoiceControlBig(sbox, choices=choices, delegate=delegate)


# GTK boxes have property lists, but the keys must be strings
class ChoiceControlLittle(Gtk.ComboBoxText, Control):
    def __init__(self, sbox, delegate=None, choices=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.init(sbox, delegate)
        self.choices = choices if choices is not None else sbox.setting.choices
        for entry in self.choices:
            self.append(str(int(entry)), str(entry))
        self.connect(GtkSignal.CHANGED.value, self.changed)

    def get_value(self):
        return int(self.get_active_id()) if self.get_active_id() is not None else None

    def set_value(self, value):
        if value is not None:
            self.set_active_id(str(int(value)))

    def get_choice(self):
        id = self.get_value()
        return next((x for x in self.choices if x == id), None)

    def set_choices(self, choices):
        self.remove_all()
        for choice in choices:
            self.append(str(int(choice)), _(str(choice)))


class ChoiceControlBig(Gtk.Entry, Control):
    def __init__(self, sbox, delegate=None, choices=None):
        super().__init__(halign=Gtk.Align.FILL)
        self.init(sbox, delegate)
        self.choices = choices if choices is not None else sbox.setting.choices
        self.value = None
        self.set_width_chars(max([len(str(x)) for x in self.choices]) + 5)
        liststore = Gtk.ListStore(int, str)
        for v in self.choices:
            liststore.append((int(v), str(v)))
        completion = Gtk.EntryCompletion()
        completion.set_model(liststore)

        def norm(s):
            return s.replace("_", "").replace(" ", "").lower()

        completion.set_match_func(lambda completion, key, it: norm(key) in norm(completion.get_model()[it][1]))
        completion.set_text_column(1)
        self.set_completion(completion)
        self.connect(GtkSignal.CHANGED.value, self.changed)
        self.connect(GtkSignal.ACTIVATE.value, self.activate)
        completion.connect(GtkSignal.MATCH_SELECTED.value, self.select)

    def get_value(self):
        choice = self.get_choice()
        return int(choice) if choice is not None else None

    def set_value(self, value):
        if value is not None:
            self.set_text(str(next((x for x in self.choices if x == value), None)))

    def get_choice(self):
        key = self.get_text()
        return next((x for x in self.choices if x == key), None)

    def changed(self, *args):
        self.value = self.get_choice()
        icon = "dialog-warning" if self.value is None else "dialog-question" if self.get_sensitive() else ""
        self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        tooltip = _("Incomplete") if self.value is None else _("Complete - ENTER to change")
        self.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, tooltip)

    def activate(self, *_args):
        if self.value is not None and self.get_sensitive():
            self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "")
            self.delegate.update()

    def select(self, _completion, model, iter):
        self.set_value(model.get(iter, 0)[0])
        if self.value and self.get_sensitive():
            self.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "")
            self.delegate.update()


class MapChoiceControl(Gtk.HBox, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(homogeneous=False, spacing=6)
        self.init(sbox, delegate)
        self.keyBox = Gtk.ComboBoxText()
        for entry in sbox.setting.choices:
            self.keyBox.append(str(int(entry)), _(str(entry)))
        self.keyBox.set_active(0)
        key_choice = int(self.keyBox.get_active_id())
        self.value_choices = self.sbox.setting.choices[key_choice]
        self.valueBox = _create_choice_control(sbox.setting, choices=self.value_choices, delegate=self)
        self.pack_start(self.keyBox, False, False, 0)
        self.pack_end(self.valueBox, False, False, 0)
        self.keyBox.connect(GtkSignal.CHANGED.value, self.map_value_notify_key)

    def get_value(self):
        key_choice = int(self.keyBox.get_active_id())
        if key_choice is not None and self.valueBox.get_value() is not None:
            return self.valueBox.get_value()

    def set_value(self, value):
        if value is None:
            return
        self.valueBox.set_sensitive(self.get_sensitive())
        key = int(self.keyBox.get_active_id())
        if value.get(key) is not None:
            self.valueBox.set_value(value.get(key))
        self.valueBox.set_sensitive(True)

    def map_populate_value_box(self, key_choice):
        choices = self.sbox.setting.choices[key_choice]
        if choices != self.value_choices:
            self.value_choices = choices
            self.valueBox.remove_all()
            self.valueBox.set_choices(choices)
        current = self.sbox.setting._value.get(key_choice) if self.sbox.setting._value else None
        if current is not None:
            self.valueBox.set_value(current)

    def map_value_notify_key(self, *_args):
        key_choice = int(self.keyBox.get_active_id())
        if self.keyBox.get_sensitive():
            self.map_populate_value_box(key_choice)

    def update(self):
        key_choice = int(self.keyBox.get_active_id())
        value = self.get_value()
        if value is not None and self.valueBox.get_sensitive() and self.sbox.setting._value.get(key_choice) != value:
            self.sbox.setting._value[int(key_choice)] = value
            _write_async(self.sbox.setting, value, self.sbox, key=int(key_choice))


class MultipleControl(Gtk.ListBox, Control):
    def __init__(self, sbox, change, button_label="...", delegate=None):
        super().__init__()
        self.init(sbox, delegate)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_no_show_all(True)
        self._showing = True
        self.setup(sbox.setting)  # set up the data and boxes for the sub-controls
        btn = Gtk.Button(label=button_label)
        btn.connect(GtkSignal.CLICKED.value, self.toggle_display)
        self._button = btn
        hbox = Gtk.HBox(homogeneous=False, spacing=6)
        hbox.pack_end(change, False, False, 0)
        hbox.pack_end(btn, False, False, 0)
        self._header = hbox
        vbox = Gtk.VBox(homogeneous=False, spacing=6)
        vbox.pack_start(hbox, True, True, 0)
        vbox.pack_end(self, True, True, 0)
        self.vbox = vbox
        self.toggle_display()
        _disable_listbox_highlight_bg(self)

    def layout(self, sbox, label, change, spinner, failed):
        self._header.pack_start(label, False, False, 0)
        self._header.pack_end(spinner, False, False, 0)
        self._header.pack_end(failed, False, False, 0)
        sbox.pack_start(self.vbox, True, True, 0)
        sbox._button = self._button
        return True

    def toggle_display(self, *_args):
        self._showing = not self._showing
        if not self._showing:
            for c in self.get_children():
                c.hide()
            self.hide()
        else:
            self.show()
            for c in self.get_children():
                c.show_all()


class MultipleToggleControl(MultipleControl):
    def setup(self, setting):
        self._label_control_pairs = []
        for k in setting._validator.get_options():
            h = Gtk.HBox(homogeneous=False, spacing=0)
            lbl_text = str(k)
            lbl_tooltip = None
            if hasattr(setting, "_labels"):
                l1, l2 = setting._labels.get(k, (None, None))
                lbl_text = l1 if l1 else lbl_text
                lbl_tooltip = l2 if l2 else lbl_tooltip
            lbl = Gtk.Label(label=lbl_text)
            h.set_tooltip_text(lbl_tooltip or " ")
            control = Gtk.Switch()
            control._setting_key = int(k)
            control.connect(GtkSignal.NOTIFY_ACTIVE.value, self.toggle_notify)
            h.pack_start(lbl, False, False, 0)
            h.pack_end(control, False, False, 0)
            lbl.set_margin_start(30)
            self.add(h)
            self._label_control_pairs.append((lbl, control))

    def toggle_notify(self, switch, _active):
        if switch.get_sensitive():
            key = switch._setting_key
            new_state = switch.get_state()
            if self.sbox.setting._value[key] != new_state:
                self.sbox.setting._value[key] = new_state
                _write_async(self.sbox.setting, new_state, self.sbox, key=int(key))

    def set_value(self, value):
        if value is None:
            return
        active = 0
        total = len(self._label_control_pairs)
        to_join = []
        for lbl, elem in self._label_control_pairs:
            v = value.get(elem._setting_key, None)
            if v is not None:
                elem.set_state(v)
            if elem.get_state():
                active += 1
            to_join.append(lbl.get_text() + ": " + str(elem.get_state()))
        b = ", ".join(to_join)
        self._button.set_label(f"{active} / {total}")
        self._button.set_tooltip_text(b)


class MultipleRangeControl(MultipleControl):
    def setup(self, setting):
        self._items = []
        for item in setting._validator.items:
            lbl_text = str(item)
            lbl_tooltip = None
            if hasattr(setting, "_labels"):
                l1, l2 = setting._labels.get(int(item), (None, None))
                lbl_text = l1 if l1 else lbl_text
                lbl_tooltip = l2 if l2 else lbl_tooltip
            item_lbl = Gtk.Label(label=lbl_text)
            self.add(item_lbl)
            self.set_tooltip_text(lbl_tooltip or " ")
            item_lb = Gtk.ListBox()
            item_lb.set_selection_mode(Gtk.SelectionMode.NONE)
            item_lb._sub_items = []
            for sub_item in setting._validator.sub_items[item]:
                h = Gtk.HBox(homogeneous=False, spacing=20)
                lbl_text = str(sub_item)
                lbl_tooltip = None
                if hasattr(setting, "_labels_sub"):
                    l1, l2 = setting._labels_sub.get(str(sub_item), (None, None))
                    lbl_text = l1 if l1 else lbl_text
                    lbl_tooltip = l2 if l2 else lbl_tooltip
                sub_item_lbl = Gtk.Label(label=lbl_text)
                h.set_tooltip_text(lbl_tooltip or " ")
                h.pack_start(sub_item_lbl, False, False, 0)
                sub_item_lbl.set_margin_start(30)
                if sub_item.widget == "Scale":
                    control = Gtk.Scale.new_with_range(
                        Gtk.Orientation.HORIZONTAL,
                        sub_item.minimum,
                        sub_item.maximum,
                        1,
                    )
                    control.set_round_digits(0)
                    control.set_digits(0)
                    h.pack_end(control, True, True, 0)
                elif sub_item.widget == "SpinButton":
                    control = Gtk.SpinButton.new_with_range(sub_item.minimum, sub_item.maximum, 1)
                    control.set_digits(0)
                    h.pack_end(control, False, False, 0)
                else:
                    raise NotImplementedError
                control.connect(GtkSignal.VALUE_CHANGED.value, self.changed, item, sub_item)
                item_lb.add(h)
                h._setting_sub_item = sub_item
                h._label, h._control = sub_item_lbl, control
                item_lb._sub_items.append(h)
            item_lb._setting_item = item
            _disable_listbox_highlight_bg(item_lb)
            self.add(item_lb)
            self._items.append(item_lb)

    def changed(self, control, item, sub_item):
        if control.get_sensitive():
            if hasattr(control, "_timer"):
                control._timer.cancel()
            control._timer = Timer(0.5, lambda: GLib.idle_add(self._write, control, item, sub_item))
            control._timer.start()

    def _write(self, control, item, sub_item):
        control._timer.cancel()
        delattr(control, "_timer")
        new_state = int(control.get_value())
        if self.sbox.setting._value[int(item)][str(sub_item)] != new_state:
            self.sbox.setting._value[int(item)][str(sub_item)] = new_state
            _write_async(self.sbox.setting, self.sbox.setting._value[int(item)], self.sbox, key=int(item))

    def set_value(self, value):
        if value is None:
            return
        b = ""
        n = 0
        for ch in self._items:
            item = ch._setting_item
            v = value.get(int(item), None)
            if v is not None:
                b += str(item) + ": ("
                to_join = []
                for c in ch._sub_items:
                    sub_item = c._setting_sub_item
                    try:
                        sub_item_value = v[str(sub_item)]
                    except KeyError:
                        sub_item_value = c._control.get_value()
                    c._control.set_value(sub_item_value)
                    n += 1
                    to_join.append(str(sub_item) + f"={sub_item_value}")
                b += ", ".join(to_join) + ") "
        lbl_text = ngettext("%d value", "%d values", n) % n
        self._button.set_label(lbl_text)
        self._button.set_tooltip_text(b)


class PackedRangeControl(MultipleRangeControl):
    def setup(self, setting):
        self._items = []
        validator = setting._validator
        for item in range(validator.count):
            h = Gtk.HBox(homogeneous=False, spacing=0)
            lbl = Gtk.Label(label=str(validator.keys[item]))
            control = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, validator.min_value, validator.max_value, 1)
            control.set_round_digits(0)
            control.set_digits(0)
            control.connect(GtkSignal.VALUE_CHANGED.value, self.changed, validator.keys[item])
            h.pack_start(lbl, False, False, 0)
            h.pack_end(control, True, True, 0)
            h._setting_item = validator.keys[item]
            h.control = control
            lbl.set_margin_start(30)
            self.add(h)
            self._items.append(h)

    def changed(self, control, item):
        if control.get_sensitive():
            if hasattr(control, "_timer"):
                control._timer.cancel()
            control._timer = Timer(0.5, lambda: GLib.idle_add(self._write, control, item))
            control._timer.start()

    def _write(self, control, item):
        control._timer.cancel()
        delattr(control, "_timer")
        new_state = int(control.get_value())
        if self.sbox.setting._value[int(item)] != new_state:
            self.sbox.setting._value[int(item)] = new_state
            _write_async(self.sbox.setting, self.sbox.setting._value[int(item)], self.sbox, key=int(item))

    def set_value(self, value):
        if value is None:
            return
        b = ""
        n = len(self._items)
        for h in self._items:
            item = h._setting_item
            v = value.get(int(item), None)
            if v is not None:
                h.control.set_value(v)
            else:
                v = self.sbox.setting._value[int(item)]
            b += str(item) + ": (" + str(v) + ") "
        lbl_text = ngettext("%d value", "%d values", n) % n
        self._button.set_label(lbl_text)
        self._button.set_tooltip_text(b)


# control with an ID key that determines what else to show
class HeteroKeyControl(Gtk.HBox, Control):
    def __init__(self, sbox, delegate=None):
        super().__init__(homogeneous=False, spacing=6)
        self.init(sbox, delegate)
        self._items = {}
        for item in sbox.setting.possible_fields:
            if item["label"]:
                item_lblbox = Gtk.Label(label=item["label"])
                self.pack_start(item_lblbox, False, False, 0)
                item_lblbox.set_visible(False)
            else:
                item_lblbox = None

            item_box = ComboBoxText()
            if item["kind"] == settings.Kind.CHOICE:
                for entry in item["choices"]:
                    item_box.append(str(int(entry)), str(entry))
                item_box.set_active(0)
                item_box.connect(GtkSignal.CHANGED.value, self.changed)
                self.pack_start(item_box, False, False, 0)
            elif item["kind"] == settings.Kind.RANGE:
                item_box = Scale()
                item_box.set_range(item["min"], item["max"])
                item_box.set_round_digits(0)
                item_box.set_digits(0)
                item_box.set_increments(1, 5)
                item_box.connect(GtkSignal.VALUE_CHANGED.value, self.changed)
                self.pack_start(item_box, True, True, 0)
            item_box.set_visible(False)
            self._items[str(item["name"])] = (item_lblbox, item_box)

    def get_value(self):
        result = {}
        for k, (_lblbox, box) in self._items.items():
            result[str(k)] = box.get_value()
        result = hidpp20.LEDEffectSetting(**result)
        return result

    def set_value(self, value):
        self.set_sensitive(False)
        if value is not None:
            for k, v in value.__dict__.items():
                if k in self._items:
                    (lblbox, box) = self._items[k]
                    box.set_value(v)
        else:
            self.sbox._failed.set_visible(True)
        self.setup_visibles(value.ID if value is not None else 0)

    def setup_visibles(self, id_):
        fields = self.sbox.setting.fields_map[id_][1] if id_ in self.sbox.setting.fields_map else {}
        for name, (lblbox, box) in self._items.items():
            visible = name in fields or name == "ID"
            if lblbox:
                lblbox.set_visible(visible)
            box.set_visible(visible)

    def changed(self, control):
        if self.get_sensitive() and control.get_sensitive():
            if "ID" in self._items and control == self._items["ID"][1]:
                self.setup_visibles(int(self._items["ID"][1].get_value()))
            if hasattr(control, "_timer"):
                control._timer.cancel()
            control._timer = Timer(0.3, lambda: GLib.idle_add(self._write, control))
            control._timer.start()

    def _write(self, control):
        control._timer.cancel()
        delattr(control, "_timer")
        new_state = self.get_value()
        if self.sbox.setting._value != new_state:
            _write_async(self.sbox.setting, new_state, self.sbox)


_allowables_icons = {True: "changes-allow", False: "changes-prevent", settings.SENSITIVITY_IGNORE: "dialog-error"}
_allowables_tooltips = {
    True: _("Changes allowed"),
    False: _("No changes allowed"),
    settings.SENSITIVITY_IGNORE: _("Ignore this setting"),
}
_next_allowable = {True: False, False: settings.SENSITIVITY_IGNORE, settings.SENSITIVITY_IGNORE: True}
_icons_allowables = {v: k for k, v in _allowables_icons.items()}


# clicking on the lock icon changes from changeable to unchangeable to ignore
def _change_click(button, sbox):
    icon = button.get_children()[0]
    icon_name, _ = icon.get_icon_name()
    allowed = _icons_allowables.get(icon_name, True)
    new_allowed = _next_allowable[allowed]
    sbox._control.set_sensitive(new_allowed is True)
    _change_icon(new_allowed, icon)
    if sbox.setting._device.persister:  # remember the new setting sensitivity
        sbox.setting._device.persister.set_sensitivity(sbox.setting.name, new_allowed)
    if allowed == settings.SENSITIVITY_IGNORE:  # update setting if it was being ignored
        setting = next((s for s in sbox.setting._device.settings if s.name == sbox.setting.name), None)
        if setting:
            persisted = sbox.setting._device.persister.get(setting.name) if sbox.setting._device.persister else None
            if setting.persist and persisted is not None:
                _write_async(setting, persisted, sbox)
            else:
                _read_async(setting, True, sbox, bool(sbox.setting._device.online), sbox._control.get_sensitive())
    return True


def _change_icon(allowed, icon):
    if allowed in _allowables_icons:
        icon._allowed = allowed
        icon.set_from_icon_name(_allowables_icons[allowed], Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_tooltip_text(_allowables_tooltips[allowed])


def _create_sbox(s, _device):
    sbox = Gtk.HBox(homogeneous=False, spacing=6)
    sbox.setting = s
    sbox.kind = s.kind
    if s.description:
        sbox.set_tooltip_text(s.description)
    lbl = Gtk.Label(label=s.label)
    label = Gtk.EventBox()
    label.add(lbl)
    spinner = Gtk.Spinner()
    spinner.set_tooltip_text(_("Working") + "...")
    sbox._spinner = spinner
    failed = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.SMALL_TOOLBAR)
    failed.set_tooltip_text(_("Read/write operation failed."))
    sbox._failed = failed
    change_icon = Gtk.Image.new_from_icon_name("changes-prevent", Gtk.IconSize.LARGE_TOOLBAR)
    sbox._change_icon = change_icon
    _change_icon(False, change_icon)
    change = Gtk.Button()
    change.set_relief(Gtk.ReliefStyle.NONE)
    change.add(change_icon)
    change.set_sensitive(True)
    change.connect(GtkSignal.CLICKED.value, _change_click, sbox)

    if s.kind == settings.Kind.TOGGLE:
        control = ToggleControl(sbox)
    elif s.kind == settings.Kind.RANGE:
        control = SliderControl(sbox)
    elif s.kind == settings.Kind.CHOICE:
        control = _create_choice_control(sbox)
    elif s.kind == settings.Kind.MAP_CHOICE:
        control = MapChoiceControl(sbox)
    elif s.kind == settings.Kind.MULTIPLE_TOGGLE:
        control = MultipleToggleControl(sbox, change)
    elif s.kind == settings.Kind.MULTIPLE_RANGE:
        control = MultipleRangeControl(sbox, change)
    elif s.kind == settings.Kind.PACKED_RANGE:
        control = PackedRangeControl(sbox, change)
    elif s.kind == settings.Kind.HETERO:
        control = HeteroKeyControl(sbox, change)
    else:
        logger.warning("setting %s display not implemented", s.label)
        return None

    control.set_sensitive(False)  # the first read will enable it
    control.layout(sbox, label, change, spinner, failed)
    sbox._control = control
    sbox.show_all()
    spinner.start()  # the first read will stop it
    failed.set_visible(False)
    return sbox


def _update_setting_item(sbox, value, is_online=True, sensitive=True, null_okay=False):
    sbox._spinner.stop()
    sensitive = sbox._change_icon._allowed if sensitive is None else sensitive
    if value is None and not null_okay:
        sbox._control.set_sensitive(sensitive is True)
        _change_icon(sensitive, sbox._change_icon)
        sbox._failed.set_visible(is_online)
        return
    sbox._failed.set_visible(False)
    sbox._control.set_sensitive(False)
    sbox._control.set_value(value)
    sbox._control.set_sensitive(sensitive is True)
    _change_icon(sensitive, sbox._change_icon)


def _disable_listbox_highlight_bg(lb):
    colour = Gdk.RGBA()
    colour.parse("rgba(0,0,0,0)")
    for child in lb.get_children():
        child.override_background_color(Gtk.StateFlags.PRELIGHT, colour)


# config panel
_box = None
_items = {}


def create():
    global _box
    assert _box is None
    _box = Gtk.VBox(homogeneous=False, spacing=4)
    _box._last_device = None

    config_scroll = Gtk.ScrolledWindow()
    config_scroll.add(_box)
    config_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    config_scroll.set_shadow_type(Gtk.ShadowType.NONE)  # was IN
    config_scroll.set_size_request(0, 350)  # ask for enough vertical space for about eight settings

    return config_scroll


def update(device, is_online=None):
    assert _box is not None
    assert device
    device_id = (device.receiver.path if device.receiver else device.path, device.number)
    if is_online is None:
        is_online = bool(device.online)

    # if the device changed since last update, clear the box first
    if device_id != _box._last_device:
        _box.set_visible(False)
        _box._last_device = device_id

    # hide controls belonging to other devices
    for k, sbox in _items.items():
        sbox = _items[k]
        sbox.set_visible(k[0:2] == device_id)

    for s in device.settings:
        k = (device_id[0], device_id[1], s.name)
        if k in _items:
            sbox = _items[k]
        else:
            sbox = _create_sbox(s, device)
            if sbox is None:
                continue
            _items[k] = sbox
            _box.pack_start(sbox, False, False, 0)
        sensitive = device.persister.get_sensitivity(s.name) if device.persister else True
        _read_async(s, False, sbox, is_online, sensitive)

    _box.set_visible(True)


def clean(device):
    """Remove the controls for a given device serial.
    Needed after the device has been unpaired.
    """
    assert _box is not None
    device_id = (device.receiver.path if device.receiver else device.path, device.number)
    for k in list(_items.keys()):
        if k[0:2] == device_id:
            _box.remove(_items[k])
            del _items[k]


def destroy():
    global _box
    _box = None
    _items.clear()


def change_setting(device, setting, values):
    """External interface to change a setting and have the GUI show the change"""
    assert device == setting._device
    GLib.idle_add(_change_setting, device, setting, values, priority=99)


def _change_setting(device, setting, values):
    device_path = device.receiver.path if device.receiver else device.path
    if (device_path, device.number, setting.name) in _items:
        sbox = _items[(device_path, device.number, setting.name)]
    else:
        sbox = None
    _write_async(setting, values[-1], sbox, None, key=values[0] if len(values) > 1 else None)


def record_setting(device, setting, values):
    """External interface to have the GUI show a change to a setting. Doesn't write to the device"""
    GLib.idle_add(_record_setting, device, setting, values, priority=99)


def _record_setting(device, setting_class, values):
    logger.debug("on %s changing setting %s to %s", device, setting_class.name, values)
    setting = next((s for s in device.settings if s.name == setting_class.name), None)
    if setting is None:
        logger.debug(
            "No setting for %s found on %s when trying to record a change made elsewhere",
            setting_class.name,
            device,
        )
    if setting:
        assert device == setting._device
        if len(values) > 1:
            setting.update_key_value(values[0], values[-1])
            value = {values[0]: values[-1]}
        else:
            setting.update(values[-1])
            value = values[-1]
        device_path = device.receiver.path if device.receiver else device.path
        if (device_path, device.number, setting.name) in _items:
            sbox = _items[(device_path, device.number, setting.name)]
            if sbox:
                _update_setting_item(sbox, value, sensitive=None)
