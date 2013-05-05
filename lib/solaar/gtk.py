#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals


from solaar import __version__, NAME

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
		logging.root.setLevel(logging.ERROR)

	return args


def _run(args):
	import solaar.ui as ui

	ui.notify.init()

	icon = ui.status_icon.create(ui.main_window.toggle_all)
	assert icon

	listeners = {}
	from solaar.listener import ReceiverListener

	def handle_receivers_events(action, device):
		assert action is not None
		assert device is not None

		# whatever the action, stop any previous receivers at this path
		l = listeners.pop(device.path, None)
		if l is not None:
			assert isinstance(l, ReceiverListener)
			l.stop()

		if action == 'add':
			# a new receiver device was detected
			try:
				l = ReceiverListener.open(device.path, status_changed)
				if l is not None:
					listeners[device.path] = l
			except OSError:
				# permission error, blacklist this path for now
				listeners.pop(device.path, None)
				GLib.idle_add(ui.error_dialog, 'Permissions error',
					'Found a Logitech Unifying Receiver device,\n'
					'but did not have permission to open it.\n'
					'\n'
					'If you\'ve just installed Solaar, try removing\n'
					'the receiver and plugging it back in.')

		# elif action == 'remove':
		# 	# we'll be receiving remove events for any hidraw devices,
		# 	# not just Logitech receivers, so it's okay if the device is not
		# 	# already in our listeners map
		# 	l = listeners.pop(device.path, None)
		# 	if l is not None:
		# 		l.stop()

		# print ("****", action, device, listeners)

	# callback delivering status notifications from the receiver/devices to the UI
	from gi.repository import GLib
	from logitech.unifying_receiver.status import ALERT
	def status_changed(device, alert=ALERT.NONE, reason=None):
		assert device is not None
		# print ("status changed", device, reason)

		GLib.idle_add(ui.status_icon.update, icon, device)
		GLib.idle_add(ui.main_window.update, device, alert & ALERT.SHOW_WINDOW)

		if alert & ALERT.NOTIFICATION:
			GLib.idle_add(ui.notify.show, device, reason)

	# ugly...
	def _startup_check_receiver():
		if not listeners:
			ui.notify.alert('No receiver found.')
	GLib.timeout_add(1000, _startup_check_receiver)

	from logitech.unifying_receiver import base as _base
	GLib.timeout_add(10, _base.notify_on_receivers, handle_receivers_events)
	from gi.repository import Gtk
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
