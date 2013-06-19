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
	elif reason == 'unpair':
		title = 'Unpairing failed'
		text = ('Failed to unpair device\n%s .' % object)
	else:
		raise Exception("ui.error_dialog: don't know how to handle (%s, %s)", reason, object)

	assert text
	assert text

	m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()


def error_dialog(reason, object):
	assert reason is not None
	GLib.idle_add(_error_dialog, reason, object)

#
#
#


from . import notify, tray, window

def init():
	notify.init()
	tray.init()
	window.init()

def run_loop():
	Gtk.main()

def destroy():
	tray.destroy()
	window.destroy()
	notify.uninit()


from logitech.unifying_receiver.status import ALERT
def _status_changed(device, alert, reason):
	assert device is not None
	_log.info("status changed: %s, %s, %s", device, alert, reason)

	tray.update(device)
	if alert & ALERT.ATTENTION:
		tray.attention(reason)

	need_popup = alert & (ALERT.SHOW_WINDOW | ALERT.ATTENTION)
	window.update(device, need_popup)

	if alert & ALERT.NOTIFICATION:
		notify.show(device, reason)


def status_changed(device, alert=ALERT.NONE, reason=None):
	GLib.idle_add(_status_changed, device, alert, reason)
