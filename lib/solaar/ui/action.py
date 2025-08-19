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
from enum import Enum

from gi.repository import Gdk
from gi.repository import Gtk

from solaar.i18n import _
from solaar.ui import common

from . import pair_window


class GtkSignal(Enum):
    ACTIVATE = "activate"


def make_image_menu_item(label, icon_name, function, *args):
    box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
    label = Gtk.Label(label=label)
    icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR) if icon_name is not None else Gtk.Image()
    box.add(icon)
    box.add(label)
    menu_item = Gtk.MenuItem()
    menu_item.add(box)
    menu_item.show_all()
    menu_item.connect(GtkSignal.ACTIVATE.value, function, *args)
    menu_item.label = label
    menu_item.icon = icon
    return menu_item


def make(name, label, function, stock_id=None, *args):
    action = Gtk.Action(name=name, label=label, tooltip=label, stock_id=None)
    action.set_icon_name(name)
    if stock_id is not None:
        action.set_stock_id(stock_id)
    if function:
        action.connect(GtkSignal.ACTIVATE.value, function, *args)
    return action


def make_toggle(name, label, function, stock_id=None, *args):
    action = Gtk.ToggleAction(name=name, label=label, tooltip=label, stock_id=None)
    action.set_icon_name(name)
    if stock_id is not None:
        action.set_stock_id(stock_id)
    action.connect(GtkSignal.ACTIVATE.value, function, *args)
    return action


def pair(window, receiver):
    assert receiver
    assert receiver.kind is None

    pair_dialog = pair_window.create(receiver)
    pair_dialog.set_transient_for(window)
    pair_dialog.set_destroy_with_parent(True)
    pair_dialog.set_modal(True)
    pair_dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)
    pair_dialog.set_position(Gtk.WindowPosition.CENTER)
    pair_dialog.present()


def unpair(window, device):
    assert device
    assert device.kind is not None

    qdialog = Gtk.MessageDialog(
        transient_for=window,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.NONE,
        text=_("Unpair") + " " + device.name + " ?",
    )
    qdialog.set_icon_name("remove")
    qdialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
    qdialog.add_button(_("Unpair"), Gtk.ResponseType.ACCEPT)
    choice = qdialog.run()
    qdialog.destroy()
    if choice == Gtk.ResponseType.ACCEPT:
        receiver = device.receiver
        assert receiver
        device_number = device.number

        try:
            del receiver[device_number]
        except Exception:
            common.error_dialog(common.ErrorReason.UNPAIR, device)
