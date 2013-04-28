#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


NAME = 'Solaar'
from solaar import __version__

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
	import solaar.ui as ui

	ui.notify.init()

	from solaar.listener import DUMMY, ReceiverListener
	window = ui.main_window.create(NAME, DUMMY.name, 6, True)
	assert window
	menu_actions = (ui.action.toggle_notifications,
					ui.action.about)
	icon = ui.status_icon.create(window, menu_actions)
	assert icon

	listener = [None]

	# initializes the receiver listener
	def check_for_listener(notify=False):
		# print ("check_for_listener", notify)
		listener[0] = None

		try:
			listener[0] = ReceiverListener.open(status_changed)
		except OSError:
			ui.error_dialog(window, 'Permissions error',
							'Found a possible Unifying Receiver device,\n'
							'but did not have permission to open it.')

		if listener[0] is None:
			if notify:
				status_changed(DUMMY)
			else:
				return True

	from gi.repository import Gtk, GObject
	from logitech.unifying_receiver import status

	# callback delivering status notifications from the receiver/devices to the UI
	def status_changed(receiver, device=None, alert=status.ALERT.NONE, reason=None):
		if alert & status.ALERT.SHOW_WINDOW:
			GObject.idle_add(window.present)
		if window:
			GObject.idle_add(ui.main_window.update, window, receiver, device)
		if icon:
			GObject.idle_add(ui.status_icon.update, icon, receiver, device)

		if ui.notify.available:
			# always notify on receiver updates
			if device is None or alert & status.ALERT.NOTIFICATION:
				GObject.idle_add(ui.notify.show, device or receiver, reason)

		if receiver is DUMMY:
			GObject.timeout_add(3000, check_for_listener)

	GObject.timeout_add(10, check_for_listener, True)
	if icon:
		GObject.timeout_add(1000, ui.status_icon.check_systray, icon, window)
	Gtk.main()

	if listener[0]:
		listener[0].stop()

	ui.notify.uninit()

	if listener[0]:
		listener[0].join()
		listener[0] = None


def main():
	_require('pyudev', 'python-pyudev')
	_require('gi.repository', 'python-gi')
	_require('gi.repository.Gtk', 'gir1.2-gtk-3.0')
	args = _parse_arguments()

	from . import appinstance
	appid = appinstance.check()
	try:
		_run(args)
	finally:
		appinstance.close(appid)


if __name__ == '__main__':
	main()
