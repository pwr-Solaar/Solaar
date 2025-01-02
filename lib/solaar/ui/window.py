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

from enum import Enum
from enum import IntEnum

import gi

from gi.repository.GObject import TYPE_PYOBJECT
from logitech_receiver import hidpp10_constants
from logitech_receiver.common import LOGITECH_VENDOR_ID
from logitech_receiver.common import NamedInt

from solaar import NAME
from solaar.i18n import _
from solaar.i18n import ngettext

from . import action
from . import config_panel
from . import diversion_rules
from . import icons
from .about import about
from .common import ui_async

gi.require_version("Gdk", "3.0")
from gi.repository import Gdk  # NOQA: E402
from gi.repository import GLib  # NOQA: E402
from gi.repository import Gtk  # NOQA: E402

logger = logging.getLogger(__name__)

_SMALL_BUTTON_ICON_SIZE = Gtk.IconSize.MENU
_NORMAL_BUTTON_ICON_SIZE = Gtk.IconSize.BUTTON
_TREE_ICON_SIZE = Gtk.IconSize.BUTTON
_INFO_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_DEVICE_ICON_SIZE = Gtk.IconSize.DND
try:
    gi.check_version("3.7.4")
    _CAN_SET_ROW_NONE = None
except (ValueError, AttributeError):
    _CAN_SET_ROW_NONE = ""


class Column(IntEnum):
    """Columns of tree model."""

    PATH = 0
    NUMBER = 1
    ACTIVE = 2
    NAME = 3
    ICON = 4
    STATUS_TEXT = 5
    STATUS_ICON = 6
    DEVICE = 7


_COLUMN_TYPES = (str, int, bool, str, str, str, str, TYPE_PYOBJECT)
_TREE_SEPATATOR = (None, 0, False, None, None, None, None, None)
assert len(_TREE_SEPATATOR) == len(_COLUMN_TYPES)
assert len(_COLUMN_TYPES) == len(Column)


class GtkSignal(Enum):
    CHANGED = "changed"
    CLICKED = "clicked"
    DELETE_EVENT = "delete-event"


def _new_button(label, icon_name=None, icon_size=_NORMAL_BUTTON_ICON_SIZE, tooltip=None, toggle=False, clicked=None):
    b = Gtk.ToggleButton() if toggle else Gtk.Button()
    c = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 5)
    if icon_name:
        c.pack_start(Gtk.Image.new_from_icon_name(icon_name, icon_size), True, True, 0)
    if label:
        c.pack_start(Gtk.Label(label=label), True, True, 0)
    b.add(c)
    if clicked is not None:
        b.connect(GtkSignal.CLICKED.value, clicked)
    if tooltip:
        b.set_tooltip_text(tooltip)
    if not label and icon_size < _NORMAL_BUTTON_ICON_SIZE:
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_focus_on_click(False)
    return b


def _create_receiver_panel():
    p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

    p._count = Gtk.Label()
    p._count.set_margin_top(24)
    p.pack_start(p._count, True, True, 0)

    p._scanning = Gtk.Label(label=_("Scanning") + "...")
    p._spinner = Gtk.Spinner()

    bp = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
    bp.pack_start(Gtk.Label(label=" "), True, True, 0)
    bp.pack_start(p._scanning, False, False, 0)
    bp.pack_end(p._spinner, False, False, 0)
    p.pack_end(bp, False, False, 0)

    return p


def _create_device_panel():
    p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

    def _status_line(label_text):
        b = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
        b.set_size_request(10, 28)

        b._label = Gtk.Label(label=label_text)
        b._label.set_size_request(170, 10)
        b.pack_start(b._label, False, False, 0)

        b._icon = Gtk.Image()
        b.pack_start(b._icon, False, False, 0)

        b._text = Gtk.Label()
        b.pack_start(b._text, False, False, 0)

        return b

    p._battery = _status_line(_("Battery"))
    p.pack_start(p._battery, False, False, 0)

    p._secure = _status_line(_("Wireless Link"))
    p._secure._icon.set_from_icon_name("dialog-warning", _INFO_ICON_SIZE)
    p.pack_start(p._secure, False, False, 0)

    p._lux = _status_line(_("Lighting"))
    p.pack_start(p._lux, False, False, 0)

    p.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 0)  # spacer

    p._config = config_panel.create()
    p.pack_end(p._config, True, True, 4)

    return p


