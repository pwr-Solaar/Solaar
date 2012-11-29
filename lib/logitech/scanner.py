#!/usr/bin/env python


def print_receiver(receiver):
	print (str(receiver))

	print ("  Serial    : %s" % receiver.serial)
	for f in receiver.firmware:
		print ("  %-10s: %s" % (f.kind, f.version))

	notifications = receiver.request(0x8100)
	if notifications:
		notifications = ord(notifications[0:1]) << 16 | ord(notifications[1:2]) << 8
		if notifications:
			print ("  Enabled notifications: %s." % lur.hidpp10.NOTIFICATION_FLAG.flag_names(notifications))
		else:
			print ("  All notifications disabled.")

	print ("  Reported %d paired device(s)." % len(receiver))
	activity = receiver.request(0x83B3)
	if activity:
		activity = [(d, ord(activity[d - 1])) for d in range(1, receiver.max_devices)]
		print("  Device activity counters: %s" % ', '.join(('%d=%d' % (d, a)) for d, a in activity if a > 0))

def scan_devices(receiver):
	for dev in receiver:
		print ("--------")
		print (str(dev))
		print ("Codename     : %s" % dev.codename)
		print ("Kind         : %s" % dev.kind)
		print ("Name         : %s" % dev.name)
		print ("Device number: %d" % dev.number)
		print ("Wireless PID : %s" % dev.wpid)
		print ("Serial number: %s" % dev.serial)
		print ("Power switch : on the %s" % dev.power_switch_location)

		if not dev.ping():
			print ("Device is not connected at this time, no further info available.")
			continue

		print ("HID protocol : HID++ %01.1f" % dev.protocol)
		if not dev.features:
			print ("Features query not supported by this device.")
			continue

		for fw in dev.firmware:
			print ("  %-11s: %s %s" % (fw.kind, fw.name, fw.version))

		print ("  %d features:" % len(dev.features))
		for index, feature in enumerate(dev.features):
			feature = dev.features[index]
			if feature:
				flags = dev.request(0x0000, feature.bytes(2))
				flags = 0 if flags is None else ord(flags[1:2])
				flags = lur.hidpp20.FEATURE_FLAG.flag_names(flags)
				print ("    %2d: %-20s {%04X}   %s" % (index, feature, feature, flags))

		if dev.keys:
			print ("  %d reprogrammable keys:" % len(dev.keys))
			for k in dev.keys:
				flags = lur.hidpp20.KEY_FLAG.flag_names(k.flags)
				print ("    %2d: %-20s => %-20s   %s" % (k.index, lur.hidpp20.KEY[k.key], lur.hidpp20.KEY[k.task], flags))


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser(prog='scan')
	arg_parser.add_argument('-v', '--verbose', action='store_true', default=False,
							help='log the HID data traffic')
	args = arg_parser.parse_args()

	import logging
	log_format='%(asctime)s %(levelname)8s %(name)s: %(message)s'
	logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING, format=log_format)

	from . import unifying_receiver as lur

	receiver = lur.Receiver.open()
	if receiver is None:
		print ("Logitech Unifying Receiver not found.")
	else:
		print_receiver(receiver)
		scan_devices(receiver)
		receiver.close()
