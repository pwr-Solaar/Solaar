#!/usr/bin/env python -u

NAME = 'Solaar'
VERSION = '0.8.2'
__author__  = "Daniel Pavel <daniel.pavel@gmail.com>"
__version__ = VERSION
__license__ = "GPL"

#
#
#

def _require(module, os_package):
	try:
		__import__(module)
	except ImportError:
		import sys
		sys.exit("%s: missing required package '%s'" % (NAME, os_package))


def _parse_arguments():
	import argparse
	arg_parser = argparse.ArgumentParser(prog=NAME.lower())
	arg_parser.add_argument('-S', '--no-systray', action='store_false', dest='systray',
							help='don\'t embed the application window into the systray')
	arg_parser.add_argument('-N', '--no-notifications', action='store_false', dest='notifications',
							help='disable desktop notifications (shown only when in systray)')
	arg_parser.add_argument('-d', '--debug', action='count', default=0,
							help='print logging messages, for debugging purposes (may be repeated for extra verbosity)')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	args = arg_parser.parse_args()

	import logging
	if args.debug > 0:
		log_level = logging.WARNING - 10 * args.debug
		log_format='%(asctime)s %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format)
	else:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.CRITICAL)

	return args


def _run(args):
	import ui

	# even if --no-notifications is given on the command line, still have to
	# check they are available, and decide whether to put the option in the
	# systray icon
	args.notifications &= args.systray
	if args.systray and ui.notify.init(NAME):
		ui.action.toggle_notifications.set_active(args.notifications)
		if not args.notifications:
			ui.notify.uninit()
	else:
		ui.action.toggle_notifications = None

	from listener import DUMMY
	window = ui.main_window.create(NAME, DUMMY.name, DUMMY.max_devices, args.systray)
	if args.systray:
		menu_actions = (ui.action.toggle_notifications,
						ui.action.about)
		icon = ui.status_icon.create(window, menu_actions)
	else:
		icon = None
		window.present()

	from gi.repository import Gtk, GObject

	# initializes the receiver listener
	def check_for_listener(notify=False):
		# print ("check_for_listener %s" % notify)
		global listener
		listener = None

		from listener import ReceiverListener
		try:
			listener = ReceiverListener.open(status_changed)
		except OSError:
			ui.error(window, 'Permissions error',
					'Found a possible Unifying Receiver device,\n'
					'but did not have permission to open it.')

		if listener is None:
			if notify:
				status_changed(DUMMY)
			else:
				return True

	from logitech.unifying_receiver import status

	# callback delivering status events from the receiver/devices to the UI
	def status_changed(receiver, device=None, alert=status.ALERT.NONE, reason=None):
		if window:
			GObject.idle_add(ui.main_window.update, window, receiver, device)
		if icon:
			GObject.idle_add(ui.status_icon.update, icon, receiver, device)
		if alert & status.ALERT.MED:
			GObject.idle_add(window.popup, icon)

		if ui.notify.available:
			# always notify on receiver updates
			if device is None or alert & status.ALERT.LOW:
				GObject.idle_add(ui.notify.show, device or receiver, reason)

		if receiver is DUMMY:
			GObject.timeout_add(3000, check_for_listener)

	GObject.timeout_add(0, check_for_listener, True)
	Gtk.main()

	if listener:
		listener.stop()
		listener.join()

	ui.notify.uninit()


if __name__ == '__main__':
	_require('pyudev', 'python-pyudev')
	_require('gi.repository', 'python-gi')
	_require('gi.repository.Gtk', 'gir1.2-gtk-3.0')

	args = _parse_arguments()
	listener = None
	_run(args)
