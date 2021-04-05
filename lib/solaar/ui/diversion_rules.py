# -*- python-mode -*-
# -*- coding: UTF-8 -*-

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

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from contextlib import contextmanager as contextlib_contextmanager
from logging import getLogger
from shlex import quote as shlex_quote

from gi.repository import Gdk, GObject, Gtk
from logitech_receiver import diversion as _DIV
from logitech_receiver.diversion import XK_KEYS as _XK_KEYS
from logitech_receiver.diversion import buttons as _buttons
from logitech_receiver.hidpp20 import FEATURE as _ALL_FEATURES
from logitech_receiver.special_keys import CONTROL as _CONTROL
from solaar.i18n import _

_log = getLogger(__name__)
del getLogger

#
#
#

_diversion_dialog = None
_rule_component_clipboard = None


class RuleComponentWrapper(GObject.GObject):
    def __init__(self, component, level=0, editable=False):
        self.component = component
        self.level = level
        self.editable = editable
        GObject.GObject.__init__(self)

    def display_left(self):
        if isinstance(self.component, _DIV.Rule):
            if self.level == 0:
                return _('Built-in rules') if not self.editable else _('User-defined rules')
            if self.level == 1:
                return '  ' + _('Rule')
            return '  ' + _('Sub-rule')
        if self.component is None:
            return _('[empty]')
        return '  ' + self.__component_ui().left_label(self.component)

    def display_right(self):
        if self.component is None:
            return ''
        return self.__component_ui().right_label(self.component)

    def display_icon(self):
        if self.component is None:
            return ''
        if isinstance(self.component, _DIV.Rule) and self.level == 0:
            return 'emblem-system' if not self.editable else 'avatar-default'
        return self.__component_ui().icon_name()

    def __component_ui(self):
        return COMPONENT_UI.get(type(self.component), UnsupportedRuleComponentUI)


