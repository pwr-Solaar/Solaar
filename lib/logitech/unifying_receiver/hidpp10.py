#
#
#

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger, DEBUG as _DEBUG
_log = getLogger('LUR').getChild('hidpp10')
del getLogger

from .common import (strhex as _strhex,
					NamedInts as _NamedInts,
					NamedInt as _NamedInt,
					FirmwareInfo as _FirmwareInfo)
from . import settings as _settings
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
				battery_status=0x100000,
				wireless=0x000100,
				software_present=0x0000800)

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
#
#


class SmoothScroll_Setting(_settings.Setting):
	def __init__(self, register):
		super(SmoothScroll_Setting, self).__init__('smooth-scroll', _settings.KIND.toggle,
						'Smooth Scrolling', 'High-sensitivity mode for vertical scroll with the wheel.')
		assert register is not None
		self.register = register

	def read(self, cached=True):
		if (self._value is None or not cached) and self._device:
			ss = self.read_register()
			if ss:
				self._value = (ss[:1] == b'\x40')
		return self._value

	def write(self, value):
		if self._device:
			reply = self.write_register(0x40 if bool(value) else 0x00)
			self._value = None
			if reply:
				return self.read()


class MouseDPI_Setting(_settings.Setting):
	def __init__(self, register, choices):
		super(MouseDPI_Setting, self).__init__('dpi', _settings.KIND.choice,
						'Sensitivity (DPI)', choices=choices)
		assert choices
		assert isinstance(choices, _NamedInts)
		assert register is not None
		self.register = register

	def read(self, cached=True):
		if (self._value is None or not cached) and self._device:
			dpi = self.read_register()
			if dpi:
				value = ord(dpi[:1])
				self._value = self.choices[value]
				assert self._value is not None
		return self._value

	def write(self, value):
		if self._device:
			choice = self.choices[value]
			if choice is None:
				raise ValueError(repr(value))
			reply = self.write_register(value)
			self._value =  None
			if reply:
				return self.read()

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
			_log.warn("%s: failed to read '%s' from default register 0x%02X, blacklisting", device, name, default_number)
			device.registers[-default_number] = name


def get_battery(device):
	"""Reads a device's battery level, if provided by the HID++ 1.0 protocol."""
	reply = get_register(device, 'battery', 0x0D)
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
