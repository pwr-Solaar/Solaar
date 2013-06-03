#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
_DEBUG = logging.DEBUG
_log = logging.getLogger('solaar.ui.icons')

from gi.repository import Gtk

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

APP_ICON = ('solaar-init', 'solaar', 'solaar-fail')


def _look_for_application_icons():
	import os.path as _path
	from os import environ as _environ

	import sys as _sys
	_log.debug("sys.path[0] = %s", _sys.path[0])
	prefix_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..'))
	src_share = _path.normpath(_path.join(_path.realpath(_sys.path[0]), '..', 'share'))
	local_share = _environ.get('XDG_DATA_HOME', _path.expanduser('~/.local/share'))
	data_dirs = _environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
	del _sys

	share_solaar = [prefix_share] + list(_path.join(x, 'solaar') for x in [src_share, local_share] + data_dirs.split(':'))
	for location in share_solaar:
		location = _path.join(location, 'icons')
		if _log.isEnabledFor(_DEBUG):
			_log.debug("looking for icons in %s", location)
		solaar_png = _path.join(location, APP_ICON[0] + '.png')
		if _path.exists(solaar_png):
			yield location

	del _environ
	# del _path

_default_theme = Gtk.IconTheme.get_default()
for p in _look_for_application_icons():
	_default_theme.prepend_search_path(p)
_log.debug("icon theme paths: %s", _default_theme.get_search_path())

#
#
#

_has_gpm_icons = _default_theme.has_icon('gpm-battery-020-charging')
_has_oxygen_icons = _default_theme.has_icon('battery-charging-caution') and \
					_default_theme.has_icon('battery-charging-040')
_has_gnome_icons = _default_theme.has_icon('battery-caution-charging') and \
					_default_theme.has_icon('battery-full-charged')
_has_elementary_icons = _default_theme.has_icon('battery-020-charging')

_log.debug("detected icon sets: gpm %s, oxygen %s, gnome %s, elementary %s", _has_gpm_icons, _has_oxygen_icons, _has_gnome_icons, _has_elementary_icons)
if (not _has_gpm_icons and not _has_oxygen_icons and
	not _has_gnome_icons and not _has_elementary_icons):
	_log.warning("failed to detect a known icon set")

#
#
#

def battery(level=None, charging=False):
	icon_name = _battery_icon_name(level, charging)
	if not _default_theme.has_icon(icon_name):
		_log.warning("icon %s not found in current theme", icon_name);
	# elif _log.isEnabledFor(_DEBUG):
	# 	_log.debug("battery icon for %s:%s = %s", level, charging, icon_name)
	return icon_name

def _battery_icon_name(level, charging):
	if level is None or level < 0:
		return 'gpm-battery-missing' \
			if _has_gpm_icons and _default_theme.has_icon('gpm-battery-missing') \
			else 'battery-missing'

	level_approx = 20 * ((level  + 10) // 20)

	if _has_gpm_icons:
		if level == 100 and charging:
			return 'gpm-battery-charged'
		return 'gpm-battery-%03d%s' % (level_approx, '-charging' if charging else '')

	if _has_oxygen_icons:
		if level_approx == 100 and charging:
			return 'battery-charging'
		level_name = ('low', 'caution', '040', '060', '080', '100')[level_approx // 20]
		return 'battery%s-%s' % ('-charging' if charging else '', level_name)

	if _has_elementary_icons:
		if level == 100 and charging:
			return 'battery-charged'
		return 'battery-%03d%s' % (level_approx, '-charging' if charging else '')

	if _has_gnome_icons:
		if level == 100 and charging:
			return 'battery-full-charged'
		if level_approx == 0 and charging:
			return 'battery-caution-charging'
		level_name = ('empty', 'caution', 'low', 'good', 'good', 'full')[level_approx // 20]
		return 'battery-%s%s' % (level_name, '-charging' if charging else '')

	if level == 100 and charging:
		return 'battery-charged'
	# fallback... most likely will fail
	return 'battery-%03d%s' % (level_approx, '-charging' if charging else '')

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
		# the theme will hopefully pick up the most appropiate
		names = ['preferences-desktop-peripherals']
		if kind:
			if str(kind) == 'numpad':
				names += ('input-keyboard', 'input-dialpad')
			elif str(kind) == 'touchpad':
				names += ('input-mouse', 'input-tablet')
			elif str(kind) == 'trackball':
				names += ('input-mouse',)
			names += ('input-' + str(kind),)
		# names += (name.replace(' ', '-'),)

		source = Gtk.IconSource.new()
		for n in names:
			source.set_icon_name(n)
			icon_set.add_source(source)
		icon_set.names = names

	return icon_set


def device_icon_file(name, kind=None, size=_LARGE_SIZE):
	icon_set = device_icon_set(name, kind)
	assert icon_set
	for n in reversed(icon_set.names):
		if _default_theme.has_icon(n):
			return _default_theme.lookup_icon(n, size, 0).get_filename()


def device_icon_name(name, kind=None):
	icon_set = device_icon_set(name, kind)
	assert icon_set
	for n in reversed(icon_set.names):
		if _default_theme.has_icon(n):
			return n


def icon_file(name, size=_LARGE_SIZE):
	# _log.debug("looking for file of icon %s at size %s", name, size)
	if _default_theme.has_icon(name):
		theme_icon = _default_theme.lookup_icon(name, size, 0)
		file_name = theme_icon.get_filename()
		# _log.debug("icon %s => %s : %s", name, theme_icon, file_name)
		return file_name
