#
#
#

import threading
from gi.repository import Gtk
from gi.repository import GObject

from . import constants as C
from .watcher import WatcherThread
from . import ui


def _status_updated(watcher, icon, window):
	while True:
		watcher.status_changed.wait()
		text = watcher.status_text
		watcher.status_changed.clear()

		if icon:
			GObject.idle_add(icon.set_tooltip_text, text)

		if window:
			ur_detected = watcher.has_receiver()
			devices = [ watcher.devices[k] for k in watcher.devices ] if ur_detected else []
			GObject.idle_add(ui.window.update, window, ur_detected, devices)


# def _pair_new_device(trigger, watcher):
# 	pass


def run(images_path):
	GObject.threads_init()

	ui.init(images_path)
	ui.notify.start(C.APP_TITLE, ui.image)

	watcher = WatcherThread(ui.notify.show)
	watcher.start()

	window = ui.window.create(C.APP_TITLE, ui.image)

	menu_actions = [('Scan all devices', watcher.request_all_statuses),
					# ('Pair new device', _pair_new_device, watcher),
					None,
					('Quit', Gtk.main_quit)]

	click_action = (ui.window.toggle, window) if window else None
	tray_icon = ui.icon.create(ui.image('icon'), C.APP_TITLE, menu_actions, click_action)

	ui_update_thread = threading.Thread(target=_status_updated, name='ui_update', args=(watcher, tray_icon, window))
	ui_update_thread.daemon = True
	ui_update_thread.start()

	Gtk.main()

	watcher.stop()
	ui.notify.stop()
