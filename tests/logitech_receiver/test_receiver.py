from unittest import mock

import pytest

from logitech_receiver import exceptions
from logitech_receiver import receiver


@pytest.mark.parametrize(
    "index, expected_kind",
    [
        (0, None),
        (1, 2),  # mouse
        (2, 2),  # mouse
        (3, 1),  # keyboard
        (4, 3),  # numpad
        (5, None),
    ],
)
def test_get_kind_from_index(index, expected_kind):
    mock_receiver = mock.Mock()

    if expected_kind:
        assert receiver._get_kind_from_index(mock_receiver, index) == expected_kind
    else:
        with pytest.raises(exceptions.NoSuchDevice):
            receiver._get_kind_from_index(mock_receiver, index)
