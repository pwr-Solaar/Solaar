#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


from logging import getLogger, DEBUG as _DEBUG, INFO as _INFO
_log = getLogger(__name__)
del getLogger

from gi.repository import GLib, Gtk
GLib.threads_init()

#
#
#

def _init_application():
	app = Gtk.Application.new('io.github.pwr.solaar', 0)
	# not sure this is necessary...
	# app.set_property('register-session', True)
	registered = app.register(None)
	if _log.isEnabledFor(_INFO):
		_log.info("application %s, registered %s", app.get_dbus_object_path(), registered)
	# assert registered, "failed to register unique application %s" % app

	# if there is already a running instance, bail out
	if app.get_is_remote():
		# pop up the window in the other instance
		app.activate()
		raise Exception("already running")

	return app

application = _init_application()

#
#
#

def _error_dialog(reason, object):
	_log.error("error: %s %s", reason, object)

	if reason == 'permissions':
		title = 'Permissions error'
		text = ('Found a Logitech Receiver (%s), but did not have permission to open it.\n'
				'\n'
				'If you\'ve just installed Solaar, try removing the receiver\n'
				'and plugging it back in.' % object)
	elif reason == 'unpair':
		title = 'Unpairing failed'
		text = ('Failed to unpair %s from %s.\n'
				'\n'
				'The receiver returned an error, with no further details.'
				% (object.name, object.receiver.name))
	else:
		raise Exception("ui.error_dialog: don't know how to handle (%s, %s)", reason, object)

	assert title
	assert text

	m = Gtk.MessageDialog(None, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, text)
	m.set_title(title)
	m.run()
	m.destroy()


def error_dialog(reason, object):
	assert reason is not None
	GLib.idle_add(_error_dialog, reason, object)

#
# A separate thread is used to read/write from the device
# so as not to block the main (GUI) thread.
#

try:
	from Queue import Queue
except ImportError:
	from queue import Queue
_task_queue = Queue(16)
del Queue


from threading import Thread, current_thread as _current_thread

def _process_async_queue():
	t = _current_thread()
	t.alive = True
	while t.alive:
		function, args, kwargs = _task_queue.get()
		if function:
			function(*args, **kwargs)
	if _log.isEnabledFor(_DEBUG):
		_log.debug("stopped")

_queue_processor = Thread(name='AsyncUI', target=_process_async_queue)
_queue_processor.daemon = True
_queue_processor.alive = False
_queue_processor.start()

del Thread

def async(function, *args, **kwargs):
	task = (function, args, kwargs)
	_task_queue.put(task)

#
#
#

from . import notify, tray, window

def init():
	notify.init()
	tray.init(lambda _ignore: window.destroy())
	window.init()

def run_loop():
	def _activate(app):
		assert app == application
		if app.get_windows():
			window.popup()
		else:
			app.add_window(window._window)

	def _shutdown(app):
		# stop the async UI processor
		_queue_processor.alive = False
		async(None)

		tray.destroy()
		notify.uninit()

	application.connect('activate', _activate)
	application.connect('shutdown', _shutdown)
	application.run(None)

#
#
#

from logitech_receiver.status import ALERT
def _status_changed(device, alert, reason):
	assert device is not None
	if _log.isEnabledFor(_DEBUG):
		_log.debug("status changed: %s (%s) %s", device, alert, reason)

	tray.update(device)
	if alert & ALERT.ATTENTION:
		tray.attention(reason)

	need_popup = alert & (ALERT.SHOW_WINDOW | ALERT.ATTENTION)
	window.update(device, need_popup)

	if alert & ALERT.NOTIFICATION:
		notify.show(device, reason)


def status_changed(device, alert=ALERT.NONE, reason=None):
	GLib.idle_add(_status_changed, device, alert, reason)
