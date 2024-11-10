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

from __future__ import annotations

import dataclasses
import logging
import string
import threading

from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from shlex import quote as shlex_quote
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk
from logitech_receiver import diversion
from logitech_receiver.common import NamedInt
from logitech_receiver.common import NamedInts
from logitech_receiver.common import UnsortedNamedInts
from logitech_receiver.settings import Kind
from logitech_receiver.settings import Setting
from logitech_receiver.settings_templates import SETTINGS

from solaar.i18n import _
from solaar.ui import rule_actions
from solaar.ui import rule_conditions
from solaar.ui.rule_base import RuleComponentUI
from solaar.ui.rule_base import norm
from solaar.ui.rule_conditions import ConditionUI

logger = logging.getLogger(__name__)

_diversion_dialog = None
_rule_component_clipboard = None


class GtkSignal(Enum):
    ACTIVATE = "activate"
    BUTTON_RELEASE_EVENT = "button-release-event"
    CHANGED = "changed"
    CLICKED = "clicked"
    DELETE_EVENT = "delete-event"
    KEY_PRESS_EVENT = "key-press-event"
    NOTIFY_ACTIVE = "notify::active"
    TOGGLED = "toggled"
    VALUE_CHANGED = "value_changed"


def create_all_settings(all_settings: list[Setting]) -> dict[str, list[Setting]]:
    settings = {}
    for s in sorted(all_settings, key=lambda setting: setting.label):
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


ALL_SETTINGS = create_all_settings(SETTINGS)


class RuleComponentWrapper(GObject.GObject):
    def __init__(self, component, level=0, editable=False):
        self.component = component
        self.level = level
        self.editable = editable
        GObject.GObject.__init__(self)

    def display_left(self):
        if isinstance(self.component, diversion.Rule):
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
        if isinstance(self.component, diversion.Rule) and self.level == 0:
            return "emblem-system" if not self.editable else "avatar-default"
        return self.__component_ui().icon_name()

    def __component_ui(self):
        return COMPONENT_UI.get(type(self.component), UnsupportedRuleComponentUI)


def _create_close_dialog(window: Gtk.Window) -> Gtk.MessageDialog:
    """Creates rule editor close dialog, when unsaved changes are present."""
    dialog = Gtk.MessageDialog(
        window,
        type=Gtk.MessageType.QUESTION,
        title=_("Make changes permanent?"),
        flags=Gtk.DialogFlags.MODAL,
    )
    dialog.set_default_size(400, 100)
    dialog.add_buttons(
        _("Yes"),
        Gtk.ResponseType.YES,
        _("No"),
        Gtk.ResponseType.NO,
        _("Cancel"),
        Gtk.ResponseType.CANCEL,
    )
    dialog.set_markup(_("If you choose No, changes will be lost when Solaar is closed."))
    return dialog


def _create_selected_rule_edit_panel() -> Gtk.Grid:
    """Creates the edit Condition/Actions panel for a rule.

    Shows the UI for the selected rule component.
    """
    grid = Gtk.Grid()
    grid.set_margin_start(10)
    grid.set_margin_end(10)
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)
    grid.set_halign(Gtk.Align.CENTER)
    grid.set_valign(Gtk.Align.CENTER)
    grid.set_size_request(0, 120)
    return grid


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
        if isinstance(rule_component, diversion.Rule):
            editable = editable or (rule_component.source is not None)
    wrapped = RuleComponentWrapper(rule_component, level, editable=editable)
    piter = model.insert(it, pos, (wrapped,))
    if isinstance(rule_component, (diversion.Rule, diversion.And, diversion.Or, diversion.Later)):
        for c in rule_component.components:
            ed = editable or (isinstance(c, diversion.Rule) and c.source is not None)
            _populate_model(model, piter, c, level + 1, editable=ed)
        if len(rule_component.components) == 0:
            _populate_model(model, piter, None, level + 1, editable=editable)
    elif isinstance(rule_component, diversion.Not):
        _populate_model(model, piter, rule_component.component, level + 1, editable=editable)


@dataclasses.dataclass
class AllowedActions:
    c: Any
    copy: bool
    delete: bool
    flatten: bool
    insert: bool
    insert_only_rule: bool
    insert_root: bool
    wrap: bool


def allowed_actions(m: Gtk.TreeStore, it: Gtk.TreeIter) -> AllowedActions:
    row = m[it]
    wrapped = row[0]
    c = wrapped.component
    parent_it = m.iter_parent(it)
    parent_c = m[parent_it][0].component if wrapped.level > 0 else None

    can_wrap = wrapped.editable and wrapped.component is not None and wrapped.level >= 2
    can_delete = wrapped.editable and not isinstance(parent_c, diversion.Not) and c is not None and wrapped.level >= 1
    can_insert = wrapped.editable and not isinstance(parent_c, diversion.Not) and wrapped.level >= 2
    can_insert_only_rule = wrapped.editable and wrapped.level == 1
    can_flatten = (
        wrapped.editable
        and not isinstance(parent_c, diversion.Not)
        and isinstance(c, (diversion.Rule, diversion.And, diversion.Or))
        and wrapped.level >= 2
        and len(c.components)
    )
    can_copy = wrapped.level >= 1
    can_insert_root = wrapped.editable and wrapped.level == 0
    return AllowedActions(
        c,
        can_copy,
        can_delete,
        can_flatten,
        can_insert,
        can_insert_only_rule,
        can_insert_root,
        can_wrap,
    )


