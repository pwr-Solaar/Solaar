#!/usr/bin/env python3
# -*- python-mode -*-
# -*- coding: UTF-8 -*-

## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import absolute_import, division, print_function, unicode_literals

import importlib


from solaar import __version__, NAME
import solaar.i18n as _i18n
import solaar.cli as _cli

#
#
#

def _require(module, os_package, gi=None, gi_package=None, gi_version=None):
	try:
		if gi is not None:
			gi.require_version(gi_package,gi_version)
		return importlib.import_module(module)
	except (ImportError, ValueError):
		import sys
		sys.exit("%s: missing required system package %s" % (NAME, os_package))

prefer_symbolic_battery_icons = False

def _parse_arguments():
	import argparse
	arg_parser = argparse.ArgumentParser(prog=NAME.lower())
	arg_parser.add_argument('-d', '--debug', action='count', default=0,
							help='print logging messages, for debugging purposes (may be repeated for extra verbosity)')
	arg_parser.add_argument('-D', '--hidraw', action='store', dest='hidraw_path', metavar='PATH',
							help='unifying receiver to use; the first detected receiver if unspecified. Example: /dev/hidraw2')
	arg_parser.add_argument('--restart-on-wake-up', action='store_true',
							help='restart Solaar on sleep wake-up (experimental)')
	arg_parser.add_argument('-w', '--window', choices=('show','hide','only'), help='start with window showing / hidden / only (no tray icon)')
	arg_parser.add_argument('-b', '--battery-icons', choices=('regular','symbolic'), help='prefer regular / symbolic icons')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	arg_parser.add_argument('--help-actions', action='store_true',
							help='print help for the optional actions')
	arg_parser.add_argument('action', nargs=argparse.REMAINDER, choices=_cli.actions,
							help='optional actions to perform')

	args = arg_parser.parse_args()

	if args.help_actions:
		_cli.print_help()
		return

	if args.window is None:
		args.window = 'show' # default behaviour is to show main window

	global prefer_symbolic_battery_icons
	prefer_symbolic_battery_icons = True if args.battery_icons == 'symbolic' else False

	import logging
	if args.debug > 0:
		log_level = logging.WARNING - 10 * args.debug
		log_format='%(asctime)s,%(msecs)03d %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format, datefmt='%H:%M:%S')
	else:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.ERROR)

	if not args.action:
		if logging.root.isEnabledFor(logging.INFO):
			logging.info("language %s (%s), translations path %s", _i18n.language, _i18n.encoding, _i18n.path)

	return args


def main():
	_require('pyudev', 'python3-pyudev')

	# handle ^C in console
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	args = _parse_arguments()
	if not args: return
	if args.action:
		# if any argument, run comandline and exit
		return _cli.run(args.action, args.hidraw_path)

	gi = _require('gi', 'python3-gi or python3-gobject')
	_require('gi.repository.Gtk', 'gir1.2-gtk-3.0', gi, 'Gtk', '3.0')

	try:
		import solaar.ui as ui
		import solaar.listener as listener
		listener.setup_scanner(ui.status_changed, ui.error_dialog)

		import solaar.upower as _upower
		if args.restart_on_wake_up:
			_upower.watch(listener.start_all, listener.stop_all)
		else:
			_upower.watch(lambda: listener.ping_all(True))

		# main UI event loop
		ui.run_loop(listener.start_all, listener.stop_all, args.window!='only', args.window!='hide')
	except Exception as e:
		import sys
		sys.exit('%s: error: %s' % (NAME.lower(), e))


if __name__ == '__main__':
	main()
