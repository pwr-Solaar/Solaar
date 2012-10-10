#
#
#

import unittest
from binascii import hexlify

from .. import base
from ..exceptions import *
from ..constants import *


class Test_UR_Base(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.ur_available = False
		cls.handle = None
		cls.device = None

	@classmethod
	def tearDownClass(cls):
		if cls.handle:
			base.close(cls.handle)
		cls.ur_available = False
		cls.handle = None
		cls.device = None

	def test_10_list_receiver_devices(self):
		rawdevices = base.list_receiver_devices()
		self.assertIsNotNone(rawdevices, "list_receiver_devices returned None")
		self.assertIsInstance(rawdevices, list, "list_receiver_devices should have returned a list")
		Test_UR_Base.ur_available = len(rawdevices) > 0

	def test_20_try_open(self):
		if not self.ur_available:
			self.fail("No receiver found")

		for rawdevice in base.list_receiver_devices():
			handle = base.try_open(rawdevice.path)
			if handle is None:
				continue

			self.assertIsInstance(handle, int, "try_open should have returned an int")

			if Test_UR_Base.handle is None:
				Test_UR_Base.handle = handle
			else:
				base.close(handle)
				base.close(Test_UR_Base.handle)
				Test_UR_Base.handle = None
				self.fail("try_open found multiple valid receiver handles")

		self.assertIsNotNone(self.handle, "no valid receiver handles found")

	def test_25_ping_device_zero(self):
		if self.handle is None:
			self.fail("No receiver found")

		w = base.write(self.handle, 0, b'\x00\x10\x00\x00\xAA')
		self.assertIsNone(w, "write should have returned None")
		reply = base.read(self.handle, base.DEFAULT_TIMEOUT * 3)
		self.assertIsNotNone(reply, "None reply for ping")
		self.assertIsInstance(reply, tuple, "read should have returned a tuple")

		reply_code, reply_device, reply_data = reply
		self.assertEqual(reply_device, 0, "got ping reply for valid device")
		self.assertGreater(len(reply_data), 4, "ping reply has wrong length: %s" % hexlify(reply_data))
		if reply_code == 0x10:
			# ping fail
			self.assertEqual(reply_data[:3], b'\x8F\x00\x10', "0x10 reply with unknown reply data: %s" % hexlify(reply_data))
		elif reply_code == 0x11:
			self.fail("Got valid ping from device 0")
		else:
			self.fail("ping got bad reply code: " + reply)

	def test_30_ping_all_devices(self):
		if self.handle is None:
			self.fail("No receiver found")

		devices = []

		for device in range(1, 1 + MAX_ATTACHED_DEVICES):
			w = base.write(self.handle, device, b'\x00\x10\x00\x00\xAA')
			self.assertIsNone(w, "write should have returned None")
			reply = base.read(self.handle, base.DEFAULT_TIMEOUT * 3)
			self.assertIsNotNone(reply, "None reply for ping")
			self.assertIsInstance(reply, tuple, "read should have returned a tuple")

			reply_code, reply_device, reply_data = reply
			self.assertEqual(reply_device, device, "ping reply for wrong device")
			self.assertGreater(len(reply_data), 4, "ping reply has wrong length: %s" % hexlify(reply_data))
			if reply_code == 0x10:
				# ping fail
				self.assertEqual(reply_data[:3], b'\x8F\x00\x10', "0x10 reply with unknown reply data: %s" % hexlify(reply_data))
			elif reply_code == 0x11:
				# ping ok
				self.assertEqual(reply_data[:2], b'\x00\x10', "0x11 reply with unknown reply data: %s" % hexlify(reply_data))
				self.assertEqual(reply_data[4:5], b'\xAA')
				devices.append(device)
			else:
				self.fail("ping got bad reply code: " + reply)

		if devices:
			Test_UR_Base.device = devices[0]

	def test_50_request_bad_device(self):
		if self.handle is None:
			self.fail("No receiver found")

		device = 1 if self.device is None else self.device + 1
		reply = base.request(self.handle, device, FEATURE.ROOT, FEATURE.FEATURE_SET)
		self.assertIsNone(reply, "request returned valid reply")

	def test_52_request_root_no_feature(self):
		if self.handle is None:
			self.fail("No receiver found")
		if self.device is None:
			self.fail("No devices attached")

		reply = base.request(self.handle, self.device, FEATURE.ROOT)
		self.assertIsNotNone(reply, "request returned None reply")
		self.assertEqual(reply[:2], b'\x00\x00', "request returned for wrong feature id")

	def test_55_request_root_feature_set(self):
		if self.handle is None:
			self.fail("No receiver found")
		if self.device is None:
			self.fail("No devices attached")

		reply = base.request(self.handle, self.device, FEATURE.ROOT, FEATURE.FEATURE_SET)
		self.assertIsNotNone(reply, "request returned None reply")
		index = reply[:1]
		self.assertGreater(index, b'\x00', "FEATURE_SET not available on device " + str(self.device))

	def test_57_request_ignore_undhandled(self):
		if self.handle is None:
			self.fail("No receiver found")
		if self.device is None:
			self.fail("No devices attached")

		fs_index = base.request(self.handle, self.device, FEATURE.ROOT, FEATURE.FEATURE_SET)
		self.assertIsNotNone(fs_index)
		fs_index = fs_index[:1]
		self.assertGreater(fs_index, b'\x00')

		global received_unhandled
		received_unhandled = None

		def _unhandled(code, device, data):
			self.assertIsNotNone(code)
			self.assertIsInstance(code, int)
			self.assertIsNotNone(device)
			self.assertIsInstance(device, int)
			self.assertIsNotNone(data)
			self.assertIsInstance(data, str)
			global received_unhandled
			received_unhandled = (code, device, data)

		base.unhandled_hook = _unhandled
		base.write(self.handle, self.device, FEATURE.ROOT + FEATURE.FEATURE_SET)
		reply = base.request(self.handle, self.device, fs_index + b'\x00')
		self.assertIsNotNone(reply, "request returned None reply")
		self.assertNotEquals(reply[:1], b'\x00')
		self.assertIsNotNone(received_unhandled, "extra message not received by unhandled hook")

		received_unhandled = None
		base.unhandled_hook = None
		base.write(self.handle, self.device, FEATURE.ROOT + FEATURE.FEATURE_SET)
		reply = base.request(self.handle, self.device, fs_index + b'\x00')
		self.assertIsNotNone(reply, "request returned None reply")
		self.assertNotEquals(reply[:1], b'\x00')
		self.assertIsNone(received_unhandled)

		del received_unhandled

	# def test_90_receiver_missing(self):
	# 	if self.handle is None:
	# 		self.fail("No receiver found")
	#
	# 	logging.warn("remove the receiver in 5 seconds or this test will fail")
	#	import time
	# 	time.sleep(5)
	# 	with self.assertRaises(NoReceiver):
	# 		self.test_30_ping_all_devices()


if __name__ == '__main__':
	unittest.main()
