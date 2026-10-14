from unittest import mock

import pytest

from logitech_receiver.common import NamedInts
from solaar.cli import config


def backlight_choices():
    # Backlight2 builds its choices with values that don't start at 0 or 1
    choices = NamedInts()
    choices[0xFF] = "Disabled"
    choices[0x1] = "Automatic"
    choices[0x3] = "Manual"
    return choices


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Manual", 0x3),
        ("1", 0x1),
        ("2", 0x3),
        ("3", 0xFF),
        ("lowest", 0x1),
        ("highest", 0xFF),
    ],
)
def test_select_choice(value, expected):
    result = config.select_choice(value, backlight_choices(), mock.Mock(), None)

    assert result == expected


def test_select_choice_by_number_out_of_range():
    with pytest.raises(Exception, match="possible values"):
        config.select_choice("4", backlight_choices(), mock.Mock(), None)
