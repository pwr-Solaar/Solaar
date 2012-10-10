#!/usr/bin/env python

__version__ = '0.4'

#
#
#

import logging
from gi.repository import Gtk
from gi.repository import GObject

from logitech.devices import constants as C

import ui
from watcher import Watcher


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


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser(prog=APP_TITLE)
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='increase the logger verbosity')
	arg_parser.add_argument('-N', '--disable-notifications', action='store_false', dest='notifications',
							help='disable desktop notifications')
	arg_parser.add_argument('-H', '--start-hidden', action='store_true', dest='start_hidden',
							help='hide the application window on start')
	arg_parser.add_argument('-t', '--close-to-tray', action='store_true',
							help='closing the application window hides it instead of terminating the application')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	args = arg_parser.parse_args()

	log_level = logging.root.level - 10 * args.verbose
	log_format='%(asctime)s %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
	logging.basicConfig(level=log_level if log_level > 0 else 1, format=log_format)

	GObject.threads_init()

	ui.notify.init(APP_TITLE, args.notifications)

	watcher = Watcher(ui.notify.show)
	watcher.start()

	window = ui.window.create(APP_TITLE, watcher.rstatus, not args.start_hidden, args.close_to_tray)
	window.set_icon_name(APP_TITLE + '-fail')

	tray_icon = ui.icon.create(APP_TITLE, (ui.window.toggle, window))
	tray_icon.set_from_icon_name(APP_TITLE + '-fail')

	import threading
	ui_update_thread = threading.Thread(target=_status_updated, name='ui_update', args=(watcher, tray_icon, window))
	ui_update_thread.daemon = True
	ui_update_thread.start()

	Gtk.main()

	watcher.stop()
	ui.notify.set_active(False)
