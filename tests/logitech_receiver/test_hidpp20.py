from logitech_receiver import common
from logitech_receiver import hidpp20
from logitech_receiver.common import FirmwareKind
from logitech_receiver.hidpp20_constants import SupportedFeature

_hidpp20 = hidpp20.Hidpp20()


def test_get_firmware(device):
    result = _hidpp20.get_firmware(device)

    assert result == (
        common.FirmwareInfo(
            kind=FirmwareKind.Bootloader,
            name="ABC",
            version="03.04.B0100",
            extras=b"\x01\x00\x01\x02\x03\x04\x05",
        ),
        common.FirmwareInfo(
            kind=FirmwareKind.Hardware,
            name="",
            version="65",
            extras=None,
        ),
    )


def test_get_kind(device):
    result = _hidpp20.get_kind(device)

    assert result == "keyboard"
    assert result == 1


def test_get_name(device):
    result = _hidpp20.get_name(device)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_friendly_name(device):
    result = _hidpp20.get_friendly_name(device)

    assert result == "ABCDEFGHIJKLMNOPQR"


def test_get_battery_status(device):
    feature, battery = _hidpp20.get_battery_status(device)

    assert feature == SupportedFeature.BATTERY_STATUS
    assert battery.level == 80
    assert battery.next_level == 32
    assert battery.status == common.BatteryStatus.DISCHARGING


def test_get_vertical_scrolling_info(device):
    result = _hidpp20.get_vertical_scrolling_info(device)

    assert result == {"roller": "standard", "ratchet": 8, "lines": 12}


def test_get_high_resolution_scrolling_info(device):
    mode, resolution = _hidpp20.get_hi_res_scrolling_info(device)

    assert mode == 0x1
    assert resolution == 0x2


def test_get_mouse_pointer_info(device):
    result = _hidpp20.get_mouse_pointer_info(device)

    assert result == {
        "dpi": 0x100,
        "acceleration": "med",
        "suggest_os_ballistics": False,
        "suggest_vertical_orientation": True,
    }


def test_get_pointer_speed_info(device):
    result = _hidpp20.get_pointer_speed_info(device)

    assert result == 0x0103 / 256
