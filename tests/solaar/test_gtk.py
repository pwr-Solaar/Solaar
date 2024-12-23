from solaar.gtk import create_parser


def test_arg_parse():
    parser = create_parser()
    res = parser.parse_args([])

    assert res.debug == 0
    assert res.hidraw_path is None
    assert res.restart_on_wake_up is False
    assert res.window is None
    assert res.battery_icons is None
    assert res.tray_icon_size is None


def test_arg_parse_debug():
    parser = create_parser()
    res = parser.parse_args(["--debug"])

    assert res.debug == 1


def test_arg_parse_version():
    parser = create_parser()
    res = parser.parse_args(["version"])

    assert res
