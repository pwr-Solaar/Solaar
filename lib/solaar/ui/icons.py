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

import solaar.gtk as gtk

from gi.repository import Gtk

_log = getLogger(__name__)
del getLogger

#
#
#

_LARGE_SIZE = 64
Gtk.IconSize.LARGE = Gtk.icon_size_register('large', _LARGE_SIZE, _LARGE_SIZE)
# Gtk.IconSize.XLARGE = Gtk.icon_size_register('x-large', _LARGE_SIZE * 2, _LARGE_SIZE * 2)
# print ("menu", int(Gtk.IconSize.MENU), Gtk.icon_size_lookup(Gtk.IconSize.MENU))
# print ("small toolbar", int(Gtk.IconSize.SMALL_TOOLBAR), Gtk.icon_size_lookup(Gtk.IconSize.SMALL_TOOLBAR))
# print ("button", int(Gtk.IconSize.BUTTON), Gtk.icon_size_lookup(Gtk.IconSize.BUTTON))
# print ("large toolbar", int(Gtk.IconSize.LARGE_TOOLBAR), Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR))
# print ("dnd", int(Gtk.IconSize.DND), Gtk.icon_size_lookup(Gtk.IconSize.DND))
# print ("dialog", int(Gtk.IconSize.DIALOG), Gtk.icon_size_lookup(Gtk.IconSize.DIALOG))

TRAY_INIT = 'solaar-init'
TRAY_OKAY = 'solaar'
TRAY_ATTENTION = 'solaar-attention'


def _look_for_application_icons():
    import os.path as _path
    from os import environ as _environ

    import sys as _sys
    if _log.isEnabledFor(_DEBUG):
        _log.debug('sys.path[0] = %s', _sys.path[0])
    prefix_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..'))
    src_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..', 'share'))
    local_share = _environ.get('XDG_DATA_HOME', _path.expanduser(_path.join('~', '.local', 'share')))
    data_dirs = _environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
    repo_share = _path.normpath(_path.join(_path.dirname(__file__), '..', '..', '..', 'share'))
    setuptools_share = _path.normpath(_path.join(_path.dirname(__file__), '..', '..', 'share'))
    del _sys

    share_solaar = [prefix_share] + list(
        _path.join(x, 'solaar') for x in [src_share, local_share, setuptools_share, repo_share] + data_dirs.split(':')
    )
    for location in share_solaar:
        location = _path.join(location, 'icons')
        if _log.isEnabledFor(_DEBUG):
            _log.debug('looking for icons in %s', location)

        if _path.exists(_path.join(location, TRAY_ATTENTION + '.svg')):
            yield location

    del _environ
    # del _path


_default_theme = None


def _init_icon_paths():
    global _default_theme
    if _default_theme:
        return

    _default_theme = Gtk.IconTheme.get_default()
    for p in _look_for_application_icons():
        _default_theme.prepend_search_path(p)
    if _log.isEnabledFor(_DEBUG):
        _log.debug('icon theme paths: %s', _default_theme.get_search_path())

    if gtk.battery_icons_style == 'symbolic':
        if not _default_theme.has_icon('battery-good-symbolic'):
            _log.warning('failed to detect symbolic icons')
            gtk.battery_icons_style = 'regular'
    if gtk.battery_icons_style == 'regular':
        if not _default_theme.has_icon('battery-good'):
            _log.warning('failed to detect icons')
            gtk.battery_icons_style = 'none'


#
#
#


def battery(level=None, charging=False):
    icon_name = _battery_icon_name(level, charging)
    if not _default_theme.has_icon(icon_name):
        _log.warning('icon %s not found in current theme', icon_name)
        return TRAY_OKAY  # use Solaar icon if battery icon not available
    elif _log.isEnabledFor(_DEBUG):
        _log.debug('battery icon for %s:%s = %s', level, charging, icon_name)
    return icon_name


# return first res where val >= guard
# _first_res(val,((guard,res),...))
def _first_res(val, pairs):
    return next((res for guard, res in pairs if val >= guard), None)


def _battery_icon_name(level, charging):
    _init_icon_paths()

    if level is None or level < 0:
        return 'battery-missing' + ('-symbolic' if gtk.battery_icons_style == 'symbolic' else '')

    level_name = _first_res(level, ((90, 'full'), (50, 'good'), (20, 'low'), (5, 'caution'), (0, 'empty')))
    return 'battery-%s%s%s' % (
        level_name, '-charging' if charging else '', '-symbolic' if gtk.battery_icons_style == 'symbolic' else ''
    )


#
#
#


def lux(level=None):
    if level is None or level < 0:
        return 'light_unknown'
    return 'light_%03d' % (20 * ((level + 50) // 100))


#
#
#

_ICON_SETS = {}


def device_icon_set(name='_', kind=None):
    icon_set = _ICON_SETS.get(name)
    if icon_set is None:
        icon_set = Gtk.IconSet.new()
        _ICON_SETS[name] = icon_set

        # names of possible icons, in reverse order of likelihood
        # the theme will hopefully pick up the most appropriate
        names = ['preferences-desktop-peripherals']
        if kind:
            if str(kind) == 'numpad':
                names += ('input-keyboard', 'input-dialpad')
            elif str(kind) == 'touchpad':
                names += ('input-mouse', 'input-tablet')
            elif str(kind) == 'trackball':
                names += ('input-mouse', )
            elif str(kind) == 'headset':
                names += ('audio-headphones', 'audio-headset')
            names += ('input-' + str(kind), )
        # names += (name.replace(' ', '-'),)

        source = Gtk.IconSource.new()
        for n in names:
            source.set_icon_name(n)
            icon_set.add_source(source)
        icon_set.names = names

    return icon_set


def device_icon_file(name, kind=None, size=_LARGE_SIZE):
    _init_icon_paths()

    icon_set = device_icon_set(name, kind)
    assert icon_set
    for n in reversed(icon_set.names):
        if _default_theme.has_icon(n):
            return _default_theme.lookup_icon(n, size, 0).get_filename()


def device_icon_name(name, kind=None):
    _init_icon_paths()

    icon_set = device_icon_set(name, kind)
    assert icon_set
    for n in reversed(icon_set.names):
        if _default_theme.has_icon(n):
            return n


def icon_file(name, size=_LARGE_SIZE):
    _init_icon_paths()

    # has_icon() somehow returned False while lookup_icon returns non-None.
    # I guess it happens because share/solaar/icons/ has no hicolor and
    # resolution subdirs
    theme_icon = _default_theme.lookup_icon(name, size, 0)
    if theme_icon:
        file_name = theme_icon.get_filename()
        # if _log.isEnabledFor(_DEBUG):
        #     _log.debug("icon %s(%d) => %s", name, size, file_name)
        return file_name

    _log.warn('icon %s(%d) not found in current theme', name, size)
