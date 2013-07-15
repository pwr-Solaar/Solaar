#!/usr/bin/env python
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


from solaar import __version__, NAME
import solaar.i18n as _i18n

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
							help="print logging messages, for debugging purposes (may be repeated for extra verbosity)")
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	args = arg_parser.parse_args()

	import logging
	if args.debug > 0:
		log_level = logging.WARNING - 10 * args.debug
		log_format='%(asctime)s,%(msecs)03d %(levelname)8s [%(threadName)s] %(name)s: %(message)s'
		logging.basicConfig(level=max(log_level, logging.DEBUG), format=log_format, datefmt='%H:%M:%S')
	else:
		logging.root.addHandler(logging.NullHandler())
		logging.root.setLevel(logging.ERROR)

	if logging.root.isEnabledFor(logging.INFO):
		logging.info("language %s (%s), translations path %s", _i18n.language, _i18n.encoding, _i18n.path)

	return args


def main():
	_require('pyudev', 'python-pyudev')
	_require('gi.repository', 'python-gi')
	_require('gi.repository.Gtk', 'gir1.2-gtk-3.0')
	_parse_arguments()

	# handle ^C in console
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	try:
		import solaar.ui as ui
		ui.init()

		import solaar.listener as listener
		listener.setup_scanner(ui.status_changed, ui.error_dialog)
		listener.start_all()

		# main UI event loop
		ui.run_loop()

		listener.stop_all()
	except Exception as e:
		import sys
		sys.exit('%s: error: %s' % (NAME.lower(), e))


if __name__ == '__main__':
	main()
