#!/usr/bin/env python

__version__ = '0.4'

#
#
#

import logging
from gi.repository import (Gtk, GObject)

from logitech.devices import constants as C

import ui
from watcher import Watcher


APP_TITLE = 'Solaar'


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser(prog=APP_TITLE)
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='increase the logger verbosity (may be repeated)')
	arg_parser.add_argument('-S', '--no-systray', action='store_false', dest='systray',
							help='embed the application into the systray')
	arg_parser.add_argument('-N', '--no-notifications', action='store_false', dest='notifications',
							help='disable desktop notifications (if systray is enabled)')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	args = arg_parser.parse_args()

	log_level = logging.root.level - 10 * args.verbose
	log_format='%(asctime)s %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
	logging.basicConfig(level=log_level if log_level > 0 else 1, format=log_format)

	GObject.threads_init()

	args.notifications &= args.systray
	if args.notifications:
		ui.notify.init(APP_TITLE)

	tray_icon = None
	window = None

	def _status_changed(text, rstatus, devices):
		icon_name = APP_TITLE + '-fail' if rstatus.code < C.STATUS.CONNECTED else APP_TITLE

		if tray_icon:
			GObject.idle_add(ui.icon.update, tray_icon, rstatus, text, icon_name)

		if window:
			GObject.idle_add(ui.window.update, window, rstatus, devices, icon_name)

	watcher = Watcher(_status_changed, ui.notify.show if args.notifications else None)
	watcher.start()

	window = ui.window.create(APP_TITLE, watcher.rstatus, args.systray)
	window.set_icon_name(APP_TITLE + '-fail')

	if args.systray:
		tray_icon = ui.icon.create(APP_TITLE, (ui.window.toggle, window))
		tray_icon.set_from_icon_name(APP_TITLE + '-fail')
	else:
		window.present()

	Gtk.main()

	watcher.stop()
	ui.notify.set_active(False)
