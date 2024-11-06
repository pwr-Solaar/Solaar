from unittest import mock
from unittest.mock import PropertyMock

import pytest

from solaar.ui import common


@pytest.mark.parametrize(
    "reason, expected_in_title, expected_in_text",
    [
        (
            "permissions",
            "Permissions error",
            "not have permission to open",
        ),
        ("nodevice", "connect to device error", "error connecting"),
        ("unpair", "Unpairing failed", "receiver returned an error"),
    ],
)
def test_create_error_text(reason, expected_in_title, expected_in_text):
    obj = mock.Mock()
    obj.name = PropertyMock(return_value="test")

    title, text = common._create_error_text(reason, obj)

    assert expected_in_title in title
    assert expected_in_text in text
