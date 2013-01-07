#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk, Gdk

from . import notify, pair_window
from ..ui import error_dialog


_NAME = 'Solaar'
from solaar import __version__


def make(name, label, function, *args):
	action = Gtk.Action(name, label, label, None)
	action.set_icon_name(name)
	if function:
		action.connect('activate', function, *args)
	return action


def make_toggle(name, label, function, *args):
	action = Gtk.ToggleAction(name, label, label, None)
	action.set_icon_name(name)
	action.connect('activate', function, *args)
	return action

#
#
#

def _toggle_notifications(action):
	if action.get_active():
		notify.init('Solaar')
	else:
		notify.uninit()
	action.set_sensitive(notify.available)
toggle_notifications = make_toggle('notifications', 'Notifications', _toggle_notifications)


def _show_about_window(action):
	about = Gtk.AboutDialog()

	about.set_icon_name(_NAME.lower())
	about.set_program_name(_NAME)
	about.set_logo_icon_name(_NAME.lower())
	about.set_version(__version__)
	about.set_comments('Shows status of devices connected\nto a Logitech Unifying Receiver.')

	about.set_copyright(b'\xC2\xA9'.decode('utf-8') + ' 2012 Daniel Pavel')
	about.set_license_type(Gtk.License.GPL_2_0)

	about.set_authors(('Daniel Pavel http://github.com/pwr',))
	try:
		about.add_credit_section('Testing', ('Douglas Wagner', 'Julien Gascard'))
		about.add_credit_section('Technical specifications\nprovided by',
						('Julien Danjou http://julien.danjou.info/blog/2012/logitech-unifying-upower',))
	except TypeError:
		# gtk3 < 3.6 has incorrect gi bindings
		pass
	except:
		# is the Gtk3 version too old?
		pass

	about.set_website('http://pwr.github.com/Solaar/')
	about.set_website_label('Solaar')

	about.run()
	about.destroy()
about = make('help-about', 'About ' + _NAME, _show_about_window)

quit = make('exit', 'Quit', Gtk.main_quit)

#
#
#

def _pair_device(action, frame):
	window = frame.get_toplevel()

	pair_dialog = pair_window.create(action, frame._device)
	pair_dialog.set_transient_for(window)
	pair_dialog.set_destroy_with_parent(True)
	pair_dialog.set_modal(True)
	pair_dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)
	pair_dialog.set_position(Gtk.WindowPosition.CENTER)
	pair_dialog.present()

def pair(frame):
	return make('list-add', 'Pair new device', _pair_device, frame)


def _unpair_device(action, frame):
	window = frame.get_toplevel()
	# window.present()
	device = frame._device
	qdialog = Gtk.MessageDialog(window, 0,
								Gtk.MessageType.QUESTION, Gtk.ButtonsType.NONE,
								"Unpair device\n%s ?" % device.name)
	qdialog.set_icon_name('remove')
	qdialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
	qdialog.add_button('Unpair', Gtk.ResponseType.ACCEPT)
	choice = qdialog.run()
	qdialog.destroy()
	if choice == Gtk.ResponseType.ACCEPT:
		try:
			del device.receiver[device.number]
		except:
			error_dialog(window, 'Unpairing failed', 'Failed to unpair device\n%s .' % device.name)

def unpair(frame):
	return make('edit-delete', 'Unpair', _unpair_device, frame)
