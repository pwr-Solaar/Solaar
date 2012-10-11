#
#
#

import unittest
import warnings

from .. import api
from ..constants import *
from ..common import *


class Test_UR_API(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.handle = None
		cls.device = None
		cls.features = None
		cls.device_info = None

	@classmethod
	def tearDownClass(cls):
		if cls.handle:
			api.close(cls.handle)
		cls.device = None
		cls.features = None
		cls.device_info = None

	def _check(self, check_device=True, check_features=False):
		if self.handle is None:
			self.fail("No receiver found")
		if check_device and self.device is None:
			self.fail("Found no devices attached.")
		if check_device and check_features and self.features is None:
			self.fail("no feature set available")

	def test_00_open_receiver(self):
		Test_UR_API.handle = api.open()
		self._check(check_device=False)

	def test_05_ping_device_zero(self):
		self._check(check_device=False)

		ok = api.ping(self.handle, 0)
		self.assertIsNotNone(ok, "invalid ping reply")
		self.assertFalse(ok, "device zero replied")

	def test_10_ping_all_devices(self):
		self._check(check_device=False)

		devices = []

		for device in range(1, 1 + MAX_ATTACHED_DEVICES):
			ok = api.ping(self.handle, device)
			self.assertIsNotNone(ok, "invalid ping reply")
			if ok:
				devices.append(device)

		if devices:
			Test_UR_API.device = devices[0]

	def test_30_get_feature_index(self):
		self._check()

		fs_index = api.get_feature_index(self.handle, self.device, FEATURE.FEATURE_SET)
		self.assertIsNotNone(fs_index, "feature FEATURE_SET not available")
		self.assertGreater(fs_index, 0, "invalid FEATURE_SET index: " + str(fs_index))

	def test_31_bad_feature(self):
		self._check()

		reply = api.request(self.handle, self.device, FEATURE.ROOT, params=b'\xFF\xFF')
		self.assertIsNotNone(reply, "invalid reply")
		self.assertEqual(reply[:5], b'\x00' * 5, "invalid reply")

	def test_40_get_device_features(self):
		self._check()

		features = api.get_device_features(self.handle, self.device)
		self.assertIsNotNone(features, "failed to read features array")
		self.assertIn(FEATURE.FEATURE_SET, features, "feature FEATURE_SET not available")
		# cache this to simplify next tests
		Test_UR_API.features = features

	def test_50_get_device_firmware(self):
		self._check(check_features=True)

		d_firmware = api.get_device_firmware(self.handle, self.device, self.features)
		self.assertIsNotNone(d_firmware, "failed to get device firmware")
		self.assertGreater(len(d_firmware), 0, "device reported no firmware")
		for fw in d_firmware:
			self.assertIsInstance(fw, FirmwareInfo)

	def test_52_get_device_type(self):
		self._check(check_features=True)

		d_type = api.get_device_type(self.handle, self.device, self.features)
		self.assertIsNotNone(d_type, "failed to get device type")
		self.assertGreater(len(d_type), 0, "empty device type")

	def test_55_get_device_name(self):
		self._check(check_features=True)

		d_name = api.get_device_name(self.handle, self.device, self.features)
		self.assertIsNotNone(d_name, "failed to read device name")
		self.assertGreater(len(d_name), 0, "empty device name")

	def test_59_get_device_info(self):
		self._check(check_features=True)

		device_info = api.get_device_info(self.handle, self.device, features=self.features)
		self.assertIsNotNone(device_info, "failed to read full device info")
		self.assertIsInstance(device_info, AttachedDeviceInfo)
		Test_UR_API.device_info = device_info

	def test_60_get_battery_level(self):
		self._check(check_features=True)

		if FEATURE.BATTERY in self.features:
			battery = api.get_device_battery_level(self.handle, self.device, self.features)
			self.assertIsNotNone(battery, "failed to read battery level")
			self.assertIsInstance(battery, tuple, "result not a tuple")
		else:
			warnings.warn("BATTERY feature not supported by device %d" % self.device)

	def test_70_list_devices(self):
		self._check(check_device=False)

		all_devices = api.list_devices(self.handle)
		if all_devices:
			self.assertIsNotNone(self.device)
			for device_info in all_devices:
				self.assertIsInstance(device_info, AttachedDeviceInfo)
		else:
			self.assertIsNone(self.device)

	def test_70_find_device_by_name(self):
		self._check()

		all_devices = api.list_devices(self.handle)
		for device_info in all_devices:
			device = api.find_device_by_name(self.handle, device_info.name)
			self.assertEqual(device, device_info)

if __name__ == '__main__':
	unittest.main()
