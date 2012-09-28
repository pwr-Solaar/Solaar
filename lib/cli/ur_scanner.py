#!/usr/bin/env python


import logging
logging.basicConfig(level=logging.DEBUG)

from binascii import hexlify

from logitech.unifying_receiver import api
from logitech.unifying_receiver.constants import *


def scan_devices(receiver):
	devices = api.list_devices(receiver)
	if not devices:
		print "!! No attached devices found."
		return

	for devinfo in devices:
		print "Device [%d] %s (%s)" % (devinfo.number, devinfo.name, devinfo.type)
		for fw in devinfo.firmware:
			print "    %s firmware: %s version %s build %d" % (fw.type, fw.name, fw.version, fw.build)

		for index in range(0, len(devinfo.features)):
			feature = devinfo.features[index]
			if feature:
				print "~ Feature %s (%s) at index %d" % (FEATURE_NAME[feature], hexlify(feature), index)

		if FEATURE.BATTERY in devinfo.features:
			discharge, dischargeNext, status = api.get_device_battery_level(receiver, devinfo.number, features_array=devinfo.features)
			print "  Battery %d charged (next level %d%), status %s" % (discharge, dischargeNext, status)

		if FEATURE.REPROGRAMMABLE_KEYS in devinfo.features:
			keys = api.get_device_keys(receiver, devinfo.number, features_array=devinfo.features)
			if keys is not None and keys:
				print "  %d reprogrammable keys found" % len(keys)
				for k in keys:
					flags = ''
					if k.flags & KEY_FLAG.REPROGRAMMABLE:
						flags += ' reprogrammable'
					if k.flags & KEY_FLAG.FN_SENSITIVE:
						flags += ' fn-sensitive'
					if k.flags & KEY_FLAG.NONSTANDARD:
						flags += ' nonstandard'
					if k.flags & KEY_FLAG.IS_FN:
						flags += ' is-fn'
					if k.flags & KEY_FLAG.MSE:
						flags += ' mse'

					print "    %2d: %s => %s :%s" % (k.index, KEY_NAME[k.id], KEY_NAME[k.task], flags)

		print "--------"


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='increase the logger verbosity')
	args = arg_parser.parse_args()

	log_level = logging.root.level - 10 * args.verbose
	logging.root.setLevel(log_level if log_level > 0 else 1)

	receiver = api.open()
	if receiver:
		print "!! Logitech Unifying Receiver found."
		scan_devices(receiver)
	else:
		print "!! Logitech Unifying Receiver not found."

	api.close(receiver)
