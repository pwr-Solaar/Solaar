#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


from gi.repository import GLib, Gtk
GLib.threads_init()

async = GLib.idle_add
run_loop = Gtk.main

def error_dialog(reason, object):
	if reason == 'permissions':
		title = 'Permissions error'
		text = ('Found a Logitech Receiver (%s), but did not have permission to open it.\n'
				'\n'
				'If you\'ve just installed Solaar, try removing the receiver\n'
				'and plugging it back in.' % object)
	else:
		raise Exception("ui.error_dialog: don't know how to handle (%s, %s)", reason, object)

	def _show_dialog(d):
		d.run()
		d.destroy()

	m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	async(_show_dialog, m)

#
#
#

from . import status_icon
from . import notify, main_window

from . import icons
# for some reason, set_icon_name does not always work on windows
Gtk.Window.set_default_icon_name(main_window.NAME.lower())
Gtk.Window.set_default_icon_from_file(icons.icon_file(main_window.NAME.lower(), 32))
