## Copyright (C) 2012-2013  Daniel Pavel
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import argparse
import os
import os.path
import platform
import readline
import sys
import time

from binascii import hexlify
from binascii import unhexlify
from select import select
from threading import Lock
from threading import Thread

if platform.system() == "Linux":
    import hidapi.udev_impl as hidapi
else:
    import hidapi.hidapi_impl as hidapi

LOGITECH_VENDOR_ID = 0x046D

interactive = os.isatty(0)
prompt = "?? Input: " if interactive else ""
start_time = time.time()


def strhex(d):
    return hexlify(d).decode("ascii").upper()


print_lock = Lock()


def _print(marker, data, scroll=False):
    t = time.time() - start_time
    if isinstance(data, str):
        s = marker + " " + data
    else:
        hexs = strhex(data)
        s = "%s (% 8.3f) [%s %s %s %s] %s" % (marker, t, hexs[0:2], hexs[2:4], hexs[4:8], hexs[8:], repr(data))

    with print_lock:
        # allow only one thread at a time to write to the console, otherwise
        # the output gets garbled, especially with ANSI codes.

        if interactive and scroll:
            # scroll the entire screen above the current line up by 1 line
            sys.stdout.write(
                "\033[s"  # save cursor position
                "\033[S"  # scroll up
                "\033[A"  # cursor up
                "\033[L"  # insert 1 line
                "\033[G"
            )  # move cursor to column 1
        sys.stdout.write(s)
        if interactive and scroll:
            # restore cursor position
            sys.stdout.write("\033[u")
        else:
            sys.stdout.write("\n")

        # flush stdout manually...
        # because trying to open stdin/out unbuffered programmatically
        # works much too differently in Python 2/3
        sys.stdout.flush()


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
        data = unhexlify(line.encode("ascii"))
    except Exception as e:
        _error("Invalid input: " + str(e))
        return None

    if hidpp:
        if len(data) < 4:
            _error("Invalid HID++ request: need at least 4 bytes")
            return None
        if data[:1] not in b"\x10\x11":
            _error("Invalid HID++ request: first byte must be 0x10 or 0x11")
            return None
        if data[1:2] not in b"\xff\x00\x01\x02\x03\x04\x05\x06\x07":
            _error("Invalid HID++ request: second byte must be 0xFF or one of 0x00..0x07")
            return None
        if data[:1] == b"\x10":
            if len(data) > 7:
                _error("Invalid HID++ request: maximum length of a 0x10 request is 7 bytes")
                return None
            while len(data) < 7:
                data = (data + b"\x00" * 7)[:7]
        elif data[:1] == b"\x11":
            if len(data) > 20:
                _error("Invalid HID++ request: maximum length of a 0x11 request is 20 bytes")
                return None
            while len(data) < 20:
                data = (data + b"\x00" * 20)[:20]

    return data


def _open(args):
    def matchfn(bid, vid, pid, _a, _b):
        if vid == LOGITECH_VENDOR_ID:
            return {"vid": vid}

    device = args.device
    if args.hidpp and not device:
        for d in hidapi.enumerate(matchfn):
            if d.driver == "logitech-djreceiver":
                device = d.path
                break
        if not device:
            sys.exit("!! No HID++ receiver found.")
    if not device:
        sys.exit("!! Device path required.")

    print(".. Opening device", device)
    handle = hidapi.open_path(device)
    if not handle:
        sys.exit(f"!! Failed to open {device}, aborting.")
    print(
        ".. Opened handle %r, vendor %r product %r serial %r."
        % (handle, hidapi.get_manufacturer(handle), hidapi.get_product(handle), hidapi.get_serial(handle))
    )
    if args.hidpp:
        if hidapi.get_manufacturer(handle) is not None and hidapi.get_manufacturer(handle) != b"Logitech":
            sys.exit("!! Only Logitech devices support the HID++ protocol.")
        print(".. HID++ validation enabled.")
    else:
        if hidapi.get_manufacturer(handle) == b"Logitech" and b"Receiver" in hidapi.get_product(handle):
            args.hidpp = True
            print(".. Logitech receiver detected, HID++ validation enabled.")

    return handle


def _parse_arguments():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--history", help="history file (default ~/.hidconsole-history)")
    arg_parser.add_argument("--hidpp", action="store_true", help="ensure input data is a valid HID++ request")
    arg_parser.add_argument(
        "device",
        nargs="?",
        help="linux device to connect to (/dev/hidrawX); "
        "may be omitted if --hidpp is given, in which case it looks for the first Logitech receiver",
    )
    return arg_parser.parse_args()


def main():
    args = _parse_arguments()
    handle = _open(args)

    if interactive:
        print(".. Press ^C/^D to exit, or type hex bytes to write to the device.")

        if args.history is None:
            args.history = os.path.join(os.path.expanduser("~"), ".hidconsole-history")
        try:
            readline.read_history_file(args.history)
        except Exception:
            # file may not exist yet
            pass

    try:
        t = Thread(target=_continuous_read, args=(handle,))
        t.daemon = True
        t.start()

        if interactive:
            # move the cursor at the bottom of the screen
            sys.stdout.write("\033[300B")  # move cusor at most 300 lines down, don't scroll

        while t.is_alive():
            line = input(prompt)
            line = line.strip().replace(" ", "")
            # print ("line", line)
            if not line:
                continue

            data = _validate_input(line, args.hidpp)
            if data is None:
                continue

            _print("<<", data)
            hidapi.write(handle, data)
            # wait for some kind of reply
            if args.hidpp and not interactive:
                rlist, wlist, xlist = select([handle], [], [], 1)
                if data[1:2] == b"\xff":
                    # the receiver will reply very fast, in a few milliseconds
                    time.sleep(0.010)
                else:
                    # the devices might reply quite slow
                    time.sleep(0.700)
    except EOFError:
        if interactive:
            print("")
        else:
            time.sleep(1)

    finally:
        print(f".. Closing handle {handle!r}")
        hidapi.close(handle)
        if interactive:
            readline.write_history_file(args.history)


if __name__ == "__main__":
    main()
