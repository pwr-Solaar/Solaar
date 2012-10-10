#
#
#

from gi.repository import Gtk


def create(parent_window, title):
	window = Gtk.Dialog(title, parent_window, Gtk.DialogFlags.MODAL, buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))

	Gtk.Window.set_default_icon_name('add')
	window.set_resizable(False)

	# window.set_wmclass(title, 'status-window')
	# window.set_role('pair')

	return window
