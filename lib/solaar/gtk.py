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
	from logging import getLogger, DEBUG as _DEBUG
	_log = getLogger(__name__)
	del getLogger

	import solaar.ui as ui

	ui.notify.init()

	status_icon = ui.status_icon.create(ui.main_window.toggle_all, ui.main_window.popup)
	assert status_icon

	# callback delivering status notifications from the receiver/devices to the UI
	from logitech.unifying_receiver.status import ALERT
	def status_changed(device, alert=ALERT.NONE, reason=None):
		assert device is not None
		if _log.isEnabledFor(_DEBUG):
			_log.debug("status changed: %s, %s, %s", device, alert, reason)

		ui.async(ui.status_icon.update, status_icon, device)
		if alert & ALERT.ATTENTION:
			ui.async(ui.status_icon.attention, status_icon, reason)

		need_popup = alert & (ALERT.SHOW_WINDOW | ALERT.ATTENTION)
		ui.async(ui.main_window.update, device, need_popup, status_icon)

		if alert & ALERT.NOTIFICATION:
			ui.async(ui.notify.show, device, reason)

	import solaar.listener as listener
	listener.start_scanner(status_changed, ui.error_dialog)

	# main UI event loop
	ui.run_loop()
	ui.status_icon.destroy(status_icon)
	ui.notify.uninit()

	listener.stop_all()


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
