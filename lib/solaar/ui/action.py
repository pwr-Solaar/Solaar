#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from gi.repository import Gtk, Gdk

# from logging import getLogger
# _log = getLogger(__name__)
# del getLogger


from solaar.i18n import _

#
#
#

def make(name, label, function, stock_id=None, *args):
	action = Gtk.Action(name, label, label, None)
	action.set_icon_name(name)
	if stock_id is not None:
		action.set_stock_id(stock_id)
	if function:
		action.connect('activate', function, *args)
	return action


def make_toggle(name, label, function, stock_id=None, *args):
	action = Gtk.ToggleAction(name, label, label, None)
	action.set_icon_name(name)
	if stock_id is not None:
		action.set_stock_id(stock_id)
	action.connect('activate', function, *args)
	return action

#
#
#

# def _toggle_notifications(action):
# 	if action.get_active():
# 		notify.init('Solaar')
# 	else:
# 		notify.uninit()
# 	action.set_sensitive(notify.available)
# toggle_notifications = make_toggle('notifications', 'Notifications', _toggle_notifications)


from .about import show_window as _show_about_window
from solaar import NAME
about = make('help-about', _("About") + ' ' + NAME, _show_about_window, stock_id=Gtk.STOCK_ABOUT)

#
#
#

from . import pair_window
def pair(window, receiver):
	assert receiver
	assert receiver.kind is None

	pair_dialog = pair_window.create(receiver)
	pair_dialog.set_transient_for(window)
	pair_dialog.set_destroy_with_parent(True)
	pair_dialog.set_modal(True)
	pair_dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)
	pair_dialog.set_position(Gtk.WindowPosition.CENTER)
	pair_dialog.present()


from ..ui import error_dialog
def unpair(window, device):
	assert device
	assert device.kind is not None

	qdialog = Gtk.MessageDialog(window, 0,
								Gtk.MessageType.QUESTION, Gtk.ButtonsType.NONE,
								_("Unpair") + ' ' + device.name + ' ?')
	qdialog.set_icon_name('remove')
	qdialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
	qdialog.add_button(_("Unpair"), Gtk.ResponseType.ACCEPT)
	choice = qdialog.run()
	qdialog.destroy()
	if choice == Gtk.ResponseType.ACCEPT:
		receiver = device.receiver
		assert receiver
		device_number = device.number

		try:
			del receiver[device_number]
		except:
			# _log.exception("unpairing %s", device)
			error_dialog('unpair', device)
