
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


def _pair_device(action, window, state):
	action.set_sensitive(False)
	pair_dialog = ui.pair_window.create(action, state)
	# window.present()
	# pair_dialog.set_transient_for(parent_window)
	# pair_dialog.set_destroy_with_parent(parent_window)
	# pair_dialog.set_modal(True)
	pair_dialog.present()
pair = _action('add', 'Pair new device', None)
