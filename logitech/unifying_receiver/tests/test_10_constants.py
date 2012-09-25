#
#
#

import unittest

from logitech.unifying_receiver import constants


class Test_UR_Constants(unittest.TestCase):

	def test_10_feature_names(self):
		self.assertIsNone(constants.FEATURE_NAME(None))
		for code in range(0x0000, 0x10000):
			feature = chr((code & 0xFF00) >> 8) + chr(code & 0x00FF)
			name = constants.FEATURE_NAME(feature)
			self.assertIsNotNone(name)
			if name.startswith('UNKNOWN_'):
				self.assertEquals(code, int(name[8:], 16))
			else:
				self.assertTrue(hasattr(constants.FEATURE, name))
				self.assertEquals(feature, getattr(constants.FEATURE, name))

	def test_20_error_names(self):
		for code in range(0x00, 0x100):
			name = constants.ERROR_NAME(code)
			self.assertIsNotNone(name)
			if code > 9:
				self.assertEquals(name, 'Unknown Error')
			else:
				self.assertEquals(code, constants._ERROR_NAMES.index(name))

if __name__ == '__main__':
	unittest.main()
