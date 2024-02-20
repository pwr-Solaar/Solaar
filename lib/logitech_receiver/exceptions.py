from .common import KwException as _KwException

#
# Exceptions that may be raised by this API.
#


class NoReceiver(_KwException):
    """Raised when trying to talk through a previously open handle, when the
    receiver is no longer available. Should only happen if the receiver is
    physically disconnected from the machine, or its kernel driver module is
    unloaded."""

    pass


class NoSuchDevice(_KwException):
    """Raised when trying to reach a device number not paired to the receiver."""

    pass


class DeviceUnreachable(_KwException):
    """Raised when a request is made to an unreachable (turned off) device."""

    pass


class FeatureNotSupported(_KwException):
    """Raised when trying to request a feature not supported by the device."""

    pass


class FeatureCallError(_KwException):
    """Raised if the device replied to a feature call with an error."""

    pass
