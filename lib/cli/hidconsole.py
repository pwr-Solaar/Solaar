#!/usr/bin/env python

# Python 2 only for now.

import time
from binascii import hexlify, unhexlify


def read_next(handle, timeout=1000, ignore_nodata=False):
	reply = hidapi.read(handle, 128, timeout)
	if reply is None:
		print "!! Read failed, aborting"
		raise Exception()
	if reply:
		hexs = hexlify(reply)
		print ">> [%s %s %s %s] %s" % (hexs[0:2], hexs[2:4], hexs[4:8], hexs[8:], repr(reply))
		return True

	if not ignore_nodata:
		print ">> []"
	return False


def console_cycle(handle):
	last_data = None

	while True:
		if read_next(handle, timeout=100, ignore_nodata=True):
			continue

		line = raw_input('!! Command: ')
		line = line.strip().replace(' ', '').replace('-', '')
		if not line:
			continue

		data = None

		if line == 'h':
			print 'Commands:'
			print '   <hex bytes>  - send a packet to the device'
			print '   r            - re-send last packet'
			print '   w<float>     - listen for events for <float> seconds'
			print '   h            - this help screen'
			print '   ^C           - exit'
		elif line == 'r':
			data = last_data
		elif line[0] == 'w':
			line = line[1:].strip()
			try:
				seconds = float(line)
			except:
				print "!! Bad number <" + line + ">"
			else:
				count = 0
				start_time = time.time()
				while time.time() - start_time < seconds:
					if read_next(handle, timeout=100, ignore_nodata=True):
						count += 1
				print "!! Got %d events" % count
		else:
			try:
				data = unhexlify(line)
			except:
				print "!! Invalid input."
				continue

		if data:
			hexs = hexlify(data)
			print "<< [%s %s %s %s] %s" % (hexs[0:2], hexs[2:4], hexs[4:8], hexs[8:], repr(data))
			last_data = data
			hidapi.write(handle, data)
			read_next(handle)


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('device', default=None,
							help='linux device to connect to')
	args = arg_parser.parse_args()

	import hidapi
	print "!! Opening device ", args.device
	handle = hidapi.open_path(args.device)
	if handle:
		print "!! Opened %x" % handle
		print "!! vendor %s product %s serial %s" % (
						repr(hidapi.get_manufacturer(handle)),
						repr(hidapi.get_product(handle)),
						repr(hidapi.get_serial(handle)))
		print "!! Type 'h' for help."
		try:
			console_cycle(handle)
		except:
			print "!! Closing handle %x" % handle
			hidapi.close(handle)
	else:
		print "!! Failed to open %s, aborting" % args.device
