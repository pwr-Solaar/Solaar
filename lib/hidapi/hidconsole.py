#!/usr/bin/env python -u

import os
import sys
from select import select as _select
import time
from binascii import hexlify, unhexlify
strhex = lambda d: hexlify(d).decode('ascii').upper()


interactive = os.isatty(0)
start_time = 0
try:  # python3 support
	read_packet = raw_input
except:
	read_packet = input

from threading import Lock
print_lock = Lock()


def _print(marker, data, scroll=False):
	t = time.time() - start_time
	hexs = strhex(data)
	s = '%s (% 8.3f) [%s %s %s %s] %s' % (marker, t, hexs[0:2], hexs[2:4], hexs[4:8], hexs[8:], repr(data))

	print_lock.acquire()

	if interactive and scroll:
		# scroll the entire screen above the current line up by 1 line
		sys.stdout.write('\033[s'  # save cursor position
						'\033[S'  # scroll up
						'\033[A'   # cursor up
						'\033[L'    # insert 1 line
						'\033[G')   # move cursor to column 1
	sys.stdout.write(s)
	if interactive and scroll:
		# restore cursor position
		sys.stdout.write('\033[u')
	else:
		sys.stdout.write('\n')

	print_lock.release()


def _continuous_read(handle, timeout=2000):
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
	arg_parser.add_argument('--history', help='history file')
	arg_parser.add_argument('device', default=None, help='linux device to connect to')
	args = arg_parser.parse_args()

	import hidapi
	print (".. Opening device %s" % args.device)
	handle = hidapi.open_path(args.device.encode('utf-8'))
	if handle:
		print (".. Opened handle %s, vendor %s product %s serial %s" % (
						repr(handle),
						repr(hidapi.get_manufacturer(handle)),
						repr(hidapi.get_product(handle)),
						repr(hidapi.get_serial(handle))))
		if interactive:
			print (".. Press ^C/^D to exit, or type hex bytes to write to the device.")

			import readline
			if args.history is None:
				import os.path
				args.history = os.path.join(os.path.expanduser("~"), ".hidconsole-history")
			try:
				readline.read_history_file(args.history)
			except:
				# file may not exist yet
				pass

		start_time = time.time()

		try:
			from threading import Thread
			t = Thread(target=_continuous_read, args=(handle,))
			t.daemon = True
			t.start()

			prompt = '?? Input: ' if interactive else ''
			if interactive:
				# move the cursor at the bottom of the screen
				sys.stdout.write('\033[300B')  # move cusor at most 300 lines down, don't scroll

			while t.is_alive():
				line = read_packet(prompt).strip().replace(' ', '')
				if line:
					try:
						data = unhexlify(line.encode('ascii'))
					except Exception as e:
						print ("!! Invalid input.")
					else:
						_print('<<', data)
						hidapi.write(handle, data)
						# wait for some kind of reply
						if not interactive:
							if data[1:2] == b'\xFF':
								# the receiver will reply very fast, in a few milliseconds
								time.sleep(0.010)
							else:
								# the devices might reply quite slow
								rlist, wlist, xlist = _select([handle], [], [], 1)
								time.sleep(1)
		except EOFError:
			pass
		except Exception as e:
			print ('%s: %s' % (type(e).__name__, e))

		print (".. Closing handle %s" % repr(handle))
		hidapi.close(handle)
		if interactive:
			readline.write_history_file(args.history)
	else:
		print ("!! Failed to open %s, aborting" % args.device)
