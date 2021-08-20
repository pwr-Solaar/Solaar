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

import os

from logging import DEBUG as _DEBUG
from logging import getLogger
from time import time as _timestamp

import solaar.gtk as gtk

from gi.repository import GLib, Gtk
from gi.repository.Gdk import ScrollDirection
from logitech_receiver.status import KEYS as _K
from solaar import NAME
from solaar.i18n import _

from . import icons as _icons
from .window import popup as _window_popup
from .window import toggle as _window_toggle

_log = getLogger(__name__)
del getLogger

#
# constants
#

_TRAY_ICON_SIZE = 32  # pixels
_MENU_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR
_RECEIVER_SEPARATOR = ('~', None, None, None)

#
#
#


def _create_menu(quit_handler):
    menu = Gtk.Menu()

    # per-device menu entries will be generated as-needed

    no_receiver = Gtk.MenuItem.new_with_label(_('No Logitech receiver found'))
    no_receiver.set_sensitive(False)
    menu.append(no_receiver)
    menu.append(Gtk.SeparatorMenuItem.new())

    from .action import about, make
    menu.append(about.create_menu_item())
    menu.append(make('application-exit', _('Quit') + ' ' + NAME, quit_handler, stock_id='application-exit').create_menu_item())
    del about, make

    menu.show_all()

    return menu


_last_scroll = 0


def _scroll(tray_icon, event, direction=None):
    if direction is None:
        direction = event.direction
        now = event.time / 1000.0
    else:
        now = None

    if direction != ScrollDirection.UP and direction != ScrollDirection.DOWN:
        # ignore all other directions
        return

    if len(_devices_info) < 4:
        # don't bother with scrolling when there's only one receiver
        # with only one device (3 = [receiver, device, separator])
        return

    # scroll events come way too fast (at least 5-6 at once)
    # so take a little break between them
    global _last_scroll
    now = now or _timestamp()
    if now - _last_scroll < 0.33:  # seconds
        return
    _last_scroll = now

    # if _log.isEnabledFor(_DEBUG):
    #     _log.debug("scroll direction %s", direction)

    global _picked_device
    candidate = None

    if _picked_device is None:
        for info in _devices_info:
            # pick first peripheral found
            if info[1] is not None:
                candidate = info
                break
    else:
        found = False
        for info in _devices_info:
            if not info[1]:
                # only conside peripherals
                continue
            # compare peripherals
            if info[0:2] == _picked_device[0:2]:
                if direction == ScrollDirection.UP and candidate:
                    # select previous device
                    break
                found = True
            else:
                if found:
                    candidate = info
                    if direction == ScrollDirection.DOWN:
                        break
                    # if direction is up, but no candidate found before _picked,
                    # let it run through all candidates, will get stuck with the last one
                else:
                    if direction == ScrollDirection.DOWN:
                        # only use the first one, in case no candidates are after _picked
                        if candidate is None:
                            candidate = info
                    else:
                        candidate = info

        # if the last _picked_device is gone, clear it
        # the candidate will be either the first or last one remaining,
        # depending on the scroll direction
        if not found:
            _picked_device = None

    _picked_device = candidate or _picked_device
    if _log.isEnabledFor(_DEBUG):
        _log.debug('scroll: picked %s', _picked_device)
    _update_tray_icon()