class ActionMenu:
    def __init__(
        self,
        window: Gtk.Window,
        tree_view: Gtk.TreeView,
        populate_model_func: Callable,
        on_update: Callable,
    ):
        self.window = window
        self.tree_view = tree_view
        self._populate_model_func = populate_model_func
        self._on_update = on_update

    def create_menu_event_button_released(self, v, e):
        if e.button == Gdk.BUTTON_SECONDARY:  # right click
            menu = Gtk.Menu()
            m, it = v.get_selection().get_selected()
            enabled_actions = allowed_actions(m, it)
            for item in self.get_insert_menus(m, it, enabled_actions):
                menu.append(item)
            if enabled_actions.flatten:
                menu.append(self._menu_flatten(m, it))
            if enabled_actions.wrap:
                menu.append(self._menu_wrap(m, it))
                menu.append(self._menu_negate(m, it))
            if menu.get_children():
                menu.append(Gtk.SeparatorMenuItem(visible=True))
            if enabled_actions.delete:
                menu.append(self._menu_cut(m, it))
            if enabled_actions.copy and enabled_actions.c is not None:
                menu.append(self._menu_copy(m, it))
            if enabled_actions.insert and _rule_component_clipboard is not None:
                p = self._menu_paste(m, it)
                menu.append(p)
                if enabled_actions.c is None:  # just a placeholder
                    p.set_label(_("Paste here"))
                else:
                    p.set_label(_("Paste above"))
                    p2 = self._menu_paste(m, it, below=True)
                    p2.set_label(_("Paste below"))
                    menu.append(p2)
            elif enabled_actions.insert_only_rule and isinstance(_rule_component_clipboard, diversion.Rule):
                p = self._menu_paste(m, it)
                menu.append(p)
                if enabled_actions.c is None:
                    p.set_label(_("Paste rule here"))
                else:
                    p.set_label(_("Paste rule above"))
                    p2 = self._menu_paste(m, it, below=True)
                    p2.set_label(_("Paste rule below"))
                    menu.append(p2)
            elif enabled_actions.insert_root and isinstance(_rule_component_clipboard, diversion.Rule):
                p = self._menu_paste(m, m.iter_nth_child(it, 0))
                p.set_label(_("Paste rule"))
                menu.append(p)
            if menu.get_children() and enabled_actions.delete:
                menu.append(Gtk.SeparatorMenuItem(visible=True))
            if enabled_actions.delete:
                menu.append(self._menu_delete(m, it))
            if menu.get_children():
                menu.popup_at_pointer(e)

    def get_insert_menus(self, m, it, enabled_actions: AllowedActions):
        items = []
        if enabled_actions.insert:
            ins = self._menu_insert(m, it)
            items.append(ins)
            if enabled_actions.c is None:  # just a placeholder
                ins.set_label(_("Insert here"))
            else:
                ins.set_label(_("Insert above"))
                ins2 = self._menu_insert(m, it, below=True)
                ins2.set_label(_("Insert below"))
                items.append(ins2)
        elif enabled_actions.insert_only_rule:
            ins = self._menu_create_rule(m, it)
            items.append(ins)
            if enabled_actions.c is None:
                ins.set_label(_("Insert new rule here"))
            else:
                ins.set_label(_("Insert new rule above"))
                ins2 = self._menu_create_rule(m, it, below=True)
                ins2.set_label(_("Insert new rule below"))
                items.append(ins2)
        elif enabled_actions.insert_root:
            ins = self._menu_create_rule(m, m.iter_nth_child(it, 0))
            items.append(ins)
        return items

    def menu_do_flatten(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        idx = parent_c.components.index(c)
        if isinstance(c, diversion.Not):
            parent_c.components = [*parent_c.components[:idx], c.component, *parent_c.components[idx + 1 :]]
            children = [next(m[it].iterchildren())[0].component]
        else:
            parent_c.components = [*parent_c.components[:idx], *c.components, *parent_c.components[idx + 1 :]]
            children = [child[0].component for child in m[it].iterchildren()]
        m.remove(it)
        self._populate_model_func(m, parent_it, children, level=wrapped.level, pos=idx)
        new_iter = m.iter_nth_child(parent_it, idx)
        self.tree_view.expand_row(m.get_path(parent_it), True)
        self.tree_view.get_selection().select_iter(new_iter)
        self._on_update()

    def _menu_flatten(self, m, it):
        menu_flatten = Gtk.MenuItem(_("Flatten"))
        menu_flatten.connect(GtkSignal.ACTIVATE.value, self.menu_do_flatten, m, it)
        menu_flatten.show()
        return menu_flatten

    def _menu_do_insert(self, _mitem, m, it, new_c, below=False):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if len(parent_c.components) == 0:  # we had only a placeholder
            idx = 0
        else:
            idx = parent_c.components.index(c)
        if isinstance(new_c, diversion.Rule) and wrapped.level == 1:
            new_c.source = diversion._file_path  # new rules will be saved to the YAML file
        idx += int(below)
        parent_c.components.insert(idx, new_c)
        self._populate_model_func(m, parent_it, new_c, level=wrapped.level, pos=idx)
        self._on_update()
        if len(parent_c.components) == 1:
            m.remove(it)  # remove placeholder in the end
        new_iter = m.iter_nth_child(parent_it, idx)
        self.tree_view.get_selection().select_iter(new_iter)
        if isinstance(new_c, (diversion.Rule, diversion.And, diversion.Or, diversion.Not)):
            self.tree_view.expand_row(m.get_path(new_iter), True)

    def _menu_do_insert_new(self, _mitem, m, it, cls, initial_value, below=False):
        new_c = cls(initial_value, warn=False)
        return self._menu_do_insert(_mitem, m, it, new_c, below=below)

    def _menu_insert(self, m, it, below=False):
        elements = [
            _("Insert"),
            [
                (_("Sub-rule"), diversion.Rule, []),
                (_("Or"), diversion.Or, []),
                (_("And"), diversion.And, []),
                [
                    _("Condition"),
                    [
                        (_("Feature"), diversion.Feature, rule_conditions.FeatureUI.FEATURES_WITH_DIVERSION[0]),
                        (_("Report"), diversion.Report, 0),
                        (_("Process"), diversion.Process, ""),
                        (_("Mouse process"), diversion.MouseProcess, ""),
                        (_("Modifiers"), diversion.Modifiers, []),
                        (_("Key"), diversion.Key, ""),
                        (_("KeyIsDown"), diversion.KeyIsDown, ""),
                        (_("Active"), diversion.Active, ""),
                        (_("Device"), diversion.Device, ""),
                        (_("Host"), diversion.Host, ""),
                        (_("Setting"), diversion.Setting, [None, "", None]),
                        (_("Test"), diversion.Test, next(iter(diversion.TESTS))),
                        (_("Test bytes"), diversion.TestBytes, [0, 1, 0]),
                        (_("Mouse Gesture"), diversion.MouseGesture, ""),
                    ],
                ],
                [
                    _("Action"),
                    [
                        (_("Key press"), diversion.KeyPress, "space"),
                        (_("Mouse scroll"), diversion.MouseScroll, [0, 0]),
                        (_("Mouse click"), diversion.MouseClick, ["left", 1]),
                        (_("Set"), diversion.Set, [None, "", None]),
                        (_("Execute"), diversion.Execute, [""]),
                        (_("Later"), diversion.Later, [1]),
                    ],
                ],
            ],
        ]

        def build(spec):
            if isinstance(spec, list):  # has sub-menu
                label, children = spec
                item = Gtk.MenuItem(label)
                submenu = Gtk.Menu()
                item.set_submenu(submenu)
                for child in children:
                    submenu.append(build(child))
                return item
            elif isinstance(spec, tuple):  # has click action
                label, feature, *args = spec
                item = Gtk.MenuItem(label)
                args = [a.copy() if isinstance(a, list) else a for a in args]
                item.connect(GtkSignal.ACTIVATE.value, self._menu_do_insert_new, m, it, feature, *args, below)
                return item
            else:
                return None

        menu_insert = build(elements)
        menu_insert.show_all()
        return menu_insert

    def _menu_create_rule(self, m, it, below=False) -> Gtk.MenuItem:
        menu_create_rule = Gtk.MenuItem(_("Insert new rule"))
        menu_create_rule.connect(GtkSignal.ACTIVATE.value, self._menu_do_insert_new, m, it, diversion.Rule, [], below)
        menu_create_rule.show()
        return menu_create_rule

    def menu_do_delete(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        idx = parent_c.components.index(c)
        parent_c.components.pop(idx)
        if len(parent_c.components) == 0:  # placeholder
            self._populate_model_func(m, parent_it, None, level=wrapped.level)
        m.remove(it)
        self.tree_view.get_selection().select_iter(m.iter_nth_child(parent_it, max(0, min(idx, len(parent_c.components) - 1))))
        self._on_update()
        return c

    def _menu_delete(self, m, it) -> Gtk.MenuItem:
        menu_delete = Gtk.MenuItem(_("Delete"))
        menu_delete.connect(GtkSignal.ACTIVATE.value, self.menu_do_delete, m, it)
        menu_delete.show()
        return menu_delete

    def menu_do_negate(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if isinstance(c, diversion.Not):  # avoid double negation
            self.menu_do_flatten(_mitem, m, it)
            self.tree_view.expand_row(m.get_path(parent_it), True)
        elif isinstance(parent_c, diversion.Not):  # avoid double negation
            self.menu_do_flatten(_mitem, m, parent_it)
        else:
            idx = parent_c.components.index(c)
            self._menu_do_insert_new(_mitem, m, it, diversion.Not, c, below=True)
            self.menu_do_delete(_mitem, m, m.iter_nth_child(parent_it, idx))
        self._on_update()

    def _menu_negate(self, m, it) -> Gtk.MenuItem:
        menu_negate = Gtk.MenuItem(_("Negate"))
        menu_negate.connect(GtkSignal.ACTIVATE.value, self.menu_do_negate, m, it)
        menu_negate.show()
        return menu_negate

    def menu_do_wrap(self, _mitem, m, it, cls):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if isinstance(parent_c, diversion.Not):
            new_c = cls([c], warn=False)
            parent_c.component = new_c
            m.remove(it)
            self._populate_model_func(m, parent_it, new_c, level=wrapped.level, pos=0)
            self.tree_view.expand_row(m.get_path(parent_it), True)
            self.tree_view.get_selection().select_iter(m.iter_nth_child(parent_it, 0))
        else:
            idx = parent_c.components.index(c)
            self._menu_do_insert_new(_mitem, m, it, cls, [c], below=True)
            self.menu_do_delete(_mitem, m, m.iter_nth_child(parent_it, idx))
        self._on_update()

    def _menu_wrap(self, m, it) -> Gtk.MenuItem:
        menu_wrap = Gtk.MenuItem(_("Wrap with"))
        submenu_wrap = Gtk.Menu()
        menu_sub_rule = Gtk.MenuItem(_("Sub-rule"))
        menu_and = Gtk.MenuItem(_("And"))
        menu_or = Gtk.MenuItem(_("Or"))
        menu_sub_rule.connect(GtkSignal.ACTIVATE.value, self.menu_do_wrap, m, it, diversion.Rule)
        menu_and.connect(GtkSignal.ACTIVATE.value, self.menu_do_wrap, m, it, diversion.And)
        menu_or.connect(GtkSignal.ACTIVATE.value, self.menu_do_wrap, m, it, diversion.Or)
        submenu_wrap.append(menu_sub_rule)
        submenu_wrap.append(menu_and)
        submenu_wrap.append(menu_or)
        menu_wrap.set_submenu(submenu_wrap)
        menu_wrap.show_all()
        return menu_wrap

    def menu_do_copy(self, _mitem: Gtk.MenuItem, m: Gtk.TreeStore, it: Gtk.TreeIter):
        global _rule_component_clipboard

        wrapped = m[it][0]
        c = wrapped.component
        _rule_component_clipboard = diversion.RuleComponent().compile(c.data())

    def menu_do_cut(self, _mitem, m, it):
        global _rule_component_clipboard

        c = self.menu_do_delete(_mitem, m, it)
        self._on_update()
        _rule_component_clipboard = c

    def _menu_cut(self, m, it):
        menu_cut = Gtk.MenuItem(_("Cut"))
        menu_cut.connect(GtkSignal.ACTIVATE.value, self.menu_do_cut, m, it)
        menu_cut.show()
        return menu_cut

    def menu_do_paste(self, _mitem, m, it, below=False):
        global _rule_component_clipboard

        c = _rule_component_clipboard
        _rule_component_clipboard = None
        if c:
            _rule_component_clipboard = diversion.RuleComponent().compile(c.data())
            self._menu_do_insert(_mitem, m, it, new_c=c, below=below)
            self._on_update()

    def _menu_paste(self, m, it, below=False):
        menu_paste = Gtk.MenuItem(_("Paste"))
        menu_paste.connect(GtkSignal.ACTIVATE.value, self.menu_do_paste, m, it, below)
        menu_paste.show()
        return menu_paste

    def _menu_copy(self, m, it):
        menu_copy = Gtk.MenuItem(_("Copy"))
        menu_copy.connect(GtkSignal.ACTIVATE.value, self.menu_do_copy, m, it)
        menu_copy.show()
        return menu_copy


class DiversionDialog:
    def __init__(self, action_menu):
        window = Gtk.Window()
        window.set_title(_("Solaar Rule Editor"))
        window.connect(GtkSignal.DELETE_EVENT.value, self._closing)
        vbox = Gtk.VBox()

        self.top_panel, self.view = self._create_top_panel()
        for col in self._create_view_columns():
            self.view.append_column(col)
        vbox.pack_start(self.top_panel, True, True, 0)

        self._action_menu = action_menu(
            window,
            self.view,
            populate_model_func=_populate_model,
            on_update=self.on_update,
        )

        self.dirty = False  # if dirty, there are pending changes to be saved

        self.type_ui = {}
        self.update_ui = {}
        self.selected_rule_edit_panel = _create_selected_rule_edit_panel()
        self.ui = defaultdict(lambda: UnsupportedRuleComponentUI(self.selected_rule_edit_panel))
        self.ui.update(
            {  # one instance per type
                rc_class: rc_ui_class(self.selected_rule_edit_panel, on_update=self.on_update)
                for rc_class, rc_ui_class in COMPONENT_UI.items()
            }
        )
        vbox.pack_start(self.selected_rule_edit_panel, False, False, 10)

        self.model = self._create_model()
        self.view.set_model(self.model)
        self.view.expand_all()

        window.add(vbox)

        geometry = Gdk.Geometry()
        geometry.min_width = 600  # don't ask for so much space
        geometry.min_height = 400
        window.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE)
        window.set_position(Gtk.WindowPosition.CENTER)

        window.show_all()

        window.connect(GtkSignal.DELETE_EVENT.value, lambda w, e: w.hide_on_delete() or True)

        style = window.get_style_context()
        style.add_class("solaar")
        self.window = window
        self._editing_component = None

    def _closing(self, window: Gtk.Window, e: Gdk.Event):
        if self.dirty:
            dialog = _create_close_dialog(window)
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.NO:
                window.hide()
            elif response == Gtk.ResponseType.YES:
                self._save_yaml_file()
                window.hide()
            else:
                # don't close
                return True
        else:
            window.hide()

    def _reload_yaml_file(self):
        self.discard_btn.set_sensitive(False)
        self.save_btn.set_sensitive(False)
        self.dirty = False
        for c in self.selected_rule_edit_panel.get_children():
            self.selected_rule_edit_panel.remove(c)
        diversion.load_config_rule_file()
        self.model = self._create_model()
        self.view.set_model(self.model)
        self.view.expand_all()

    def _save_yaml_file(self):
        if diversion._save_config_rule_file():
            self.dirty = False
            self.save_btn.set_sensitive(False)
            self.discard_btn.set_sensitive(False)

    def _create_top_panel(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        view = Gtk.TreeView()
        view.set_headers_visible(False)
        view.set_enable_tree_lines(True)
        view.set_reorderable(False)

        view.connect(GtkSignal.KEY_PRESS_EVENT.value, self._event_key_pressed)
        view.connect(GtkSignal.BUTTON_RELEASE_EVENT.value, self._event_button_released)
        view.get_selection().connect(GtkSignal.CHANGED.value, self._selection_changed)
        sw.add(view)
        sw.set_size_request(0, 300)  # don't ask for so much height

        button_box = Gtk.HBox(spacing=20)
        self.save_btn = Gtk.Button.new_from_icon_name("document-save", Gtk.IconSize.BUTTON)
        self.save_btn.set_label(_("Save changes"))
        self.save_btn.set_always_show_image(True)
        self.save_btn.set_sensitive(False)
        self.save_btn.set_valign(Gtk.Align.CENTER)
        self.discard_btn = Gtk.Button.new_from_icon_name("document-revert", Gtk.IconSize.BUTTON)
        self.discard_btn.set_label(_("Discard changes"))
        self.discard_btn.set_always_show_image(True)
        self.discard_btn.set_sensitive(False)
        self.discard_btn.set_valign(Gtk.Align.CENTER)
        self.save_btn.connect(GtkSignal.CLICKED.value, lambda *_args: self._save_yaml_file())
        self.discard_btn.connect(GtkSignal.CLICKED.value, lambda *_args: self._reload_yaml_file())
        button_box.pack_start(self.save_btn, False, False, 0)
        button_box.pack_start(self.discard_btn, False, False, 0)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_valign(Gtk.Align.CENTER)
        button_box.set_size_request(0, 50)

        vbox = Gtk.VBox()
        vbox.pack_start(button_box, False, False, 0)
        vbox.pack_start(sw, True, True, 0)

        return vbox, view

    def _create_model(self):
        model = Gtk.TreeStore(RuleComponentWrapper)
        if len(diversion.rules.components) == 1:
            # only built-in rules - add empty user rule list
            diversion.rules.components.insert(0, diversion.Rule([], source=diversion._file_path))
        _populate_model(model, None, diversion.rules.components)
        return model

    def _create_view_columns(self):
        cell_icon = Gtk.CellRendererPixbuf()
        cell1 = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn("Type")
        col1.pack_start(cell_icon, False)
        col1.pack_start(cell1, True)
        col1.set_cell_data_func(cell1, lambda _c, c, m, it, _d: c.set_property("text", m.get_value(it, 0).display_left()))
        cell2 = Gtk.CellRendererText()
        col2 = Gtk.TreeViewColumn("Summary")
        col2.pack_start(cell2, True)
        col2.set_cell_data_func(cell2, lambda _c, c, m, it, _d: c.set_property("text", m.get_value(it, 0).display_right()))
        col2.set_cell_data_func(
            cell_icon, lambda _c, c, m, it, _d: c.set_property("icon-name", m.get_value(it, 0).display_icon())
        )
        return col1, col2

    def on_update(self):
        self.view.queue_draw()
        self.dirty = True
        self.save_btn.set_sensitive(True)
        self.discard_btn.set_sensitive(True)

    def _selection_changed(self, selection):
        self.selected_rule_edit_panel.set_sensitive(False)
        (model, it) = selection.get_selected()
        if it is None:
            return
        wrapped = model[it][0]
        component = wrapped.component
        self._editing_component = component
        self.ui[type(component)].show(component, wrapped.editable)
        self.selected_rule_edit_panel.set_sensitive(wrapped.editable)

    def _event_key_pressed(self, v, e):
        """
        Shortcuts:
            Ctrl + I                insert component
            Ctrl + Delete           delete row
            &                       wrap with And
            |                       wrap with Or
            Shift + R               wrap with Rule
            !                       negate
            Ctrl + X                cut
            Ctrl + C                copy
            Ctrl + V                paste below (or here if empty)
            Ctrl + Shift + V        paste above
            *                       flatten
            Ctrl + S                save changes
        """
        state = e.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
        m, it = v.get_selection().get_selected()
        enabled_actions = allowed_actions(m, it)
        if state & Gdk.ModifierType.CONTROL_MASK:
            if enabled_actions.delete and e.keyval in [Gdk.KEY_x, Gdk.KEY_X]:
                self._action_menu.menu_do_cut(None, m, it)
            elif enabled_actions.copy and e.keyval in [Gdk.KEY_c, Gdk.KEY_C] and enabled_actions.c is not None:
                self._action_menu.menu_do_copy(None, m, it)
            elif enabled_actions.insert and _rule_component_clipboard is not None and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self._action_menu.menu_do_paste(
                    None, m, it, below=enabled_actions.c is not None and not (state & Gdk.ModifierType.SHIFT_MASK)
                )
            elif (
                enabled_actions.insert_only_rule
                and isinstance(_rule_component_clipboard, diversion.Rule)
                and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]
            ):
                self._action_menu.menu_do_paste(
                    None, m, it, below=enabled_actions.c is not None and not (state & Gdk.ModifierType.SHIFT_MASK)
                )
            elif (
                enabled_actions.insert_root
                and isinstance(_rule_component_clipboard, diversion.Rule)
                and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]
            ):
                self._action_menu.menu_do_paste(None, m, m.iter_nth_child(it, 0))
            elif enabled_actions.delete and e.keyval in [Gdk.KEY_KP_Delete, Gdk.KEY_Delete]:
                self._action_menu.menu_do_delete(None, m, it)
            elif (enabled_actions.insert or enabled_actions.insert_only_rule or enabled_actions.insert_root) and e.keyval in [
                Gdk.KEY_i,
                Gdk.KEY_I,
            ]:
                menu = Gtk.Menu()
                for item in self._action_menu.get_insert_menus(
                    m,
                    it,
                    enabled_actions,
                ):
                    menu.append(item)
                menu.show_all()
                rect = self.view.get_cell_area(m.get_path(it), self.view.get_column(1))
                menu.popup_at_rect(self.window.get_window(), rect, Gdk.Gravity.WEST, Gdk.Gravity.CENTER, e)
            elif self.dirty and e.keyval in [Gdk.KEY_s, Gdk.KEY_S]:
                self._save_yaml_file()
        else:
            if enabled_actions.wrap:
                if e.keyval == Gdk.KEY_exclam:
                    self._action_menu.menu_do_negate(None, m, it)
                elif e.keyval == Gdk.KEY_ampersand:
                    self._action_menu.menu_do_wrap(None, m, it, diversion.And)
                elif e.keyval == Gdk.KEY_bar:
                    self._action_menu.menu_do_wrap(None, m, it, diversion.Or)
                elif e.keyval in [Gdk.KEY_r, Gdk.KEY_R] and (state & Gdk.ModifierType.SHIFT_MASK):
                    self._action_menu.menu_do_wrap(None, m, it, diversion.Rule)
            if enabled_actions.flatten and e.keyval in [Gdk.KEY_asterisk, Gdk.KEY_KP_Multiply]:
                self._action_menu.menu_do_flatten(None, m, it)

    def _event_button_released(self, v, e):
        self._action_menu.create_menu_event_button_released(v, e)

    def update_devices(self):
        for rc in self.ui.values():
            rc.update_devices()
        self.view.queue_draw()


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

        self.connect(GtkSignal.CHANGED.value, lambda *a: replace_with(self.get_value(invalid_as_str=False)))

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
    def id(self) -> str:
        return self.serial or self.unitId or ""

    @property
    def identifiers(self) -> list[str]:
        return [id for id in (self.serial, self.unitId) if id]

    @property
    def display_name(self) -> str:
        return f"{self.codename} ({self.id})"

    def matches(self, search: str) -> bool:
        return search and search in (self.serial, self.unitId, self.display_name)

    def update(self, device: DeviceInfo) -> None:
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
        self._devices: list[DeviceInfo] = []
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
    CLASS = diversion.Rule

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
    CLASS = diversion.And

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("And")


class OrUI(RuleComponentUI):
    CLASS = diversion.Or

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("Or")


class LaterUI(RuleComponentUI):
    CLASS = diversion.Later
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
        self.field.connect(GtkSignal.VALUE_CHANGED.value, self._on_update)
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
    CLASS = diversion.Not

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.component  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _("Not")


class ActionUI(RuleComponentUI):
    CLASS = diversion.Action

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
        self.toggle_widget.connect(GtkSignal.CHANGED.value, self._changed)
        self.range_widget = Gtk.SpinButton.new_with_range(0, 0xFFFF, 1)
        self.range_widget.connect(GtkSignal.VALUE_CHANGED.value, self._changed)
        self.choice_widget = SmartComboBox(
            [], completion=True, has_entry=True, case_insensitive=True, replace_with_default_name=True
        )
        self.choice_widget.connect(GtkSignal.CHANGED.value, self._changed)
        self.sub_key_widget = SmartComboBox([])
        self.sub_key_widget.connect(GtkSignal.CHANGED.value, self._changed)
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
        self.device_field.connect(GtkSignal.CHANGED.value, self._on_update)
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
    CLASS = diversion.Active
    label_text = _("Device is active and its settings can be changed.")

    @classmethod
    def left_label(cls, component):
        return _("Active")


class DeviceUI(_DeviceUI, ConditionUI):
    CLASS = diversion.Device
    label_text = _("Device that originated the current notification.")

    @classmethod
    def left_label(cls, component):
        return _("Device")


class HostUI(ConditionUI):
    CLASS = diversion.Host

    def create_widgets(self):
        self.widgets = {}
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True)
        self.label.set_text(_("Name of host computer."))
        self.widgets[self.label] = (0, 0, 1, 1)
        self.field = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True)
        self.field.set_size_request(600, 0)
        self.field.connect(GtkSignal.CHANGED.value, self._on_update)
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
    MULTIPLE = [Kind.MULTIPLE_TOGGLE, Kind.MAP_CHOICE, Kind.MULTIPLE_RANGE]
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
        self.device_field.connect(GtkSignal.CHANGED.value, self._changed_device)
        self.device_field.connect(GtkSignal.CHANGED.value, self._on_update)
        self.widgets[self.device_field] = (1, 1, 1, 1)

        lbl = Gtk.Label(
            label=_("Setting"),
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            hexpand=True,
            vexpand=False,
        )
        self.widgets[lbl] = (0, 2, 1, 1)
        self.setting_field = SmartComboBox([(s[0].name, s[0].label) for s in ALL_SETTINGS.values()])
        self.setting_field.set_valign(Gtk.Align.CENTER)
        self.setting_field.connect(GtkSignal.CHANGED.value, self._changed_setting)
        self.setting_field.connect(GtkSignal.CHANGED.value, self._on_update)
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
        self.key_field.connect(GtkSignal.CHANGED.value, self._changed_key)
        self.key_field.connect(GtkSignal.CHANGED.value, self._on_update)
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
        settings = ALL_SETTINGS.get(setting, [])
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
            settings = ALL_SETTINGS.get(setting_name, [None])
            setting = settings[0]  # if settings have the same name, use the first one to get the basic data
        val_class = setting.validator_class if setting else None
        kind = val_class.kind if val_class else None
        if kind in cls.MULTIPLE:
            keys = UnsortedNamedInts()
            for s in settings:
                universe = getattr(s, "keys_universe" if kind == Kind.MAP_CHOICE else "choices_universe", None)
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
            if lbl and isinstance(lbl, tuple) and lbl[0]:
                label = lbl[0]
            else:
                label = str(k)
            return k, label

        with self.ignore_changes():
            self.key_field.set_all_values(sorted(map(item, keys), key=lambda k: k[1]))
            ds = device.settings if device else {}
            device_setting = ds.get(setting_name, None)
            supported_keys = None
            if device_setting:
                val = device_setting._validator
                if device_setting.kind == Kind.MULTIPLE_TOGGLE:
                    supported_keys = val.get_options() or None
                elif device_setting.kind == Kind.MAP_CHOICE:
                    choices = val.choices or None
                    supported_keys = choices.keys() if choices else None
                elif device_setting.kind == Kind.MULTIPLE_RANGE:
                    supported_keys = val.keys
            self.key_field.show_only(supported_keys, include_new=True)
            self._update_validation()

    def _update_value_list(self, setting_name, device=None, key=None):
        setting, val_class, kind, keys = self._setting_attributes(setting_name, device)
        ds = device.settings if device else {}
        device_setting = ds.get(setting_name, None)
        if kind in (Kind.TOGGLE, Kind.MULTIPLE_TOGGLE):
            self.value_field.make_toggle()
        elif kind in (Kind.CHOICE, Kind.MAP_CHOICE):
            all_values, extra = self._all_choices(device_setting or setting_name)
            self.value_field.make_choice(all_values, extra)
            supported_values = None
            if device_setting:
                val = device_setting._validator
                choices = getattr(val, "choices", None) or None
                if kind == Kind.CHOICE:
                    supported_values = choices
                elif kind == Kind.MAP_CHOICE and isinstance(choices, dict):
                    supported_values = choices.get(key, None) or None
            self.value_field.choice_widget.show_only(supported_values, include_new=True)
            self._update_validation()
        elif kind == Kind.RANGE:
            self.value_field.make_range(val_class.min_value, val_class.max_value)
        elif kind == Kind.MULTIPLE_RANGE:
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
        if kind in (Kind.CHOICE, Kind.MAP_CHOICE):
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
        key = None
        if kind in cls.MULTIPLE:
            key = next(a, None)
            key = _from_named_ints(key, keys) if keys else key
            key_label = getattr(setting, "_labels", {}).get(key, [None])[0] if setting else None
            disp.append(key_label or key)
        value = next(a, None)
        if setting and (kind in (Kind.CHOICE, Kind.MAP_CHOICE)):
            all_values = cls._all_choices(setting or setting_name)[0]
            supported_values = None
            if device_setting:
                val = device_setting._validator
                choices = getattr(val, "choices", None) or None
                if kind == Kind.CHOICE:
                    supported_values = choices
                elif kind == Kind.MAP_CHOICE and isinstance(choices, dict):
                    supported_values = choices.get(key, None) or None
                if supported_values and isinstance(supported_values, NamedInts):
                    value = supported_values[value]
            if not supported_values and all_values and isinstance(all_values, NamedInts):
                value = all_values[value]
            disp.append(value)
        elif kind == Kind.MULTIPLE_RANGE and isinstance(value, dict) and len(value) == 1:
            k, v = next(iter(value.items()))
            k = (getattr(setting, "_labels_sub", {}).get(k, (None,))[0] if setting else None) or k
            disp.append(f"{k}={v}")
        elif kind in (Kind.TOGGLE, Kind.MULTIPLE_TOGGLE):
            disp.append(_(str(value)))
        else:
            disp.append(value)
        return device_disp + "  " + "  ".join(map(lambda s: shlex_quote(str(s)), [*disp, *a]))


