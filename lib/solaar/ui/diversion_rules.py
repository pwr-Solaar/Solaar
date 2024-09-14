## Copyright (C) 2020 Solaar
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
import string
import threading

from copy import copy
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from shlex import quote as shlex_quote
from typing import Any
from typing import Dict
from typing import Optional

from gi.repository import GObject
from gi.repository import Gtk
from logitech_receiver import diversion as _DIV
from logitech_receiver.common import NamedInt
from logitech_receiver.common import NamedInts
from logitech_receiver.common import UnsortedNamedInts
from logitech_receiver.settings import KIND as _SKIND
from logitech_receiver.settings import Setting
from logitech_receiver.settings_templates import SETTINGS

from solaar.i18n import _
from solaar.ui import rule_actions
from solaar.ui import rule_conditions
from solaar.ui.rule_base import RuleComponentUI
from solaar.ui.rule_base import norm
from solaar.ui.rule_conditions import ConditionUI
from solaar.ui.rules import rule_window
from solaar.ui.rules.model import RulesModel
from solaar.ui.rules.view import RulesView

logger = logging.getLogger(__name__)

_diversion_dialog = None
_all_devices = None
_dev_model = None


class RuleComponentWrapper(GObject.GObject):
    def __init__(self, component, level=0, editable=False):
        self.component = component
        self.level = level
        self.editable = editable
        GObject.GObject.__init__(self)

    def display_left(self):
        if isinstance(self.component, _DIV.Rule):
            if self.level == 0:
                return _("Built-in rules") if not self.editable else _("User-defined rules")
            if self.level == 1:
                return "  " + _("Rule")
            return "  " + _("Sub-rule")
        if self.component is None:
            return _("[empty]")
        return "  " + self.__component_ui().left_label(self.component)

    def display_right(self):
        if self.component is None:
            return ""
        return self.__component_ui().right_label(self.component)

    def display_icon(self):
        if self.component is None:
            return ""
        if isinstance(self.component, _DIV.Rule) and self.level == 0:
            return "emblem-system" if not self.editable else "avatar-default"
        return self.__component_ui().icon_name()

    def __component_ui(self):
        return COMPONENT_UI.get(type(self.component), UnsupportedRuleComponentUI)


