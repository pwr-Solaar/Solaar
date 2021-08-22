# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
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

from logging import DEBUG as _DEBUG
from logging import getLogger

from gi.repository import Gdk, GLib, Gtk
from gi.repository.GObject import TYPE_PYOBJECT
from logitech_receiver import hidpp10 as _hidpp10
from logitech_receiver.common import NamedInt as _NamedInt
from logitech_receiver.common import NamedInts as _NamedInts
from logitech_receiver.status import KEYS as _K
from solaar import NAME
from solaar.i18n import _, ngettext
# from solaar import __version__ as VERSION
from solaar.ui import ui_async as _ui_async

from . import action as _action
from . import config_panel as _config_panel
from . import icons as _icons
from .about import show_window as _show_about_window
from .diversion_rules import show_window as _show_diversion_window

_log = getLogger(__name__)
del getLogger

#
# constants
#

_SMALL_BUTTON_ICON_SIZE = Gtk.IconSize.MENU
_NORMAL_BUTTON_ICON_SIZE = Gtk.IconSize.BUTTON
_TREE_ICON_SIZE = Gtk.IconSize.BUTTON
_INFO_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_DEVICE_ICON_SIZE = Gtk.IconSize.DND
try:
    import gi
    gi.check_version('3.7.4')
    _CAN_SET_ROW_NONE = None
except (ValueError, AttributeError):
    _CAN_SET_ROW_NONE = ''

# tree model columns
_COLUMN = _NamedInts(PATH=0, NUMBER=1, ACTIVE=2, NAME=3, ICON=4, STATUS_TEXT=5, STATUS_ICON=6, DEVICE=7)
_COLUMN_TYPES = (str, int, bool, str, str, str, str, TYPE_PYOBJECT)
_TREE_SEPATATOR = (None, 0, False, None, None, None, None, None)
assert len(_TREE_SEPATATOR) == len(_COLUMN_TYPES)
assert len(_COLUMN_TYPES) == len(_COLUMN)

#
# create UI layout
#


def _new_button(label, icon_name=None, icon_size=_NORMAL_BUTTON_ICON_SIZE, tooltip=None, toggle=False, clicked=None):
    if toggle:
        b = Gtk.ToggleButton()
    else:
        b = Gtk.Button(label) if label else Gtk.Button()

    if icon_name:
        image = Gtk.Image.new_from_icon_name(icon_name, icon_size)
        b.set_image(image)

    if tooltip:
        b.set_tooltip_text(tooltip)

    if not label and icon_size < _NORMAL_BUTTON_ICON_SIZE:
        b.set_relief(Gtk.ReliefStyle.NONE)
        b.set_focus_on_click(False)

    if clicked is not None:
        b.connect('clicked', clicked)

    return b


def _create_receiver_panel():
    p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

    p._count = Gtk.Label()
    p._count.set_padding(24, 0)
    p._count.set_alignment(0, 0.5)
    p.pack_start(p._count, True, True, 0)

    p._scanning = Gtk.Label(_('Scanning') + '...')
    p._spinner = Gtk.Spinner()

    bp = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
    bp.pack_start(Gtk.Label(' '), True, True, 0)
    bp.pack_start(p._scanning, False, False, 0)
    bp.pack_end(p._spinner, False, False, 0)
    p.pack_end(bp, False, False, 0)

    return p


def _create_device_panel():
    p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

    def _status_line(label_text):
        b = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 8)
        b.set_size_request(10, 28)

        b._label = Gtk.Label(label_text)
        b._label.set_alignment(0, 0.5)
        b._label.set_size_request(170, 10)
        b.pack_start(b._label, False, False, 0)

        b._icon = Gtk.Image()
        b.pack_start(b._icon, False, False, 0)

        b._text = Gtk.Label()
        b._text.set_alignment(0, 0.5)
        b.pack_start(b._text, True, True, 0)

        return b

    p._battery = _status_line(_('Battery'))
    p.pack_start(p._battery, False, False, 0)

    p._secure = _status_line(_('Wireless Link'))
    p._secure._icon.set_from_icon_name('dialog-warning', _INFO_ICON_SIZE)
    p.pack_start(p._secure, False, False, 0)

    p._lux = _status_line(_('Lighting'))
    p.pack_start(p._lux, False, False, 0)

    p.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 0)  # spacer

    p._config = _config_panel.create()
    p.pack_end(p._config, True, True, 4)

    return p