class SetUI(_SettingWithValueUI, ActionUI):
    CLASS = diversion.Set
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
    CLASS = diversion.Setting
    ACCEPT_TOGGLE = False

    label_text = _("Setting on device")

    def show(self, component, editable):
        ConditionUI.show(self, component, editable)
        _SettingWithValueUI.show(self, component, editable)

    def _on_update(self, *_args):
        if not self._ignore_changes and self.component:
            ConditionUI._on_update(self, *_args)
            _SettingWithValueUI._on_update(self, *_args)


COMPONENT_UI: dict[Any, RuleComponentUI] = {
    diversion.Rule: RuleUI,
    diversion.Not: NotUI,
    diversion.Or: OrUI,
    diversion.And: AndUI,
    diversion.Later: LaterUI,
    diversion.Process: rule_conditions.ProcessUI,
    diversion.MouseProcess: rule_conditions.MouseProcessUI,
    diversion.Active: ActiveUI,
    diversion.Device: DeviceUI,
    diversion.Host: HostUI,
    diversion.Feature: rule_conditions.FeatureUI,
    diversion.Report: rule_conditions.ReportUI,
    diversion.Modifiers: rule_conditions.ModifiersUI,
    diversion.Key: rule_conditions.KeyUI,
    diversion.KeyIsDown: rule_conditions.KeyIsDownUI,
    diversion.Test: rule_conditions.TestUI,
    diversion.TestBytes: rule_conditions.TestBytesUI,
    diversion.Setting: SettingUI,
    diversion.MouseGesture: rule_conditions.MouseGestureUI,
    diversion.KeyPress: rule_actions.KeyPressUI,
    diversion.MouseScroll: rule_actions.MouseScrollUI,
    diversion.MouseClick: rule_actions.MouseClickUI,
    diversion.Execute: rule_actions.ExecuteUI,
    diversion.Set: SetUI,
    # type(None): RuleComponentUI,  # placeholders for empty rule/And/Or
}

_all_devices = AllDevicesInfo()
_dev_model = None


def update_devices():
    global _dev_model
    global _all_devices
    global _diversion_dialog
    if _dev_model and _all_devices.refresh() and _diversion_dialog:
        _diversion_dialog.update_devices()


def show_window(model: Gtk.TreeStore):
    GObject.type_register(RuleComponentWrapper)
    global _diversion_dialog
    global _dev_model
    _dev_model = model
    if _diversion_dialog is None:
        _diversion_dialog = DiversionDialog(ActionMenu)
    update_devices()
    _diversion_dialog.window.present()