def _create_details_panel():
    p = Gtk.Frame()
    p.set_shadow_type(Gtk.ShadowType.NONE)
    p.set_size_request(240, 0)
    p.set_state_flags(Gtk.StateFlags.ACTIVE, True)

    p._text = Gtk.Label()
    p._text.set_margin_start(6)
    p._text.set_margin_end(4)
    p._text.set_selectable(True)
    p.add(p._text)

    return p


def _create_buttons_box():
    bb = Gtk.HButtonBox()
    bb.set_layout(Gtk.ButtonBoxStyle.END)

    bb._details = _new_button(
        None,
        "dialog-information",
        _SMALL_BUTTON_ICON_SIZE,
        tooltip=_("Show Technical Details"),
        toggle=True,
        clicked=_update_details,
    )
    bb.add(bb._details)
    bb.set_child_secondary(bb._details, True)
    bb.set_child_non_homogeneous(bb._details, True)

    def _pair_new_device(trigger):
        assert _find_selected_device_id() is not None
        receiver = _find_selected_device()
        assert receiver is not None
        assert bool(receiver)
        assert receiver.kind is None
        action.pair(_window, receiver)

    bb._pair = _new_button(_("Pair new device"), "list-add", clicked=_pair_new_device)
    bb.add(bb._pair)

    def _unpair_current_device(trigger):
        assert _find_selected_device_id() is not None
        device = _find_selected_device()
        assert device is not None
        assert device.kind is not None
        action.unpair(_window, device)

    bb._unpair = _new_button(_("Unpair"), "edit-delete", clicked=_unpair_current_device)
    bb.add(bb._unpair)

    return bb


def _create_empty_panel():
    p = Gtk.Label()
    p.set_markup("<small>" + _("Select a device") + "</small>")
    p.set_sensitive(False)

    return p


def _create_info_panel():
    p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

    p._title = Gtk.Label(label=" ")
    p._icon = Gtk.Image()

    b1 = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
    b1.pack_start(p._title, True, True, 0)
    b1.pack_start(p._icon, False, False, 0)
    p.pack_start(b1, False, False, 0)

    p.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 0)  # spacer

    p._receiver = _create_receiver_panel()
    p.pack_start(p._receiver, True, True, 0)

    p._device = _create_device_panel()
    p.pack_start(p._device, True, True, 0)

    p.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 0)  # spacer

    p._buttons = _create_buttons_box()
    p.pack_end(p._buttons, False, False, 0)

    return p


def _create_tree(model):
    tree = Gtk.TreeView()
    tree.set_size_request(330, 0)  # enough width for simple setups
    tree.set_headers_visible(False)
    tree.set_show_expanders(False)
    tree.set_level_indentation(20)
    tree.set_enable_tree_lines(True)
    tree.set_reorderable(False)
    tree.set_enable_search(False)
    tree.set_model(model)

    def _is_separator(model, item, _ignore=None):
        return model.get_value(item, Column.PATH) is None

    tree.set_row_separator_func(_is_separator, None)

    icon_cell_renderer = Gtk.CellRendererPixbuf()
    icon_cell_renderer.set_property("stock-size", _TREE_ICON_SIZE)
    icon_column = Gtk.TreeViewColumn("Icon", icon_cell_renderer)
    icon_column.add_attribute(icon_cell_renderer, "sensitive", Column.ACTIVE)
    icon_column.add_attribute(icon_cell_renderer, "icon-name", Column.ICON)
    tree.append_column(icon_column)

    name_cell_renderer = Gtk.CellRendererText()
    name_column = Gtk.TreeViewColumn("device name", name_cell_renderer)
    name_column.add_attribute(name_cell_renderer, "sensitive", Column.ACTIVE)
    name_column.add_attribute(name_cell_renderer, "text", Column.NAME)
    name_column.set_expand(True)
    tree.append_column(name_column)
    tree.set_expander_column(name_column)

    status_cell_renderer = Gtk.CellRendererText()
    status_cell_renderer.set_property("scale", 0.85)
    status_cell_renderer.set_property("xalign", 1)
    status_column = Gtk.TreeViewColumn("status text", status_cell_renderer)
    status_column.add_attribute(status_cell_renderer, "sensitive", Column.ACTIVE)
    status_column.add_attribute(status_cell_renderer, "text", Column.STATUS_TEXT)
    status_column.set_expand(True)
    tree.append_column(status_column)

    battery_cell_renderer = Gtk.CellRendererPixbuf()
    battery_cell_renderer.set_property("stock-size", _TREE_ICON_SIZE)
    battery_column = Gtk.TreeViewColumn("status icon", battery_cell_renderer)
    battery_column.add_attribute(battery_cell_renderer, "sensitive", Column.ACTIVE)
    battery_column.add_attribute(battery_cell_renderer, "icon-name", Column.STATUS_ICON)
    tree.append_column(battery_column)

    return tree


