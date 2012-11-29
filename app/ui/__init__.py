# pass

from . import (notify, status_icon, main_window, pair_window, action)

from gi.repository import (GObject, Gtk)
GObject.threads_init()


from solaar import NAME
_APP_ICONS = (NAME + '-init', NAME + '-fail', NAME)
def appicon(receiver_status):
	return (_APP_ICONS[1] if type(receiver_status) == str
			else _APP_ICONS[2] if receiver_status
			else _APP_ICONS[0])



def get_icon(name, *fallback):
	theme = Gtk.IconTheme.get_default()
	return (str(name) if name and theme.has_icon(str(name))
			else get_icon(*fallback) if fallback
			else None)

def get_battery_icon(level):
	if level < 0:
		return 'battery_unknown'
	return 'battery_%03d' % (10 * ((level + 5) // 10))

def icon_file(name):
	theme = Gtk.IconTheme.get_default()
	return (theme.lookup_icon(str(name), 0, 0).get_filename() if name and theme.has_icon(str(name))
			else None)


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