class CompletionEntry(Gtk.Entry):
    def __init__(self, values, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CompletionEntry.add_completion_to_entry(self, values)

    @classmethod
    def add_completion_to_entry(cls, entry, values):
        completion = entry.get_completion()
        if not completion:
            liststore = Gtk.ListStore(str)
            completion = Gtk.EntryCompletion()
            completion.set_model(liststore)
            completion.set_match_func(lambda completion, key, it: norm(key) in norm(completion.get_model()[it][0]))
            completion.set_text_column(0)
            entry.set_completion(completion)
        else:
            liststore = completion.get_model()
            liststore.clear()
        for v in sorted(set(values), key=str.casefold):
            liststore.append((v,))


class SmartComboBox(Gtk.ComboBox):
    """A custom ComboBox with some extra features.

    The constructor requires a collection of allowed values.
    Each element must be a single value or a non-empty tuple containing:
    - a value (any hashable object)
    - a name (optional; str(value) is used if not provided)
    - alternative names.
    Example: (some_object, 'object name', 'other name', 'also accept this').

    It is assumed that the same string cannot be the name or an
    alternative name of more than one value.

    The widget displays the names, but the alternative names are also suggested and accepted as input.

    If `has_entry` is `True`, then the user can insert arbitrary text (possibly with auto-complete if `completion` is True).
    Otherwise, only a drop-down list is shown, with an extra blank item in the beginning (correspondent to `None`).
    The display text of the blank item is defined by the parameter `blank`.

    If `case_insensitive` is `True`, then upper-case and lower-case letters are treated as equal.

    If `replace_with_default_name`, then the field text is immediately replaced with the default name of a value
    as soon as the user finishes typing any accepted name.

    """

    def __init__(
        self, all_values, blank="", completion=False, case_insensitive=False, replace_with_default_name=False, **kwargs
    ):
        super().__init__(**kwargs)
        self._name_to_idx = {}
        self._value_to_idx = {}
        self._hidden_idx = set()
        self._all_values = []
        self._blank = blank
        self._model = None
        self._commpletion = completion
        self._case_insensitive = case_insensitive
        self._norm = lambda s: None if s is None else s if not case_insensitive else str(s).upper()
        self._replace_with_default_name = replace_with_default_name

        def replace_with(value):
            if self.get_has_entry() and self._replace_with_default_name and value is not None:
                item = self._all_values[self._value_to_idx[value]]
                name = item[1] if len(item) > 1 else str(item[0])
                if name != self.get_child().get_text():
                    self.get_child().set_text(name)

        self.connect("changed", lambda *a: replace_with(self.get_value(invalid_as_str=False)))

        self.set_id_column(0)
        if self.get_has_entry():
            self.set_entry_text_column(1)
        else:
            renderer = Gtk.CellRendererText()
            self.pack_start(renderer, True)
            self.add_attribute(renderer, "text", 1)
        self.set_all_values(all_values)
        self.set_active_id("")

    @classmethod
    def new_model(cls):
        model = Gtk.ListStore(str, str, bool)
        # (index: int converted to str, name: str, visible: bool)
        filtered_model = model.filter_new()
        filtered_model.set_visible_column(2)
        return model, filtered_model

    def set_all_values(self, all_values, visible_fn=(lambda value: True)):
        old_value = self.get_value()
        self._name_to_idx = {}
        self._value_to_idx = {}
        self._hidden_idx = set()
        self._all_values = [v if isinstance(v, tuple) else (v,) for v in all_values]

        model, filtered_model = SmartComboBox.new_model()
        # creating a new model seems to be necessary to avoid firing 'changed' event once per inserted item
        model.append(("", self._blank, True))
        self._model = model

        to_complete = [self._blank]
        for idx, item in enumerate(self._all_values):
            value, *names = item if isinstance(item, tuple) else (item,)
            visible = visible_fn(value)
            self._include(model, idx, value, visible, *names)
            if visible:
                to_complete += names if names else [str(value).strip()]
        self.set_model(filtered_model)
        if self.get_has_entry() and self._commpletion:
            CompletionEntry.add_completion_to_entry(self.get_child(), to_complete)
        if self._find_idx(old_value) is not None:
            self.set_value(old_value)
        else:
            self.set_value(self._blank)
        self.queue_draw()

    def _include(self, model, idx, value, visible, *names):
        name = str(names[0]) if names else str(value).strip()
        self._name_to_idx[self._norm(name)] = idx
        if isinstance(value, NamedInt):
            self._name_to_idx[self._norm(str(name))] = idx
        model.append((str(idx), name, visible))
        for alt in names[1:]:
            self._name_to_idx[self._norm(str(alt).strip())] = idx
        self._value_to_idx[value] = idx
        if self._case_insensitive and isinstance(value, str):
            self._name_to_idx[self._norm(value)] = idx

    def get_value(self, invalid_as_str=True, accept_hidden=True):
        """Return the selected value or the typed text.

        If the typed or selected text corresponds to one of the allowed values (or their names and
        alternative names), then the value is returned.

        Otherwise, the raw text is returned as string if the widget has an entry and `invalid_as_str`
        is `True`; if the widget has no entry or `invalid_as_str` is `False`, then `None` is returned.

        """
        tree_iter = self.get_active_iter()
        if tree_iter is not None:
            t = self.get_model()[tree_iter]
            number = t[0]
            return self._all_values[int(number)][0] if number != "" and (accept_hidden or t[2]) else None
        elif self.get_has_entry():
            text = self.get_child().get_text().strip()
            if text == self._blank:
                return None
            idx = self._find_idx(text)
            if idx is None:
                return text if invalid_as_str else None
            item = self._all_values[idx]
            return item[0]
        return None

    def _find_idx(self, search):
        if search == self._blank:
            return None
        try:
            return self._value_to_idx[search]
        except KeyError:
            pass
        try:
            return self._name_to_idx[self._norm(search)]
        except KeyError:
            pass
        return None

    def set_value(self, value, accept_invalid=True):
        """Set a specific value.

        Raw values, their names and alternative names are accepted.
        Base-10 representations of int values as strings are also accepted.
        The actual value is used in all cases.

        If `value` is invalid, then the entry text is set to the provided value
        if the widget has an entry and `accept_invalid` is True, or else the blank value is set.
        """
        idx = self._find_idx(value) if value != self._blank else ""
        if idx is not None:
            self.set_active_id(str(idx))
        else:
            if self.get_has_entry() and accept_invalid:
                self.get_child().set_text(str(value or "") if value != "" else self._blank)
            else:
                self.set_active_id("")

    def show_only(self, only, include_new=False):
        """Hide items not present in `only`.

        Only values are accepted (not their names and alternative names).

        If `include_new` is True, then the values in `only` not currently present
        are included with their string representation as names; otherwise,
        they are ignored.

        If `only` is new, then the visibility status is reset and all values are shown.
        """
        values = self._all_values[:]
        if include_new and only is not None:
            values += [v for v in only if v not in self._value_to_idx]
        self.set_all_values(values, (lambda v: only is None or (v in only)))


@dataclass
class DeviceInfo:
    serial: str = ""
    unitId: str = ""
    codename: str = ""
    settings: Dict[str, Setting] = field(default_factory=dict)

    def __post_init__(self):
        if self.serial is None or self.serial == "?":
            self.serial = ""
        if self.unitId is None or self.unitId == "?":
            self.unitId = ""

    @property
    def id(self):
        return self.serial or self.unitId or ""

    @property
    def identifiers(self):
        return [id for id in (self.serial, self.unitId) if id]

    @property
    def display_name(self):
        return f"{self.codename} ({self.id})"

    def matches(self, search):
        return search and search in (self.serial, self.unitId, self.display_name)

    def update(self, device):
        for k in ("serial", "unitId", "codename", "settings"):
            if not getattr(self, k, None):
                v = getattr(device, k, None)
                if v and v != "?":
                    setattr(self, k, copy(v) if k != "settings" else {s.name: s for s in v})


class DeviceInfoFactory:
    @classmethod
    def create_device_info(cls, device) -> DeviceInfo:
        d = DeviceInfo()
        d.update(device)
        return d


class AllDevicesInfo:
    def __init__(self):
        self._devices = []
        self._lock = threading.Lock()

    def __iter__(self):
        return iter(self._devices)

    def __getitem__(self, search):
        if not search:
            return search
        assert isinstance(search, str)
        # linear search - ok because it is always a small list
        return next((d for d in self._devices if d.matches(search)), None)

    def refresh(self):
        updated = False

        def dev_in_row(_store, _treepath, row):
            nonlocal updated
            device = _dev_model.get_value(row, 7)
            if device and device.kind and (device.serial and device.serial != "?" or device.unitId and device.unitId != "?"):
                existing = self[device.serial] or self[device.unitId]
                if not existing:
                    updated = True
                    device_info = DeviceInfoFactory.create_device_info(device)
                    self._devices.append(device_info)
                elif not existing.settings and device.settings:
                    updated = True
                    existing.update(device)

        with self._lock:
            _dev_model.foreach(dev_in_row)
        return updated


class UnsupportedRuleComponentUI(RuleComponentUI):
    CLASS = None

    def create_widgets(self):
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("This editor does not support the selected rule component yet."))
        self.widgets[self.label] = (0, 0, 1, 1)

    @classmethod
    def right_label(cls, component):
        return str(component)


