#!/usr/bin/env python

NAME = 'Solaar'
VERSION = '0.7.3'
__author__  = "Daniel Pavel <daniel.pavel@gmail.com>"
__version__ = VERSION
__license__ = "GPL"

#
#
#

def _parse_arguments():
	import argparse
	arg_parser = argparse.ArgumentParser(prog=NAME.lower())
	arg_parser.add_argument('-q', '--quiet',
							action='store_true',
							help='disable all logging, takes precedence over --verbose')
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
	if args.quiet:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.CRITICAL)
	else:
		log_level = logging.WARNING - 10 * args.verbose
		log_format='%(asctime)s %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format)

	return args


def _check_requirements():
	try:
		import pyudev
	except ImportError:
		return 'python-pyudev'

	try:
		import gi.repository
	except ImportError:
		return 'python-gi'

	try:
		from gi.repository import Gtk
	except ImportError:
		return 'gir1.2-gtk-3.0'


if __name__ == '__main__':
	args = _parse_arguments()

	req_fail = _check_requirements()
	if req_fail:
		raise ImportError('missing required package: %s' % req_fail)

	import ui

	# check if the notifications are available and enabled
	args.notifications &= args.systray
	if ui.notify.available and ui.notify.init(NAME):
		ui.action.toggle_notifications.set_active(args.notifications)
	else:
		ui.action.toggle_notifications = None

	from receiver import DUMMY
	window = ui.main_window.create(NAME, DUMMY.name, DUMMY.max_devices, args.systray)
	if args.systray:
		menu_actions = (ui.action.toggle_notifications,
						ui.action.about)
		icon = ui.status_icon.create(window, menu_actions)
	else:
		icon = None
		window.present()

	import pairing
	from logitech.devices.constants import STATUS
	from gi.repository import Gtk, GObject

	listener = None
	notify_missing = True

	def status_changed(receiver, device=None, ui_flags=0):
		ui.update(receiver, icon, window, device)
		if ui_flags & STATUS.UI_POPUP:
			window.present()

		if ui_flags & STATUS.UI_NOTIFY and ui.notify.available:
			GObject.idle_add(ui.notify.show, device or receiver)

		global listener
		if not listener:
			GObject.timeout_add(5000, check_for_listener)
			listener = None

	from receiver import ReceiverListener
	def check_for_listener(retry=True):
		def _check_still_scanning(listener):
			if listener.receiver.status == STATUS.BOOTING:
				listener.change_status(STATUS.CONNECTED)

		global listener, notify_missing
		if listener is None:
			try:
				listener = ReceiverListener.open(status_changed)
			except OSError:
				ui.error(window, 'Permissions error',
						'Found a possible Unifying Receiver device,\n'
						'but did not have permission to open it.')

			if listener is None:
				pairing.state = None
				if notify_missing:
					status_changed(DUMMY, None, STATUS.UI_NOTIFY)
					notify_missing = False
				return retry

			# print ("opened receiver", listener, listener.receiver)
			notify_missing = True
			pairing.state = pairing.State(listener)
			status_changed(listener.receiver, None, STATUS.UI_NOTIFY)
			listener.trigger_device_events()
			GObject.timeout_add(5 * 1000, _check_still_scanning, listener)

	GObject.timeout_add(50, check_for_listener, False)
	Gtk.main()

	if listener is not None:
		listener.stop()

	ui.notify.uninit()
