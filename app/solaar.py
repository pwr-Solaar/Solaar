#!/usr/bin/env python

__author__  = "Daniel Pavel <daniel.pavel@gmail.com>"
__version__ = '0.5'
__license__ = "GPL"

#
#
#

APPNAME = 'Solaar'


def _parse_arguments():
	import argparse
	arg_parser = argparse.ArgumentParser(prog=APPNAME.lower())
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
	logging.basicConfig(level=log_level if log_level > 0 else 1,
						format=log_format,
						datefmt='%H:%M:%S')

	return args


if __name__ == '__main__':
	args = _parse_arguments()

	import ui

	# check if the notifications are available
	args.notifications &= args.systray
	if ui.notify.init(APPNAME):
		ui.action.toggle_notifications.set_active(args.notifications)
	else:
		ui.action.toggle_notifications = None

	import watcher

	window = ui.main_window.create(APPNAME,
									watcher.DUMMY.NAME,
									watcher.DUMMY.max_devices,
									args.systray)
	ui.action.pair.window = window
	ui.action.unpair.window = window

	if args.systray:
		menu_actions = (ui.action.pair,
						ui.action.toggle_notifications,
						ui.action.about)
		icon = ui.status_icon.create(window, menu_actions)
	else:
		icon = None
		window.present()

	w = watcher.Watcher(APPNAME,
						lambda r: ui.update(r, icon, window),
						ui.notify.show if ui.notify.available else None)
	w.start()

	import pairing
	pairing.state = pairing.State(w)

	from gi.repository import Gtk
	Gtk.main()

	w.stop()
	ui.notify.uninit()
