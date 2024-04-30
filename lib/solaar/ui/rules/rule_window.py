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

from collections import defaultdict
from typing import Any
from typing import Callable

from gi.repository import Gdk
from gi.repository import Gtk
from logitech_receiver import diversion as _DIV

from solaar.i18n import _
from solaar.ui import rule_conditions


class DiversionDialog:
    def __init__(
        self,
        model,
        view,
        component_ui: dict,
        unsupported_rule_component_ui,
        create_model_func: Callable,
        populate_model_func: Callable,
        load_rules_func: Callable,
        save_rules_func: Callable[..., bool],
    ):
        self.rule_model = model
        self.rule_view = view
        self._unsupported_rule_component_ui = unsupported_rule_component_ui
        self._create_model_func = create_model_func
        self._populate_model_func = populate_model_func
        self._load_rules_func = load_rules_func
        self._save_rules_func = save_rules_func

        window = self.rule_view.create_main_window()
        window.connect("delete-event", self.handle_close)
        vbox = Gtk.VBox()

        top_panel, self.tree_view = self._create_top_panel()
        for col in self.rule_view.create_view_columns():
            self.tree_view.append_column(col)
        vbox.pack_start(top_panel, True, True, 0)

        self.action_menu = ActionMenu(window, self.tree_view, populate_model_func, on_update=self.on_update)

        self.selected_rule_edit_panel = self.rule_view.create_selected_rule_edit_panel()
        self.ui = defaultdict(lambda: self._unsupported_rule_component_ui(self.selected_rule_edit_panel))
        self.ui.update(
            {  # one instance per type
                rc_class: rc_ui_class(self.selected_rule_edit_panel, on_update=self.on_update)
                for rc_class, rc_ui_class in component_ui.items()
            }
        )
        vbox.pack_start(self.selected_rule_edit_panel, False, False, 10)

        self.model = self._create_model_func()
        self.tree_view.set_model(self.model)
        self.tree_view.expand_all()

        window.add(vbox)
        window.show_all()
        window.connect("delete-event", lambda w, e: w.hide_on_delete() or True)

        style = window.get_style_context()
        style.add_class("solaar")
        self.window = window
        self._editing_component = None

    def _create_top_panel(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)

        tree_view = self.rule_view.create_tree_view(
            callback_key_pressed=self.handle_event_key_pressed,
            callback_event_button_released=self.handle_event_button_released,
            callback_selection_changed=self.handle_selection_changed,
        )

        sw.add(tree_view)
        sw.set_size_request(0, 300)  # don't ask for so much height

        self.rule_view.save_btn = self.rule_view.create_save_button(lambda *_args: self.handle_save_yaml_file())
        self.rule_view.discard_btn = self.rule_view.create_discard_button(lambda *_args: self.handle_reload_yaml_file())

        button_box = Gtk.HBox(spacing=20)
        button_box.pack_start(self.rule_view.save_btn, False, False, 0)
        button_box.pack_start(self.rule_view.discard_btn, False, False, 0)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_valign(Gtk.Align.CENTER)
        button_box.set_size_request(0, 50)

        vbox = Gtk.VBox()
        vbox.pack_start(button_box, False, False, 0)
        vbox.pack_start(sw, True, True, 0)

        return vbox, tree_view

    def on_update(self):
        self.tree_view.queue_draw()
        self.rule_model.unsaved_changes = True
        self.rule_view.set_save_discard_buttons_status(True)

    def update_devices(self):
        for rc in self.ui.values():
            rc.update_devices()
        self.tree_view.queue_draw()

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
            unsaved_changes=self.rule_model.unsaved_changes,
            save_callback=self.handle_save_yaml_file,
        )

    def handle_event_button_released(self, v, e):
        if e.button == Gdk.BUTTON_SECONDARY:  # right click
            self.action_menu.create_context_menu(v, e)

    def handle_close(self, window: Gtk.Window, _e: Gdk.Event):
        if self.rule_model.unsaved_changes:
            self.rule_view.show_close_dialog(window, self.handle_save_yaml_file)
        else:
            window.hide()

    def handle_reload_yaml_file(self):
        self.rule_view.set_save_discard_buttons_status(False)

        self.rule_model.unsaved_changes = False
        for c in self.selected_rule_edit_panel.get_children():
            self.selected_rule_edit_panel.remove(c)
        self._load_rules_func()
        self.model = self._create_model_func()
        self.tree_view.set_model(self.model)
        self.tree_view.expand_all()

    def handle_save_yaml_file(self):
        if self._save_rules_func():
            self.rule_model.unsaved_changes = False
            self.rule_view.set_save_discard_buttons_status(False)

    def handle_selection_changed(self, selection: Gtk.TreeSelection):
        self.selected_rule_edit_panel.set_sensitive(False)

        (model, it) = selection.get_selected()
        if it is None:
            return
        wrapped = model[it][0]
        component = wrapped.component
        self._editing_component = component
        self.ui[type(component)].show(component, wrapped.editable)
        self.selected_rule_edit_panel.set_sensitive(wrapped.editable)


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
    def __init__(self, window, tree_view, populate_model_func, on_update):
        self.window = window
        self.tree_view = tree_view
        self._populate_model_func = populate_model_func
        self._on_update = on_update
        self._clipboard = None

    def create_menu_event_key_pressed(self, v: Gtk.TreeView, e: Gdk.EventKey, unsaved_changes: bool, save_callback: Callable):
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
                self.handle_paster(
                    None, m, it, below=enabled_actions.c is not None and not (state & Gdk.ModifierType.SHIFT_MASK)
                )
            elif (
                enabled_actions.insert_only_rule
                and isinstance(self._clipboard, _DIV.Rule)
                and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]
            ):
                self.handle_paster(
                    None, m, it, below=enabled_actions.c is not None and not (state & Gdk.ModifierType.SHIFT_MASK)
                )
            elif enabled_actions.insert_root and isinstance(self._clipboard, _DIV.Rule) and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self.handle_paster(None, m, m.iter_nth_child(it, 0))
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
            elif unsaved_changes and e.keyval in [Gdk.KEY_s, Gdk.KEY_S]:
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

    def create_context_menu(self, v, e):
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
        menu_paste.connect("activate", self.handle_paster, m, it, below)
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
        self._populate_model_func(m, parent_it, children, level=wrapped.level, pos=idx)
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
            self._populate_model_func(m, parent_it, None, level=wrapped.level)
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
            new_c.source = _DIV._file_path  # new rules will be saved to the YAML file
        idx += int(below)
        parent_c.components.insert(idx, new_c)
        self._populate_model_func(m, parent_it, new_c, level=wrapped.level, pos=idx)
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
            self._populate_model_func(m, parent_it, new_c, level=wrapped.level, pos=0)
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

    def handle_paster(self, _mitem, m: Gtk.TreeStore, it: Gtk.TreeIter, below=False):
        c = self._clipboard
        self._clipboard = None
        if c:
            self._clipboard = _DIV.RuleComponent().compile(c.data())
            self.handle_insert(_mitem, m, it, new_c=c, below=below)
            self._on_update()
