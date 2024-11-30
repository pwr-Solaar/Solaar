import platform

from unittest import mock

if platform.system() == "Linux":
    import hidapi.udev_impl as hidapi
else:
    import hidapi.hidapi_impl as hidapi


def test_find_paired_node():
    hidapi.enumerate(mock.Mock())
