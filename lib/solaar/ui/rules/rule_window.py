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
import dataclasses

from typing import Any
from typing import Callable
from typing import Optional

from gi.repository import Gdk
from gi.repository import Gtk
from logitech_receiver import diversion as _DIV

from solaar.i18n import _
from solaar.ui import diversion_rules
from solaar.ui import rule_conditions
from solaar.ui.rules.handler import EventHandler


def _create_model(rules: _DIV.Rule) -> Gtk.TreeStore:
    """Converts a Rules instance into a Gtk.TreeStore."""
    model = Gtk.TreeStore(diversion_rules.RuleComponentWrapper)
    if len(rules.components) == 1:
        # only built-in rules - add empty user rule list
        rules.components.insert(0, _DIV.Rule([], source=_DIV._CONFIG_FILE_PATH))
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
    wrapped = diversion_rules.RuleComponentWrapper(rule_component, level, editable=editable)
    piter = model.insert(it, pos, (wrapped,))
    if isinstance(rule_component, (_DIV.Rule, _DIV.And, _DIV.Or, _DIV.Later)):
        for c in rule_component.components:
            ed = editable or (isinstance(c, _DIV.Rule) and c.source is not None)
            _populate_model(model, piter, c, level + 1, editable=ed)
        if len(rule_component.components) == 0:
            _populate_model(model, piter, None, level + 1, editable=editable)
    elif isinstance(rule_component, _DIV.Not):
        _populate_model(model, piter, rule_component.component, level + 1, editable=editable)


class DiversionDialog:
    def __init__(self, model, view):
        self._model = model
        self._view = view

        self.action_menu = None

        # Init UI
        event_handler = EventHandler(
            handle_event_key_pressed=self.handle_event_key_pressed,
            handle_event_button_released=self.handle_event_button_released,
            handle_selection_changed=self.handle_selection_changed,
            handle_save_yaml_file=self.handle_save_yaml_file,
            handle_reload_yaml_file=self.handle_reload_yaml_file,
            handle_close=self.handle_close,
        )
        self._view.init_ui(event_handler, self.on_update)

        self.action_menu = ActionMenu(self._view.window, self._view.tree_view, on_update=self.on_update)

        self.handle_rule_update(self._model.rules)

    def handle_rule_update(self, rules: _DIV.Rule):
        """Updates rule view given rules.

        Removes all existing rules and adds new ones.
        """
        self._view.clear_selected_rule_edit_panel()
        tree_model = _create_model(rules)
        self._view.update_tree_view(tree_model)

    def on_update(self):
        self._view.tree_view.queue_draw()
        self._model.unsaved_changes = True
        self._view.set_save_discard_buttons_status(True)

    def update_devices(self):
        for rc in self._view.ui.values():
            rc.update_devices()
        self._view.tree_view.queue_draw()

    def handle_event_key_pressed(self, v: Gtk.TreeView, e: Gdk.EventKey):
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
        self.action_menu.create_menu_event_key_pressed(
            v,
            e,
            save_callback=self.handle_save_yaml_file,
        )

    def handle_event_button_released(self, v, e):
        if e.button == Gdk.BUTTON_SECONDARY:  # right click
            self.action_menu.create_context_menu(v, e)

    def handle_close(self, window: Gtk.Window, _e: Gdk.Event):
        if self._model.unsaved_changes:
            self._view.show_close_dialog(window, self.handle_save_yaml_file)
        else:
            self._view.close()

    def handle_reload_yaml_file(self):
        self._view.set_save_discard_buttons_status(False)

        loaded_rules = self._model.load_rules()
        self.handle_rule_update(loaded_rules)

    def handle_save_yaml_file(self):
        if self._model.save_rules():
            self._view.set_save_discard_buttons_status(False)

    def handle_selection_changed(self, selection: Gtk.TreeSelection):
        self._view.selected_rule_edit_panel.set_sensitive(False)

        (model, it) = selection.get_selected()
        if it is None:
            return
        wrapped = model[it][0]
        component = wrapped.component

        # TODO fix None not allowed
        self._view.ui[type(component)].show(component, wrapped.editable)
        self._view.selected_rule_edit_panel.set_sensitive(wrapped.editable)

    def run(self):
        self._view.show()


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
    can_delete = wrapped.editable and not isinstance(parent_c, _DIV.Not) and c is not None and wrapped.level >= 1
    can_insert = wrapped.editable and not isinstance(parent_c, _DIV.Not) and wrapped.level >= 2
    can_insert_only_rule = wrapped.editable and wrapped.level == 1
    can_flatten = (
        wrapped.editable
        and not isinstance(parent_c, _DIV.Not)
        and isinstance(c, (_DIV.Rule, _DIV.And, _DIV.Or))
        and wrapped.level >= 2
        and len(c.components)
    )
    can_copy = wrapped.level >= 1
    can_insert_root = wrapped.editable and wrapped.level == 0
    return AllowedActions(c, can_copy, can_delete, can_flatten, can_insert, can_insert_only_rule, can_insert_root, can_wrap)