def _create_details_panel():
    p = Gtk.Frame()
    p.set_shadow_type(Gtk.ShadowType.NONE)
    p.set_size_request(240, 0)
    p.set_state_flags(Gtk.StateFlags.ACTIVE, True)

    p._text = Gtk.Label()
    p._text.set_padding(6, 4)
    p._text.set_alignment(0, 0)
    p._text.set_selectable(True)
    p.add(p._text)

    return p


def _create_buttons_box():
    bb = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
    bb.set_layout(Gtk.ButtonBoxStyle.END)

    bb._details = _new_button(
        None,
        'dialog-information',
        _SMALL_BUTTON_ICON_SIZE,
        tooltip=_('Show Technical Details'),
        toggle=True,
        clicked=_update_details
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
        _action.pair(_window, receiver)

    bb._pair = _new_button(_('Pair new device'), 'list-add', clicked=_pair_new_device)
    bb.add(bb._pair)

    def _unpair_current_device(trigger):
        assert _find_selected_device_id() is not None
        device = _find_selected_device()
        assert device is not None
        assert bool(device)
        assert device.kind is not None
        _action.unpair(_window, device)

    bb._unpair = _new_button(_('Unpair'), 'edit-delete', clicked=_unpair_current_device)
    bb.add(bb._unpair)

    return bb


def _create_empty_panel():
    p = Gtk.Label()
    p.set_markup('<small>' + _('Select a device') + '</small>')
    p.set_sensitive(False)

    return p


def _create_info_panel():
    p = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)

    p._title = Gtk.Label(' ')
    p._title.set_alignment(0, 0.5)
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
    # tree.set_fixed_height_mode(True)
    tree.set_enable_tree_lines(True)
    tree.set_reorderable(False)
    tree.set_enable_search(False)
    tree.set_model(model)

    def _is_separator(model, item, _ignore=None):
        return model.get_value(item, _COLUMN.PATH) is None

    tree.set_row_separator_func(_is_separator, None)

    icon_cell_renderer = Gtk.CellRendererPixbuf()
    icon_cell_renderer.set_property('stock-size', _TREE_ICON_SIZE)
    icon_column = Gtk.TreeViewColumn('Icon', icon_cell_renderer)
    icon_column.add_attribute(icon_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
    icon_column.add_attribute(icon_cell_renderer, 'icon-name', _COLUMN.ICON)
    tree.append_column(icon_column)

    name_cell_renderer = Gtk.CellRendererText()
    name_column = Gtk.TreeViewColumn('device name', name_cell_renderer)
    name_column.add_attribute(name_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
    name_column.add_attribute(name_cell_renderer, 'text', _COLUMN.NAME)
    name_column.set_expand(True)
    tree.append_column(name_column)
    tree.set_expander_column(name_column)

    status_cell_renderer = Gtk.CellRendererText()
    status_cell_renderer.set_property('scale', 0.85)
    status_cell_renderer.set_property('xalign', 1)
    status_column = Gtk.TreeViewColumn('status text', status_cell_renderer)
    status_column.add_attribute(status_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
    status_column.add_attribute(status_cell_renderer, 'text', _COLUMN.STATUS_TEXT)
    status_column.set_expand(True)
    tree.append_column(status_column)

    battery_cell_renderer = Gtk.CellRendererPixbuf()
    battery_cell_renderer.set_property('stock-size', _TREE_ICON_SIZE)
    battery_column = Gtk.TreeViewColumn('status icon', battery_cell_renderer)
    battery_column.add_attribute(battery_cell_renderer, 'sensitive', _COLUMN.ACTIVE)
    battery_column.add_attribute(battery_cell_renderer, 'icon-name', _COLUMN.STATUS_ICON)
    tree.append_column(battery_column)

    return tree


def _create_window_layout():
    assert _tree is not None
    assert _details is not None
    assert _info is not None
    assert _empty is not None

    assert _tree.get_selection().get_mode() == Gtk.SelectionMode.SINGLE
    _tree.get_selection().connect('changed', _device_selected)

    tree_scroll = Gtk.ScrolledWindow()
    tree_scroll.add(_tree)
    tree_scroll.set_min_content_width(_tree.get_size_request()[0])
    tree_scroll.set_shadow_type(Gtk.ShadowType.IN)

    tree_panel = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    tree_panel.set_homogeneous(False)
    tree_panel.pack_start(tree_scroll, True, True, 0)
    tree_panel.pack_start(_details, False, False, 0)

    panel = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 16)
    panel.pack_start(tree_panel, True, True, 0)
    panel.pack_start(_info, True, True, 0)
    panel.pack_start(_empty, True, True, 0)

    bottom_buttons_box = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
    bottom_buttons_box.set_layout(Gtk.ButtonBoxStyle.START)
    bottom_buttons_box.set_spacing(20)
    quit_button = _new_button(_('Quit') + ' ' + NAME, 'application-exit', icon_size=_SMALL_BUTTON_ICON_SIZE, clicked=destroy)
    bottom_buttons_box.add(quit_button)
    about_button = _new_button(
        _('About') + ' ' + NAME, 'help-about', icon_size=_SMALL_BUTTON_ICON_SIZE, clicked=_show_about_window
    )
    bottom_buttons_box.add(about_button)
    diversion_button = _new_button(_('Rule Editor'), '', icon_size=_SMALL_BUTTON_ICON_SIZE, clicked=_show_diversion_window)
    bottom_buttons_box.add(diversion_button)
    bottom_buttons_box.set_child_secondary(diversion_button, True)

    # solaar_version = Gtk.Label()
    # solaar_version.set_markup('<small>' + NAME + ' v' + VERSION + '</small>')
    # bottom_buttons_box.add(solaar_version)
    # bottom_buttons_box.set_child_secondary(solaar_version, True)

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
    window.set_role('status-window')

    # window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    # window.set_skip_taskbar_hint(True)
    # window.set_skip_pager_hint(True)
    window.connect('delete-event', delete_action)

    vbox = _create_window_layout()
    window.add(vbox)

    geometry = Gdk.Geometry()
    geometry.min_width = 600
    geometry.min_height = 320
    window.set_geometry_hints(vbox, geometry, Gdk.WindowHints.MIN_SIZE)
    window.set_position(Gtk.WindowPosition.CENTER)

    style = window.get_style_context()
    style.add_class('solaar')

    return window


#
# window updates
#


def _find_selected_device():
    selection = _tree.get_selection()
    model, item = selection.get_selected()
    return model.get_value(item, _COLUMN.DEVICE) if item else None


def _find_selected_device_id():
    selection = _tree.get_selection()
    model, item = selection.get_selected()
    if item:
        return _model.get_value(item, _COLUMN.PATH), _model.get_value(item, _COLUMN.NUMBER)


# triggered by changing selection in the tree
def _device_selected(selection):
    model, item = selection.get_selected()
    device = model.get_value(item, _COLUMN.DEVICE) if item else None
    # if _log.isEnabledFor(_DEBUG):
    #     _log.debug("window tree selected device %s", device)
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
        if _model.get_value(item, _COLUMN.PATH) == receiver_path:
            return item
        item = _model.iter_next(item)

    if not item and receiver:
        icon_name = _icons.device_icon_name(receiver.name)
        status_text = None
        status_icon = None
        row_data = (receiver_path, 0, True, receiver.name, icon_name, status_text, status_icon, receiver)
        assert len(row_data) == len(_TREE_SEPATATOR)
        if _log.isEnabledFor(_DEBUG):
            _log.debug('new receiver row %s', row_data)
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
            if _model.get_value(item, _COLUMN.PATH) != receiver_path:
                _log.warn(
                    'path for device row %s different from path for receiver %s', _model.get_value(item, _COLUMN.PATH),
                    receiver_path
                )
            item_number = _model.get_value(item, _COLUMN.NUMBER)
            if item_number == device_number:
                return item
            if item_number > device_number:
                item = None
                break
            new_child_index += 1
            item = _model.iter_next(item)

    if not item and device:
        icon_name = _icons.device_icon_name(device.name, device.kind)
        status_text = None
        status_icon = None
        row_data = (
            receiver_path, device_number, bool(device.online), device.codename, icon_name, status_text, status_icon, device
        )
        assert len(row_data) == len(_TREE_SEPATATOR)
        if _log.isEnabledFor(_DEBUG):
            _log.debug('new device row %s at index %d', row_data, new_child_index)
        item = _model.insert(receiver_row, new_child_index, row_data)

    return item or None


#
#
#


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
        _log.warn('select(%s, %s) failed to find an item', receiver_path, device_number)


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


#
#
#


def _update_details(button):
    assert button
    visible = button.get_active()

    if visible:
        # _details._text.set_markup('<small>reading...</small>')

        def _details_items(device, read_all=False):
            # If read_all is False, only return stuff that is ~100% already
            # cached, and involves no HID++ calls.

            yield (_('Path'), device.path)
            if device.kind is None:
                # 046d is the Logitech vendor id
                yield (_('USB ID'), '046d:' + device.product_id)

                if read_all:
                    yield (_('Serial'), device.serial)
                else:
                    yield (_('Serial'), '...')

            else:
                # yield ('Codename', device.codename)
                yield (_('Index'), device.number)
                if device.wpid:
                    yield (_('Wireless PID'), device.wpid)
                if device.product_id:
                    yield (_('Product ID'), '046d:' + device.product_id)
                hid_version = device.protocol
                yield (_('Protocol'), 'HID++ %1.1f' % hid_version if hid_version else _('Unknown'))
                if read_all and device.polling_rate:
                    yield (
                        _('Polling rate'), _('%(rate)d ms (%(rate_hz)dHz)') % {
                            'rate': device.polling_rate,
                            'rate_hz': 1000 // device.polling_rate
                        }
                    )

                if read_all or not device.online:
                    yield (_('Serial'), device.serial)
                else:
                    yield (_('Serial'), '...')
                if read_all and device.unitId and device.unitId != device.serial:
                    yield (_('Unit ID'), device.unitId)

            if read_all:
                if device.firmware:
                    for fw in list(device.firmware):
                        yield ('  ' + _(str(fw.kind)), (fw.name + ' ' + fw.version).strip())
            elif device.kind is None or device.online:
                yield ('  %s' % _('Firmware'), '...')

            flag_bits = device.status.get(_K.NOTIFICATION_FLAGS)
            if flag_bits is not None:
                flag_names = ('(%s)' % _('none'), ) if flag_bits == 0 else _hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits)
                yield (_('Notifications'), ('\n%15s' % ' ').join(flag_names))

        def _set_details(text):
            _details._text.set_markup(text)

        def _make_text(items):
            text = '\n'.join('%-13s: %s' % i for i in items)
            return '<small><tt>' + text + '</tt></small>'

        def _read_slow(device):
            items = _details_items(selected_device, True)
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
            _ui_async(_read_slow, selected_device)

    _details.set_visible(visible)


def _update_receiver_panel(receiver, panel, buttons, full=False):
    assert receiver

    devices_count = len(receiver)

    paired_text = _(
        'No device paired.'
    ) if devices_count == 0 else ngettext('%(count)s paired device.', '%(count)s paired devices.', devices_count) % {
        'count': devices_count
    }

    if (receiver.max_devices > 0):
        paired_text += '\n\n<small>%s</small>' % ngettext(
            'Up to %(max_count)s device can be paired to this receiver.',
            'Up to %(max_count)s devices can be paired to this receiver.', receiver.max_devices
        ) % {
            'max_count': receiver.max_devices
        }
    elif devices_count > 0:
        paired_text += '\n\n<small>%s</small>' % _('Only one device can be paired to this receiver.')
    pairings = receiver.remaining_pairings(False)
    if (pairings is not None and pairings >= 0):
        paired_text += '\n<small>%s</small>' % (
            ngettext('This receiver has %d pairing remaining.', 'This receiver has %d pairings remaining.', pairings) %
            pairings
        )

    panel._count.set_markup(paired_text)

    is_pairing = receiver.status.lock_open
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

    if (receiver.may_unpair or receiver.re_pairs) and not is_pairing and \
       (receiver.remaining_pairings() is None or receiver.remaining_pairings() != 0):
        if not receiver.re_pairs and devices_count >= receiver.max_devices:
            paired_devices = tuple(n for n in range(1, receiver.max_devices + 1) if n in receiver)
            buttons._pair.set_sensitive(len(paired_devices) < receiver.max_devices)
        else:
            buttons._pair.set_sensitive(True)
    else:
        buttons._pair.set_sensitive(False)

    buttons._pair.set_visible(True)


def _update_device_panel(device, panel, buttons, full=False):
    assert device
    is_online = bool(device.online)
    panel.set_sensitive(is_online)

    if device.status.get(_K.BATTERY_LEVEL) is None:
        device.status.read_battery(device)

    battery_level = device.status.get(_K.BATTERY_LEVEL)
    battery_next_level = device.status.get(_K.BATTERY_NEXT_LEVEL)
    battery_voltage = device.status.get(_K.BATTERY_VOLTAGE)

    if battery_level is None:
        icon_name = _icons.battery()
        panel._battery._icon.set_from_icon_name(icon_name, _INFO_ICON_SIZE)
        panel._battery._icon.set_sensitive(False)
        panel._battery._text.set_sensitive(is_online)
        panel._battery._label.set_text(_('Battery'))
        panel._battery._text.set_markup('<small>%s</small>' % _('unknown'))
        panel._battery.set_tooltip_text(_('Battery information unknown.'))
    else:
        charging = device.status.get(_K.BATTERY_CHARGING)
        icon_name = _icons.battery(battery_level, charging)
        panel._battery._icon.set_from_icon_name(icon_name, _INFO_ICON_SIZE)
        panel._battery._icon.set_sensitive(True)

        if battery_voltage is not None:
            panel._battery._label.set_text(_('Battery Voltage'))
            text = '%(battery_voltage)dmV' % {'battery_voltage': battery_voltage}
            tooltip_text = _('Voltage reported by battery')
        elif isinstance(battery_level, _NamedInt):
            panel._battery._label.set_text(_('Battery Level'))
            text = _(str(battery_level))
            tooltip_text = _('Approximate level reported by battery')
        else:
            panel._battery._label.set_text(_('Battery Level'))
            text = '%(battery_percent)d%%' % {'battery_percent': battery_level}
            tooltip_text = _('Approximate level reported by battery')
        if battery_next_level is not None:
            if isinstance(battery_next_level, _NamedInt):
                text += '<small> (' + _('next reported ') + _(str(battery_next_level)) + ')</small>'
            else:
                text += '<small> (' + _('next reported ') + ('%d%%' % battery_next_level) + ')</small>'
            tooltip_text = tooltip_text + _(' and next level to be reported.')
        if is_online:
            if charging:
                text += ' <small>(%s)</small>' % _('charging')
        else:
            text += ' <small>(%s)</small>' % _('last known')
        panel._battery._text.set_sensitive(is_online)
        panel._battery._text.set_markup(text)
        panel._battery.set_tooltip_text(tooltip_text)

    if is_online:
        not_secure = device.status.get(_K.LINK_ENCRYPTED) is False
        if not_secure:
            panel._secure._text.set_text(_('not encrypted'))
            panel._secure._icon.set_from_icon_name('security-low', _INFO_ICON_SIZE)
            panel._secure.set_tooltip_text(
                _(
                    'The wireless link between this device and its receiver is not encrypted.\n'
                    '\n'
                    'For pointing devices (mice, trackballs, trackpads), this is a minor security issue.\n'
                    '\n'
                    'It is, however, a major security issue for text-input devices (keyboards, numpads),\n'
                    'because typed text can be sniffed inconspicuously by 3rd parties within range.'
                )
            )
        else:
            panel._secure._text.set_text(_('encrypted'))
            panel._secure._icon.set_from_icon_name('security-high', _INFO_ICON_SIZE)
            panel._secure.set_tooltip_text(_('The wireless link between this device and its receiver is encrypted.'))
        panel._secure._icon.set_visible(True)
    else:
        panel._secure._text.set_markup('<small>%s</small>' % _('offline'))
        panel._secure._icon.set_visible(False)
        panel._secure.set_tooltip_text('')

    if is_online:
        light_level = device.status.get(_K.LIGHT_LEVEL)
        if light_level is None:
            panel._lux.set_visible(False)
        else:
            panel._lux._icon.set_from_icon_name(_icons.lux(light_level), _INFO_ICON_SIZE)
            panel._lux._text.set_text(_('%(light_level)d lux') % {'light_level': light_level})
            panel._lux.set_visible(True)
    else:
        panel._lux.set_visible(False)

    buttons._pair.set_visible(False)
    buttons._unpair.set_sensitive(device.receiver.may_unpair if device.receiver else False)
    buttons._unpair.set_visible(True)

    panel.set_visible(True)

    if full:
        _config_panel.update(device, is_online)


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

    _info._title.set_markup('<b>%s</b>' % device.name)
    icon_name = _icons.device_icon_name(device.name, device.kind)
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


#
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
    Gtk.Window.set_default_icon_from_file(_icons.icon_file(NAME.lower()))

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
    _config_panel.destroy()

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
            was_pairing = bool(_model.get_value(item, _COLUMN.STATUS_ICON))
            is_pairing = (not device.isDevice) and bool(device.status.lock_open)
            _model.set_value(item, _COLUMN.STATUS_ICON, 'network-wireless' if is_pairing else _CAN_SET_ROW_NONE)

            if selected_device_id == (device.path, 0):
                full_update = need_popup or was_pairing != is_pairing
                _update_info_panel(device, full=full_update)

        elif item:
            if _TREE_SEPATATOR:
                separator = _model.iter_next(item)
                _model.remove(separator)
            _model.remove(item)

    else:
        path = device.receiver.path if device.receiver else device.path
        assert device.number is not None and device.number >= 0, 'invalid device number' + str(device.number)
        item = _device_row(path, device.number, device if bool(device) else None)

        if bool(device) and item:
            update_device(device, item, selected_device_id, need_popup, full=refresh)
        elif item:
            _model.remove(item)
            _config_panel.clean(device)

    # make sure all rows are visible
    _tree.expand_all()


def update_device(device, item, selected_device_id, need_popup, full=False):
    was_online = _model.get_value(item, _COLUMN.ACTIVE)
    is_online = bool(device.online)
    _model.set_value(item, _COLUMN.ACTIVE, is_online)

    battery_level = device.status.get(_K.BATTERY_LEVEL)
    battery_voltage = device.status.get(_K.BATTERY_VOLTAGE)
    if battery_level is None:
        _model.set_value(item, _COLUMN.STATUS_TEXT, _CAN_SET_ROW_NONE)
        _model.set_value(item, _COLUMN.STATUS_ICON, _CAN_SET_ROW_NONE)
    else:
        if battery_voltage is not None:
            status_text = '%(battery_voltage)dmV' % {'battery_voltage': battery_voltage}
        elif isinstance(battery_level, _NamedInt):
            status_text = _(str(battery_level))
        else:
            status_text = '%(battery_percent)d%%' % {'battery_percent': battery_level}
        _model.set_value(item, _COLUMN.STATUS_TEXT, status_text)

        charging = device.status.get(_K.BATTERY_CHARGING)
        icon_name = _icons.battery(battery_level, charging)
        _model.set_value(item, _COLUMN.STATUS_ICON, icon_name)

    if selected_device_id is None or need_popup:
        select(device.receiver.path if device.receiver else device.path, device.number)
    elif selected_device_id == (device.receiver.path if device.receiver else device.path, device.number):
        full_update = full or was_online != is_online
        _update_info_panel(device, full=full_update)
