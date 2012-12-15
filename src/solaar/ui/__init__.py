#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import GObject, Gtk
GObject.threads_init()


def error_dialog(window, title, text):
	m = Gtk.MessageDialog(window, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()


from . import notify, status_icon, main_window
