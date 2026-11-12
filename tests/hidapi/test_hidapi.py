import platform

from unittest import mock

if platform.system() == "Linux":
    import hidapi.udev_impl as hidapi
else:
    import hidapi.hidapi_impl as hidapi


def test_find_paired_node():
    hidapi.enumerate(mock.Mock())


if platform.system() == "Linux":
    import pytest

    @pytest.mark.parametrize(
        "hidpp_short, hidpp_long, centurion, expected",
        [
            (None, None, False, (None, None)),  # unparsable descriptor keeps fallback to product ID ranges
            (False, False, False, (False, False)),
            (True, False, False, (True, False)),
            (False, True, False, (False, True)),
            (False, False, True, (True, True)),
            (None, None, True, (True, True)),
        ],
    )
    def test_filter_hidpp_flags(hidpp_short, hidpp_long, centurion, expected):
        assert hidapi._filter_hidpp_flags(hidpp_short, hidpp_long, centurion) == expected
