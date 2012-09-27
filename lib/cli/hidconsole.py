
import logging
from binascii import hexlify, unhexlify


def read_next(handle, timeout=1000, ignore_nodata=False):
	reply = hidapi.read(handle, 128, timeout)
	if reply is None:
		print "!! Read failed, aborting"
		raise Exception()
	if reply:
		print ">> %s [%s]" % (hexlify(reply), repr(reply))
		return True

	if not ignore_nodata:
		print ">> []"
	return False

def console_cycle(handle):
	while True:
		if read_next(handle, timeout=100, ignore_nodata=True):
			continue

		line = raw_input('!! Enter packet to send (hex bytes): ')
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
		print "<< %s [%s]" % (hexlify(data), repr(data))
		hidapi.write(handle, data)
		read_next(handle)


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('-v', '--verbose', action='count', default=0,
							help='increase the logger verbosity')
	arg_parser.add_argument('device', default=None,
							help='linux device to connect to')
	args = arg_parser.parse_args()

	log_level = logging.root.level - 10 * args.verbose
	logging.root.setLevel(log_level if log_level > 0 else 1)

	import hidapi
	print "!! Opening device ", args.device
	handle = hidapi.open_path(args.device)
	if handle:
		print "!! Opened %x" % handle
		print "!! vendor=%s product=%s serial=%s" % (
						hidapi.get_manufacturer(handle),
						hidapi.get_product(handle),
						hidapi.get_serial(handle))
		try:
			console_cycle(handle)
		except:
			print "!! Closing handle %x" % handle
			hidapi.close(handle)
	else:
		print "!! Failed to open %s, aborting" % args.device
