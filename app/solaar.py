#!/usr/bin/env python

__version__ = '0.5'

#
#
#

APP_TITLE = 'Solaar'


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser(prog=APP_TITLE)
	arg_parser.add_argument('-v', '--verbose',
							action='count', default=0,
							help='increase the logger verbosity (may be repeated)')
	arg_parser.add_argument('-S', '--no-systray',
							action='store_false',
							dest='systray',
							help='don\'t embed the application window into the systray')
	arg_parser.add_argument('-N', '--no-notifications',
							action='store_false',
							dest='notifications',
							help='disable desktop notifications (shown only when in systray)')
	arg_parser.add_argument('-V', '--version',
							action='version',
							version='%(prog)s ' + __version__)
	args = arg_parser.parse_args()

	import logging
	log_level = logging.root.level - 10 * args.verbose
	log_format='%(asctime)s.%(msecs)03d %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
	logging.basicConfig(level=log_level if log_level > 0 else 1, format=log_format, datefmt='%H:%M:%S')

	from gi.repository import GObject
	GObject.threads_init()

	import ui

	args.notifications &= args.systray
	if args.notifications:
		args.notifications &= ui.notify.init(APP_TITLE)

	import watcher
	tray_icon = None
	window = ui.window.create(APP_TITLE,
								watcher.DUMMY.NAME,
								watcher.DUMMY.max_devices,
								args.systray)
	window.set_icon_name(APP_TITLE + '-init')

	def _ui_update(receiver, tray_icon, window):
		icon_name = APP_TITLE + '-fail' if receiver.status < 1 else APP_TITLE
		if window:
			GObject.idle_add(ui.window.update, window, receiver, icon_name)
		if tray_icon:
			GObject.idle_add(ui.icon.update, tray_icon, receiver, icon_name)

	def _notify(device):
		GObject.idle_add(ui.notify.show, device)

	w = watcher.Watcher(APP_TITLE,
						lambda r: _ui_update(r, tray_icon, window),
						_notify if args.notifications else None)
	w.start()

	if args.systray:
		def _toggle_notifications(item):
			# logging.debug("toggle notifications %s", item)
			if ui.notify.available:
				if item.get_active():
					ui.notify.init(APP_TITLE)
				else:
					ui.notify.uninit()
			item.set_sensitive(ui.notify.available)

		menu = (
				('Notifications', _toggle_notifications if args.notifications else None, args.notifications),
				)

		tray_icon = ui.icon.create(APP_TITLE, (ui.window.toggle, window), menu)
		tray_icon.set_from_icon_name(APP_TITLE + '-init')
	else:
		window.present()

	from gi.repository import Gtk
	Gtk.main()

	w.stop()
	ui.notify.uninit()
