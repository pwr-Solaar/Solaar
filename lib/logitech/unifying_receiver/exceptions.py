#
# Exceptions that may be raised by this API.
#

from . import constants as C


class NoReceiver(Exception):
	"""May be raised when trying to talk through a previously connected
	receiver that is no longer available. Should only happen if the receiver is
	physically disconnected from the machine, or its kernel driver module is
	unloaded."""
	pass


class FeatureNotSupported(Exception):
	"""Raised when trying to request a feature not supported by the device."""
	def __init__(self, device, feature):
		super(FeatureNotSupported, self).__init__(device, feature, C.FEATURE_NAME[feature])
		self.device = device
		self.feature = feature
		self.feature_name = C.FEATURE_NAME[feature]


class FeatureCallError(Exception):
	"""Raised if the device replied to a feature call with an error."""
	def __init__(self, device, feature, feature_index, feature_function, error_code, data=None):
		super(FeatureCallError, self).__init__(device, feature, feature_index, feature_function, error_code, C.ERROR_NAME[error_code])
		self.device = device
		self.feature = feature
		self.feature_name = None if feature is None else C.FEATURE_NAME[feature]
		self.feature_index = feature_index
		self.feature_function = feature_function
		self.error_code = error_code
		self.error_string = C.ERROR_NAME[error_code]
		self.data = data
