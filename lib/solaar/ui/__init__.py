#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


from gi.repository import GLib, Gtk
GLib.threads_init()


def error_dialog(title, text):
	m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()

#
#
#

from . import status_icon
from . import notify, main_window

from . import icons
# for some reason, set_icon_name does not always work on windows
Gtk.Window.set_default_icon_name(main_window.NAME.lower())
Gtk.Window.set_default_icon_from_file(icons.icon_file(main_window.NAME.lower(), 32))
