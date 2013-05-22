#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger  # , DEBUG as _DEBUG
_log = getLogger('LUR.hidpp10')
del getLogger

from .common import (strhex as _strhex,
					NamedInts as _NamedInts,
					FirmwareInfo as _FirmwareInfo)
from .hidpp20 import FIRMWARE_KIND

#
# Constants - most of them as defined by the official Logitech HID++ 1.0
# documentation, some of them guessed.
#

DEVICE_KIND = _NamedInts(
				keyboard=0x01,
				mouse=0x02,
				numpad=0x03,
				presenter=0x04,
				trackball=0x08,
				touchpad=0x09)

POWER_SWITCH_LOCATION = _NamedInts(
				base=0x01,
				top_case=0x02,
				edge_of_top_right_corner=0x03,
				top_left_corner=0x05,
				bottom_left_corner=0x06,
				top_right_corner=0x07,
				bottom_right_corner=0x08,
				top_edge=0x09,
				right_edge=0x0A,
				left_edge=0x0B,
				bottom_edge=0x0C)

# Some flags are used both by devices and receivers. The Logitech documentation
# mentions that the first and last (third) byte are used for devices while the
# second is used for the receiver. In practise, the second byte is also used for
# some device-specific notifications (keyboard illumination level). Do not
# simply set all notification bits if the software does not support it. For
# example, enabling keyboard_sleep_raw makes the Sleep key a no-operation unless
# the software is updated to handle that event.
# Observations:
# - wireless and software present were seen on receivers, reserved_r1b4 as well
# - the rest work only on devices as far as we can tell right now
# In the future would be useful to have separate enums for receiver and device notification flags,
# but right now we don't know enough.
NOTIFICATION_FLAG = _NamedInts(
				battery_status=         0x100000,  # send battery charge notifications (0x07 or 0x0D)
				keyboard_sleep_raw=     0x020000,  # system control keys such as Sleep
				keyboard_multimedia_raw=0x010000,  # consumer controls such as Mute and Calculator
				# reserved_r1b4=        0x001000,  # unknown, seen on a unifying receiver
				software_present=       0x000800,  # .. no idea
				keyboard_backlight=     0x000200,  # illumination brightness level changes (by pressing keys)
				wireless=               0x000100,  # notify when the device wireless goes on/off-line
				)

ERROR = _NamedInts(
				invalid_SubID__command=0x01,
				invalid_address=0x02,
				invalid_value=0x03,
				connection_request_failed=0x04,
				too_many_devices=0x05,
				already_exists=0x06,
				busy=0x07,
				unknown_device=0x08,
				resource_error=0x09,
				request_unavailable=0x0A,
				unsupported_parameter_value=0x0B,
				wrong_pin_code=0x0C)

PAIRING_ERRORS = _NamedInts(
				device_timeout=0x01,
				device_not_supported=0x02,
				too_many_devices=0x03,
				sequence_timeout=0x06)

#
# functions
#

def get_register(device, name, default_number=-1):
	known_register = device.registers[name]
	register = known_register or default_number
	if register > 0:
		reply = device.request(0x8100 + (register & 0xFF))
		if reply:
			return reply

		if not known_register and device.ping():
			_log.warn("%s: failed to read '%s' from default register 0x%02X, blacklisting",
							device, name, default_number)
			device.registers[name] = -default_number


def get_battery(device):
	"""Reads a device's battery level, if provided by the HID++ 1.0 protocol."""
	if device.protocol >= 2.0:
		# let's just assume HID++ 2.0 devices do not provide the battery info in a register
		return

	reply = get_register(device, 'battery_charge', 0x0D)
	if reply:
		level = ord(reply[:1])
		battery_status = ord(reply[2:3])
		return parse_battery_reply_0D(level, battery_status)

	reply = get_register(device, 'battery_status', 0x07)
	if reply:
		level = ord(reply[:1])
		battery_status = ord(reply[1:2])
		return parse_battery_reply_07(level, battery_status)

def parse_battery_reply_0D(level, battery_status):
	charge = level
	status = battery_status & 0xF0
	status = ('discharging' if status == 0x30
			else 'charging' if status == 0x50
			else 'fully charged' if status == 0x90
			else None)
	return charge, status

def parse_battery_reply_07(level, battery_status):
	charge = (90 if level == 7 # full
		else 50 if level == 5 # good
		else 20 if level == 3 # low
		else 5 if level == 1 # critical
		else 0 ) # wtf?
	status = ('charging' if battery_status == 0x21 or battery_status == 0x25
		else 'fully charged' if battery_status == 0x22
		else 'discharging' if battery_status == 0x00
		else None)
	return charge, status


def get_serial(device):
	if device.kind is None:
		dev_id = 0x03
		receiver = device
	else:
		dev_id = 0x30 + device.number - 1
		receiver = device.receiver

	serial = receiver.request(0x83B5, dev_id)
	if serial:
		return _strhex(serial[1:5])


def get_firmware(device):
	firmware = [None, None]

	reply = device.request(0x81F1, 0x01)
	if reply:
		fw_version = _strhex(reply[1:3])
		fw_version = '%s.%s' % (fw_version[0:2], fw_version[2:4])
		reply = device.request(0x81F1, 0x02)
		if reply:
			fw_version += '.B' + _strhex(reply[1:3])
		fw = _FirmwareInfo(FIRMWARE_KIND.Firmware, '', fw_version, None)
		firmware[0] = fw

	reply = device.request(0x81F1, 0x04)
	if reply:
		bl_version = _strhex(reply[1:3])
		bl_version = '%s.%s' % (bl_version[0:2], bl_version[2:4])
		bl = _FirmwareInfo(FIRMWARE_KIND.Bootloader, '', bl_version, None)
		firmware[1] = bl

	if any(firmware):
		return tuple(f for f in firmware if f)


def get_notification_flags(device):
	flags = device.request(0x8100)
	if flags is not None:
		assert len(flags) == 3
		return ord(flags[0:1]) << 16 | ord(flags[1:2]) << 8 | ord(flags[2:3])


def set_notification_flags(device, *flag_bits):
	flag_bits = sum(int(b) for b in flag_bits)
	result = device.request(0x8000, 0xFF & (flag_bits >> 16), 0xFF & (flag_bits >> 8), 0xFF & flag_bits)
	return result is not None
