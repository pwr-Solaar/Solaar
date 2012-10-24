
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

def _pair_device(action):
	action.set_sensitive(False)
	pair_dialog = ui.pair_window.create(action, pairing.state)
	action.window.present()
	pair_dialog.set_transient_for(action.window)
	pair_dialog.set_destroy_with_parent(action.window)
	pair_dialog.set_modal(True)
	pair_dialog.present()
pair = _action('add', 'Pair new device', _pair_device)


def _unpair_device(action):
	dev = pairing.state.device(action.devnumber)
	action.devnumber = 0
	if dev:
		q = Gtk.MessageDialog.new(action.window,
									Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
									'Unpair device <b>%s</b>?', dev.name)
		if q.run() == Gtk.ResponseType.YES:
			pairing.state.unpair(dev.number)
unpair = _action('remove', 'Unpair', _unpair_device)
