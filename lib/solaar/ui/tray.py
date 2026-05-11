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
import os

from enum import Enum
from time import time

import gi

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository.Gdk import ScrollDirection

import solaar.gtk as gtk

from solaar import NAME
from solaar.i18n import _

from . import action
from . import icons
from . import window
from .about import about

logger = logging.getLogger(__name__)

_TRAY_ICON_SIZE = 48
_MENU_ICON_SIZE = Gtk.IconSize.LARGE_TOOLBAR


class GtkSignal(Enum):
    ACTIVATE = "activate"
    SCROLL_EVENT = "scroll-event"


def _create_menu(quit_handler):
    # per-device menu entries will be generated as-needed
    menu = Gtk.Menu()

    no_receiver = Gtk.MenuItem.new_with_label(_("No supported device found"))
    no_receiver.set_sensitive(False)
    menu.append(no_receiver)
    menu.append(Gtk.SeparatorMenuItem.new())

    menu.append(action.make_image_menu_item(_("About %s") % NAME, "help-about", about.show))
    menu.append(action.make_image_menu_item(_("Quit %s") % NAME, "application-exit", quit_handler))

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

    # don't bother even trying to scroll if less than two devices
    if sum(map(lambda i: i[1] is not None, _devices_info)) < 2:
        return

    # scroll events come way too fast (at least 5-6 at once) so take a little break between them
    global _last_scroll
    now = now or time()
    if now - _last_scroll < 0.33:  # seconds
        return
    _last_scroll = now

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
    logger.debug("scroll: picked %s", _picked_device)
    _update_tray_icon()


try:
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as AppIndicator3

        ayatana_appindicator_found = True
    except ValueError:
        try:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3

            ayatana_appindicator_found = False
        except ValueError as exc:
            # treat unavailable versions the same as unavailable packages
            raise ImportError from exc

    logger.debug(f"using {'Ayatana ' if ayatana_appindicator_found else ''}AppIndicator3")

    # Defense against AppIndicator3 bug that treats files in current directory as icon files
    # https://bugs.launchpad.net/ubuntu/+source/libappindicator/+bug/1363277
    # Defense against bug that shows up in XFCE 4.16 where icons are not upscaled
    def _icon_file(icon_name):
        if gtk.tray_icon_size is None and not os.path.isfile(icon_name):
            return icon_name
        icon_info = Gtk.IconTheme.get_default().lookup_icon(
            icon_name, gtk.tray_icon_size or _TRAY_ICON_SIZE, Gtk.IconLookupFlags.FORCE_SVG
        )
        return icon_info.get_filename() if icon_info else icon_name

    def _create(menu):
        icons._init_icon_paths()
        ind = AppIndicator3.Indicator.new(
            "indicator-solaar", _icon_file(icons.TRAY_INIT), AppIndicator3.IndicatorCategory.HARDWARE
        )
        ind.set_title(NAME)
        ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        # ind.set_attention_icon_full(_icon_file(icons.TRAY_ATTENTION), '') # works poorly for XFCE 16
        # ind.set_label(NAME.lower(), NAME.lower())

        ind.set_menu(menu)
        ind.connect(GtkSignal.SCROLL_EVENT.value, _scroll)

        return ind

    def _hide(indicator):
        indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)

    def _show(indicator):
        indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    def _update_tray_icon():
        if _picked_device and gtk.battery_icons_style != "solaar":
            _ignore, _ignore, name, device = _picked_device
            battery_level = device.battery_info.level if device.battery_info is not None else None
            battery_charging = device.battery_info.charging() if device.battery_info is not None else None
            tray_icon_name = icons.battery(battery_level, battery_charging)
            description = f"{name}: {device.status_string()}"
        else:
            # there may be a receiver, but no peripherals
            tray_icon_name = icons.TRAY_OKAY if _devices_info else icons.TRAY_INIT

            description_lines = _generate_description_lines()
            description = "\n".join(description_lines).rstrip("\n")

        # icon_file = icons.icon_file(icon_name, _TRAY_ICON_SIZE)
        _icon.set_icon_full(_icon_file(tray_icon_name), description)

    def attention(reason=None):
        if _icon.get_status() != AppIndicator3.IndicatorStatus.ATTENTION:
            # _icon.set_attention_icon_full(_icon_file(icons.TRAY_ATTENTION), reason or '') # works poorly for XFCe 16
            _icon.set_status(AppIndicator3.IndicatorStatus.ATTENTION)
            GLib.timeout_add(10 * 1000, _icon.set_status, AppIndicator3.IndicatorStatus.ACTIVE)