try:
    import gi
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        ayatana_appindicator_found = True
    except ValueError:
        try:
            gi.require_version('AppIndicator3', '0.1')
            ayatana_appindicator_found = False
        except ValueError:
            # treat unavailable versions the same as unavailable packages
            raise ImportError

    if ayatana_appindicator_found:
        from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    else:
        from gi.repository import AppIndicator3

    if _log.isEnabledFor(_DEBUG):
        _log.debug('using %sAppIndicator3' % ('Ayatana ' if ayatana_appindicator_found else ''))

    # Defense against AppIndicator3 bug that treats files in current directory as icon files
    # https://bugs.launchpad.net/ubuntu/+source/libappindicator/+bug/1363277
    def _icon_file(icon_name):
        if not os.path.isfile(icon_name):
            return icon_name
        icon_info = Gtk.IconTheme.get_default().lookup_icon(icon_name, _TRAY_ICON_SIZE, 0)
        return icon_info.get_filename() if icon_info else icon_name

    def _create(menu):
        _icons._init_icon_paths()
        theme_paths = Gtk.IconTheme.get_default().get_search_path()

        ind = AppIndicator3.Indicator.new_with_path(
            'indicator-solaar', _icon_file(_icons.TRAY_INIT), AppIndicator3.IndicatorCategory.HARDWARE, theme_paths[0]
        )
        ind.set_title(NAME)
        ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        # ind.set_attention_icon_full(_icon_file(_icons.TRAY_ATTENTION), '') # works poorly for XFCE 16
        # ind.set_label(NAME, NAME)

        ind.set_menu(menu)
        ind.connect('scroll-event', _scroll)

        return ind

    def _destroy(indicator):
        indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)

    def _update_tray_icon():
        if _picked_device and gtk.battery_icons_style != 'solaar':
            _ignore, _ignore, name, device_status = _picked_device
            battery_level = device_status.get(_K.BATTERY_LEVEL)
            battery_charging = device_status.get(_K.BATTERY_CHARGING)
            tray_icon_name = _icons.battery(battery_level, battery_charging)

            description = '%s: %s' % (name, device_status.to_string())
        else:
            # there may be a receiver, but no peripherals
            tray_icon_name = _icons.TRAY_OKAY if _devices_info else _icons.TRAY_INIT

            description_lines = _generate_description_lines()
            description = '\n'.join(description_lines).rstrip('\n')

        # icon_file = _icons.icon_file(icon_name, _TRAY_ICON_SIZE)
        _icon.set_icon_full(_icon_file(tray_icon_name), description)

    def _update_menu_icon(image_widget, icon_name):
        image_widget.set_from_icon_name(icon_name, _MENU_ICON_SIZE)
        # icon_file = _icons.icon_file(icon_name, _MENU_ICON_SIZE)
        # image_widget.set_from_file(icon_file)
        # image_widget.set_pixel_size(_TRAY_ICON_SIZE)

    def attention(reason=None):
        if _icon.get_status() != AppIndicator3.IndicatorStatus.ATTENTION:
            # _icon.set_attention_icon_full(_icon_file(_icons.TRAY_ATTENTION), reason or '') # works poorly for XFCe 16
            _icon.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
            GLib.timeout_add(10 * 1000, _icon.set_status, AppIndicator3.IndicatorStatus.ACTIVE)

except ImportError:

    if _log.isEnabledFor(_DEBUG):
        _log.debug('using StatusIcon')

    def _create(menu):
        icon = Gtk.StatusIcon.new_from_icon_name(_icons.TRAY_INIT)
        icon.set_name(NAME)
        icon.set_title(NAME)
        icon.set_tooltip_text(NAME)
        icon.connect('activate', _window_toggle)
        icon.connect('scroll-event', _scroll)
        icon.connect('popup-menu', lambda icon, button, time: menu.popup(None, None, icon.position_menu, icon, button, time))

        return icon

    def _destroy(icon):
        icon.set_visible(False)

    def _update_tray_icon():
        tooltip_lines = _generate_tooltip_lines()
        tooltip = '\n'.join(tooltip_lines).rstrip('\n')
        _icon.set_tooltip_markup(tooltip)

        if _picked_device and gtk.battery_icons_style != 'solaar':
            _ignore, _ignore, name, device_status = _picked_device
            battery_level = device_status.get(_K.BATTERY_LEVEL)
            battery_charging = device_status.get(_K.BATTERY_CHARGING)
            tray_icon_name = _icons.battery(battery_level, battery_charging)
        else:
            # there may be a receiver, but no peripherals
            tray_icon_name = _icons.TRAY_OKAY if _devices_info else _icons.TRAY_ATTENTION
        _icon.set_from_icon_name(tray_icon_name)

    def _update_menu_icon(image_widget, icon_name):
        image_widget.set_from_icon_name(icon_name, _MENU_ICON_SIZE)

    _icon_before_attention = None

    def _blink(count):
        global _icon_before_attention
        if count % 2:
            _icon.set_from_icon_name(_icons.TRAY_ATTENTION)
        else:
            _icon.set_from_icon_name(_icon_before_attention)

        if count > 0:
            GLib.timeout_add(1000, _blink, count - 1)
        else:
            _icon_before_attention = None

    def attention(reason=None):
        global _icon_before_attention
        if _icon_before_attention is None:
            _icon_before_attention = _icon.get_icon_name()
            GLib.idle_add(_blink, 9)