class ActionMenu:
    def __init__(self, window, tree_view, on_update):
        self.window = window
        self.tree_view = tree_view
        self._on_update = on_update
        self._clipboard = None

    def create_menu_event_key_pressed(self, v: Gtk.TreeView, e: Gdk.EventKey, save_callback: Callable):
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
                self.handle_cut(None, m, it)
            elif enabled_actions.copy and e.keyval in [Gdk.KEY_c, Gdk.KEY_C] and enabled_actions.c is not None:
                self.handle_copy(None, m, it)
            elif enabled_actions.insert and self._clipboard is not None and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self.handle_paste(
                    None, m, it, below=enabled_actions.c is not None and not (state & Gdk.ModifierType.SHIFT_MASK)
                )
            elif (
                enabled_actions.insert_only_rule
                and isinstance(self._clipboard, _DIV.Rule)
                and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]
            ):
                self.handle_paste(
                    None, m, it, below=enabled_actions.c is not None and not (state & Gdk.ModifierType.SHIFT_MASK)
                )
            elif enabled_actions.insert_root and isinstance(self._clipboard, _DIV.Rule) and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self.handle_paste(None, m, m.iter_nth_child(it, 0))
            elif enabled_actions.delete and e.keyval in [Gdk.KEY_KP_Delete, Gdk.KEY_Delete]:
                self.handle_delete(None, m, it)
            elif (enabled_actions.insert or enabled_actions.insert_only_rule or enabled_actions.insert_root) and e.keyval in [
                Gdk.KEY_i,
                Gdk.KEY_I,
            ]:
                menu = Gtk.Menu()
                for item in self._get_insert_menus(m, it, enabled_actions):
                    menu.append(item)
                menu.show_all()
                rect = self.tree_view.get_cell_area(m.get_path(it), self.tree_view.get_column(1))
                menu.popup_at_rect(self.window.get_window(), rect, Gdk.Gravity.WEST, Gdk.Gravity.CENTER, e)
            elif e.keyval in [Gdk.KEY_s, Gdk.KEY_S]:
                save_callback()
        else:
            if enabled_actions.wrap:
                if e.keyval == Gdk.KEY_exclam:
                    self.handle_negate(None, m, it)
                elif e.keyval == Gdk.KEY_ampersand:
                    self.handle_wrap(None, m, it, _DIV.And)
                elif e.keyval == Gdk.KEY_bar:
                    self.handle_wrap(None, m, it, _DIV.Or)
                elif e.keyval in [Gdk.KEY_r, Gdk.KEY_R] and (state & Gdk.ModifierType.SHIFT_MASK):
                    self.handle_wrap(None, m, it, _DIV.Rule)
            if enabled_actions.flatten and e.keyval in [Gdk.KEY_asterisk, Gdk.KEY_KP_Multiply]:
                self.create_menu_do_flatten(None, m, it)

    def create_context_menu(self, v: Gtk.TreeView, e: Gdk.EventButton):
        """Creates right-click dialog."""
        menu = Gtk.Menu()
        m, it = v.get_selection().get_selected()

        enabled_actions = allowed_actions(m, it)
        for item in self._get_insert_menus(m, it, enabled_actions):
            menu.append(item)

        if enabled_actions.flatten:
            menu.append(self.create_menu_flatten(m, it))
        if enabled_actions.wrap:
            menu.append(self.create_menu_wrap(m, it))
            menu.append(self.create_menu_negate(m, it))
        if menu.get_children():
            menu.append(Gtk.SeparatorMenuItem(visible=True))
        if enabled_actions.delete:
            menu.append(self.create_menu_cut(m, it))
        if enabled_actions.copy and enabled_actions.c is not None:
            menu.append(self.create_menu_copy(m, it))
        if enabled_actions.insert and self._clipboard is not None:
            p = self.create_menu_paste(m, it)
            menu.append(p)
            if enabled_actions.c is None:  # just a placeholder
                p.set_label(_("Paste here"))
            else:
                p.set_label(_("Paste above"))
                p2 = self.create_menu_paste(m, it, below=True)
                p2.set_label(_("Paste below"))
                menu.append(p2)
        elif enabled_actions.insert_only_rule and isinstance(self._clipboard, _DIV.Rule):
            p = self.create_menu_paste(m, it)
            menu.append(p)
            if enabled_actions.c is None:
                p.set_label(_("Paste rule here"))
            else:
                p.set_label(_("Paste rule above"))
                p2 = self.create_menu_paste(m, it, below=True)
                p2.set_label(_("Paste rule below"))
                menu.append(p2)
        elif enabled_actions.insert_root and isinstance(self._clipboard, _DIV.Rule):
            p = self.create_menu_paste(m, m.iter_nth_child(it, 0))
            p.set_label(_("Paste rule"))
            menu.append(p)
        if menu.get_children() and enabled_actions.delete:
            menu.append(Gtk.SeparatorMenuItem(visible=True))
        if enabled_actions.delete:
            menu.append(self.create_menu_delete(m, it))
        if menu.get_children():
            menu.popup_at_pointer(e)

    def create_insert_menu(self, m: Gtk.TreeStore, it: Gtk.TreeIter, below=False) -> Gtk.MenuItem:
        elements = [
            _("Insert"),
            [
                (_("Sub-rule"), _DIV.Rule, []),
                (_("Or"), _DIV.Or, []),
                (_("And"), _DIV.And, []),
                [
                    _("Condition"),
                    [
                        (_("Feature"), _DIV.Feature, rule_conditions.FeatureUI.FEATURES_WITH_DIVERSION[0]),
                        (_("Report"), _DIV.Report, 0),
                        (_("Process"), _DIV.Process, ""),
                        (_("Mouse process"), _DIV.MouseProcess, ""),
                        (_("Modifiers"), _DIV.Modifiers, []),
                        (_("Key"), _DIV.Key, ""),
                        (_("KeyIsDown"), _DIV.KeyIsDown, ""),
                        (_("Active"), _DIV.Active, ""),
                        (_("Device"), _DIV.Device, ""),
                        (_("Host"), _DIV.Host, ""),
                        (_("Setting"), _DIV.Setting, [None, "", None]),
                        (_("Test"), _DIV.Test, next(iter(_DIV.TESTS))),
                        (_("Test bytes"), _DIV.TestBytes, [0, 1, 0]),
                        (_("Mouse Gesture"), _DIV.MouseGesture, ""),
                    ],
                ],
                [
                    _("Action"),
                    [
                        (_("Key press"), _DIV.KeyPress, "space"),
                        (_("Mouse scroll"), _DIV.MouseScroll, [0, 0]),
                        (_("Mouse click"), _DIV.MouseClick, ["left", 1]),
                        (_("Set"), _DIV.Set, [None, "", None]),
                        (_("Execute"), _DIV.Execute, [""]),
                        (_("Later"), _DIV.Later, [1]),
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
                item.connect("activate", self.handle_insert_new, m, it, feature, *args, below)
                return item
            else:
                return None

        menu_insert = build(elements)
        menu_insert.show_all()
        return menu_insert

    def _get_insert_menus(self, m: Gtk.TreeStore, it: Gtk.TreeIter, enabled_actions: AllowedActions) -> list:
        items = []
        if enabled_actions.insert:
            ins = self.create_insert_menu(m, it)
            items.append(ins)
            if enabled_actions.c is None:  # just a placeholder
                ins.set_label(_("Insert here"))
            else:
                ins.set_label(_("Insert above"))
                ins2 = self.create_insert_menu(m, it, below=True)
                ins2.set_label(_("Insert below"))
                items.append(ins2)
        elif enabled_actions.insert_only_rule:
            ins = self.create_menu_create_rule(m, it)
            items.append(ins)
            if enabled_actions.c is None:
                ins.set_label(_("Insert new rule here"))
            else:
                ins.set_label(_("Insert new rule above"))
                ins2 = self.create_menu_create_rule(m, it, below=True)
                ins2.set_label(_("Insert new rule below"))
                items.append(ins2)
        elif enabled_actions.insert_root:
            ins = self.create_menu_create_rule(m, m.iter_nth_child(it, 0))
            items.append(ins)
        return items

    def create_menu_flatten(self, m, it) -> Gtk.MenuItem:
        menu_flatten = Gtk.MenuItem(_("Flatten"))
        menu_flatten.connect("activate", self.create_menu_do_flatten, m, it)
        menu_flatten.show()
        return menu_flatten

    def create_menu_create_rule(self, m: Gtk.TreeStore, it: Gtk.TreeIter, below=False) -> Gtk.MenuItem:
        menu_create_rule = Gtk.MenuItem(_("Insert new rule"))
        menu_create_rule.connect("activate", self.handle_insert_new, m, it, _DIV.Rule, [], below)
        menu_create_rule.show()
        return menu_create_rule

    def create_menu_delete(self, m: Gtk.TreeStore, it: Gtk.TreeIter) -> Gtk.MenuItem:
        menu_delete = Gtk.MenuItem(_("Delete"))
        menu_delete.connect("activate", self.handle_delete, m, it)
        menu_delete.show()
        return menu_delete

    def create_menu_negate(self, m: Gtk.TreeStore, it: Gtk.TreeIter) -> Gtk.MenuItem:
        menu_negate = Gtk.MenuItem(_("Negate"))
        menu_negate.connect("activate", self.handle_negate, m, it)
        menu_negate.show()
        return menu_negate

    def create_menu_wrap(self, m: Gtk.TreeStore, it: Gtk.TreeIter) -> Gtk.MenuItem:
        menu_wrap = Gtk.MenuItem(_("Wrap with"))
        submenu_wrap = Gtk.Menu()
        menu_sub_rule = Gtk.MenuItem(_("Sub-rule"))
        menu_and = Gtk.MenuItem(_("And"))
        menu_or = Gtk.MenuItem(_("Or"))
        menu_sub_rule.connect("activate", self.handle_wrap, m, it, _DIV.Rule)
        menu_and.connect("activate", self.handle_wrap, m, it, _DIV.And)
        menu_or.connect("activate", self.handle_wrap, m, it, _DIV.Or)
        submenu_wrap.append(menu_sub_rule)
        submenu_wrap.append(menu_and)
        submenu_wrap.append(menu_or)
        menu_wrap.set_submenu(submenu_wrap)
        menu_wrap.show_all()
        return menu_wrap

    def create_menu_cut(self, m: Gtk.TreeStore, it: Gtk.TreeIter) -> Gtk.MenuItem:
        menu_cut = Gtk.MenuItem(_("Cut"))
        menu_cut.connect("activate", self.handle_cut, m, it)
        menu_cut.show()
        return menu_cut

    def create_menu_paste(self, m: Gtk.TreeStore, it: Gtk.TreeIter, below=False) -> Gtk.MenuItem:
        menu_paste = Gtk.MenuItem(_("Paste"))
        menu_paste.connect("activate", self.handle_paste, m, it, below)
        menu_paste.show()
        return menu_paste

    def create_menu_copy(self, m: Gtk.TreeStore, it: Gtk.TreeIter) -> Gtk.MenuItem:
        menu_copy = Gtk.MenuItem(_("Copy"))
        menu_copy.connect("activate", self.handle_copy, m, it)
        menu_copy.show()
        return menu_copy

    def create_menu_do_flatten(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        idx = parent_c.components.index(c)
        if isinstance(c, _DIV.Not):
            parent_c.components = [*parent_c.components[:idx], c.component, *parent_c.components[idx + 1 :]]
            children = [next(m[it].iterchildren())[0].component]
        else:
            parent_c.components = [*parent_c.components[:idx], *c.components, *parent_c.components[idx + 1 :]]
            children = [child[0].component for child in m[it].iterchildren()]
        m.remove(it)
        _populate_model(m, parent_it, children, level=wrapped.level, pos=idx)
        new_iter = m.iter_nth_child(parent_it, idx)
        self.tree_view.expand_row(m.get_path(parent_it), True)
        self.tree_view.get_selection().select_iter(new_iter)
        self._on_update()

    def handle_delete(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        idx = parent_c.components.index(c)
        parent_c.components.pop(idx)
        if len(parent_c.components) == 0:  # placeholder
            _populate_model(m, parent_it, None, level=wrapped.level)
        m.remove(it)
        self.tree_view.get_selection().select_iter(m.iter_nth_child(parent_it, max(0, min(idx, len(parent_c.components) - 1))))
        self._on_update()
        return c

    def handle_insert(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter, new_c, below=False):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if len(parent_c.components) == 0:  # we had only a placeholder
            idx = 0
        else:
            idx = parent_c.components.index(c)
        if isinstance(new_c, _DIV.Rule) and wrapped.level == 1:
            new_c.source = _DIV._CONFIG_FILE_PATH  # new rules will be saved to the YAML file
        idx += int(below)
        parent_c.components.insert(idx, new_c)
        _populate_model(m, parent_it, new_c, level=wrapped.level, pos=idx)
        self._on_update()
        if len(parent_c.components) == 1:
            m.remove(it)  # remove placeholder in the end
        new_iter = m.iter_nth_child(parent_it, idx)
        self.tree_view.get_selection().select_iter(new_iter)
        if isinstance(new_c, (_DIV.Rule, _DIV.And, _DIV.Or, _DIV.Not)):
            self.tree_view.expand_row(m.get_path(new_iter), True)

    def handle_insert_new(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter, cls, initial_value, below=False):
        new_c = cls(initial_value, warn=False)
        return self.handle_insert(_mitem, m, it, new_c, below=below)

    def handle_negate(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if isinstance(c, _DIV.Not):  # avoid double negation
            self.create_menu_do_flatten(_mitem, m, it)
            self.tree_view.expand_row(m.get_path(parent_it), True)
        elif isinstance(parent_c, _DIV.Not):  # avoid double negation
            self.create_menu_do_flatten(_mitem, m, parent_it)
        else:
            idx = parent_c.components.index(c)
            self.handle_insert_new(_mitem, m, it, _DIV.Not, c, below=True)
            self.handle_delete(_mitem, m, m.iter_nth_child(parent_it, idx))
        self._on_update()

    def handle_wrap(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter, cls):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if isinstance(parent_c, _DIV.Not):
            new_c = cls([c], warn=False)
            parent_c.component = new_c
            m.remove(it)
            _populate_model(m, parent_it, new_c, level=wrapped.level, pos=0)
            self.tree_view.expand_row(m.get_path(parent_it), True)
            self.tree_view.get_selection().select_iter(m.iter_nth_child(parent_it, 0))
        else:
            idx = parent_c.components.index(c)
            self.handle_insert_new(_mitem, m, it, cls, [c], below=True)
            self.handle_delete(_mitem, m, m.iter_nth_child(parent_it, idx))
        self._on_update()

    def handle_copy(self, _mitem: Gtk.MenuItem, m: Gtk.TreeStore, it: Gtk.TreeIter):
        wrapped = m[it][0]
        c = wrapped.component
        self._clipboard = _DIV.RuleComponent().compile(c.data())

    def handle_cut(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter):
        c = self.handle_delete(_mitem, m, it)
        self._on_update()
        self._clipboard = c

    def handle_paste(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter, below=False):
        c = self._clipboard
        self._clipboard = None
        if c:
            self._clipboard = _DIV.RuleComponent().compile(c.data())
            self.handle_insert(_mitem, m, it, new_c=c, below=below)
            self._on_update()
