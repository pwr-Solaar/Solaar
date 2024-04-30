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

from solaar.i18n import _


class RulesView:
    def __init__(self):
        self.window = None
        self.save_btn = None
        self.discard_btn = None

    def init_ui(self):
        pass

    def create_main_window(self) -> Gtk.Window:
        window = Gtk.Window()
        window.set_title(_("Solaar Rule Editor"))
        geometry = Gdk.Geometry()
        geometry.min_width = 600  # don't ask for so much space
        geometry.min_height = 400
        window.set_geometry_hints(None, geometry, Gdk.WindowHints.MIN_SIZE)
        window.set_position(Gtk.WindowPosition.CENTER)
        return window

    def create_tree_view(
        self, callback_key_pressed: Callable, callback_event_button_released: Callable, callback_selection_changed: Callable
    ) -> Gtk.TreeView:
        view = Gtk.TreeView()
        view.set_headers_visible(False)
        view.set_enable_tree_lines(True)
        view.set_reorderable(False)

        view.connect("key-press-event", callback_key_pressed)
        view.connect("button-release-event", callback_event_button_released)
        view.get_selection().connect("changed", callback_selection_changed)
        return view

    def create_save_button(self, callback: Callable) -> Gtk.Button:
        save_btn = Gtk.Button.new_from_icon_name("document-save", Gtk.IconSize.BUTTON)
        save_btn.set_label(_("Save changes"))
        save_btn.set_always_show_image(True)
        save_btn.set_sensitive(False)
        save_btn.set_valign(Gtk.Align.CENTER)
        save_btn.connect("clicked", callback)
        return save_btn

    def create_discard_button(self, callback: Callable) -> Gtk.Button:
        discard_btn = Gtk.Button.new_from_icon_name("document-revert", Gtk.IconSize.BUTTON)
        discard_btn.set_label(_("Discard changes"))
        discard_btn.set_always_show_image(True)
        discard_btn.set_sensitive(False)
        discard_btn.set_valign(Gtk.Align.CENTER)
        discard_btn.connect("clicked", callback)
        return discard_btn

    def set_save_discard_buttons_status(self, enable: bool):
        """Enable or disable the save and discard buttons."""
        self.save_btn.set_sensitive(enable)
        self.discard_btn.set_sensitive(enable)

    def create_save_discard_button_box(self):
        pass

    def create_selected_rule_edit_panel(self) -> Gtk.Grid:
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

    def create_view_columns(self):
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

    def show_close_dialog(self, window: Gtk.Window, yes_callback: Callable) -> Gtk.MessageDialog:
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

        response = dialog.run()

        dialog.destroy()
        if response == Gtk.ResponseType.NO:
            window.hide()
        elif response == Gtk.ResponseType.YES:
            yes_callback()
            window.hide()
        else:
            # don't close
            return True
        return dialog
