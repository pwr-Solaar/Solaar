#!/usr/bin/env python

# Python 2 only for now.

import sys
import time
import readline
import threading
from binascii import hexlify, unhexlify


start_time = 0


def _print(marker, data, scroll=False):
	hexs = hexlify(data)
	t = time.time() - start_time
	s = '%s (% 8.3f) [%s %s %s %s] %s' % (marker, t, hexs[0:2], hexs[2:4], hexs[4:8], hexs[8:], repr(data))

	if scroll:
		sys.stdout.write(b'\033[s')
		sys.stdout.write(b'\033[S')  # scroll up
		sys.stdout.write(b'\033[A\033[L\033[G')   # insert new line above the current one, position on first column

	sys.stdout.write(s)

	if scroll:
		sys.stdout.write(b'\033[u')
	else:
		sys.stdout.write(b'\n')


def _continuous_read(handle, timeout=1000):
	while True:
		reply = hidapi.read(handle, 128, timeout)
		if reply is None:
			print "!! Read failed, aborting"
			break
		elif reply:
			_print('>>', reply, True)


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('device', default=None,
							help='linux device to connect to')
	arg_parser.add_argument('--history', default='.hidconsole-history',
							help='history file')
	args = arg_parser.parse_args()

	import hidapi
	print ".. Opening device ", args.device
	handle = hidapi.open_path(args.device)
	if handle:
		print ".. Opened handle %x, vendor %s product %s serial %s" % (handle,
						repr(hidapi.get_manufacturer(handle)),
						repr(hidapi.get_product(handle)),
						repr(hidapi.get_serial(handle)))
		print ".. Press ^C/^D to exit, or type hex bytes to write to the device."

		readline.read_history_file(args.history)

		start_time = time.time()

		try:
			t = threading.Thread(target=_continuous_read, args=(handle,))
			t.daemon = True
			t.start()

			while t.is_alive():
				line = raw_input('?? Input: ').strip().replace(' ', '')
				if line:
					try:
						data = unhexlify(line)
						_print('<<', data)
						hidapi.write(handle, data)
					except:
						print "!! Invalid input."
		except:
			pass

		print ".. Closing handle %x" % handle
		hidapi.close(handle)
		readline.write_history_file(args.history)
	else:
		print "!! Failed to open %s, aborting" % args.device
