import pytest

from logitech_receiver import common
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


def _color_validator():
    rng = settings_validator.Range(min=0, max=0xFFFFFF, byte_count=3, value_type=common.ColorInt)
    choices = {
        common.NamedInt(1, "A"): rng,
        common.NamedInt(2, "B"): rng,
        common.NamedInt(3, "C"): rng,
    }
    return settings_validator.MapRangeValidator(choices)


def test_map_range_to_string_formats_plain_int_through_value_type():
    """Configs loaded from YAML come back as plain ints; to_string should
    re-wrap them via the choice's value_type so `solaar show` renders hex
    regardless of whether the dict came from a fresh read or a stale load."""
    v = _color_validator()
    plain = {1: 12590120, 2: 12922150, 3: 16106001}  # what YAML load produces
    rendered = v.to_string(plain)
    assert "0xc01c28" in rendered
    assert "0xc52d26" in rendered
    assert "0xf5c211" in rendered


def test_map_range_to_string_passes_color_int_through():
    v = _color_validator()
    wrapped = {1: common.ColorInt(0xFC3300), 2: common.ColorInt(0x00FF00)}
    rendered = v.to_string(wrapped)
    assert "0xfc3300" in rendered
    assert "0x00ff00" in rendered


def test_map_range_to_string_preserves_sentinel_subclass():
    """NamedInt 'No change' = -1 must not be re-wrapped (its name would be
    lost). The exact-type guard `type(v) is int` excludes it."""
    v = _color_validator()
    mixed = {1: common.ColorInt(0xFC3300), 2: -1}
    rendered = v.to_string(mixed)
    assert "0xfc3300" in rendered
    assert "2:-1" in rendered


def test_map_range_to_string_int_value_type_unchanged():
    """When value_type is the default int, to_string emits decimal as before
    (no behavior change for non-color settings)."""
    rng = settings_validator.Range(min=0, max=255, byte_count=1)
    choices = {common.NamedInt(1, "A"): rng, common.NamedInt(2, "B"): rng}
    v = settings_validator.MapRangeValidator(choices)
    rendered = v.to_string({1: 42, 2: 200})
    assert "1:42" in rendered
    assert "2:200" in rendered