class DiversionDialog:
    def __init__(self):

        window = Gtk.Window()
        window.set_title(_('Solaar Rule Editor'))
        window.connect('delete-event', self._closing)
        vbox = Gtk.VBox()

        self.top_panel, self.view = self._create_top_panel()
        for col in self._create_view_columns():
            self.view.append_column(col)
        vbox.pack_start(self.top_panel, True, True, 0)

        self.dirty = False  # if dirty, there are pending changes to be saved

        self.type_ui = {}
        self.update_ui = {}
        self.bottom_panel = self._create_bottom_panel()
        self.ui = defaultdict(lambda: UnsupportedRuleComponentUI(self.bottom_panel))
        self.ui.update({  # one instance per type
            rc_class: rc_ui_class(self.bottom_panel, on_update=self.on_update)
            for rc_class, rc_ui_class in COMPONENT_UI.items()
        })
        bottom_box = Gtk.ScrolledWindow()
        bottom_box.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        bottom_box.add(self.bottom_panel)
        vbox.pack_start(bottom_box, True, True, 0)

        self.model = self._create_model()
        self.view.set_model(self.model)
        self.view.expand_all()

        window.add(vbox)

        geometry = Gdk.Geometry()
        geometry.min_width = 800
        geometry.min_height = 800
        window.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE)
        window.set_position(Gtk.WindowPosition.CENTER)

        window.show_all()

        window.connect('delete-event', lambda w, e: w.hide_on_delete() or True)

        style = window.get_style_context()
        style.add_class('solaar')
        self.window = window
        self._editing_component = None

    def _closing(self, w, e):
        if self.dirty:
            dialog = Gtk.MessageDialog(
                self.window,
                type=Gtk.MessageType.QUESTION,
                title=_('Make changes permanent?'),
                flags=Gtk.DialogFlags.MODAL,
            )
            dialog.set_default_size(400, 100)
            dialog.add_buttons(
                _('Yes'),
                Gtk.ResponseType.YES,
                _('No'),
                Gtk.ResponseType.NO,
                _('Cancel'),
                Gtk.ResponseType.CANCEL,
            )
            dialog.set_markup(_('If you choose No, changes will be lost when Solaar is closed.'))
            dialog.show_all()
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.NO:
                w.hide()
            elif response == Gtk.ResponseType.YES:
                self._save_yaml_file()
                w.hide()
            else:
                # don't close
                return True
        else:
            w.hide()

    def _reload_yaml_file(self):
        self.discard_btn.set_sensitive(False)
        self.save_btn.set_sensitive(False)
        self.dirty = False
        for c in self.bottom_panel.get_children():
            self.bottom_panel.remove(c)
        _DIV._load_config_rule_file()
        self.model = self._create_model()
        self.view.set_model(self.model)
        self.view.expand_all()

    def _save_yaml_file(self):
        if _DIV._save_config_rule_file():
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

        view.connect('key-press-event', self._event_key_pressed)
        view.connect('button-release-event', self._event_button_released)
        view.get_selection().connect('changed', self._selection_changed)
        sw.add(view)
        sw.set_size_request(0, 600)

        button_box = Gtk.HBox(spacing=20)
        self.save_btn = Gtk.Button.new_from_icon_name('document-save', Gtk.IconSize.BUTTON)
        self.save_btn.set_label('Save changes')
        self.save_btn.set_always_show_image(True)
        self.save_btn.set_sensitive(False)
        self.save_btn.set_valign(Gtk.Align.CENTER)
        self.discard_btn = Gtk.Button.new_from_icon_name('document-revert', Gtk.IconSize.BUTTON)
        self.discard_btn.set_label('Discard changes')
        self.discard_btn.set_always_show_image(True)
        self.discard_btn.set_sensitive(False)
        self.discard_btn.set_valign(Gtk.Align.CENTER)
        self.save_btn.connect('clicked', lambda *_args: self._save_yaml_file())
        self.discard_btn.connect('clicked', lambda *_args: self._reload_yaml_file())
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
        if len(_DIV.rules.components) == 1:
            # only built-in rules - add empty user rule list
            _DIV.rules.components.insert(0, _DIV.Rule([], source=_DIV._file_path))
        self._populate_model(model, None, _DIV.rules.components)
        return model

    def _create_view_columns(self):
        cell_icon = Gtk.CellRendererPixbuf()
        cell1 = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn('Type')
        col1.pack_start(cell_icon, False)
        col1.pack_start(cell1, True)
        col1.set_cell_data_func(cell1, lambda _c, c, m, it, _d: c.set_property('text', m.get_value(it, 0).display_left()))
        cell2 = Gtk.CellRendererText()
        col2 = Gtk.TreeViewColumn('Summary')
        col2.pack_start(cell2, True)
        col2.set_cell_data_func(cell2, lambda _c, c, m, it, _d: c.set_property('text', m.get_value(it, 0).display_right()))
        col2.set_cell_data_func(
            cell_icon, lambda _c, c, m, it, _d: c.set_property('icon-name',
                                                               m.get_value(it, 0).display_icon())
        )
        return col1, col2

    def _populate_model(self, model, it, rule_component, level=0, pos=-1, editable=None):
        if isinstance(rule_component, list):
            for c in rule_component:
                self._populate_model(model, it, c, level=level, pos=pos, editable=editable)
                if pos >= 0:
                    pos += 1
            return
        if editable is None:
            editable = model[it][0].editable if it is not None else False
            if isinstance(rule_component, _DIV.Rule):
                editable = editable or (rule_component.source is not None)
        wrapped = RuleComponentWrapper(rule_component, level, editable=editable)
        piter = model.insert(it, pos, (wrapped, ))
        if isinstance(rule_component, (_DIV.Rule, _DIV.And, _DIV.Or)):
            for c in rule_component.components:
                ed = editable or (isinstance(c, _DIV.Rule) and c.source is not None)
                self._populate_model(model, piter, c, level + 1, editable=ed)
            if len(rule_component.components) == 0:
                self._populate_model(model, piter, None, level + 1, editable=editable)
        elif isinstance(rule_component, _DIV.Not):
            self._populate_model(model, piter, rule_component.component, level + 1, editable=editable)

    def _create_bottom_panel(self):
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_size_request(0, 120)
        return grid

    def on_update(self):
        self.view.queue_draw()
        self.dirty = True
        self.save_btn.set_sensitive(True)
        self.discard_btn.set_sensitive(True)

    def _selection_changed(self, selection):
        self.bottom_panel.set_sensitive(False)
        (model, it) = selection.get_selected()
        if it is None:
            return
        wrapped = model[it][0]
        component = wrapped.component
        self._editing_component = component
        self.ui[type(component)].show(component)
        for c in self.bottom_panel.get_children():
            c.set_sensitive(wrapped.editable)
        self.bottom_panel.set_sensitive(wrapped.editable)

    def _event_key_pressed(self, v, e):
        '''
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
        '''
        state = e.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)
        m, it = v.get_selection().get_selected()
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component if wrapped.level > 0 else None
        can_wrap = wrapped.editable and wrapped.component is not None and wrapped.level >= 2
        can_delete = wrapped.editable and not isinstance(parent_c, _DIV.Not) and c is not None and wrapped.level >= 1
        can_insert = wrapped.editable and not isinstance(parent_c, _DIV.Not) and wrapped.level >= 2
        can_insert_only_rule = wrapped.editable and wrapped.level == 1
        can_flatten = wrapped.editable and not isinstance(parent_c, _DIV.Not) and isinstance(
            c, (_DIV.Rule, _DIV.And, _DIV.Or)
        ) and wrapped.level >= 2 and len(c.components)
        can_copy = wrapped.level >= 1
        can_insert_root = wrapped.editable and wrapped.level == 0
        if state & Gdk.ModifierType.CONTROL_MASK:
            if can_delete and e.keyval in [Gdk.KEY_x, Gdk.KEY_X]:
                self._menu_do_cut(None, m, it)
            elif can_copy and e.keyval in [Gdk.KEY_c, Gdk.KEY_C] and c is not None:
                self._menu_do_copy(None, m, it)
            elif can_insert and _rule_component_clipboard is not None and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self._menu_do_paste(None, m, it, below=c is not None and not (state & Gdk.ModifierType.SHIFT_MASK))
            elif can_insert_only_rule and isinstance(_rule_component_clipboard,
                                                     _DIV.Rule) and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self._menu_do_paste(None, m, it, below=c is not None and not (state & Gdk.ModifierType.SHIFT_MASK))
            elif can_insert_root and isinstance(_rule_component_clipboard, _DIV.Rule) and e.keyval in [Gdk.KEY_v, Gdk.KEY_V]:
                self._menu_do_paste(None, m, m.iter_nth_child(it, 0))
            elif can_delete and e.keyval in [Gdk.KEY_KP_Delete, Gdk.KEY_Delete]:
                self._menu_do_delete(None, m, it)
            elif (can_insert or can_insert_only_rule or can_insert_root) and e.keyval in [Gdk.KEY_i, Gdk.KEY_I]:
                menu = Gtk.Menu()
                for item in self.__get_insert_menus(m, it, c, can_insert, can_insert_only_rule, can_insert_root):
                    menu.append(item)
                menu.show_all()
                rect = self.view.get_cell_area(m.get_path(it), self.view.get_column(1))
                menu.popup_at_rect(self.window.get_window(), rect, Gdk.Gravity.WEST, Gdk.Gravity.CENTER, e)
            elif self.dirty and e.keyval in [Gdk.KEY_s, Gdk.KEY_S]:
                self._save_yaml_file()
        else:
            if can_wrap:
                if e.keyval == Gdk.KEY_exclam:
                    self._menu_do_negate(None, m, it)
                elif e.keyval == Gdk.KEY_ampersand:
                    self._menu_do_wrap(None, m, it, _DIV.And)
                elif e.keyval == Gdk.KEY_bar:
                    self._menu_do_wrap(None, m, it, _DIV.Or)
                elif e.keyval in [Gdk.KEY_r, Gdk.KEY_R] and (state & Gdk.ModifierType.SHIFT_MASK):
                    self._menu_do_wrap(None, m, it, _DIV.Rule)
            if can_flatten and e.keyval in [Gdk.KEY_asterisk, Gdk.KEY_KP_Multiply]:
                self._menu_do_flatten(None, m, it)

    def __get_insert_menus(self, m, it, c, can_insert, can_insert_only_rule, can_insert_root):
        items = []
        if can_insert:
            ins = self._menu_insert(m, it)
            items.append(ins)
            if c is None:  # just a placeholder
                ins.set_label(_('Insert here'))
            else:
                ins.set_label(_('Insert above'))
                ins2 = self._menu_insert(m, it, below=True)
                ins2.set_label(_('Insert below'))
                items.append(ins2)
        elif can_insert_only_rule:
            ins = self._menu_create_rule(m, it)
            items.append(ins)
            if c is None:
                ins.set_label(_('Insert new rule here'))
            else:
                ins.set_label(_('Insert new rule above'))
                ins2 = self._menu_create_rule(m, it, below=True)
                ins2.set_label(_('Insert new rule below'))
                items.append(ins2)
        elif can_insert_root:
            ins = self._menu_create_rule(m, m.iter_nth_child(it, 0))
            items.append(ins)
        return items

    def _event_button_released(self, v, e):
        if e.button == 3:  # right click
            m, it = v.get_selection().get_selected()
            wrapped = m[it][0]
            c = wrapped.component
            parent_it = m.iter_parent(it)
            parent_c = m[parent_it][0].component if wrapped.level > 0 else None
            menu = Gtk.Menu()
            can_wrap = wrapped.editable and wrapped.component is not None and wrapped.level >= 2
            can_delete = wrapped.editable and not isinstance(parent_c, _DIV.Not) and c is not None and wrapped.level >= 1
            can_insert = wrapped.editable and not isinstance(parent_c, _DIV.Not) and wrapped.level >= 2
            can_insert_only_rule = wrapped.editable and wrapped.level == 1
            can_flatten = wrapped.editable and not isinstance(parent_c, _DIV.Not) and isinstance(
                c, (_DIV.Rule, _DIV.And, _DIV.Or)
            ) and wrapped.level >= 2 and len(c.components)
            can_copy = wrapped.level >= 1
            can_insert_root = wrapped.editable and wrapped.level == 0
            for item in self.__get_insert_menus(m, it, c, can_insert, can_insert_only_rule, can_insert_root):
                menu.append(item)
            if can_flatten:
                menu.append(self._menu_flatten(m, it))
            if can_wrap:
                menu.append(self._menu_wrap(m, it))
                menu.append(self._menu_negate(m, it))
            if menu.get_children():
                menu.append(Gtk.SeparatorMenuItem(visible=True))
            if can_delete:
                menu.append(self._menu_cut(m, it))
            if can_copy and c is not None:
                menu.append(self._menu_copy(m, it))
            if can_insert and _rule_component_clipboard is not None:
                p = self._menu_paste(m, it)
                menu.append(p)
                if c is None:  # just a placeholder
                    p.set_label(_('Paste here'))
                else:
                    p.set_label(_('Paste above'))
                    p2 = self._menu_paste(m, it, below=True)
                    p2.set_label(_('Paste below'))
                    menu.append(p2)
            elif can_insert_only_rule and isinstance(_rule_component_clipboard, _DIV.Rule):
                p = self._menu_paste(m, it)
                menu.append(p)
                if c is None:
                    p.set_label(_('Paste rule here'))
                else:
                    p.set_label(_('Paste rule above'))
                    p2 = self._menu_paste(m, it, below=True)
                    p2.set_label(_('Paste rule below'))
                    menu.append(p2)
            elif can_insert_root and isinstance(_rule_component_clipboard, _DIV.Rule):
                p = self._menu_paste(m, m.iter_nth_child(it, 0))
                p.set_label(_('Paste rule'))
                menu.append(p)
            if menu.get_children() and can_delete:
                menu.append(Gtk.SeparatorMenuItem(visible=True))
            if can_delete:
                menu.append(self._menu_delete(m, it))
            if menu.get_children():
                menu.popup_at_pointer(e)

    def _menu_do_flatten(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        idx = parent_c.components.index(c)
        if isinstance(c, _DIV.Not):
            parent_c.components = [*parent_c.components[:idx], c.component, *parent_c.components[idx + 1:]]
            children = [next(m[it].iterchildren())[0].component]
        else:
            parent_c.components = [*parent_c.components[:idx], *c.components, *parent_c.components[idx + 1:]]
            children = [child[0].component for child in m[it].iterchildren()]
        m.remove(it)
        self._populate_model(m, parent_it, children, level=wrapped.level, pos=idx)
        new_iter = m.iter_nth_child(parent_it, idx)
        self.view.expand_row(m.get_path(parent_it), True)
        self.view.get_selection().select_iter(new_iter)
        self.on_update()

    def _menu_flatten(self, m, it):
        menu_flatten = Gtk.MenuItem(_('Flatten'))
        menu_flatten.connect('activate', self._menu_do_flatten, m, it)
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
        if isinstance(new_c, _DIV.Rule) and wrapped.level == 1:
            new_c.source = _DIV._file_path  # new rules will be saved to the YAML file
        idx += int(below)
        parent_c.components.insert(idx, new_c)
        self._populate_model(m, parent_it, new_c, level=wrapped.level, pos=idx)
        self.on_update()
        if len(parent_c.components) == 1:
            m.remove(it)  # remove placeholder in the end
        new_iter = m.iter_nth_child(parent_it, idx)
        self.view.get_selection().select_iter(new_iter)
        if isinstance(new_c, (_DIV.Rule, _DIV.And, _DIV.Or, _DIV.Not)):
            self.view.expand_row(m.get_path(new_iter), True)

    def _menu_do_insert_new(self, _mitem, m, it, cls, initial_value, below=False):
        new_c = cls(initial_value)
        return self._menu_do_insert(_mitem, m, it, new_c, below=below)

    def _menu_insert(self, m, it, below=False):
        elements = [
            _('Insert'),
            [
                (_('Sub-rule'), _DIV.Rule, []),
                (_('Or'), _DIV.Or, []),
                (_('And'), _DIV.And, []),
                [
                    _('Condition'),
                    [
                        (_('Feature'), _DIV.Feature, FeatureUI.FEATURES_WITH_DIVERSION[0]),
                        (_('Process'), _DIV.Process, ''),
                        (_('Report'), _DIV.Report, 0),
                        (_('Modifiers'), _DIV.Modifiers, []),
                        (_('Key'), _DIV.Key, ''),
                        (_('Test'), _DIV.Test, next(iter(_DIV.TESTS))),
                    ]
                ],
                [
                    _('Action'),
                    [
                        (_('Key press'), _DIV.KeyPress, 'space'),
                        (_('Mouse scroll'), _DIV.MouseScroll, [0, 0]),
                        (_('Mouse click'), _DIV.MouseClick, ['left', 1]),
                        (_('Execute'), _DIV.Execute, ['']),
                    ]
                ],
            ]
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
                item.connect('activate', self._menu_do_insert_new, m, it, feature, *args, below)
                return item
            else:
                return None

        menu_insert = build(elements)
        menu_insert.show_all()
        return menu_insert

    def _menu_create_rule(self, m, it, below=False):
        menu_create_rule = Gtk.MenuItem(_('Insert new rule'))
        menu_create_rule.connect('activate', self._menu_do_insert_new, m, it, _DIV.Rule, [], below)
        menu_create_rule.show()
        return menu_create_rule

    def _menu_do_delete(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        idx = parent_c.components.index(c)
        parent_c.components.pop(idx)
        if len(parent_c.components) == 0:  # placeholder
            self._populate_model(m, parent_it, None, level=wrapped.level)
        m.remove(it)
        self.view.get_selection().select_iter(m.iter_nth_child(parent_it, max(0, min(idx, len(parent_c.components) - 1))))
        self.on_update()
        return c

    def _menu_delete(self, m, it):
        menu_delete = Gtk.MenuItem(_('Delete'))
        menu_delete.connect('activate', self._menu_do_delete, m, it)
        menu_delete.show()
        return menu_delete

    def _menu_do_negate(self, _mitem, m, it):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if isinstance(c, _DIV.Not):  # avoid double negation
            self._menu_do_flatten(_mitem, m, it)
            self.view.expand_row(m.get_path(parent_it), True)
        elif isinstance(parent_c, _DIV.Not):  # avoid double negation
            self._menu_do_flatten(_mitem, m, parent_it)
        else:
            idx = parent_c.components.index(c)
            self._menu_do_insert_new(_mitem, m, it, _DIV.Not, c, below=True)
            self._menu_do_delete(_mitem, m, m.iter_nth_child(parent_it, idx))
        self.on_update()

    def _menu_negate(self, m, it):
        menu_negate = Gtk.MenuItem(_('Negate'))
        menu_negate.connect('activate', self._menu_do_negate, m, it)
        menu_negate.show()
        return menu_negate

    def _menu_do_wrap(self, _mitem, m, it, cls):
        wrapped = m[it][0]
        c = wrapped.component
        parent_it = m.iter_parent(it)
        parent_c = m[parent_it][0].component
        if isinstance(parent_c, _DIV.Not):
            new_c = cls([c])
            parent_c.component = new_c
            m.remove(it)
            self._populate_model(m, parent_it, new_c, level=wrapped.level, pos=0)
            self.view.expand_row(m.get_path(parent_it), True)
            self.view.get_selection().select_iter(m.iter_nth_child(parent_it, 0))
        else:
            idx = parent_c.components.index(c)
            self._menu_do_insert_new(_mitem, m, it, cls, [c], below=True)
            self._menu_do_delete(_mitem, m, m.iter_nth_child(parent_it, idx))
        self.on_update()

    def _menu_wrap(self, m, it):
        menu_wrap = Gtk.MenuItem(_('Wrap with'))
        submenu_wrap = Gtk.Menu()
        menu_sub_rule = Gtk.MenuItem(_('Sub-rule'))
        menu_and = Gtk.MenuItem(_('And'))
        menu_or = Gtk.MenuItem(_('Or'))
        menu_sub_rule.connect('activate', self._menu_do_wrap, m, it, _DIV.Rule)
        menu_and.connect('activate', self._menu_do_wrap, m, it, _DIV.And)
        menu_or.connect('activate', self._menu_do_wrap, m, it, _DIV.Or)
        submenu_wrap.append(menu_sub_rule)
        submenu_wrap.append(menu_and)
        submenu_wrap.append(menu_or)
        menu_wrap.set_submenu(submenu_wrap)
        menu_wrap.show_all()
        return menu_wrap

    def _menu_do_cut(self, _mitem, m, it):
        c = self._menu_do_delete(_mitem, m, it)
        self.on_update()
        global _rule_component_clipboard
        _rule_component_clipboard = c

    def _menu_cut(self, m, it):
        menu_cut = Gtk.MenuItem(_('Cut'))
        menu_cut.connect('activate', self._menu_do_cut, m, it)
        menu_cut.show()
        return menu_cut

    def _menu_do_paste(self, _mitem, m, it, below=False):
        global _rule_component_clipboard
        c = _rule_component_clipboard
        _rule_component_clipboard = None
        if c:
            _rule_component_clipboard = _DIV.RuleComponent().compile(c.data())
            self._menu_do_insert(_mitem, m, it, new_c=c, below=below)
            self.on_update()

    def _menu_paste(self, m, it, below=False):
        menu_paste = Gtk.MenuItem(_('Paste'))
        menu_paste.connect('activate', self._menu_do_paste, m, it, below)
        menu_paste.show()
        return menu_paste

    def _menu_do_copy(self, _mitem, m, it):
        global _rule_component_clipboard
        wrapped = m[it][0]
        c = wrapped.component
        _rule_component_clipboard = _DIV.RuleComponent().compile(c.data())

    def _menu_copy(self, m, it):
        menu_copy = Gtk.MenuItem(_('Copy'))
        menu_copy.connect('activate', self._menu_do_copy, m, it)
        menu_copy.show()
        return menu_copy


## Not currently used
#
# class HexEntry(Gtk.Entry, Gtk.Editable):
#
#     def do_insert_text(self, new_text, length, pos):
#         new_text = new_text.upper()
#         from string import hexdigits
#         if any(c for c in new_text if c not in hexdigits):
#             return pos
#         else:
#             self.get_buffer().insert_text(pos, new_text, length)
#             return pos + length


class CompletionEntry(Gtk.Entry):
    def __init__(self, values, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CompletionEntry.add_completion_to_entry(self, values)

    @classmethod
    def add_completion_to_entry(cls, entry, values):
        entry.liststore = Gtk.ListStore(str)
        for v in sorted(values, key=str.casefold):
            entry.liststore.append((v, ))
        entry.completion = Gtk.EntryCompletion()
        entry.completion.set_model(entry.liststore)
        norm = lambda s: s.replace('_', '').replace(' ', '').lower()
        entry.completion.set_match_func(lambda completion, key, it: norm(key) in norm(completion.get_model()[it][0]))
        entry.completion.set_text_column(0)
        entry.set_completion(entry.completion)


class RuleComponentUI:

    CLASS = _DIV.RuleComponent

    def __init__(self, panel, on_update=None):
        self.panel = panel
        self.widgets = {}  # widget -> coord. in grid
        self.component = None
        self._ignore_changes = False
        self._on_update_callback = (lambda: None) if on_update is None else on_update
        self.create_widgets()

    def create_widgets(self):
        pass

    def show(self, component):
        self._show_widgets()
        self.component = component

    def collect_value(self):
        return None

    @contextlib_contextmanager
    def ignore_changes(self):
        self._ignore_changes = True
        yield None
        self._ignore_changes = False

    def _on_update(self, *_args):
        if not self._ignore_changes and self.component is not None:
            value = self.collect_value()
            self.component.__init__(value)
            self._on_update_callback()
            return value
        return None

    def _show_widgets(self):
        self._remove_panel_items()
        for widget, coord in self.widgets.items():
            self.panel.attach(widget, *coord)
            widget.show()

    @classmethod
    def left_label(cls, component):
        return type(component).__name__

    @classmethod
    def right_label(cls, _component):
        return ''

    @classmethod
    def icon_name(cls):
        return ''

    def _remove_panel_items(self):
        for c in self.panel.get_children():
            self.panel.remove(c)


class UnsupportedRuleComponentUI(RuleComponentUI):

    CLASS = None

    def create_widgets(self):
        self.label = Gtk.Label(valign=Gtk.Align.CENTER, hexpand=True, vexpand=True)
        self.label.set_text(_('This editor does not support the selected rule component yet.'))
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
        return _('Rule')

    @classmethod
    def icon_name(cls):
        return 'format-justify-fill'


class ConditionUI(RuleComponentUI):

    CLASS = _DIV.Condition

    @classmethod
    def icon_name(cls):
        return 'dialog-question'


class AndUI(RuleComponentUI):

    CLASS = _DIV.And

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _('And')


class OrUI(RuleComponentUI):

    CLASS = _DIV.Or

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.components[:]  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _('Or')


class NotUI(RuleComponentUI):

    CLASS = _DIV.Not

    def create_widgets(self):
        self.widgets = {}

    def collect_value(self):
        return self.component.component  # not editable on the bottom panel

    @classmethod
    def left_label(cls, component):
        return _('Not')


class ProcessUI(ConditionUI):

    CLASS = _DIV.Process

    def create_widgets(self):
        self.widgets = {}
        self.field = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, vexpand=True)
        self.field.set_size_request(600, 0)
        self.field.connect('changed', self._on_update)
        self.widgets[self.field] = (0, 0, 1, 1)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            self.field.set_text(component.process)

    def collect_value(self):
        return self.field.get_text()

    @classmethod
    def left_label(cls, component):
        return _('Process')

    @classmethod
    def right_label(cls, component):
        return str(component.process)


class FeatureUI(ConditionUI):

    CLASS = _DIV.Feature
    FEATURES_WITH_DIVERSION = [
        'CROWN',
        'GESTURE 2',
        'REPROG CONTROLS V4',
        'THUMB WHEEL',
    ]

    def create_widgets(self):
        self.widgets = {}
        self.field = Gtk.ComboBoxText.new_with_entry()
        self.field.append('', '')
        for feature in self.FEATURES_WITH_DIVERSION:
            self.field.append(feature, feature)
        self.field.set_valign(Gtk.Align.CENTER)
        self.field.set_vexpand(True)
        self.field.set_size_request(600, 0)
        self.field.connect('changed', self._on_update)
        all_features = [str(f) for f in _ALL_FEATURES]
        CompletionEntry.add_completion_to_entry(self.field.get_child(), all_features)
        self.widgets[self.field] = (0, 0, 1, 1)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            f = str(component.feature) if component.feature else ''
            self.field.set_active_id(f)
            if f not in self.FEATURES_WITH_DIVERSION:
                self.field.get_child().set_text(f)

    def collect_value(self):
        return (self.field.get_active_text() or '').strip()

    def _on_update(self, *args):
        super()._on_update(*args)
        icon = 'dialog-warning' if not self.component.feature else ''
        self.field.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _('Feature')

    @classmethod
    def right_label(cls, component):
        return '%s (%04X)' % (str(component.feature), int(component.feature or 0))


class ReportUI(ConditionUI):

    CLASS = _DIV.Report
    MIN_VALUE = -1  # for invalid values
    MAX_VALUE = 15

    def create_widgets(self):
        self.widgets = {}
        self.field = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        self.field.set_halign(Gtk.Align.CENTER)
        self.field.set_valign(Gtk.Align.CENTER)
        self.field.set_hexpand(True)
        self.field.set_vexpand(True)
        self.field.connect('changed', self._on_update)
        self.widgets[self.field] = (0, 0, 1, 1)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            self.field.set_value(component.report)

    def collect_value(self):
        return int(self.field.get_value())

    @classmethod
    def left_label(cls, component):
        return _('Report')

    @classmethod
    def right_label(cls, component):
        return str(component.report)


class ModifiersUI(ConditionUI):

    CLASS = _DIV.Modifiers

    def create_widgets(self):
        self.widgets = {}
        self.labels = {}
        self.switches = {}
        for i, m in enumerate(_DIV.MODIFIERS):
            switch = Gtk.Switch(halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True, vexpand=True)
            label = Gtk.Label(m, halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True, vexpand=True)
            self.widgets[label] = (i, 0, 1, 1)
            self.widgets[switch] = (i, 1, 1, 1)
            self.labels[m] = label
            self.switches[m] = switch
            switch.connect('notify::active', self._on_update)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            for m in _DIV.MODIFIERS:
                self.switches[m].set_active(m in component.modifiers)

    def collect_value(self):
        return [m for m, s in self.switches.items() if s.get_active()]

    @classmethod
    def left_label(cls, component):
        return _('Modifiers')

    @classmethod
    def right_label(cls, component):
        return '+'.join(component.modifiers) or 'None'


class KeyUI(ConditionUI):

    CLASS = _DIV.Key
    KEY_NAMES = map(str, _CONTROL)

    def create_widgets(self):
        self.widgets = {}
        self.field = CompletionEntry(
            self.KEY_NAMES, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True, vexpand=True
        )
        self.field.set_size_request(600, 0)
        self.field.connect('changed', self._on_update)
        self.widgets[self.field] = (0, 0, 1, 1)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            self.field.set_text(str(component.key) if self.component.key else '')

    def collect_value(self):
        return self.field.get_text()

    def _on_update(self, *args):
        super()._on_update(*args)
        icon = 'dialog-warning' if not self.component.key else ''
        self.field.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _('Key')

    @classmethod
    def right_label(cls, component):
        return '%s (%04X)' % (str(component.key), int(component.key)) if component.key else 'None'


class TestUI(ConditionUI):

    CLASS = _DIV.Test

    def create_widgets(self):
        self.widgets = {}
        self.field = Gtk.ComboBoxText.new_with_entry()
        self.field.append('', '')
        for t in _DIV.TESTS:
            self.field.append(t, t)
        self.field.set_valign(Gtk.Align.CENTER)
        self.field.set_vexpand(True)
        self.field.set_size_request(600, 0)
        CompletionEntry.add_completion_to_entry(self.field.get_child(), _DIV.TESTS)
        self.field.connect('changed', self._on_update)
        self.widgets[self.field] = (0, 0, 1, 1)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            self.field.set_active_id(component.test or '')
            if component.test not in _DIV.TESTS:
                self.field.get_child().set_text(component.test)
                self._change_status_icon()

    def collect_value(self):
        return (self.field.get_active_text() or '').strip()

    def _on_update(self, *args):
        super()._on_update(*args)
        self._change_status_icon()

    def _change_status_icon(self):
        icon = 'dialog-warning' if self.component.test not in _DIV.TESTS else ''
        self.field.get_child().set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    @classmethod
    def left_label(cls, component):
        return _('Test')

    @classmethod
    def right_label(cls, component):
        return str(component.test)


class ActionUI(RuleComponentUI):

    CLASS = _DIV.Action

    @classmethod
    def icon_name(cls):
        return 'go-next'


class KeyPressUI(ActionUI):

    CLASS = _DIV.KeyPress
    KEY_NAMES = [k[3:] if k.startswith('XK_') else k for k, v in _XK_KEYS.items() if isinstance(v, int)]

    def create_widgets(self):
        self.widgets = {}
        self.fields = []
        self.del_btns = []
        self.add_btn = Gtk.Button(_('Add key'), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        self.add_btn.connect('clicked', self._clicked_add)
        self.widgets[self.add_btn] = (1, 0, 1, 1)

    def _create_field(self):
        field = CompletionEntry(self.KEY_NAMES, halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        field.connect('changed', self._on_update)
        self.fields.append(field)
        self.widgets[field] = (len(self.fields) - 1, 0, 1, 1)
        return field

    def _create_del_btn(self):
        btn = Gtk.Button(_('Delete'), halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True, vexpand=True)
        self.del_btns.append(btn)
        self.widgets[btn] = (len(self.del_btns) - 1, 1, 1, 1)
        btn.connect('clicked', self._clicked_del, len(self.del_btns) - 1)
        return btn

    def _clicked_add(self, _btn):
        self.component.__init__(self.collect_value() + [''])
        self.show(self.component)
        self.fields[len(self.component.key_symbols) - 1].grab_focus()

    def _clicked_del(self, _btn, pos):
        v = self.collect_value()
        v.pop(pos)
        self.component.__init__(v)
        self.show(self.component)
        self._on_update_callback()

    def _on_update(self, *args):
        super()._on_update(*args)
        for i, f in enumerate(self.fields):
            if f.get_visible():
                icon = 'dialog-warning' if i < len(self.component.key_symbols
                                                   ) and self.component.key_symbols[i] not in self.KEY_NAMES else ''
                f.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, icon)

    def show(self, component):
        n = len(component.key_symbols)
        while len(self.fields) < n:
            self._create_field()
            self._create_del_btn()
        self.widgets[self.add_btn] = (n + 1, 0, 1, 1)
        super().show(component)
        for i in range(n):
            field = self.fields[i]
            with self.ignore_changes():
                field.set_text(component.key_symbols[i])
            field.set_size_request(int(0.3 * self.panel.get_toplevel().get_size()[0]), 0)
            field.show_all()
            self.del_btns[i].show()
        for i in range(n, len(self.fields)):
            self.fields[i].hide()
            self.del_btns[i].hide()
        self.add_btn.set_valign(Gtk.Align.END if n >= 1 else Gtk.Align.CENTER)

    def collect_value(self):
        return [f.get_text().strip() for f in self.fields if f.get_visible()]

    @classmethod
    def left_label(cls, component):
        return _('Key press')

    @classmethod
    def right_label(cls, component):
        return ' + '.join(component.key_symbols)


class MouseScrollUI(ActionUI):

    CLASS = _DIV.MouseScroll
    MIN_VALUE = -2000
    MAX_VALUE = 2000

    def create_widgets(self):
        self.widgets = {}
        self.label_x = Gtk.Label(label='x', halign=Gtk.Align.START, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        self.label_y = Gtk.Label(label='y', halign=Gtk.Align.START, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        self.field_x = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        self.field_y = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        for field in [self.field_x, self.field_y]:
            field.set_halign(Gtk.Align.CENTER)
            field.set_valign(Gtk.Align.START)
            field.set_vexpand(True)
        self.field_x.connect('changed', self._on_update)
        self.field_y.connect('changed', self._on_update)
        self.widgets[self.label_x] = (0, 0, 1, 1)
        self.widgets[self.label_y] = (1, 0, 1, 1)
        self.widgets[self.field_x] = (0, 1, 1, 1)
        self.widgets[self.field_y] = (1, 1, 1, 1)

    @classmethod
    def __parse(cls, v):
        try:
            # allow floats, but round them down
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            self.field_x.set_value(self.__parse(component.amounts[0] if len(component.amounts) >= 1 else 0))
            self.field_y.set_value(self.__parse(component.amounts[1] if len(component.amounts) >= 2 else 0))

    def collect_value(self):
        return [int(self.field_x.get_value()), int(self.field_y.get_value())]

    @classmethod
    def left_label(cls, component):
        return _('Mouse scroll')

    @classmethod
    def right_label(cls, component):
        x = y = 0
        x = cls.__parse(component.amounts[0] if len(component.amounts) >= 1 else 0)
        y = cls.__parse(component.amounts[1] if len(component.amounts) >= 2 else 0)
        return f'{x}, {y}'


class MouseClickUI(ActionUI):

    CLASS = _DIV.MouseClick
    MIN_VALUE = 1
    MAX_VALUE = 9
    BUTTONS = list(_buttons.keys())

    def create_widgets(self):
        self.widgets = {}
        self.label_b = Gtk.Label(label=_('Button'), halign=Gtk.Align.START, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        self.label_c = Gtk.Label(label=_('Count'), halign=Gtk.Align.START, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        self.field_b = CompletionEntry(self.BUTTONS)
        self.field_c = Gtk.SpinButton.new_with_range(self.MIN_VALUE, self.MAX_VALUE, 1)
        for field in [self.field_b, self.field_c]:
            field.set_halign(Gtk.Align.CENTER)
            field.set_valign(Gtk.Align.START)
            field.set_vexpand(True)
        self.field_b.connect('changed', self._on_update)
        self.field_c.connect('changed', self._on_update)
        self.widgets[self.label_b] = (0, 0, 1, 1)
        self.widgets[self.label_c] = (1, 0, 1, 1)
        self.widgets[self.field_b] = (0, 1, 1, 1)
        self.widgets[self.field_c] = (1, 1, 1, 1)

    def show(self, component):
        super().show(component)
        with self.ignore_changes():
            self.field_b.set_text(component.button)
            self.field_c.set_value(component.count)

    def collect_value(self):
        b, c = self.field_b.get_text(), int(self.field_c.get_value())
        if b not in self.BUTTONS:
            b = 'unknown'
        return [b, c]

    @classmethod
    def left_label(cls, component):
        return _('Mouse click')

    @classmethod
    def right_label(cls, component):
        return f'{component.button} (x{component.count})'


class ExecuteUI(ActionUI):

    CLASS = _DIV.Execute

    def create_widgets(self):
        self.widgets = {}
        self.fields = []
        self.add_btn = Gtk.Button(_('Add argument'), halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        self.del_btns = []
        self.add_btn.connect('clicked', self._clicked_add)
        self.widgets[self.add_btn] = (1, 0, 1, 1)

    def _create_field(self):
        field = Gtk.Entry(halign=Gtk.Align.CENTER, valign=Gtk.Align.END, hexpand=True, vexpand=True)
        field.set_size_request(150, 0)
        field.connect('changed', self._on_update)
        self.fields.append(field)
        self.widgets[field] = (len(self.fields) - 1, 0, 1, 1)
        return field

    def _create_del_btn(self):
        btn = Gtk.Button(_('Delete'), halign=Gtk.Align.CENTER, valign=Gtk.Align.START, hexpand=True, vexpand=True)
        btn.set_size_request(150, 0)
        self.del_btns.append(btn)
        self.widgets[btn] = (len(self.del_btns) - 1, 1, 1, 1)
        btn.connect('clicked', self._clicked_del, len(self.del_btns) - 1)
        return btn

    def _clicked_add(self, *_args):
        self.component.__init__(self.collect_value() + [''])
        self.show(self.component)
        self.fields[len(self.component.args) - 1].grab_focus()

    def _clicked_del(self, _btn, pos):
        v = self.collect_value()
        v.pop(pos)
        self.component.__init__(v)
        self.show(self.component)
        self._on_update_callback()

    def show(self, component):
        n = len(component.args)
        while len(self.fields) < n:
            self._create_field()
            self._create_del_btn()
        for i in range(n):
            field = self.fields[i]
            with self.ignore_changes():
                field.set_text(component.args[i])
            self.del_btns[i].show()
        self.widgets[self.add_btn] = (n + 1, 0, 1, 1)
        super().show(component)
        for i in range(n, len(self.fields)):
            self.fields[i].hide()
            self.del_btns[i].hide()
        self.add_btn.set_valign(Gtk.Align.END if n >= 1 else Gtk.Align.CENTER)

    def collect_value(self):
        return [f.get_text() for f in self.fields if f.get_visible()]

    @classmethod
    def left_label(cls, component):
        return _('Execute')

    @classmethod
    def right_label(cls, component):
        return ' '.join([shlex_quote(a) for a in component.args])


COMPONENT_UI = {
    _DIV.Rule: RuleUI,
    _DIV.Not: NotUI,
    _DIV.Or: OrUI,
    _DIV.And: AndUI,
    _DIV.Process: ProcessUI,
    _DIV.Feature: FeatureUI,
    _DIV.Report: ReportUI,
    _DIV.Modifiers: ModifiersUI,
    _DIV.Key: KeyUI,
    _DIV.Test: TestUI,
    _DIV.KeyPress: KeyPressUI,
    _DIV.MouseScroll: MouseScrollUI,
    _DIV.MouseClick: MouseClickUI,
    _DIV.Execute: ExecuteUI,
    type(None): RuleComponentUI,  # placeholders for empty rule/And/Or
}


def show_window(trigger=None):
    GObject.type_register(RuleComponentWrapper)
    global _diversion_dialog
    if _diversion_dialog is None:
        _diversion_dialog = DiversionDialog()
    _diversion_dialog.window.present()
