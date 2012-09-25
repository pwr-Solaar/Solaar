#
# test loading the hidapi library
#

import logging
import unittest


class Test_Import_HIDAPI(unittest.TestCase):
	def test_00_import_hidapi(self):
		import hidapi
		self.assertIsNotNone(hidapi)
		logging.info("hidapi loaded native implementation %s", hidapi._native._name)


if __name__ == '__main__':
	unittest.main()
