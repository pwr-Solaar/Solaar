#!/usr/bin/env python

__version__ = '0.4'

#
#
#

import logging


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='increase the logger verbosity')
	args = arg_parser.parse_args()

	log_level = logging.root.level - 10 * args.verbose
	logging.basicConfig(level=log_level if log_level > 0 else 1)

	import app
	app.run()
