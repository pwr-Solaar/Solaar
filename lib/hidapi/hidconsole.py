#!/usr/bin/env python -u

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
from select import select as _select
import time
from binascii import hexlify, unhexlify

#
#
#

interactive = os.isatty(0)
start_time = 0
try:  # python3 support
	read_packet = raw_input
except:
	read_packet = input
prompt = '?? Input: ' if interactive else ''

strhex = lambda d: hexlify(d).decode('ascii').upper()

#
#
#

from threading import Lock
print_lock = Lock()

def _print(marker, data, scroll=False):
	t = time.time() - start_time
	if type(data) == unicode:
		s = marker + ' ' + data
	else:
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


def _error(text, scroll=False):
	_print("!!", text, scroll)


def _continuous_read(handle, timeout=2000):
	while True:
		try:
			reply = hidapi.read(handle, 128, timeout)
		except OSError as e:
			_error("Read failed, aborting: " + str(e), True)
			break
		assert reply is not None
		if reply:
			_print(">>", reply, True)


def _validate_input(line, hidpp=False):
	try:
		data = unhexlify(line.encode('ascii'))
	except Exception as e:
		_error("Invalid input: " + str(e))
		return None

	if hidpp:
		if len(data) < 4:
			_error("Invalid HID++ request: need at least 4 bytes")
			return None
		if data[:1] not in b'\x10\x11':
			_error("Invalid HID++ request: first byte must be 0x10 or 0x11")
			return None
		if data[1:2] not in b'\xFF\x01\x02\x03\x04\x05\x06':
			_error("Invalid HID++ request: second byte must be 0xFF or one of 0x01..0x06")
			return None
		if data[:1] == b'\x10':
			if len(data) > 7:
				_error("Invalid HID++ request: maximum length of a 0x10 request is 7 bytes")
				return None
			while len(data) < 7:
				data = (data + b'\x00' * 7)[:7]
		elif data[:1] == b'\x11':
			if len(data) > 20:
				_error("Invalid HID++ request: maximum length of a 0x11 request is 20 bytes")
				return None
			while len(data) < 20:
				data = (data + b'\x00' * 20)[:20]

	return data

def _open(device, hidpp):
	if hidpp and not device:
		for d in hidapi.enumerate(vendor_id=0x046d):
			if d.driver == 'logitech-djreceiver':
				device = d.path
				break
		if not device:
			sys.exit("!! No HID++ receiver found.")
	if not device:
		sys.exit("!! Device path required.")

	print (".. Opening device %s" % device)
	handle = hidapi.open_path(device)
	if not handle:
		sys.exit("!! Failed to open %s, aborting." % device)

	print (".. Opened handle %s, vendor %s product %s serial %s." % (
					repr(handle),
					repr(hidapi.get_manufacturer(handle)),
					repr(hidapi.get_product(handle)),
					repr(hidapi.get_serial(handle))))
	if args.hidpp:
		if hidapi.get_manufacturer(handle) != 'Logitech':
			sys.exit("!! Only Logitech devices support the HID++ protocol.")
		print (".. HID++ validation enabled.")

	return handle

#
#
#

if __name__ == '__main__':
	import argparse
	arg_parser = argparse.ArgumentParser()
	arg_parser.add_argument('--history', help='history file (default ~/.hidconsole-history)')
	arg_parser.add_argument('--hidpp', action='store_true', help='ensure input data is a valid HID++ request')
	arg_parser.add_argument('device', nargs='?', help='linux device to connect to (/dev/hidrawX); '
							'may be omitted if --hidpp is given, in which case it looks for the first Logitech receiver')
	args = arg_parser.parse_args()

	import hidapi
	handle = _open(args.device, args.hidpp)

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

		if interactive:
			# move the cursor at the bottom of the screen
			sys.stdout.write('\033[300B')  # move cusor at most 300 lines down, don't scroll

		while t.is_alive():
			line = read_packet(prompt)
			line = line.strip().replace(' ', '')
			if not line:
				continue

			data = _validate_input(line, args.hidpp)
			if data is None:
				continue

			_print("<<", data)
			hidapi.write(handle, data)
			# wait for some kind of reply
			if args.hidpp and not interactive:
				if data[1:2] == b'\xFF':
					# the receiver will reply very fast, in a few milliseconds
					time.sleep(0.010)
				else:
					# the devices might reply quite slow
					rlist, wlist, xlist = _select([handle], [], [], 1)
					time.sleep(1)
	except EOFError:
		if interactive:
			print ("")
	except Exception as e:
		print ('%s: %s' % (type(e).__name__, e))

	print (".. Closing handle %s" % repr(handle))
	hidapi.close(handle)
	if interactive:
		readline.write_history_file(args.history)
