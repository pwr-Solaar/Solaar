from unittest import mock

import hidapi


def test_find_paired_node():
    hidapi.enumerate(mock.Mock())
