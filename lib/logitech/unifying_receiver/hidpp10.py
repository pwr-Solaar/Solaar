#
#
#

from .common import (strhex as _strhex,
					NamedInts as _NamedInts,
					FirmwareInfo as _FirmwareInfo)
from .hidpp20 import FIRMWARE_KIND

#
# constants
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

NOTIFICATION_FLAG = _NamedInts(
				battery_status=0x00100000,
				wireless=0x00000100,
				software_present=0x000000800)

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

REGISTERS = _NamedInts(
				battery=0x0D,
				dpi=0x63,
				leds=0x51)

#
# functions
#

def get_battery(device):
	"""Reads a device's battery level, if provided by the HID++ 1.0 protocol."""
	reply = device.request(0x810D)
	if reply:
		charge = ord(reply[:1])
		status = ord(reply[2:3]) & 0xF0
		status = ('discharging' if status == 0x30
				else 'charging' if status == 0x50
				else 'fully charged' if status == 0x90
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
	firmware = []

	reply = device.request(0x81F1, 0x01)
	if reply:
		fw_version = _strhex(reply[1:3])
		fw_version = '%s.%s' % (fw_version[0:2], fw_version[2:4])
		reply = device.request(0x81F1, 0x02)
		if reply:
			fw_version += '.B' + _strhex(reply[1:3])
		fw = _FirmwareInfo(FIRMWARE_KIND.Firmware, '', fw_version, None)
		firmware.append(fw)

	reply = device.request(0x81F1, 0x04)
	if reply:
		bl_version = _strhex(reply[1:3])
		bl_version = '%s.%s' % (bl_version[0:2], bl_version[2:4])
		bl = _FirmwareInfo(FIRMWARE_KIND.Bootloader, '', bl_version, None)
		firmware.append(bl)

	return tuple(firmware)