except ImportError:
    logger.debug("using StatusIcon")

    def _create(menu):
        icon = Gtk.StatusIcon.new_from_icon_name(icons.TRAY_INIT)
        icon.set_name(NAME.lower())
        icon.set_title(NAME)
        icon.set_tooltip_text(NAME)
        icon.connect(GtkSignal.ACTIVATE.value, window.toggle)
        icon.connect(GtkSignal.SCROLL_EVENT.value, _scroll)
        icon.connect(
            "popup-menu",
            lambda icon, button, time: menu.popup(None, None, icon.position_menu, icon, button, time),
        )

        return icon

    def _hide(icon):
        icon.set_visible(False)

    def _show(icon):
        icon.set_visible(True)

    def _update_tray_icon():
        tooltip_lines = _generate_tooltip_lines()
        tooltip = "\n".join(tooltip_lines).rstrip("\n")
        _icon.set_tooltip_markup(tooltip)

        if _picked_device and gtk.battery_icons_style != "solaar":
            _ignore, _ignore, name, device = _picked_device
            battery_level = device.battery_info.level if device.battery_info is not None else None
            battery_charging = device.battery_info.charging() if device.battery_info is not None else None
            tray_icon_name = icons.battery(battery_level, battery_charging)
        else:
            # there may be a receiver, but no peripherals
            tray_icon_name = icons.TRAY_OKAY if _devices_info else icons.TRAY_ATTENTION
        _icon.set_from_icon_name(tray_icon_name)

    _icon_before_attention = None

    def _blink(count):
        global _icon_before_attention
        if count % 2:
            _icon.set_from_icon_name(icons.TRAY_ATTENTION)
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


def _generate_tooltip_lines():
    if not _devices_info:
        yield f"<b>{NAME}</b>: " + _("no receiver")
        return

    yield from _generate_description_lines()


def _generate_description_lines():
    if not _devices_info:
        yield _("no receiver")
        return

    for _ignore, number, name, device in _devices_info:
        if number is None:  # receiver
            continue

        p = device.status_string()
        if p:  # does it have any properties to print?
            yield f"<b>{name}</b>"
            if device.online:
                yield f"\t{p}"
            else:
                yield f"\t{p} <small>(" + _("offline") + ")</small>"
        else:
            if device.online:
                yield f"<b>{name}</b> <small>(" + _("no status") + ")</small>"
            else:
                yield f"<b>{name}</b> <small>(" + _("offline") + ")</small>"


def _pick_device_with_lowest_battery():
    if not _devices_info:
        return None

    picked = None
    picked_level = 1000

    for info in _devices_info:
        if info[1] is None:  # is receiver
            continue
        level = info[-1].battery_info.level if info[-1].battery_info is not None else None
        if level is not None and picked_level > level:
            picked = info
            picked_level = level or 0

    logger.debug("picked device with lowest battery: %s", picked)

    return picked


def _add_device(device):
    assert device

    index = 0
    receiver_path = device.receiver.path if device.receiver is not None else device.path
    if device.receiver is not None:  # if receiver insert into devices for the receiver in device number order
        for idx, (path, _ignore, _ignore, _ignore) in enumerate(_devices_info):
            if path and path == receiver_path:
                index = idx + 1  # the first entry matching the receiver serial should be for the receiver itself
                break
        while index < len(_devices_info):
            path, number, _ignore, _ignore = _devices_info[index]
            if not path == receiver_path:
                break
            assert number != device.number
            if number > device.number:
                break
            index = index + 1

    new_device_info = (receiver_path, device.number, device.name, device)
    _devices_info.insert(index, new_device_info)

    label = ("   " if device.number else "") + device.name
    new_menu_item = action.make_image_menu_item(label, None, window.popup, receiver_path, device.number)
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
    _devices_info.insert(index, new_receiver_info)
    icon_name = icons.device_icon_name(receiver.name, receiver.kind)
    new_menu_item = action.make_image_menu_item(receiver.name, icon_name, window.popup, receiver.path)
    _menu.insert(new_menu_item, index)
    return 0


def _remove_receiver(receiver):
    index = 0
    # remove all entries in devices_info that match this receiver
    while index < len(_devices_info):
        path, _ignore, _ignore, _ignore = _devices_info[index]
        if path == receiver.path:
            _remove_device(index)
        else:
            index += 1


def _update_menu_item(index, device):
    if device is None:
        logger.warning("updating an inactive device %s, assuming disconnected", device)
        return None
    menu_items = _menu.get_children()
    menu_item = menu_items[index]
    level = device.battery_info.level if device.battery_info is not None else None
    charging = device.battery_info.charging() if device.battery_info is not None else None
    icon_name = icons.battery(level, charging)
    menu_item.label.set_label(("  " if 0 < device.number <= 6 else "") + device.name + ": " + device.status_string())
    image_widget = menu_item.icon
    image_widget.set_sensitive(bool(device.online))
    image_widget.set_from_icon_name(icon_name, _MENU_ICON_SIZE)


# for which device to show the battery info in systray, if more than one
# it's actually an entry in _devices_info
_picked_device = None

# cached list of devices and some of their properties
# contains tuples of (receiver path, device number, name, device)
_devices_info = []

_menu = None
_icon = None


def init(_quit_handler):
    global _menu, _icon
    assert _menu is None
    _menu = _create_menu(_quit_handler)
    assert _icon is None
    _icon = _create(_menu)
    update()


def destroy():
    global _icon, _menu, _devices_info
    if _icon is not None:
        i, _icon = _icon, None
        _hide(i)
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

    global _picked_device
    if (not _picked_device or _last_scroll == 0) and device is not None and device.kind is not None:
        # if it's just a receiver update, it's unlikely the picked device would change
        _picked_device = _pick_device_with_lowest_battery()

    _update_tray_icon()

    if _icon:
        if not _devices_info:
            _hide(_icon)
        else:
            _show(_icon)
