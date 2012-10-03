#
#
#

import unittest
import struct

from ..constants import *


class Test_UR_Constants(unittest.TestCase):

	def test_10_feature_names(self):
		for code in range(0x0000, 0x10000):
			feature = struct.pack('!H', code)
			name = FEATURE_NAME[feature]
			self.assertIsNotNone(name)
			self.assertEqual(FEATURE_NAME[code], name)
			if name.startswith('UNKNOWN_'):
				self.assertEqual(code, struct.unpack('!H', feature)[0])
			else:
				self.assertTrue(hasattr(FEATURE, name))
				self.assertEqual(feature, getattr(FEATURE, name))

	def test_20_error_names(self):
		for code in range(0, len(ERROR_NAME)):
			name = ERROR_NAME[code]
			self.assertIsNotNone(name)
			# self.assertEqual(code, ERROR_NAME.index(name))


if __name__ == '__main__':
	unittest.main()