def _create_window_layout():
    assert _tree is not None
    assert _details is not None
    assert _info is not None
    assert _empty is not None

    assert _tree.get_selection().get_mode() == Gtk.SelectionMode.SINGLE
    _tree.get_selection().connect(GtkSignal.CHANGED.value, _device_selected)

    tree_scroll = Gtk.ScrolledWindow()
    tree_scroll.add(_tree)
    tree_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    tree_scroll.set_shadow_type(Gtk.ShadowType.IN)

    tree_panel = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    tree_panel.set_homogeneous(False)
    tree_panel.pack_start(tree_scroll, True, True, 0)
    tree_panel.pack_start(_details, False, False, 0)

    panel = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 16)
    panel.pack_start(tree_panel, False, False, 0)
    panel.pack_start(_info, True, True, 0)
    panel.pack_start(_empty, True, True, 0)

    bottom_buttons_box = Gtk.HButtonBox()
    bottom_buttons_box.set_layout(Gtk.ButtonBoxStyle.START)
    bottom_buttons_box.set_spacing(20)
    quit_button = _new_button(_("Quit %s") % NAME, "application-exit", _SMALL_BUTTON_ICON_SIZE, clicked=destroy)
    bottom_buttons_box.add(quit_button)
    about_button = _new_button(_("About %s") % NAME, "help-about", _SMALL_BUTTON_ICON_SIZE, clicked=about.show)
    bottom_buttons_box.add(about_button)
    diversion_button = _new_button(
        _("Rule Editor"), "", _SMALL_BUTTON_ICON_SIZE, clicked=lambda *_trigger: diversion_rules.show_window(_model)
    )
    bottom_buttons_box.add(diversion_button)
    bottom_buttons_box.set_child_secondary(diversion_button, True)

    vbox = Gtk.Box.new(Gtk.Orientation.VERTICAL, 8)
    vbox.set_border_width(8)
    vbox.pack_start(panel, True, True, 0)
    vbox.pack_end(bottom_buttons_box, False, False, 0)
    vbox.show_all()

    _details.set_visible(False)
    _info.set_visible(False)
    return vbox


def _create(delete_action):
    window = Gtk.Window()
    window.set_title(NAME)
    window.set_role("status-window")
    window.connect(GtkSignal.DELETE_EVENT.value, delete_action)

    vbox = _create_window_layout()
    window.add(vbox)

    geometry = Gdk.Geometry()
    geometry.min_width = 600
    geometry.min_height = 320
    window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)
    window.set_position(Gtk.WindowPosition.CENTER)

    style = window.get_style_context()
    style.add_class("solaar")

    return window


def _find_selected_device():
    selection = _tree.get_selection()
    model, item = selection.get_selected()
    return model.get_value(item, Column.DEVICE) if item else None


def _find_selected_device_id():
    selection = _tree.get_selection()
    model, item = selection.get_selected()
    if item:
        return _model.get_value(item, Column.PATH), _model.get_value(item, Column.NUMBER)


# triggered by changing selection in the tree
def _device_selected(selection):
    model, item = selection.get_selected()
    device = model.get_value(item, Column.DEVICE) if item else None
    if device:
        _update_info_panel(device, full=True)
    else:
        # When removing a receiver, one of its children may get automatically selected
        # before the tree had time to remove them as well.
        # Rather than chase around for another device to select, just clear the selection.
        _tree.get_selection().unselect_all()
        _update_info_panel(None, full=True)