class RuleUI(RuleComponentUI):
    CLASS = _DIV.Rule

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("Rule")

    @classmethod
    def icon_name(cls):
        return "format-justify-fill"


class AndUI(RuleComponentUI):
    CLASS = _DIV.And

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("And")


class OrUI(RuleComponentUI):
    CLASS = _DIV.Or

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("Or")


class LaterUI(RuleComponentUI):
    CLASS = _DIV.Later
    MIN_VALUE = 0.01
    MAX_VALUE = 100

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Number of seconds to delay.  Delay between 0 and 1 is done with higher precision."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        self.field.set_digits(3)
        self.field.set_halign(Gtk.Align.CENTER)
        self.field.set_valign(Gtk.Align.CENTER)
        self.field.set_hexpand(True)
        self.field.connect("value-changed", self._on_update)
        self.widgets[self.field] = (0, 1, 1, 1)

    def show(self, component, editable):
        super().show(component, editable)
        with self.ignore_changes():
            self.field.set_value(component.delay)

    def collect_value(self):
        return [float(int((self.field.get_value() + 0.0001) * 1000)) / 1000] + self.component.components

    @classmethod
    def left_label(cls, component):
        return _("Later")

    @classmethod
    def right_label(cls, component):
        return str(component.delay)


class NotUI(RuleComponentUI):
    CLASS = _DIV.Not

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.component  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("Not")


class ActionUI(RuleComponentUI):
    CLASS = _DIV.Action

    @classmethod
    def icon_name(cls):
        return "go-next"


def _from_named_ints(v, all_values):
    """Obtain a NamedInt from NamedInts given its numeric value (as int) or name."""
    if all_values and (v in all_values):
        return all_values[v]
    return v


class SetValueControlKinds(Enum):
    TOGGLE = "toggle"
    RANGE = "range"
    RANGE_WITH_KEY = "range_with_key"
    CHOICE = "choice"


