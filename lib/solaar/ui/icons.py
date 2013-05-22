#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

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


APP_ICON = { 1: 'solaar', 2: 'solaar-mask', 0: 'solaar-init', -1: 'solaar-fail' }

#
#
#

def battery(level=None, charging=False):
	if level is None or level < 0:
		return 'battery_unknown'
	return 'battery_%03d' % (10 * ((level + 5) // 10))


def lux(level=None):
	if level is None or level < 0:
		return 'light_unknown'
	return 'light_%03d' % (20 * ((level + 50) // 100))


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
		# names += (name,)

		source = Gtk.IconSource.new()
		for n in names:
			source.set_icon_name(n)
			icon_set.add_source(source)
		icon_set.names = names

	return icon_set


def device_icon_file(name, kind=None, size=_LARGE_SIZE):
	icon_set = device_icon_set(name, kind)
	assert icon_set
	theme = Gtk.IconTheme.get_default()
	for n in reversed(icon_set.names):
		if theme.has_icon(n):
			return theme.lookup_icon(n, size, 0).get_filename()


def device_icon_name(name, kind=None):
	icon_set = device_icon_set(name, kind)
	assert icon_set
	theme = Gtk.IconTheme.get_default()
	for n in reversed(icon_set.names):
		if theme.has_icon(n):
			return n


def icon_file(name, size=_LARGE_SIZE):
	theme = Gtk.IconTheme.get_default()
	if theme.has_icon(name):
		theme_icon = theme.lookup_icon(name, size, 0)
		file_name = theme_icon.get_filename()
		# print ("icon", name, "->", theme_icon, file_name)
		return file_name