#
#
#


def _generate_tooltip_lines():
    if not _devices_info:
        yield '<b>%s</b>: ' % NAME + _('no receiver')
        return

    yield from _generate_description_lines()


def _generate_description_lines():
    if not _devices_info:
        yield _('no receiver')
        return

    for _ignore, number, name, status in _devices_info:
        if number is None:  # receiver
            continue

        p = status.to_string()
        if p:  # does it have any properties to print?
            yield '<b>%s</b>' % name
            if status:
                yield '\t%s' % p
            else:
                yield '\t%s <small>(' % p + _('offline') + ')</small>'
        else:
            if status:
                yield '<b>%s</b> <small>(' % name + _('no status') + ')</small>'
            else:
                yield '<b>%s</b> <small>(' % name + _('offline') + ')</small>'
        yield ''


def _pick_device_with_lowest_battery():
    if not _devices_info:
        return None

    picked = None
    picked_level = 1000

    for info in _devices_info:
        if info[1] is None:  # is receiver/separator
            continue
        level = info[-1].get(_K.BATTERY_LEVEL)
        # print ("checking %s -> %s", info, level)
        if level is not None and picked_level > level:
            picked = info
            picked_level = level or 0

    if _log.isEnabledFor(_DEBUG):
        _log.debug('picked device with lowest battery: %s', picked)

    return picked


#
#
#


def _add_device(device):
    assert device
    # not true for wired devices - assert device.receiver
    receiver_path = device.receiver.path if device.receiver is not None else device.path
    # not true for wired devices - assert receiver_path

    index = 0
    for idx, (path, _ignore, _ignore, _ignore) in enumerate(_devices_info):
        if path == receiver_path:
            # the first entry matching the receiver serial should be for the receiver itself
            index = idx + 1
            break
    # assert index is not None

    if device.receiver:
        # proper ordering (according to device.number) for a receiver's devices
        while True:
            path, number, _ignore, _ignore = _devices_info[index]
            if path == _RECEIVER_SEPARATOR[0]:
                break
            assert path == receiver_path
            assert number != device.number
            if number > device.number:
                break
            index = index + 1

    new_device_info = (receiver_path, device.number, device.name, device.status)
    assert len(new_device_info) == len(_RECEIVER_SEPARATOR)
    _devices_info.insert(index, new_device_info)

    # label_prefix = b'\xE2\x94\x84 '.decode('utf-8')
    label_prefix = '   '

    new_menu_item = Gtk.ImageMenuItem.new_with_label((label_prefix if device.number else '') + device.name)
    new_menu_item.set_image(Gtk.Image())
    new_menu_item.show_all()
    new_menu_item.connect('activate', _window_popup, receiver_path, device.number)
    _menu.insert(new_menu_item, index)

    return index


def _remove_device(index):
    assert index is not None

    menu_items = _menu.get_children()
    _menu.remove(menu_items[index])

    removed_device = _devices_info.pop(index)
    global _picked_device
    if _picked_device and _picked_device[0:2] == removed_device[0:2]:
        # the current pick was unpaired
        _picked_device = None