def _receiver_row(receiver_path, receiver=None):
    assert receiver_path
    r = _model.get_iter_first()
    while r:
        r = _model.iter_next(r)

    item = _model.get_iter_first()
    while item:
        # first row matching the path must be the receiver one
        if _model.get_value(item, Column.PATH) == receiver_path:
            return item
        item = _model.iter_next(item)

    if not item and receiver:
        icon_name = icons.device_icon_name(receiver.name)
        status_text = None
        status_icon = None
        row_data = (receiver_path, 0, True, receiver.name, icon_name, status_text, status_icon, receiver)
        assert len(row_data) == len(_TREE_SEPATATOR)
        logger.debug("new receiver row %s", row_data)
        item = _model.append(None, row_data)
        if _TREE_SEPATATOR:
            _model.append(None, _TREE_SEPATATOR)

    return item or None


def _device_row(receiver_path, device_number, device=None):
    assert receiver_path
    assert device_number is not None

    receiver_row = _receiver_row(receiver_path, None if device is None else device.receiver)

    if device_number == 0xFF or device_number == 0x0:  # direct-connected device, receiver row is device row
        if receiver_row:
            return receiver_row
        item = None
        new_child_index = 0
    else:
        item = _model.iter_children(receiver_row)
        new_child_index = 0
        while item:
            if _model.get_value(item, Column.PATH) != receiver_path:
                logger.warning(
                    "path for device row %s different from path for receiver %s",
                    _model.get_value(item, Column.PATH),
                    receiver_path,
                )
            item_number = _model.get_value(item, Column.NUMBER)
            if item_number == device_number:
                return item
            if item_number > device_number:
                item = None
                break
            new_child_index += 1
            item = _model.iter_next(item)

    if not item and device:
        icon_name = icons.device_icon_name(device.name, device.kind)
        status_text = None
        status_icon = None
        row_data = (
            receiver_path,
            device_number,
            bool(device.online),
            device.codename,
            icon_name,
            status_text,
            status_icon,
            device,
        )
        assert len(row_data) == len(_TREE_SEPATATOR)
        logger.debug("new device row %s at index %d", row_data, new_child_index)
        item = _model.insert(receiver_row, new_child_index, row_data)

    return item or None


def select(receiver_path, device_number=None):
    assert _window
    assert receiver_path is not None
    if device_number is None:
        item = _receiver_row(receiver_path)
    else:
        item = _device_row(receiver_path, device_number)
    if item:
        selection = _tree.get_selection()
        selection.select_iter(item)
    else:
        logger.warning("select(%s, %s) failed to find an item", receiver_path, device_number)


def _hide(w, _ignore=None):
    assert w == _window
    # some window managers move the window to 0,0 after hide()
    # so try to remember the last position
    position = _window.get_position()
    _window.hide()
    _window.move(*position)
    return True


def popup(trigger=None, receiver_path=None, device_id=None):
    if receiver_path:
        select(receiver_path, device_id)
    _window.present()
    return True


def toggle(trigger=None):
    if _window.get_visible():
        _hide(_window)
    else:
        _window.present()


