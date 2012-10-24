#!/usr/bin/env python

import sys
import time
from binascii import hexlify, unhexlify
_hex = lambda d: hexlify(d).decode('ascii').upper()


start_time = 0
try:
	read_packet = raw_input
except:
	read_packet = input


def _print(marker, data, scroll=False):
	hexs = _hex(data)

	t = time.time() - start_time
	s = '%s (% 8.3f) [%s %s %s %s] %s' % (marker, t, hexs[0:2], hexs[2:4], hexs[4:8], hexs[8:], repr(data))

	if scroll:
		sys.stdout.write('\033[s')
		sys.stdout.write('\033[S')  # scroll up
		sys.stdout.write('\033[A\033[L\033[G')   # insert new line above the current one, position on first column

	sys.stdout.write(s)

	if scroll:
		sys.stdout.write('\033[u')
	else:
		sys.stdout.write('\n')


def _continuous_read(handle, timeout=1000):
	while True:
		reply = hidapi.read(handle, 128, timeout)
		if reply is None:
			print ("!! Read failed, aborting")
			break
		elif reply:
			_print('>>', reply, True)


if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--history', default='.hidconsole-history', help='history file')
	arg_parser.add_argument('device', default=None, help='linux device to connect to')
	args = arg_parser.parse_args()

	import hidapi
	print (".. Opening device %s" % args.device)
	handle = hidapi.open_path(args.device.encode('utf-8'))
	if handle:
		print (".. Opened handle %X, vendor %s product %s serial %s" % (handle,
						repr(hidapi.get_manufacturer(handle)),
						repr(hidapi.get_product(handle)),
						repr(hidapi.get_serial(handle))))
		print (".. Press ^C/^D to exit, or type hex bytes to write to the device.")

		import readline
		readline.read_history_file(args.history)

		start_time = time.time()

		try:
			from threading import Thread
			t = Thread(target=_continuous_read, args=(handle,))
			t.daemon = True
			t.start()

			while t.is_alive():
				line = read_packet ('?? Input: ').strip().replace(' ', '')
				if line:
					try:
						data = unhexlify(line.encode('ascii'))
					except Exception as e:
						print ("!! Invalid input.")
					else:
						_print('<<', data)
						hidapi.write(handle, data)
		except Exception as e:
			pass

		print (".. Closing handle %X" % handle)
		hidapi.close(handle)
		readline.write_history_file(args.history)
	else:
		print ("!! Failed to open %s, aborting" % args.device)
