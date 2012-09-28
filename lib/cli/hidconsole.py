#!/usr/bin/env python

# Python 2 only for now.

from binascii import hexlify, unhexlify


def read_next(handle, timeout=1000, ignore_nodata=False):
	reply = hidapi.read(handle, 128, timeout)
	if reply is None:
		print "!! Read failed, aborting"
		raise Exception()
	if reply:
		print ">> %s %s" % (hexlify(reply), repr(reply))
		return True

	if not ignore_nodata:
		print ">> []"
	return False


def console_cycle(handle):
	while True:
		if read_next(handle, timeout=100, ignore_nodata=True):
			continue

		line = raw_input('!! Enter packet to send (hex bytes) or ^C to abort: ')
		line = line.strip()
		if not line:
			continue
		if len(line) % 2 == 1:
			line += '0'

		try:
			data = unhexlify(line)
		except:
			print "!! Invalid input."
			continue
		print "<< %s %s" % (hexlify(data), repr(data))
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
		try:
			console_cycle(handle)
		except:
			print "!! Closing handle %x" % handle
			hidapi.close(handle)
	else:
		print "!! Failed to open %s, aborting" % args.device
