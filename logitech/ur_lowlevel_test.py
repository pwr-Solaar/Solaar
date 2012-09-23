import unittest
import logging

logging.root.addHandler(logging.FileHandler('test.log', mode='w'))
logging.root.setLevel(1)

from . import ur_lowlevel as urll


class TestLUR(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.handle = urll.open()
		cls.device = None
		cls.features_array = None

	@classmethod
	def tearDownClass(cls):
		cls.device = None
		cls.features_array = None
		if cls.handle:
			urll.close(cls.handle)

	def setUp(self):
		if self.handle is None:
			self.skipTest("Logitech Unifying Receiver not found")

	def first_device(self):
		if TestLUR.device is None:
			for device in range(1, 7):
				ok = urll.ping(self.handle, device)
				self.assertIsNotNone(ok, "invalid ping reply")
				if ok:
					TestLUR.device = device
					return device
			self.skipTest("No attached device found")
		else:
			return TestLUR.device

	def test_00_ping_device_zero(self):
		ok = urll.ping(self.handle, 0)
		self.assertIsNotNone(ok, "invalid ping reply")
		self.assertFalse(ok, "device zero replied")

	def test_10_ping_all_devices(self):
		devices = []
		for device in range(1, 7):
			ok = urll.ping(self.handle, device)
			self.assertIsNotNone(ok, "invalid ping reply")
			if ok:
				devices.append(device)
		# if devices:
		# 	print "found", len(devices), "device(s)", devices
		# else:
		# 	print "no devices found"

	def test_30_root_feature(self):
		device = self.first_device()
		fs_index = urll.get_feature_index(self.handle, device, urll.FEATURE.FEATURE_SET)
		self.assertIsNotNone(fs_index, "feature FEATURE_SET not available")
		self.assertGreater(fs_index, 0, "invalid FEATURE_SET index: " + str(fs_index))

	def test_31_bad_feature(self):
		device = self.first_device()
		reply = urll._request(self.handle, device, urll.FEATURE.ROOT, b'\xFF\xFF')
		self.assertIsNotNone(reply, "invalid reply")
		self.assertEquals(reply[:5], b'\x00' * 5, "invalid reply")

	def test_40_features(self):
		device = self.first_device()
		features = urll.get_device_features(self.handle, device)
		self.assertIsNotNone(features, "failed to read features array")
		self.assertIn(urll.FEATURE.FEATURE_SET, features, "feature FEATURE_SET not available")
		# cache this to simplify next tests
		TestLUR.features_array = features

	def test_50_device_type(self):
		device = self.first_device()
		if not TestLUR.features_array:
			self.skipTest("no feature set available")

		d_type = urll.request(self.handle, device, urll.FEATURE.NAME, function=b'\x20', features_array=TestLUR.features_array)
		self.assertIsNotNone(d_type, "no device type for " + str(device))
		d_type = ord(d_type[0])
		self.assertGreaterEqual(d_type, 0, "negative device type " + str(d_type))
		self.assertLess(d_type, len(urll.DEVICE_TYPES[d_type]), "unknown device type " + str(d_type))
		print "device", device, "type", urll.DEVICE_TYPES[d_type],

	def test_55_device_name(self):
		device = self.first_device()
		if not TestLUR.features_array:
			self.skipTest("no feature set available")

		d_name_length = urll.request(self.handle, device, urll.FEATURE.NAME, features_array=TestLUR.features_array)
		self.assertIsNotNone(d_name_length, "no device name length for " + str(device))
		self.assertTrue(d_name_length > 0, "zero device name length for " + str(device))
		d_name_length = ord(d_name_length[0])

		d_name = ''
		while len(d_name) < d_name_length:
			name_index = len(d_name)
			name_fragment = urll.request(self.handle, device, urll.FEATURE.NAME, function=b'\x10', data=chr(name_index), features_array=TestLUR.features_array)
			self.assertIsNotNone(name_fragment, "no device name fragment " + str(device) + " @" + str(name_index))
			name_fragment = name_fragment[:d_name_length - len(d_name)]
			self.assertNotEqual(name_fragment[0], b'\x00', "empty fragment " + str(device) + " @" + str(name_index))
			d_name += name_fragment
		self.assertEquals(len(d_name), d_name_length)
		print "device", device, "name", d_name,


if __name__ == '__main__':
	unittest.main()
