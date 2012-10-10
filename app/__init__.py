#
#
#

from gi.repository import GObject

from . import ui
from logitech.devices import constants as C


APP_TITLE = 'Solaar'


def _status_updated(watcher, icon, window):
	while True:
		watcher.status_changed.wait()
		text = watcher.status_text
		watcher.status_changed.clear()

		icon_name = APP_TITLE + '-fail' if watcher.rstatus.code < C.STATUS.CONNECTED else APP_TITLE

		if icon:
			GObject.idle_add(ui.icon.update, icon, watcher.rstatus, text, icon_name)

		if window:
			GObject.idle_add(ui.window.update, window, watcher.rstatus, dict(watcher.devices), icon_name)


def run(config):
	GObject.threads_init()

	ui.notify.init(APP_TITLE, config.notifications)

	from .watcher import WatcherThread
	watcher = WatcherThread(ui.notify.show)
	watcher.start()

	window = ui.window.create(APP_TITLE, watcher.rstatus, not config.start_hidden, config.close_to_tray)
	window.set_icon_name(APP_TITLE + '-fail')

	tray_icon = ui.icon.create(APP_TITLE, (ui.window.toggle, window))
	tray_icon.set_from_icon_name(APP_TITLE + '-fail')

	import threading
	ui_update_thread = threading.Thread(target=_status_updated, name='ui_update', args=(watcher, tray_icon, window))
	ui_update_thread.daemon = True
	ui_update_thread.start()

	from gi.repository import Gtk
	Gtk.main()

	watcher.stop()
	ui.notify.set_active(False)
