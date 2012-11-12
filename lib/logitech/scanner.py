#!/usr/bin/env python


def print_receiver(receiver):
	print (str(receiver))

	print ("  Serial    : %s" % receiver.serial)
	for f in receiver.firmware:
		print ("  %-10s: %s" % (f.kind, f.version))
	print ("  Reported %d paired device(s)" % len(receiver))


def scan_devices(receiver):
	for number in range(1, 1 + receiver.max_devices):
		dev = receiver[number]
		if dev is None:
			dev = api.PairedDevice(receiver.handle, number)
			if dev.codename is None:
				continue

		print ("--------")
		print (str(dev))
		print ("Codename     : %s" % dev.codename)
		print ("Name         : %s" % dev.name)
		print ("Kind         : %s" % dev.kind)
		print ("Serial number: %s" % dev.serial)

		if not dev.protocol:
			print ("Device is not connected at this time, no further info available.")
			continue

		print ("HID protocol : HID %01.1f" % dev.protocol)
		if dev.protocol < 2.0:
			print ("Features query not supported by this device")
			continue

		firmware = dev.firmware
		for fw in firmware:
			print ("  %-11s: %s %s" % (fw.kind, fw.name, fw.version))

		all_features = api.get_device_features(dev.handle, dev.number)
		for index in range(0, len(all_features)):
			feature = all_features[index]
			if feature:
				print ("  ~ Feature %-20s (%s) at index %02X" % (FEATURE_NAME[feature], api._hex(feature), index))

		if FEATURE.BATTERY in all_features:
			discharge, dischargeNext, status = api.get_device_battery_level(dev.handle, dev.number, features=all_features)
			print ("  Battery %d charged (next level %d%), status %s" % (discharge, dischargeNext, status))

		if FEATURE.REPROGRAMMABLE_KEYS in all_features:
			keys = api.get_device_keys(dev.handle, dev.number, features=all_features)
			if keys is not None and keys:
				print ("  %d reprogrammable keys found" % len(keys))
				for k in keys:
					flags = ','.join(KEY_FLAG_NAME[f] for f in KEY_FLAG_NAME if k.flags & f)
					print ("    %2d: %-12s => %-12s : %s" % (k.index, KEY_NAME[k.id], KEY_NAME[k.task], flags))


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser(prog='scan')
	arg_parser.add_argument('-v', '--verbose', action='store_true', default=False,
							help='log the HID data traffic')
	args = arg_parser.parse_args()

	import logging
	logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

	from .unifying_receiver import api
	from .unifying_receiver.constants import *

	receiver = api.Receiver.open()
	if receiver is None:
		print ("Logitech Unifying Receiver not found.")
	else:
		print_receiver(receiver)
		scan_devices(receiver)
		receiver.close()
