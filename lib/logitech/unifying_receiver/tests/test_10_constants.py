#
#
#

import unittest
import struct

from logitech.unifying_receiver import constants


class Test_UR_Constants(unittest.TestCase):

	def test_10_feature_names(self):
		self.assertIsNone(constants.FEATURE_NAME(None))
		for code in range(0x0000, 0x10000):
			feature = struct.pack('!H', code)
			name = constants.FEATURE_NAME(feature)
			self.assertIsNotNone(name)
			if name.startswith('UNKNOWN_'):
				self.assertEqual(code, struct.unpack('!H', feature)[0])
			else:
				self.assertTrue(hasattr(constants.FEATURE, name))
				self.assertEqual(feature, getattr(constants.FEATURE, name))

	def test_20_error_names(self):
		for code in range(0x00, 0x100):
			name = constants.ERROR_NAME(code)
			self.assertIsNotNone(name)
			if code > 9:
				self.assertEqual(name, 'Unknown Error')
			else:
				self.assertEqual(code, constants._ERROR_NAMES.index(name))

if __name__ == '__main__':
	unittest.main()
