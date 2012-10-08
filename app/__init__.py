#
#
#

import threading
from gi.repository import Gtk
from gi.repository import GObject

from .watcher import WatcherThread
from . import ui


APP_TITLE = 'Solaar'

def _status_updated(watcher, icon, window):
	while True:
		watcher.status_changed.wait()
		text = watcher.status_text
		watcher.status_changed.clear()

		if icon:
			GObject.idle_add(ui.icon.update, icon, watcher.rstatus, text)

		if window:
			GObject.idle_add(ui.window.update, window, watcher.rstatus, dict(watcher.devices))


def run(config):
	GObject.threads_init()

	ui.notify.init(APP_TITLE, config.notifications)

	watcher = WatcherThread(ui.notify.show)
	watcher.start()

	window = ui.window.create(APP_TITLE, watcher.rstatus, not config.start_hidden, config.close_to_tray)
	tray_icon = ui.icon.create(APP_TITLE, (ui.window.toggle, window))

	ui_update_thread = threading.Thread(target=_status_updated, name='ui_update', args=(watcher, tray_icon, window))
	ui_update_thread.daemon = True
	ui_update_thread.start()

	Gtk.main()

	watcher.stop()
	ui.notify.set_active(False)
