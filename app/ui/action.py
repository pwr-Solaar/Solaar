
from gi.repository import Gtk

import ui


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


def wrap_action(action, prefire):
	def _wrap(aw, aa):
		prefire(aa)
		aa.activate()
	wrapper = _action(action.get_name(), action.get_label(), None)
	wrapper.set_icon_name(action.get_icon_name())
	wrapper.connect('activate', _wrap, action)
	return wrapper

#
#
#

def _toggle_notifications(action):
	if action.get_active():
		ui.notify.init(ui.APPNAME)
	else:
		ui.notify.uninit()
	action.set_sensitive(ui.notify.available)
toggle_notifications = _toggle_action('notifications', 'Notifications', _toggle_notifications)


def _show_about_window(action):
	about = Gtk.AboutDialog()
	about.set_icon_name(ui.APPNAME)
	about.set_program_name(ui.APPNAME)
	about.set_logo_icon_name(ui.APPNAME)
	about.set_version(ui.APPVERSION)
	about.set_license_type(Gtk.License.GPL_2_0)
	about.set_authors(('Daniel Pavel http://github.com/pwr', ))
	about.set_website('http://github.com/pwr/Solaar/wiki')
	about.run()
	about.destroy()
about = _action('help-about', 'About ' + ui.APPNAME, _show_about_window)

quit = _action('exit', 'Quit', Gtk.main_quit)

#
#
#

import pairing

def _pair_device(action, frame):
	window = frame.get_toplevel()

	pair_dialog = ui.pair_window.create( action, pairing.state)
	pair_dialog.set_transient_for(window)
	pair_dialog.set_modal(True)

	window.present()
	pair_dialog.present()

def pair(frame):
	return _action('add', 'Pair new device', _pair_device, frame)


def _unpair_device(action, frame):
	window = frame.get_toplevel()
	window.present()
	device = frame._device
	qdialog = Gtk.MessageDialog(window, 0,
								Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
								"Unpair device\n%s ?" % device.name)
	choice = qdialog.run()
	qdialog.destroy()
	if choice == Gtk.ResponseType.YES:
		pairing.state.unpair(device)

def unpair(frame):
	return _action('remove', 'Unpair', _unpair_device, frame)
