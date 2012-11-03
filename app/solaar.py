#!/usr/bin/env python

APPNAME = 'Solaar'
__author__  = "Daniel Pavel <daniel.pavel@gmail.com>"
__version__ = '0.7'
__license__ = "GPL"

#
#
#

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
	log_level = logging.WARNING - 10 * args.verbose
	log_format='%(asctime)s %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
	logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format)

	return args


if __name__ == '__main__':
	args = _parse_arguments()

	import ui

	# check if the notifications are available and enabled
	args.notifications &= args.systray
	if ui.notify.available and ui.notify.init(APPNAME):
		ui.action.toggle_notifications.set_active(args.notifications)
	else:
		ui.action.toggle_notifications = None

	from receiver import (ReceiverListener, DUMMY)

	window = ui.main_window.create(APPNAME,
									DUMMY.name,
									DUMMY.max_devices,
									args.systray)

	if args.systray:
		menu_actions = (ui.action.toggle_notifications,
						ui.action.about)
		icon = ui.status_icon.create(window, menu_actions)
	else:
		icon = None
		window.present()

	import pairing
	from gi.repository import Gtk, GObject

	listener = None
	notify_missing = True

	def status_changed(receiver, device=None, urgent=False):
		ui.update(receiver, icon, window, device)
		if ui.notify.available and urgent:
			ui.notify.show(device or receiver)

		global listener
		if not listener:
			GObject.timeout_add(5000, check_for_listener)
			listener = None

	def check_for_listener(retry=True):
		global listener, notify_missing

		if listener is None:
			listener = ReceiverListener.open(status_changed)
			if listener is None:
				pairing.state = None
				if notify_missing:
					status_changed(DUMMY, None, True)
					notify_missing = False
				return retry

			# print ("opened receiver", listener, listener.receiver)
			notify_missing = True
			pairing.state = pairing.State(listener)
			status_changed(listener.receiver, None, True)

	GObject.timeout_add(100, check_for_listener, False)
	Gtk.main()

	if listener is not None:
		listener.stop()

	ui.notify.uninit()
