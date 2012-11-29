#
#
#

# from sys import version as PYTTHON_VERSION
from gi.repository import (Gtk, Gdk)

import ui
from solaar import NAME as _NAME
from solaar import VERSION as _VERSION


def _action(name, label, function, *args):
	action = Gtk.Action(name, label, label, None)
	action.set_icon_name(name)
	if function:
		action.connect('activate', function, *args)
	return action


def _toggle_action(name, label, function, *args):
	action = Gtk.ToggleAction(name, label, label, None)
	action.set_icon_name(name)
	action.connect('activate', function, *args)
	return action

#
#
#

def _toggle_notifications(action):
	if action.get_active():
		ui.notify.init(_NAME)
	else:
		ui.notify.uninit()
	action.set_sensitive(ui.notify.available)
toggle_notifications = _toggle_action('notifications', 'Notifications', _toggle_notifications)


def _show_about_window(action):
	about = Gtk.AboutDialog()

	about.set_icon_name(_NAME)
	about.set_program_name(_NAME)
	about.set_logo_icon_name(_NAME)
	about.set_version(_VERSION)
	about.set_comments('Shows status of devices connected\nto a Logitech Unifying Receiver.')

	about.set_license_type(Gtk.License.GPL_2_0)
	about.set_copyright(b'\xC2\xA9'.decode('utf-8') + ' 2012 Daniel Pavel')

	about.set_authors(('Daniel Pavel http://github.com/pwr',))
	try:
		about.add_credit_section('Testing', ('Douglas Wagner',))
	except Exception:
		pass

	about.set_website('http://github.com/pwr/Solaar/wiki')
	about.set_website_label('Solaar Wiki')

	about.run()
	about.destroy()
about = _action('help-about', 'About ' + _NAME, _show_about_window)

quit = _action('exit', 'Quit', Gtk.main_quit)

#
#
#

def _pair_device(action, frame):
	window = frame.get_toplevel()

	pair_dialog = ui.pair_window.create(action, frame._device)
	pair_dialog.set_transient_for(window)
	pair_dialog.set_modal(True)
	pair_dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)
	pair_dialog.set_position(Gtk.WindowPosition.CENTER)
	pair_dialog.present()

def pair(frame):
	return _action('add', 'Pair new device', _pair_device, frame)


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
			ui.error(window, 'Unpairing failed', 'Failed to unpair device\n%s .' % device.name)

def unpair(frame):
	return _action('remove', 'Unpair', _unpair_device, frame)
