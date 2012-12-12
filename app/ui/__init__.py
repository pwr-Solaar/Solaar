#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import GObject, Gtk
GObject.threads_init()

_LARGE_SIZE = 64
Gtk.IconSize.LARGE = Gtk.icon_size_register('large', _LARGE_SIZE, _LARGE_SIZE)
# Gtk.IconSize.XLARGE = Gtk.icon_size_register('x-large', _LARGE_SIZE * 2, _LARGE_SIZE * 2)

from . import notify, status_icon, main_window, pair_window, action

from solaar import NAME
_APP_ICONS = (NAME + '-init', NAME + '-fail', NAME)
def appicon(receiver_status):
	return (_APP_ICONS[1] if isinstance(receiver_status, basestring)
			else _APP_ICONS[2] if receiver_status
			else _APP_ICONS[0])


def get_battery_icon(level):
	if level < 0:
		return 'battery_unknown'
	return 'battery_%03d' % (10 * ((level + 5) // 10))


_ICON_SETS = {}

def device_icon_set(name, kind=None):
	icon_set = _ICON_SETS.get(name)
	if icon_set is None:
		icon_set = Gtk.IconSet.new()
		_ICON_SETS[name] = icon_set

		names = ['preferences-desktop-peripherals']
		if kind:
			if str(kind) == 'numpad':
				names += ('input-dialpad',)
			elif str(kind) == 'touchpad':
				names += ('input-tablet',)
			elif str(kind) == 'trackball':
				names += ('input-mouse',)
			names += ('input-' + str(kind),)

		theme = Gtk.IconTheme.get_default()
		if theme.has_icon(name):
			names += (name,)

		source = Gtk.IconSource.new()
		for n in names:
			source.set_icon_name(n)
			icon_set.add_source(source)
		icon_set.names = names

	return icon_set


def device_icon_file(name, kind=None):
	icon_set = device_icon_set(name, kind)
	assert icon_set
	theme = Gtk.IconTheme.get_default()
	for n in reversed(icon_set.names):
		if theme.has_icon(n):
			return theme.lookup_icon(n, _LARGE_SIZE, 0).get_filename()


def icon_file(name, size=_LARGE_SIZE):
	theme = Gtk.IconTheme.get_default()
	if theme.has_icon(name):
		return theme.lookup_icon(name, size, 0).get_filename()


def error(window, title, text):
	m = Gtk.MessageDialog(window, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()


# def find_children(container, *child_names):
# 	assert container is not None
# 	assert isinstance(container, Gtk.Container)
#
# 	def _iterate_children(widget, names, result, count):
# 		assert isinstance(widget, Gtk.Widget)
# 		wname = widget.get_name()
# 		if wname in names:
# 			index = names.index(wname)
# 			names[index] = None
# 			result[index] = widget
# 			count -= 1
#
# 		if count > 0 and isinstance(widget, Gtk.Container):
# 			for w in widget:
# 				# assert isinstance(w, Gtk.Widget):
# 				count = _iterate_children(w, names, result, count)
# 				if count == 0:
# 					break
#
# 		return count
#
# 	names = list(child_names)
# 	count = len(names)
# 	result = [None] * count
# 	if _iterate_children(container, names, result, count) > 0:
# 		# some children could not be found
# 		pass
# 	return tuple(result) if count > 1 else result[0]
