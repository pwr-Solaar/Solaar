#!/usr/bin/env python

__version__ = '0.4'

#
#
#

if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser(prog='Solaar')
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='increase the logger verbosity')
	arg_parser.add_argument('-N', '--disable-notifications', action='store_false', dest='notifications',
							help='disable desktop notifications')
	arg_parser.add_argument('-H', '--start-hidden', action='store_true', dest='start_hidden',
							help='hide the application window on start')
	arg_parser.add_argument('-t', '--close-to-tray', action='store_true',
							help='closing the application window hides it instead of terminating the application')
	arg_parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)
	args = arg_parser.parse_args()

	import logging
	log_level = logging.root.level - 10 * args.verbose
	logging.basicConfig(level=log_level if log_level > 0 else 1)

	import app
	app.run(args)
