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

from gi.repository import Gtk

import solaar.gtk as gtk

logger = logging.getLogger(__name__)

LARGE_SIZE = Gtk.IconSize.DIALOG  # was 64
TRAY_INIT = "solaar-init"
TRAY_OKAY = "solaar"
TRAY_ATTENTION = "solaar-attention"

_default_theme = None
_has_level_icons = False


def _init_icon_paths():
    global _default_theme, _has_level_icons
    if _default_theme:
        return
    _default_theme = Gtk.IconTheme.get_default()
    logger.debug("icon theme paths: %s", _default_theme.get_search_path())
    if gtk.battery_icons_style == "symbolic":
        global TRAY_OKAY
        TRAY_OKAY = TRAY_INIT  # use monochrome tray icon
        if not _default_theme.has_icon("battery-good-symbolic"):
            logger.warning("failed to detect symbolic icons")
            gtk.battery_icons_style = "regular"
    if gtk.battery_icons_style == "regular":
        if not _default_theme.has_icon("battery-good"):
            logger.warning("failed to detect icons")
            gtk.battery_icons_style = "solaar"
    suffix = "-symbolic" if gtk.battery_icons_style == "symbolic" else ""
    _has_level_icons = _default_theme.has_icon(f"battery-level-50{suffix}")
    logger.debug("battery level icons available: %s", _has_level_icons)


def battery(level=None, charging=False):
    icon_name = _battery_icon_name(level, charging)
    if not _default_theme.has_icon(icon_name):
        logger.warning("icon %s not found in current theme", icon_name)
        return TRAY_OKAY  # use Solaar icon if battery icon not available
    logger.debug("battery icon for %s:%s = %s", level, charging, icon_name)
    return icon_name


# return first res where val >= guard
# _first_res(val,((guard,res),...))
def _first_res(val, pairs):
    return next((res for guard, res in pairs if val >= guard), None)


def _battery_icon_name(level, charging):
    _init_icon_paths()
    suffix = "-symbolic" if gtk.battery_icons_style == "symbolic" else ""

    if level is None or level < 0:
        return f"battery-missing{suffix}"

    rounded = min(100, max(0, round(level / 10) * 10))

    # Try precise level icons first (battery-level-N[-charging|-charged][-symbolic])
    if _has_level_icons:
        if charging and rounded == 100:
            charging_str = "-charged"
        elif charging:
            charging_str = "-charging"
        else:
            charging_str = ""
        icon_name = f"battery-level-{rounded}{charging_str}{suffix}"
        if _default_theme.has_icon(icon_name):
            logger.debug("battery level icon for %s:%s = %s", level, charging, icon_name)
            return icon_name

    # Fall back to semantic names with corrected thresholds
    level_name = _first_res(level, ((90, "full"), (60, "good"), (20, "low"), (5, "caution"), (0, "empty")))
    if level_name:
        if charging:
            charging_str = "-charging"
        else:
            charging_str = ""
        icon_name = f"battery-{level_name}{charging_str}{suffix}"
        if _default_theme.has_icon(icon_name):
            logger.debug("battery semantic icon for %s:%s = %s", level, charging, icon_name)
            return icon_name

    # Last resort: plain battery icon
    icon_name = f"battery{suffix}"
    logger.debug("battery generic icon for %s:%s = %s", level, charging, icon_name)
    return icon_name


def lux(level=None):
    if level is None or level < 0:
        return "light_unknown"
    return f"solaar-light_{int(20 * ((level + 50) // 100)):03}"


_ICON_SETS = {}


def device_icon_set(name="_", kind=None):
    icon_set = _ICON_SETS.get(name)
    if icon_set is None:
        # names of possible icons, in reverse desirability
        icon_set = ["preferences-desktop-peripherals"]
        if kind:
            if str(kind) == "numpad":
                icon_set += ("input-keyboard", "input-dialpad")
            elif str(kind) == "touchpad":
                icon_set += ("input-mouse", "input-tablet")
            elif str(kind) == "trackball":
                icon_set += ("input-mouse",)
            elif str(kind) == "headset":
                icon_set += ("audio-headphones", "audio-headset")
            icon_set += (f"input-{str(kind)}",)
        # icon_set += (name.replace(' ', '-'),)
        _ICON_SETS[name] = icon_set
    return icon_set


def device_icon_file(name, kind=None, size=LARGE_SIZE):
    icon_name = device_icon_name(name, kind)
    return _default_theme.lookup_icon(icon_name, size, 0).get_filename() if icon_name is not None else None


def device_icon_name(name, kind=None):
    _init_icon_paths()
    icon_set = device_icon_set(name, kind)
    assert icon_set
    for n in reversed(icon_set):
        if _default_theme.has_icon(n):
            return n


def icon_file(name, size=LARGE_SIZE):
    _init_icon_paths()
    # has_icon() somehow returned False while lookup_icon returns non-None.
    # I guess it happens because share/solaar/icons/ has no hicolor and resolution subdirs
    theme_icon = _default_theme.lookup_icon(name, size, 0)
    if theme_icon:
        file_name = theme_icon.get_filename()
        return file_name
    logger.warning("icon %s(%d) not found in current theme", name, size)
