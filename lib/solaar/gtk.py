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

	from solaar.listener import DUMMY_RECEIVER, ReceiverListener
	window = ui.main_window.create(NAME)
	assert window
	icon = ui.status_icon.create(window)
	assert icon

	listeners = {}

	# initializes the receiver listener
	def check_for_listener(notify=False):
		# print ("check_for_listener", notify)

		try:
			l = ReceiverListener.open(status_changed)
		except OSError:
			l = None
			ui.error_dialog(window, 'Permissions error',
							'Found a possible Unifying Receiver device,\n'
							'but did not have permission to open it.')

		listeners.clear()
		if l:
			listeners[l.receiver.serial] = l
		else:
			if notify:
				status_changed(DUMMY_RECEIVER)
			else:
				return True

	from gi.repository import Gtk, GLib
	from logitech.unifying_receiver.status import ALERT

	# callback delivering status notifications from the receiver/devices to the UI
	def status_changed(device, alert=ALERT.NONE, reason=None):
		assert device is not None

		if alert & ALERT.SHOW_WINDOW:
			GLib.idle_add(window.present)
		GLib.idle_add(ui.main_window.update, window, device)
		GLib.idle_add(ui.status_icon.update, icon, device)

		if ui.notify.available:
			# always notify on receiver updates
			if device is DUMMY_RECEIVER or alert & ALERT.NOTIFICATION:
				GLib.idle_add(ui.notify.show, device, reason)

		if device is DUMMY_RECEIVER:
			GLib.timeout_add(3000, check_for_listener)

	GLib.timeout_add(10, check_for_listener, True)
	Gtk.main()

	map(ReceiverListener.stop, listeners.values())
	ui.notify.uninit()
	map(ReceiverListener.join, listeners.values())


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
