#!/usr/bin/env python -u

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


def _require(module, package):
	try:
		__import__(module)
	except ImportError:
		import sys
		sys.exit("%s: missing required package '%s'" % (NAME, package))


if __name__ == '__main__':
	_require('pyudev', 'python-pyudev')
	_require('gi.repository', 'python-gi')
	_require('gi.repository.Gtk', 'gir1.2-gtk-3.0')

	args = _parse_arguments()

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
		assert receiver is not None
		if window:
			GObject.idle_add(ui.main_window.update, window, receiver, device)
		if icon:
			GObject.idle_add(ui.status_icon.update, icon, receiver)
		if ui_flags & STATUS.UI_POPUP:
			GObject.idle_add(window.popup, icon)

		if device is None:
			# always notify on receiver updates
			ui_flags |= STATUS.UI_NOTIFY
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
			status_changed(listener.receiver, None, STATUS.UI_NOTIFY)
			GObject.timeout_add(3 * 1000, _check_still_scanning, listener)
			pairing.state = pairing.State(listener)
			listener.trigger_device_events()

	_DEVICE_TIMEOUT = 3 * 60  # seconds
	_DEVICE_STATUS_CHECK = 30  # seconds
	from time import time as _timestamp

	def check_for_inactive_devices():
		if listener and listener.receiver:
			for dev in listener.receiver.devices.values():
				if (dev.status < STATUS.CONNECTED and
					dev.props and
					_timestamp() - dev.status_updated > _DEVICE_TIMEOUT):
					dev.props.clear()
					status_changed(listener.receiver, dev)
		return True

	GObject.timeout_add(50, check_for_listener, False)
	GObject.timeout_add(_DEVICE_STATUS_CHECK * 1000, check_for_inactive_devices)
	Gtk.main()

	if listener is not None:
		listener.stop()

	ui.notify.uninit()
