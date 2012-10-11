#!/usr/bin/env python


import logging
logging.basicConfig(level=logging.DEBUG)

from binascii import hexlify

from .unifying_receiver import (api, base)
from .unifying_receiver.constants import *


def print_receiver(receiver):
	print ("Unifying Receiver")

	reply = base.request(receiver, 0xff, b'\x83\xB5', b'\x03')
	if reply and reply[0:1] == b'\x03':
		print ("  Serial: %s" % hexlify(reply[1:5]))

	reply = base.request(receiver, 0xff, b'\x81\xF1', b'\x01')
	if reply and reply[0:1] == b'\x01':
		fw_version = hexlify(reply[1:3])
		firmware = fw_version[0:2] + '.' + fw_version[2:4]
	else:
		firmware = '??.??'

	reply = base.request(receiver, 0xff, b'\x81\xF1', b'\x02')
	if reply and reply[0:1] == b'\x02':
		firmware += '.B' + hexlify(reply[1:3])
	print ("  Firmware version: %s" % firmware)

	reply = base.request(receiver, 0xff, b'\x81\xF1', b'\x04')
	if reply and reply[0:1] == b'\x04':
		bl_version = hexlify(reply[1:3])
		print ("  Bootloader: %s.%s" % (bl_version[0:2], bl_version[2:4]))

	print ("--------")


def scan_devices(receiver):
	print_receiver(receiver)

	devices = api.list_devices(receiver)
	if not devices:
		print ("!! No attached devices found.")
		return

	for devinfo in devices:
		print ("Device [%d] %s (%s)" % (devinfo.number, devinfo.name, devinfo.type))
		# print "  Protocol %s" % devinfo.protocol

		for fw in devinfo.firmware:
			print ("  %s firmware: %s version %s build %d" % (fw.type, fw.name, fw.version, fw.build))

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
							help='increase the logger verbosity')
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