def _update_details(button):
    assert button
    visible = button.get_active()

    if visible:
        # _details._text.set_markup('<small>reading...</small>')

        def _details_items(device, read_all=False):
            # If read_all is False, only return stuff that is ~100% already
            # cached, and involves no HID++ calls.

            yield _("Path"), device.path
            if device.kind is None:
                yield _("USB ID"), f"{LOGITECH_VENDOR_ID:04x}:" + device.product_id

                if read_all:
                    yield _("Serial"), device.serial
                else:
                    yield _("Serial"), "..."

            else:
                # yield ('Codename', device.codename)
                yield _("Index"), device.number
                if device.wpid:
                    yield _("Wireless PID"), device.wpid
                if device.product_id:
                    yield _("Product ID"), f"{LOGITECH_VENDOR_ID:04x}:" + device.product_id
                hid_version = device.protocol
                yield _("Protocol"), f"HID++ {hid_version:1.1f}" if hid_version else _("Unknown")
                if read_all and device.polling_rate:
                    yield _("Polling rate"), device.polling_rate

                if read_all or not device.online:
                    yield _("Serial"), device.serial
                else:
                    yield _("Serial"), "..."
                if read_all and device.unitId and device.unitId != device.serial:
                    yield _("Unit ID"), device.unitId

            if read_all:
                if device.firmware:
                    for fw in list(device.firmware):
                        yield "  " + _(str(fw.kind)), (fw.name + " " + fw.version).strip()
            elif device.kind is None or device.online:
                yield f"  {_('Firmware')}", "..."

            flag_bits = device.notification_flags
            if flag_bits is not None:
                flag_names = hidpp10_constants.flags_to_str(flag_bits, fallback=f"({_('none')})")
                yield _("Notifications"), flag_names

        def _set_details(text):
            _details._text.set_markup(text)

        def _make_text(items):
            text = "\n".join("%-13s: %s" % (name, value) for name, value in items)
            return "<small><tt>" + text + "</tt></small>"

        def _displayable_items(items):
            for name, value in items:
                value = GLib.markup_escape_text(str(value).replace("\x00", "")).strip()
                if value:
                    yield name, value

        def _read_slow(device):
            items = _details_items(selected_device, True)
            items = _displayable_items(items)
            text = _make_text(items)
            if device == _details._current_device:
                GLib.idle_add(_set_details, text)

        selected_device = _find_selected_device()
        assert selected_device
        _details._current_device = selected_device

        read_all = not (selected_device.kind is None or selected_device.online)
        items = _details_items(selected_device, read_all)
        _set_details(_make_text(items))

        if read_all:
            _details._current_device = None
        else:
            ui_async(_read_slow, selected_device)

    _details.set_visible(visible)


def _update_receiver_panel(receiver, panel, buttons, full=False):
    assert receiver

    devices_count = len(receiver)

    paired_text = (
        _(_("No device paired."))
        if devices_count == 0
        else ngettext("%(count)s paired device.", "%(count)s paired devices.", devices_count) % {"count": devices_count}
    )

    if receiver.max_devices > 0:
        paired_text += (
            "\n\n<small>%s</small>"
            % ngettext(
                "Up to %(max_count)s device can be paired to this receiver.",
                "Up to %(max_count)s devices can be paired to this receiver.",
                receiver.max_devices,
            )
            % {"max_count": receiver.max_devices}
        )
    elif devices_count > 0:
        paired_text += f"\n\n<small>{_('Only one device can be paired to this receiver.')}</small>"
    pairings = receiver.remaining_pairings()
    if pairings is not None and pairings >= 0:
        paired_text += "\n<small>%s</small>" % (
            ngettext("This receiver has %d pairing remaining.", "This receiver has %d pairings remaining.", pairings)
            % pairings
        )

    panel._count.set_markup(paired_text)

    is_pairing = receiver.pairing.lock_open
    if is_pairing:
        panel._scanning.set_visible(True)
        if not panel._spinner.get_visible():
            panel._spinner.start()
        panel._spinner.set_visible(True)
    else:
        panel._scanning.set_visible(False)
        if panel._spinner.get_visible():
            panel._spinner.stop()
        panel._spinner.set_visible(False)

    panel.set_visible(True)

    # b._insecure.set_visible(False)
    buttons._unpair.set_visible(False)

    if (
        not is_pairing
        and (receiver.remaining_pairings() is None or receiver.remaining_pairings() != 0)
        and (receiver.re_pairs or devices_count < receiver.max_devices)
    ):
        buttons._pair.set_sensitive(True)
    else:
        buttons._pair.set_sensitive(False)

    buttons._pair.set_visible(True)


