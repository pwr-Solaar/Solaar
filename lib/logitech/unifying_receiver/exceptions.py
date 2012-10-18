#
# Exceptions that may be raised by this API.
#

from .constants import (FEATURE_NAME, ERROR_NAME)


class NoReceiver(Exception):
	"""May be raised when trying to talk through a previously connected
	receiver that is no longer available. Should only happen if the receiver is
	physically disconnected from the machine, or its kernel driver module is
	unloaded."""
	pass


class FeatureNotSupported(Exception):
	"""Raised when trying to request a feature not supported by the device."""
	def __init__(self, devnumber, feature):
		super(FeatureNotSupported, self).__init__(devnumber, feature, FEATURE_NAME[feature])
		self.devnumber = devnumber
		self.feature = feature
		self.feature_name = FEATURE_NAME[feature]


class FeatureCallError(Exception):
	"""Raised if the device replied to a feature call with an error."""
	def __init__(self, devnumber, feature, feature_index, feature_function, error_code, data=None):
		super(FeatureCallError, self).__init__(devnumber, feature, feature_index, feature_function, error_code, ERROR_NAME[error_code])
		self.devnumber = devnumber
		self.feature = feature
		self.feature_name = None if feature is None else FEATURE_NAME[feature]
		self.feature_index = feature_index
		self.feature_function = feature_function
		self.error_code = error_code
		self.error_string = ERROR_NAME[error_code]
		self.data = data