def _add_receiver(receiver):
    index = len(_devices_info)

    new_receiver_info = (receiver.path, None, receiver.name, None)
    assert len(new_receiver_info) == len(_RECEIVER_SEPARATOR)
    _devices_info.append(new_receiver_info)

    new_menu_item = Gtk.ImageMenuItem.new_with_label(receiver.name)
    _menu.insert(new_menu_item, index)
    icon_set = _icons.device_icon_set(receiver.name)
    new_menu_item.set_image(Gtk.Image().new_from_icon_set(icon_set, _MENU_ICON_SIZE))
    new_menu_item.show_all()
    new_menu_item.connect('activate', _window_popup, receiver.path)

    _devices_info.append(_RECEIVER_SEPARATOR)
    separator = Gtk.SeparatorMenuItem.new()
    separator.set_visible(True)
    _menu.insert(separator, index + 1)

    return 0


def _remove_receiver(receiver):
    index = 0
    found = False

    # remove all entries in devices_info that match this receiver
    while index < len(_devices_info):
        path, _ignore, _ignore, _ignore = _devices_info[index]
        if path == receiver.path:
            found = True
            _remove_device(index)
        elif found and path == _RECEIVER_SEPARATOR[0]:
            # the separator after this receiver
            _remove_device(index)
            break
        else:
            index += 1


def _update_menu_item(index, device):
    if not device or device.status is None:
        _log.warn('updating an inactive device %s, assuming disconnected', device)
        return None

    menu_items = _menu.get_children()
    menu_item = menu_items[index]

    level = device.status.get(_K.BATTERY_LEVEL)
    charging = device.status.get(_K.BATTERY_CHARGING)
    icon_name = _icons.battery(level, charging)

    image_widget = menu_item.get_image()
    image_widget.set_sensitive(bool(device.online))
    _update_menu_icon(image_widget, icon_name)


#
#
#

# for which device to show the battery info in systray, if more than one
# it's actually an entry in _devices_info
_picked_device = None

# cached list of devices and some of their properties
# contains tuples of (receiver path, device number, name, status)
_devices_info = []

_menu = None
_icon = None


def init(_quit_handler):
    global _menu, _icon
    assert _menu is None
    _menu = _create_menu(_quit_handler)
    assert _icon is None
    _icon = _create(_menu)


def destroy():
    global _icon, _menu, _devices_info
    if _icon is not None:
        i, _icon = _icon, None
        _destroy(i)
        i = None

    _icon = None
    _menu = None
    _devices_info = None


def update(device=None):
    if _icon is None:
        return

    if device is not None:
        if device.kind is None:
            # receiver
            is_alive = bool(device)
            receiver_path = device.path
            if is_alive:
                index = None
                for idx, (path, _ignore, _ignore, _ignore) in enumerate(_devices_info):
                    if path == receiver_path:
                        index = idx
                        break

                if index is None:
                    _add_receiver(device)
            else:
                _remove_receiver(device)

        else:
            # peripheral
            is_paired = bool(device)
            receiver_path = device.receiver.path if device.receiver is not None else device.path
            index = None
            for idx, (path, number, _ignore, _ignore) in enumerate(_devices_info):
                if path == receiver_path and number == device.number:
                    index = idx

            if is_paired:
                if index is None:
                    index = _add_device(device)
                _update_menu_item(index, device)
            else:  # was just unpaired or unplugged
                if index is not None:
                    _remove_device(index)

        menu_items = _menu.get_children()
        no_receivers_index = len(_devices_info)
        menu_items[no_receivers_index].set_visible(not _devices_info)
        menu_items[no_receivers_index + 1].set_visible(not _devices_info)

    global _picked_device
    if (not _picked_device or _last_scroll == 0) and device is not None and device.kind is not None:
        # if it's just a receiver update, it's unlikely the picked device would change
        _picked_device = _pick_device_with_lowest_battery()

    _update_tray_icon()