def _update_device_panel(device, panel, buttons, full=False):
    assert device
    is_online = bool(device.online)
    panel.set_sensitive(is_online)

    if device.battery_info is None or device.battery_info.level is None:
        device.read_battery()

    battery_level = device.battery_info.level if device.battery_info is not None else None
    battery_voltage = device.battery_info.voltage if device.battery_info is not None else None
    if battery_level is None and battery_voltage is None:
        panel._battery.set_visible(False)
    else:
        panel._battery.set_visible(True)
        battery_next_level = device.battery_info.next_level
        charging = device.battery_info.charging() if device.battery_info is not None else None
        icon_name = icons.battery(battery_level, charging)
        panel._battery._icon.set_from_icon_name(icon_name, _INFO_ICON_SIZE)
        panel._battery._icon.set_sensitive(True)
        panel._battery._text.set_sensitive(is_online)

        if battery_voltage is not None:
            panel._battery._label.set_text(_("Battery Voltage"))
            text = f"{int(battery_voltage)}mV"
            tooltip_text = _("Voltage reported by battery")
        else:
            panel._battery._label.set_text(_("Battery Level"))
            text = ""
            tooltip_text = _("Approximate level reported by battery")
        if battery_voltage is not None and battery_level is not None:
            text += ", "
        if battery_level is not None:
            text += _(str(battery_level)) if isinstance(battery_level, NamedInt) else f"{int(battery_level)}%"
        if battery_next_level is not None and not charging:
            if isinstance(battery_next_level, NamedInt):
                text += "<small> (" + _("next reported ") + _(str(battery_next_level)) + ")</small>"
            else:
                text += "<small> (" + _("next reported ") + f"{int(battery_next_level)}%" + ")</small>"
            tooltip_text = tooltip_text + _(" and next level to be reported.")
        if is_online:
            if charging:
                text += f" <small>({_('charging')})</small>"
        else:
            text += f" <small>({_('last known')})</small>"

        panel._battery._text.set_markup(text)
        panel._battery.set_tooltip_text(tooltip_text)

    if device.link_encrypted is None:
        panel._secure.set_visible(False)
    elif is_online:
        panel._secure.set_visible(True)
        panel._secure._icon.set_visible(True)
        if device.link_encrypted is True:
            panel._secure._text.set_text(_("encrypted"))
            panel._secure._icon.set_from_icon_name("security-high", _INFO_ICON_SIZE)
            panel._secure.set_tooltip_text(_("The wireless link between this device and its receiver is encrypted."))
        else:
            panel._secure._text.set_text(_("not encrypted"))
            panel._secure._icon.set_from_icon_name("security-low", _INFO_ICON_SIZE)
            panel._secure.set_tooltip_text(
                _(
                    "The wireless link between this device and its receiver is not encrypted.\n"
                    "This is a security issue for pointing devices, and a major security issue for text-input devices."
                )
            )
    else:
        panel._secure.set_visible(True)
        panel._secure._icon.set_visible(False)
        panel._secure._text.set_markup(f"<small>{_('offline')}</small>")
        panel._secure.set_tooltip_text("")

    if is_online:
        light_level = device.battery_info.light_level if device.battery_info is not None else None
        if light_level is None:
            panel._lux.set_visible(False)
        else:
            panel._lux._icon.set_from_icon_name(icons.lux(light_level), _INFO_ICON_SIZE)
            panel._lux._text.set_text(_("%(light_level)d lux") % {"light_level": light_level})
            panel._lux.set_visible(True)
    else:
        panel._lux.set_visible(False)

    buttons._pair.set_visible(False)
    buttons._unpair.set_sensitive(device.receiver.may_unpair if device.receiver else False)
    buttons._unpair.set_visible(True)

    panel.set_visible(True)

    if full:
        config_panel.update(device, is_online)


def _update_info_panel(device, full=False):
    if device is None:
        # no selected device, show the 'empty' panel
        _details.set_visible(False)
        _info.set_visible(False)
        _empty.set_visible(True)
        return

    # a receiver must be valid
    # a device must be paired
    assert device

    _info._title.set_markup(f"<b>{device.name}</b>")
    icon_name = icons.device_icon_name(device.name, device.kind)
    _info._icon.set_from_icon_name(icon_name, _DEVICE_ICON_SIZE)

    if device.kind is None:
        _info._device.set_visible(False)
        _info._icon.set_sensitive(True)
        _info._title.set_sensitive(True)
        _update_receiver_panel(device, _info._receiver, _info._buttons, full)
    else:
        _info._receiver.set_visible(False)
        is_online = bool(device.online)
        _info._icon.set_sensitive(is_online)
        _info._title.set_sensitive(is_online)
        _update_device_panel(device, _info._device, _info._buttons, full)

    _empty.set_visible(False)
    _info.set_visible(True)

    if full:
        _update_details(_info._buttons._details)


