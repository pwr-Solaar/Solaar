#!/usr/bin/env python


import logging
logging.basicConfig(level=logging.DEBUG)

import struct
from binascii import hexlify

from logitech.unifying_receiver import api


def scan_devices(receiver):
	devices = api.list_devices(receiver)
	if not devices:
		print "!! No attached devices found."
		return

	for devinfo in devices:
		print "Device [%d] %s (%s)" % (devinfo.number, devinfo.name, devinfo.type)
		for fw in devinfo.firmware:
			print "    %s firmware: %s version %s build %d" % (fw.type, fw.name, fw.version, fw.build)

		for index in range(0, len(devinfo.features_array)):
			feature = devinfo.features_array[index]
			if feature:
				print "  Feature %s (%s) available at index %d" % (api.FEATURE_NAME(feature), hexlify(feature), index)

		if api.FEATURE.REPROGRAMMABLE_KEYS in devinfo.features_array:
			keys_count = api.request(receiver, devinfo.number, api.FEATURE.REPROGRAMMABLE_KEYS, features_array=devinfo.features_array)
			if keys_count:
				keys_count = ord(keys_count[:1])
				print "  %d reprogrammable keys available" % keys_count
				for index in range(0, keys_count):
					key_info = api.request(receiver, devinfo.number, api.FEATURE.REPROGRAMMABLE_KEYS,
						function=b'\x10', params=struct.pack('!B', index),
						features_array=devinfo.features_array)
					ctrl_id_indexes, ctrl_task_indexes, flags = struct.unpack('!HHB', key_info[:5])

					flag = ''
					if flags & 0x10:
						flag += ' reprogrammable'
					if flags & 0x08:
						flag += ' fn-sensitive'
					if flags & 0x04:
						flag += ' nonstandard'
					if flags & 0x02:
						flag += ' is-fn'
					if flags & 0x01:
						flag += ' mse'

					print "  key %d : %04x %04x %s" % (index, ctrl_id_indexes, ctrl_task_indexes, flag)



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
