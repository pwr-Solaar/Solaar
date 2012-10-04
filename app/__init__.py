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
			GObject.idle_add(icon.set_tooltip_markup, text)

		if window:
			GObject.idle_add(ui.window.update, window, dict(watcher.devices))


# def _pair_new_device(trigger, watcher):
# 	pass


def run():
	GObject.threads_init()

	ui.notify.start(APP_TITLE)

	watcher = WatcherThread(ui.notify.show)
	watcher.start()

	window = ui.window.create(APP_TITLE, watcher.devices[0])

	menu_actions = [('Scan all devices', watcher.full_scan),
					# ('Pair new device', _pair_new_device, watcher),
					None,
					('Quit', Gtk.main_quit)]

	tray_icon = ui.icon.create(APP_TITLE, menu_actions, (ui.window.toggle, window))

	ui_update_thread = threading.Thread(target=_status_updated, name='ui_update', args=(watcher, tray_icon, window))
	ui_update_thread.daemon = True
	ui_update_thread.start()

	Gtk.main()

	watcher.stop()
	ui.notify.stop()
