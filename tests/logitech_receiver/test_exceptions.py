from unittest import mock

import pytest

from logitech_receiver.exceptions import FeatureCallError
from logitech_receiver.exceptions import FeatureNotSupportedError
from logitech_receiver.exceptions import LogitechReceiverError
from logitech_receiver.exceptions import NoSuchDeviceError
from logitech_receiver.exceptions import ReceiverNotAvailableError


def test_exception_part_of_base():
    number = 1
    receiver = mock.Mock()

    with pytest.raises(LogitechReceiverError):
        raise NoSuchDeviceError(number, receiver, "Is subclass of base exception")


def test_receiver_not_available_error():
    expected_reason = "Failed to open path"

    e = ReceiverNotAvailableError(expected_reason)

    assert str(e) == expected_reason


def test_no_such_device_error():
    expected_reason = "No device"

    number = 1
    receiver = mock.Mock()
    e = NoSuchDeviceError(number, receiver, expected_reason)

    assert str(e) == expected_reason


def test_feature_not_supported_error():
    expected_reason = "Feature not supported"

    e = FeatureNotSupportedError(expected_reason)

    assert str(e) == expected_reason


def test_feature_call_error():
    expected_reason = "Call unsupported feature"

    e = FeatureCallError(expected_reason)

    assert str(e) == expected_reason
