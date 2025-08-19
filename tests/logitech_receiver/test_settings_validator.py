import pytest

from logitech_receiver import settings_validator


@pytest.mark.parametrize(
    "current, new, expected",
    [
        (False, "toggle", True),
        (True, "~", False),
        ("don't care", True, True),
        ("don't care", "true", True),
        ("don't care", "false", False),
        ("don't care", "no", False),
        ("don't care", "off", False),
        ("don't care", "True", True),
        ("don't care", "yes", True),
        ("don't care", "on", True),
        ("anything", "anything", None),
    ],
)
def test_bool_or_toggle(current, new, expected):
    result = settings_validator.bool_or_toggle(current=current, new=new)

    assert result == expected
