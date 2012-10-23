#!/usr/bin/env python


import logging
logging.basicConfig(level=logging.DEBUG)

from binascii import hexlify

from .unifying_receiver import api
from .unifying_receiver.constants import *


def print_receiver(receiver):
	print ("Unifying Receiver")

	serial, firmware  = api.get_receiver_info(receiver)

	print ("  Serial    : %s" % serial)
	for f in firmware:
		print ("  %-10s: %s" % (f.kind, f.version))

	print ("--------")


def scan_devices(receiver):
	print_receiver(receiver)

	devices = api.list_devices(receiver)
	if not devices:
		print ("!! No attached devices found.")
		return

	for devinfo in devices:
		print ("Device [%d] %s (%s)" % (devinfo.number, devinfo.name, devinfo.kind))
		# print "  Protocol %s" % devinfo.protocol

		firmware = api.get_device_firmware(receiver, devinfo.number, features=devinfo.features)
		for fw in firmware:
			print ("  %-10s: %s %s" % (fw.kind, fw.name, fw.version))

		for index in range(0, len(devinfo.features)):
			feature = devinfo.features[index]
			if feature:
				print ("  ~ Feature %s (%s) at index %d" % (FEATURE_NAME[feature], hexlify(feature), index))

		if FEATURE.BATTERY in devinfo.features:
			discharge, dischargeNext, status = api.get_device_battery_level(receiver, devinfo.number, features=devinfo.features)
			print ("  Battery %d charged (next level %d%), status %s" % (discharge, dischargeNext, status))

		if FEATURE.REPROGRAMMABLE_KEYS in devinfo.features:
			keys = api.get_device_keys(receiver, devinfo.number, features=devinfo.features)
			if keys is not None and keys:
				print ("  %d reprogrammable keys found" % len(keys))
				for k in keys:
					flags = ','.join(KEY_FLAG_NAME[f] for f in KEY_FLAG_NAME if k.flags & f)
					print ("    %2d: %-12s => %-12s :%s" % (k.index, KEY_NAME[k.id], KEY_NAME[k.task], flags))

		print ("--------")


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='log the HID data traffic with the receiver')
	args = arg_parser.parse_args()

	log_level = logging.root.level - 10 * args.verbose
	logging.root.setLevel(log_level if log_level > 0 else 1)

	for rawdevice in api._base.list_receiver_devices():
		receiver = api._base.try_open(rawdevice.path)
		if receiver:
			print ("!! Logitech Unifying Receiver found (%s)." % rawdevice.path)
			scan_devices(receiver)
			api.close(receiver)
			break
	else:
		print ("!! Logitech Unifying Receiver not found.")


	# import pyudev
	# ctx = pyudev.Context()
	# m = pyudev.Monitor.from_netlink(ctx)
	# m.filter_by(subsystem='hid')
	# for action, device in m:
	# 	print '%s: %s' % (action, device)
