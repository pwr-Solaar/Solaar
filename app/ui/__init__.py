# pass

from . import (notify, status_icon, main_window, pair_window, action)

from gi.repository import (GObject, Gtk)
GObject.threads_init()


from solaar import NAME
_APP_ICONS = (NAME + '-fail', NAME + '-init', NAME)
def appicon(receiver_status):
	return (_APP_ICONS[0] if receiver_status < 0 else
			_APP_ICONS[1] if receiver_status < 1 else
			_APP_ICONS[2])


_ICON_THEME = Gtk.IconTheme.get_default()

def get_icon(name, fallback):
	return name if name and _ICON_THEME.has_icon(name) else fallback

def get_battery_icon(level):
	if level < 0:
		return 'battery_unknown'
	return 'battery_%03d' % (10 * ((level + 5) // 10))

def icon_file(name):
	if name and _ICON_THEME.has_icon(name):
		return _ICON_THEME.lookup_icon(name, 0, 0).get_filename()
	return None


def error(window, title, text):
	m = Gtk.MessageDialog(window, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()


def find_children(container, *child_names):
	assert container is not None

	def _iterate_children(widget, names, result, count):
		wname = widget.get_name()
		if wname in names:
			index = names.index(wname)
			names[index] = None
			result[index] = widget
			count -= 1

		if count > 0 and isinstance(widget, Gtk.Container):
			for w in widget:
				count = _iterate_children(w, names, result, count)
				if count == 0:
					break

		return count

	names = list(child_names)
	count = len(names)
	result = [None] * count
	_iterate_children(container, names, result, count)
	return tuple(result) if count > 1 else result[0]