# window layout:
#  +--------------------------------+
#  |  tree      | receiver  | empty |
#  |            | or device |       |
#  |------------| status    |       |
#  | details    |           |       |
#  |--------------------------------|
#  | (about)                        |
#  +--------------------------------|
# either the status or empty panel is visible at any point
# the details panel can be toggle on/off

_model = None
_tree = None
_details = None
_info = None
_empty = None
_window = None


def init(show_window, hide_on_close):
    Gtk.Window.set_default_icon_name(NAME.lower())

    global _model, _tree, _details, _info, _empty, _window
    _model = Gtk.TreeStore(*_COLUMN_TYPES)
    _tree = _create_tree(_model)
    _details = _create_details_panel()
    _info = _create_info_panel()
    _empty = _create_empty_panel()
    _window = _create(_hide if hide_on_close else destroy)
    if show_window:
        _window.present()


def destroy(_ignore1=None, _ignore2=None):
    global _model, _tree, _details, _info, _empty, _window
    w, _window = _window, None
    w.destroy()
    w = None
    config_panel.destroy()

    _empty = None
    _info = None
    _details = None
    _tree = None
    _model = None


def update(device, need_popup=False, refresh=False):
    if _window is None:
        return

    assert device is not None

    if need_popup:
        popup()

    selected_device_id = _find_selected_device_id()

    if device.kind is None:  # receiver
        # receiver
        is_alive = bool(device)
        item = _receiver_row(device.path, device if is_alive else None)

        if is_alive and item:
            was_pairing = bool(_model.get_value(item, Column.STATUS_ICON))
            is_pairing = (not device.isDevice) and bool(device.pairing.lock_open)
            _model.set_value(item, Column.STATUS_ICON, "network-wireless" if is_pairing else _CAN_SET_ROW_NONE)

            if selected_device_id == (device.path, 0):
                full_update = need_popup or was_pairing != is_pairing
                _update_info_panel(device, full=full_update)

        elif item:
            if _TREE_SEPATATOR:
                separator = _model.iter_next(item)
                if separator:
                    _model.remove(separator)
            _model.remove(item)

    else:
        path = device.receiver.path if device.receiver is not None else device.path
        assert device.number is not None and device.number >= 0, "invalid device number" + str(device.number)
        item = _device_row(path, device.number, device if bool(device) else None)

        if bool(device) and item:
            update_device(device, item, selected_device_id, need_popup, full=refresh)
        elif item:
            _model.remove(item)
            config_panel.clean(device)

    # make sure all rows are visible
    _tree.expand_all()


def update_device(device, item, selected_device_id, need_popup, full=False):
    was_online = _model.get_value(item, Column.ACTIVE)
    is_online = bool(device.online)
    _model.set_value(item, Column.ACTIVE, is_online)

    battery_level = device.battery_info.level if device.battery_info is not None else None
    battery_voltage = device.battery_info.voltage if device.battery_info is not None else None
    if battery_level is None:
        _model.set_value(item, Column.STATUS_TEXT, _CAN_SET_ROW_NONE)
        _model.set_value(item, Column.STATUS_ICON, _CAN_SET_ROW_NONE)
    else:
        if battery_voltage is not None and False:  # Use levels instead of voltage here
            status_text = f"{int(battery_voltage)}mV"
        elif isinstance(battery_level, NamedInt):
            status_text = _(str(battery_level))
        else:
            status_text = f"{int(battery_level)}%"
        _model.set_value(item, Column.STATUS_TEXT, status_text)

        charging = device.battery_info.charging() if device.battery_info is not None else None
        icon_name = icons.battery(battery_level, charging)
        _model.set_value(item, Column.STATUS_ICON, icon_name)

    _model.set_value(item, Column.NAME, device.codename)

    if selected_device_id is None or need_popup:
        select(device.receiver.path if device.receiver else device.path, device.number)
    elif selected_device_id == (device.receiver.path if device.receiver else device.path, device.number):
        full_update = full or was_online != is_online
        _update_info_panel(device, full=full_update)


def find_device(serial):
    assert serial, "need serial number or unit ID to find a device"
    result = None

    def check(_store, _treepath, row):
        nonlocal result
        device = _model.get_value(row, Column.DEVICE)
        if device and device.kind and (device.unitId == serial or device.serial == serial):
            result = device
            return True

    _model.foreach(check)
    return result
