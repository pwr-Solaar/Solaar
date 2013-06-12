#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


from logging import getLogger, DEBUG as _DEBUG
_log = getLogger(__name__)
del getLogger

from gi.repository import GLib, Gtk
GLib.threads_init()


def _error_dialog(reason, object):
	if reason == 'permissions':
		title = 'Permissions error'
		text = ('Found a Logitech Receiver (%s), but did not have permission to open it.\n'
				'\n'
				'If you\'ve just installed Solaar, try removing the receiver\n'
				'and plugging it back in.' % object)
	else:
		raise Exception("ui.error_dialog: don't know how to handle (%s, %s)", reason, object)

	m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()

def error_dialog(reason, object):
	GLib.idle_add(_error_dialog, reason, object)

#
#
#

_tray_icon = None

def init():
	notify.init()

	global _tray_icon
	_tray_icon = status_icon.create(main_window.toggle_all, main_window.popup)
	assert _tray_icon

def run_loop():
	global _tray_icon
	Gtk.main()
	t, _tray_icon = _tray_icon, None
	status_icon.destroy(t)
	notify.uninit()

from logitech.unifying_receiver.status import ALERT
def _status_changed(device, alert, reason):
	assert device is not None
	if _log.isEnabledFor(_DEBUG):
		_log.debug("status changed: %s, %s, %s", device, alert, reason)

	status_icon.update(_tray_icon, device)
	if alert & ALERT.ATTENTION:
		status_icon.attention(_tray_icon, reason)

	need_popup = alert & (ALERT.SHOW_WINDOW | ALERT.ATTENTION)
	main_window.update(device, need_popup, _tray_icon)

	if alert & ALERT.NOTIFICATION:
		notify.show(device, reason)

def status_changed(device, alert=ALERT.NONE, reason=None):
	GLib.idle_add(_status_changed, device, alert, reason)

#
#
#

from . import status_icon
from . import notify, main_window

from . import icons
# for some reason, set_icon_name does not always work on windows
Gtk.Window.set_default_icon_name(main_window.NAME.lower())
Gtk.Window.set_default_icon_from_file(icons.icon_file(main_window.NAME.lower(), 32))
