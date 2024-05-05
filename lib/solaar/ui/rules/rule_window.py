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

from typing import Callable

from gi.repository import Gdk
from gi.repository import Gtk

from solaar.ui.rules.action_menu import ActionMenu
from solaar.ui.rules.handler import EventHandler


class DiversionDialog:
    """A presenter class for the Rule window.

    This class is responsible for handling events and updating the view.
    """

    def __init__(self, model, view, create_model_cb: Callable, populate_model_cb: Callable):
        self._model = model
        self._view = view

        self._create_model = create_model_cb

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

        self.action_menu = ActionMenu(self._view.tree_view, on_update_cb=self.on_update, populate_model_cb=populate_model_cb)

        self.handle_rule_update(self._model.rules)

    def handle_rule_update(self, rules):
        """Updates rule view given rules.

        Removes all existing rules and adds new ones.
        """
        self._view.clear_selected_rule_edit_panel()
        tree_model = self._create_model(rules)
        self._view.update_tree_view(tree_model)

    def on_update(self):
        self._view.tree_view.queue_draw()
        self._model.unsaved_changes = True
        self._view.set_save_discard_buttons_active(True)

    def update_devices(self):
        for rc in self._view.ui.values():
            rc.update_devices()
        self._view.tree_view.queue_draw()

    def handle_event_key_pressed(self, v: Gtk.TreeView, e: Gdk.EventKey):
        """Handles key press events in the tree view.

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
            self._view.window,
            v,
            e,
            save_callback=self.handle_save_yaml_file,
        )

    def handle_event_button_released(self, v: Gtk.TreeView, e: Gdk.EventKey):
        """Handles button release events in the tree view."""
        if e.button == Gdk.BUTTON_SECONDARY:  # right click
            self.action_menu.create_context_menu(v, e)

    def handle_close(self, window: Gtk.Window, _e: Gdk.Event):
        """Handles the close event of the window."""
        if self._model.unsaved_changes:
            self._view.show_close_with_unsaved_changes_dialog(window, self.handle_save_yaml_file)
        else:
            self._view.close()

    def handle_reload_yaml_file(self):
        if self._model.unsaved_changes:
            self._view.show_reload_with_unsaved_changes_dialog()
            return

        self._view.set_save_discard_buttons_active(False)

        loaded_rules = self._model.load_rules()
        self.handle_rule_update(loaded_rules)

    def handle_save_yaml_file(self):
        if self._model.unsaved_changes and self._model.save_rules():
            self._view.set_save_discard_buttons_active(False)

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
