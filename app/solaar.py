#!/usr/bin/env python

__version__ = '0.4'

#
#
#

import logging
from gi.repository import (Gtk, GObject)

from logitech.devices import constants as C

import ui


APP_TITLE = 'Solaar'


def _status_check(watcher, tray_icon, window):
	last_text = None

	while True:
		watcher.status_changed.wait()
		watcher.status_changed.clear()

		if watcher.devices:
			lines = []
			if watcher.rstatus.code < C.STATUS.CONNECTED:
				lines += (watcher.rstatus.text, '')

			devstatuses = [watcher.devices[d] for d in range(1, 1 + watcher.rstatus.max_devices) if d in watcher.devices]
			for devstatus in devstatuses:
				if devstatus.text:
					if ' ' in devstatus.text:
						lines += ('<b>' + devstatus.name + '</b>', '      ' + devstatus.text)
					else:
						lines.append('<b>' + devstatus.name + '</b> ' + devstatus.text)
				else:
					lines.append('<b>' + devstatus.name + '</b>')
				lines.append('')

			text = '\n'.join(lines).rstrip('\n')
		else:
			text = watcher.rstatus.text

		if text != last_text:
			last_text = text
			icon_name = APP_TITLE + '-fail' if watcher.rstatus.code < C.STATUS.CONNECTED else APP_TITLE

			if tray_icon:
				GObject.idle_add(ui.icon.update, tray_icon, watcher.rstatus, text, icon_name)

			if window:
				GObject.idle_add(ui.window.update, window, watcher.rstatus, watcher.devices, icon_name)


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

	from watcher import Watcher
	watcher = Watcher(APP_TITLE, ui.notify.show if args.notifications else None)
	watcher.start()

	window = ui.window.create(APP_TITLE, watcher.rstatus, args.systray)
	window.set_icon_name(APP_TITLE + '-fail')

	if args.systray:
		tray_icon = ui.icon.create(APP_TITLE, (ui.window.toggle, window))
		tray_icon.set_from_icon_name(APP_TITLE + '-fail')
	else:
		tray_icon = None
		window.present()

	from threading import Thread
	status_check = Thread(group=APP_TITLE, name='StatusCheck', target=_status_check, args=(watcher, tray_icon, window))
	status_check.daemon = True
	status_check.start()

	Gtk.main()

	watcher.stop()
	ui.notify.set_active(False)