class SetValueControl(Gtk.HBox):
    def __init__(self, on_change, *args, accept_toggle=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_change = on_change
        self.toggle_widget = SmartComboBox(
            [
                *([("Toggle", _("Toggle"), "~")] if accept_toggle else []),
                (True, _("True"), "True", "yes", "on", "t", "y"),
                (False, _("False"), "False", "no", "off", "f", "n"),
            ],
            case_insensitive=True,
        )
        self.toggle_widget.connect("changed", self._changed)
        self.range_widget = Gtk.SpinButton.new_with_range(0, 0xFFFF, 1)
        self.range_widget.connect("value-changed", self._changed)
        self.choice_widget = SmartComboBox(
            [], completion=True, has_entry=True, case_insensitive=True, replace_with_default_name=True
        )
        self.choice_widget.connect("changed", self._changed)
        self.sub_key_widget = SmartComboBox([])
        self.sub_key_widget.connect("changed", self._changed)
        self.unsupported_label = Gtk.Label(label=_("Unsupported setting"))
        self.pack_start(self.sub_key_widget, False, False, 0)
        self.sub_key_widget.set_hexpand(False)
        self.sub_key_widget.set_size_request(120, 0)
        self.sub_key_widget.hide()
        for w in [self.toggle_widget, self.range_widget, self.choice_widget, self.unsupported_label]:
            self.pack_end(w, True, True, 0)
            w.hide()
        self.unsupp_value = None
        self.current_kind: Optional[SetValueControlKinds] = None
        self.sub_key_range_items = None

    def _changed(self, widget, *args):
        if widget.get_visible():
            value = self.get_value()
            if self.current_kind == SetValueControlKinds.CHOICE:
                value = widget.get_value()
                icon = "dialog-warning" if widget._allowed_values and (value not in widget._allowed_values) else ""
                widget.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
            elif self.current_kind == SetValueControlKinds.RANGE_WITH_KEY and widget == self.sub_key_widget:
                key = self.sub_key_widget.get_value()
                selected_item = (
                    next((item for item in self.sub_key_range_items if key == item.id), None)
                    if self.sub_key_range_items
                    else None
                )
                (minimum, maximum) = (selected_item.minimum, selected_item.maximum) if selected_item else (0, 0xFFFF)
                self.range_widget.set_range(minimum, maximum)
            self.on_change(value)

    def _hide_all(self):
        for w in self.get_children():
            w.hide()

    def get_value(self):
        if self.current_kind == SetValueControlKinds.TOGGLE:
            return self.toggle_widget.get_value()
        if self.current_kind == SetValueControlKinds.RANGE:
            return int(self.range_widget.get_value())
        if self.current_kind == SetValueControlKinds.RANGE_WITH_KEY:
            return {self.sub_key_widget.get_value(): int(self.range_widget.get_value())}
        if self.current_kind == SetValueControlKinds.CHOICE:
            return self.choice_widget.get_value()
        return self.unsupp_value

    def set_value(self, value):
        if self.current_kind == SetValueControlKinds.TOGGLE:
            self.toggle_widget.set_value(value if value is not None else "")
        elif self.current_kind == SetValueControlKinds.RANGE:
            minimum, maximum = self.range_widget.get_range()
            try:
                v = round(float(value))
            except (ValueError, TypeError):
                v = minimum
            self.range_widget.set_value(max(minimum, min(maximum, v)))
        elif self.current_kind == SetValueControlKinds.RANGE_WITH_KEY:
            if not (isinstance(value, dict) and len(value) == 1):
                value = {None: None}
            key = next(iter(value.keys()))
            selected_item = (
                next((item for item in self.sub_key_range_items if key == item.id), None) if self.sub_key_range_items else None
            )
            (minimum, maximum) = (selected_item.minimum, selected_item.maximum) if selected_item else (0, 0xFFFF)
            try:
                v = round(float(next(iter(value.values()))))
            except (ValueError, TypeError):
                v = minimum
            self.sub_key_widget.set_value(key or "")
            self.range_widget.set_value(max(minimum, min(maximum, v)))
        elif self.current_kind == SetValueControlKinds.CHOICE:
            self.choice_widget.set_value(value)
        else:
            self.unsupp_value = value
        if value is None or value == "":  # reset all
            self.range_widget.set_range(0x0000, 0xFFFF)
            self.range_widget.set_value(0)
            self.toggle_widget.set_active_id("")
            self.sub_key_widget.set_value("")
            self.choice_widget.set_value("")

    def make_toggle(self):
        self.current_kind = SetValueControlKinds.TOGGLE
        self._hide_all()
        self.toggle_widget.show()

    def make_range(self, minimum, maximum):
        self.current_kind = SetValueControlKinds.RANGE
        self._hide_all()
        self.range_widget.set_range(minimum, maximum)
        self.range_widget.show()

    def make_range_with_key(self, items, labels=None):
        self.current_kind = SetValueControlKinds.RANGE_WITH_KEY
        self._hide_all()
        self.sub_key_range_items = items or None
        if not labels:
            labels = {}
        self.sub_key_widget.set_all_values(
            map(lambda item: (item.id, labels.get(item.id, [str(item.id)])[0]), items) if items else []
        )
        self.sub_key_widget.show()
        self.range_widget.show()

    def make_choice(self, values, extra=None):
        # if extra is not in values, it is ignored
        self.current_kind = SetValueControlKinds.CHOICE
        self._hide_all()
        sort_key = int if all((v == extra or str(v).isdigit()) for v in values) else str
        if extra is not None and extra in values:
            values = [extra] + sorted((v for v in values if v != extra), key=sort_key)
        else:
            values = sorted(values, key=sort_key)
        self.choice_widget.set_all_values(values)
        self.choice_widget._allowed_values = values
        self.choice_widget.show()

    def make_unsupported(self):
        self.current_kind = None
        self._hide_all()
        self.unsupported_label.show()


def _all_settings():
    settings = {}
    for s in sorted(SETTINGS, key=lambda setting: setting.label):
        if s.name not in settings:
            settings[s.name] = [s]
        else:
            prev_setting = settings[s.name][0]
            prev_kind = prev_setting.validator_class.kind
            if prev_kind != s.validator_class.kind:
                logger.warning(
                    "ignoring setting {} - same name of {}, but different kind ({} != {})".format(
                        s.__name__, prev_setting.__name__, prev_kind, s.validator_class.kind
                    )
                )
                continue
            settings[s.name].append(s)
    return settings


class _DeviceUI:
    label_text = ""

    def show(self, component, editable):
        super().show(component, editable)
        with self.ignore_changes():
            same = not component.devID
            device = _all_devices[component.devID]
            self.device_field.set_value(device.id if device else "" if same else component.devID or "")

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(self.label_text)
        self.widgets[self.label] = (0, 0, 5, 1)
        lbl = Gtk.Label(label=_("Device"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.widgets[lbl] = (0, 1, 1, 1)
        self.device_field = SmartComboBox(
            [],
            completion=True,
            has_entry=True,
            blank=_("Originating device"),
            case_insensitive=True,
            replace_with_default_name=True,
        )
        self.device_field.set_value("")
        self.device_field.set_valign(Gtk.Align.CENTER)
        self.device_field.set_size_request(400, 0)
        self.device_field.connect("changed", self._on_update)
        self.widgets[self.device_field] = (1, 1, 1, 1)

    def update_devices(self):
        self._update_device_list()

    def _update_device_list(self):
        with self.ignore_changes():
            self.device_field.set_all_values([(d.id, d.display_name, *d.identifiers[1:]) for d in _all_devices])

    def collect_value(self):
        device_str = self.device_field.get_value()
        same = device_str in ["", _("Originating device")]
        device = None if same else _all_devices[device_str]
        device_value = device.id if device else None if same else device_str
        return device_value

    @classmethod
    def right_label(cls, component):
        device = _all_devices[component.devID]
        return device.display_name if device else shlex_quote(component.devID)


class ActiveUI(_DeviceUI, ConditionUI):
    CLASS = _DIV.Active
    label_text = _("Device is active and its settings can be changed.")

    @classmethod
    def left_label(cls, component):
        return _("Active")


class DeviceUI(_DeviceUI, ConditionUI):
    CLASS = _DIV.Device
    label_text = _("Device that originated the current notification.")

    @classmethod
    def left_label(cls, component):
        return _("Device")


class HostUI(ConditionUI):
    CLASS = _DIV.Host

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Name of host computer."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.field.set_size_request(600, 0)
        self.field.connect("changed", self._on_update)
        self.widgets[self.field] = (0, 1, 1, 1)

    def show(self, component, editable):
        super().show(component, editable)
        with self.ignore_changes():
            self.field.set_text(component.host)

    def collect_value(self):
        return self.field.get_text()

    @classmethod
    def left_label(cls, component):
        return _("Host")

    @classmethod
    def right_label(cls, component):
        return str(component.host)


class _SettingWithValueUI:
    ALL_SETTINGS = _all_settings()

    MULTIPLE = [_SKIND.multiple_toggle, _SKIND.map_choice, _SKIND.multiple_range]

    ACCEPT_TOGGLE = True

    label_text = ""

    def create_widgets(self):
        self.widgets = {}

        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(self.label_text)
        self.widgets[self.label] = (0, 0, 5, 1)

        m = 20
        lbl = Gtk.Label(label=_("Device"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, margin_top=m)
        self.widgets[lbl] = (0, 1, 1, 1)
        self.device_field = SmartComboBox(
            [],
            completion=True,
            has_entry=True,
            blank=_("Originating device"),
            case_insensitive=True,
            replace_with_default_name=True,
        )
        self.device_field.set_value("")
        self.device_field.set_valign(Gtk.Align.CENTER)
        self.device_field.set_size_request(400, 0)
        self.device_field.set_margin_top(m)
        self.device_field.connect("changed", self._changed_device)
        self.device_field.connect("changed", self._on_update)
        self.widgets[self.device_field] = (1, 1, 1, 1)

        lbl = Gtk.Label(label=_("Setting"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False)
        self.widgets[lbl] = (0, 2, 1, 1)
        self.setting_field = SmartComboBox([(s[0].name, s[0].label) for s in self.ALL_SETTINGS.values()])
        self.setting_field.set_valign(Gtk.Align.CENTER)
        self.setting_field.connect("changed", self._changed_setting)
        self.setting_field.connect("changed", self._on_update)
        self.widgets[self.setting_field] = (1, 2, 1, 1)

        self.value_lbl = Gtk.Label(
            label=_("Value"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False
        )
        self.widgets[self.value_lbl] = (2, 2, 1, 1)
        self.value_field = SetValueControl(self._on_update, accept_toggle=self.ACCEPT_TOGGLE)
        self.value_field.set_valign(Gtk.Align.CENTER)
        self.value_field.set_size_request(250, 35)
        self.widgets[self.value_field] = (3, 2, 1, 1)

        self.key_lbl = Gtk.Label(
            label=_("Item"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, vexpand=False, margin_top=m
        )
        self.key_lbl.hide()
        self.widgets[self.key_lbl] = (2, 1, 1, 1)
        self.key_field = SmartComboBox(
            [], has_entry=True, completion=True, case_insensitive=True, replace_with_default_name=True
        )
        self.key_field.set_margin_top(m)
        self.key_field.hide()
        self.key_field.set_valign(Gtk.Align.CENTER)
        self.key_field.connect("changed", self._changed_key)
        self.key_field.connect("changed", self._on_update)
        self.widgets[self.key_field] = (3, 1, 1, 1)

    @classmethod
    def _all_choices(cls, setting):  # choice and map-choice
        """Return a NamedInts instance with the choices for a setting.

        If the argument `setting` is a Setting instance or subclass, then the choices are taken only from it.
        If instead it is a name, then the function returns the union of the choices for each setting with that name.
        Only one label per number is kept.

        The function returns a 2-tuple whose first element is a NamedInts instance with the possible choices
        (including the extra value if it exists) and the second element is the extra value to be pinned to
        the start of the list (or `None` if there is no extra value).
        """
        if isinstance(setting, Setting):
            setting = type(setting)
        if isinstance(setting, type) and issubclass(setting, Setting):
            choices = UnsortedNamedInts()
            universe = getattr(setting, "choices_universe", None)
            if universe:
                choices |= universe
            extra = getattr(setting, "choices_extra", None)
            if extra is not None:
                choices |= NamedInts(**{str(extra): int(extra)})
            return choices, extra
        settings = cls.ALL_SETTINGS.get(setting, [])
        choices = UnsortedNamedInts()
        extra = None
        for s in settings:
            ch, ext = cls._all_choices(s)
            choices |= ch
            if ext is not None:
                extra = ext
        return choices, extra

    @classmethod
    def _setting_attributes(cls, setting_name, device=None):
        if device and setting_name in device.settings:
            setting = device.settings.get(setting_name, None)
            settings = [type(setting)] if setting else None
        else:
            settings = cls.ALL_SETTINGS.get(setting_name, [None])
            setting = settings[0]  # if settings have the same name, use the first one to get the basic data
        val_class = setting.validator_class if setting else None
        kind = val_class.kind if val_class else None
        if kind in cls.MULTIPLE:
            keys = UnsortedNamedInts()
            for s in settings:
                universe = getattr(s, "keys_universe" if kind == _SKIND.map_choice else "choices_universe", None)
                if universe:
                    keys |= universe
            # only one key per number is used
        else:
            keys = None
        return setting, val_class, kind, keys

    def _changed_device(self, *args):
        device = _all_devices[self.device_field.get_value()]
        setting_name = self.setting_field.get_value()
        if not device or not device.settings or setting_name in device.settings:
            kind = self._setting_attributes(setting_name, device)[2]
            key = self.key_field.get_value() if kind in self.MULTIPLE else None
        else:
            setting_name = kind = key = None
        with self.ignore_changes():
            self._update_setting_list(device)
            self._update_key_list(setting_name, device)
            self._update_value_list(setting_name, device, key)

    def _changed_setting(self, *args):
        with self.ignore_changes():
            device = _all_devices[self.device_field.get_value()]
            setting_name = self.setting_field.get_value()
            self._update_key_list(setting_name, device)
            key = self.key_field.get_value()
            self._update_value_list(setting_name, device, key)

    def _changed_key(self, *args):
        with self.ignore_changes():
            setting_name = self.setting_field.get_value()
            device = _all_devices[self.device_field.get_value()]
            key = self.key_field.get_value()
            self._update_value_list(setting_name, device, key)

    def update_devices(self):
        self._update_device_list()

    def _update_device_list(self):
        with self.ignore_changes():
            self.device_field.set_all_values([(d.id, d.display_name, *d.identifiers[1:]) for d in _all_devices])

    def _update_setting_list(self, device=None):
        supported_settings = device.settings.keys() if device else {}
        with self.ignore_changes():
            self.setting_field.show_only(supported_settings or None)

    def _update_key_list(self, setting_name, device=None):
        setting, val_class, kind, keys = self._setting_attributes(setting_name, device)
        multiple = kind in self.MULTIPLE
        self.key_field.set_visible(multiple)
        self.key_lbl.set_visible(multiple)
        if not multiple:
            return
        labels = getattr(setting, "_labels", {})

        def item(k):
            lbl = labels.get(k, None)
            return (k, lbl[0] if lbl and isinstance(lbl, tuple) and lbl[0] else str(k))

        with self.ignore_changes():
            self.key_field.set_all_values(sorted(map(item, keys), key=lambda k: k[1]))
            ds = device.settings if device else {}
            device_setting = ds.get(setting_name, None)
            supported_keys = None
            if device_setting:
                val = device_setting._validator
                if device_setting.kind == _SKIND.multiple_toggle:
                    supported_keys = val.get_options() or None
                elif device_setting.kind == _SKIND.map_choice:
                    choices = val.choices or None
                    supported_keys = choices.keys() if choices else None
                elif device_setting.kind == _SKIND.multiple_range:
                    supported_keys = val.keys
            self.key_field.show_only(supported_keys, include_new=True)
            self._update_validation()

    def _update_value_list(self, setting_name, device=None, key=None):
        setting, val_class, kind, keys = self._setting_attributes(setting_name, device)
        ds = device.settings if device else {}
        device_setting = ds.get(setting_name, None)
        if kind in (_SKIND.toggle, _SKIND.multiple_toggle):
            self.value_field.make_toggle()
        elif kind in (_SKIND.choice, _SKIND.map_choice):
            all_values, extra = self._all_choices(device_setting or setting_name)
            self.value_field.make_choice(all_values, extra)
            supported_values = None
            if device_setting:
                val = device_setting._validator
                choices = getattr(val, "choices", None) or None
                if kind == _SKIND.choice:
                    supported_values = choices
                elif kind == _SKIND.map_choice and isinstance(choices, dict):
                    supported_values = choices.get(key, None) or None
            self.value_field.choice_widget.show_only(supported_values, include_new=True)
            self._update_validation()
        elif kind == _SKIND.range:
            self.value_field.make_range(val_class.min_value, val_class.max_value)
        elif kind == _SKIND.multiple_range:
            self.value_field.make_range_with_key(
                getattr(setting, "sub_items_universe", {}).get(key, {}) if setting else {},
                getattr(setting, "_labels_sub", None) if setting else None,
            )
        else:
            self.value_field.make_unsupported()

    def _on_update(self, *_args):
        if not self._ignore_changes and self.component:
            self._update_validation()

    def _update_validation(self):
        device_str = self.device_field.get_value()
        device = _all_devices[device_str]
        if device_str and not device:
            icon = (
                "dialog-question"
                if len(device_str) == 8 and all(c in string.hexdigits for c in device_str)
                else "dialog-warning"
            )
        else:
            icon = ""
        self.device_field.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        setting_name = self.setting_field.get_value()
        setting, val_class, kind, keys = self._setting_attributes(setting_name, device)
        multiple = kind in self.MULTIPLE
        if multiple:
            key = self.key_field.get_value(invalid_as_str=False, accept_hidden=False)
            icon = "dialog-warning" if key is None else ""
            self.key_field.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)
        if kind in (_SKIND.choice, _SKIND.map_choice):
            value = self.value_field.choice_widget.get_value(invalid_as_str=False, accept_hidden=False)
            icon = "dialog-warning" if value is None else ""
            self.value_field.choice_widget.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    def show(self, component, editable):
        a = iter(component.args)
        with self.ignore_changes():
            device_str = next(a, None)
            same = not device_str
            device = _all_devices[device_str]
            self.device_field.set_value(device.id if device else "" if same else device_str or "")
            setting_name = next(a, "")
            setting, _v, kind, keys = self._setting_attributes(setting_name, device)
            self.setting_field.set_value(setting.name if setting else "")
            self._changed_setting()
            key = None
            if kind in self.MULTIPLE or kind is None and len(self.component.args) > 3:
                key = _from_named_ints(next(a, ""), keys)
            self.key_field.set_value(key)
            self.value_field.set_value(next(a, ""))
            self._update_validation()

    def collect_value(self):
        device_str = self.device_field.get_value()
        same = device_str in ["", _("Originating device")]
        device = None if same else _all_devices[device_str]
        device_value = device.id if device else None if same else device_str
        setting_name = self.setting_field.get_value()
        setting, val_class, kind, keys = self._setting_attributes(setting_name, device)
        key_value = []
        if kind in self.MULTIPLE or kind is None and len(self.component.args) > 3:
            key = self.key_field.get_value()
            key = _from_named_ints(key, keys)
            key_value.append(key)
        key_value.append(self.value_field.get_value())
        return [device_value, setting_name, *key_value]

    @classmethod
    def right_label(cls, component):
        a = iter(component.args)
        device_str = next(a, None)
        device = None if not device_str else _all_devices[device_str]
        device_disp = _("Originating device") if not device_str else device.display_name if device else shlex_quote(device_str)
        setting_name = next(a, None)
        setting, val_class, kind, keys = cls._setting_attributes(setting_name, device)
        device_setting = (device.settings if device else {}).get(setting_name, None)
        disp = [setting.label or setting.name if setting else setting_name]
        if kind in cls.MULTIPLE:
            key = next(a, None)
            key = _from_named_ints(key, keys) if keys else key
            key_label = getattr(setting, "_labels", {}).get(key, [None])[0] if setting else None
            disp.append(key_label or key)
        value = next(a, None)
        if setting and (kind in (_SKIND.choice, _SKIND.map_choice)):
            all_values = cls._all_choices(setting or setting_name)[0]
            supported_values = None
            if device_setting:
                val = device_setting._validator
                choices = getattr(val, "choices", None) or None
                if kind == _SKIND.choice:
                    supported_values = choices
                elif kind == _SKIND.map_choice and isinstance(choices, dict):
                    supported_values = choices.get(key, None) or None
                if supported_values and isinstance(supported_values, NamedInts):
                    value = supported_values[value]
            if not supported_values and all_values and isinstance(all_values, NamedInts):
                value = all_values[value]
            disp.append(value)
        elif kind == _SKIND.multiple_range and isinstance(value, dict) and len(value) == 1:
            k, v = next(iter(value.items()))
            k = (getattr(setting, "_labels_sub", {}).get(k, (None,))[0] if setting else None) or k
            disp.append(f"{k}={v}")
        elif kind in (_SKIND.toggle, _SKIND.multiple_toggle):
            disp.append(_(str(value)))
        else:
            disp.append(value)
        return device_disp + "  " + "  ".join(map(lambda s: shlex_quote(str(s)), [*disp, *a]))


class SetUI(_SettingWithValueUI, ActionUI):
    CLASS = _DIV.Set
    ACCEPT_TOGGLE = True

    label_text = _("Change setting on device")

    def show(self, component, editable):
        ActionUI.show(self, component, editable)
        _SettingWithValueUI.show(self, component, editable)

    def _on_update(self, *_args):
        if not self._ignore_changes and self.component:
            ActionUI._on_update(self, *_args)
            _SettingWithValueUI._on_update(self, *_args)


class SettingUI(_SettingWithValueUI, ConditionUI):
    CLASS = _DIV.Setting
    ACCEPT_TOGGLE = False

    label_text = _("Setting on device")

    def show(self, component, editable):
        ConditionUI.show(self, component, editable)
        _SettingWithValueUI.show(self, component, editable)

    def _on_update(self, *_args):
        if not self._ignore_changes and self.component:
            ConditionUI._on_update(self, *_args)
            _SettingWithValueUI._on_update(self, *_args)


COMPONENT_UI = {
    _DIV.Rule: RuleUI,
    _DIV.Not: NotUI,
    _DIV.Or: OrUI,
    _DIV.And: AndUI,
    _DIV.Later: LaterUI,
    _DIV.Process: rule_conditions.ProcessUI,
    _DIV.MouseProcess: rule_conditions.MouseProcessUI,
    _DIV.Active: ActiveUI,
    _DIV.Device: DeviceUI,
    _DIV.Host: HostUI,
    _DIV.Feature: rule_conditions.FeatureUI,
    _DIV.Report: rule_conditions.ReportUI,
    _DIV.Modifiers: rule_conditions.ModifiersUI,
    _DIV.Key: rule_conditions.KeyUI,
    _DIV.KeyIsDown: rule_conditions.KeyIsDownUI,
    _DIV.Test: rule_conditions.TestUI,
    _DIV.TestBytes: rule_conditions.TestBytesUI,
    _DIV.Setting: SettingUI,
    _DIV.MouseGesture: rule_conditions.MouseGestureUI,
    _DIV.KeyPress: rule_actions.KeyPressUI,
    _DIV.MouseScroll: rule_actions.MouseScrollUI,
    _DIV.MouseClick: rule_actions.MouseClickUI,
    _DIV.Execute: rule_actions.ExecuteUI,
    _DIV.Set: SetUI,
    type(None): RuleComponentUI,  # placeholders for empty rule/And/Or
}

_all_devices = AllDevicesInfo()


def update_devices():
    global _dev_model
    global _all_devices
    global _diversion_dialog

    if _dev_model and _all_devices.refresh() and _diversion_dialog:
        _diversion_dialog.update_devices()


def _create_model(rules: _DIV.Rule) -> Gtk.TreeStore:
    """Converts a Rules instance into a Gtk.TreeStore."""
    if len(rules.components) == 1:
        # only built-in rules - add empty user rule list
        rules.components.insert(0, _DIV.Rule([], source=_DIV._RULES_FILE_PATH))

    model = Gtk.TreeStore(RuleComponentWrapper)
    _populate_model(model, None, rules.components)
    return model


def _populate_model(
    model: Gtk.TreeStore,
    it: Gtk.TreeIter,
    rule_component: Any,
    level: int = 0,
    pos: int = -1,
    editable: Optional[bool] = None,
):
    if isinstance(rule_component, list):
        for c in rule_component:
            _populate_model(model, it, c, level=level, pos=pos, editable=editable)
            if pos >= 0:
                pos += 1
        return
    if editable is None:
        editable = model[it][0].editable if it is not None else False
        if isinstance(rule_component, _DIV.Rule):
            editable = editable or (rule_component.source is not None)
    wrapped = RuleComponentWrapper(rule_component, level, editable=editable)
    piter = model.insert(it, pos, (wrapped,))
    if isinstance(rule_component, (_DIV.Rule, _DIV.And, _DIV.Or, _DIV.Later)):
        for c in rule_component.components:
            ed = editable or (isinstance(c, _DIV.Rule) and c.source is not None)
            _populate_model(model, piter, c, level + 1, editable=ed)
        if len(rule_component.components) == 0:
            _populate_model(model, piter, None, level + 1, editable=editable)
    elif isinstance(rule_component, _DIV.Not):
        _populate_model(model, piter, rule_component.component, level + 1, editable=editable)


def show_window(model):
    global _diversion_dialog
    global _dev_model

    GObject.type_register(RuleComponentWrapper)
    _dev_model = model
    if _diversion_dialog is None:
        rules_model = RulesModel(
            load_rules_func=_DIV.rule_storage.load_config,
            save_rules_func=_DIV.rule_storage.save_config,
        )
        rules_view = RulesView(COMPONENT_UI, UnsupportedRuleComponentUI)
        _diversion_dialog = rule_window.DiversionDialog(
            rules_model,
            rules_view,
            convert_to_model_func=_create_model,
            populate_model_func=_populate_model,
        )
    update_devices()
    _diversion_dialog.run()
