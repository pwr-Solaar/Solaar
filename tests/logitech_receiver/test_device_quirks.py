## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import pytest

from logitech_receiver import common
from logitech_receiver import device_quirks
from logitech_receiver import settings_templates
from logitech_receiver.hidpp20_constants import SupportedFeature

from . import fake_hidpp

G560 = "000000000A78"


def _firmware(*versions, kind=common.FirmwareKind.Firmware):
    return tuple(common.FirmwareInfo(kind, "U", version, None) for version in versions)


class FakeDevice:
    def __init__(self, model_id=G560, firmware=()):
        self.modelId = model_id
        self.firmware = firmware


@pytest.mark.parametrize(
    "version, equalizer_inert, bass_inert",
    [
        ("122.04.B0370", True, False),  # verified on hardware: EQ silent, bass audible
        ("122.03.B0023", True, False),  # the swap version itself
        ("122.03.B0022", False, True),  # one build below the swap
        ("122.02.B9999", False, True),
        ("98.03.B0027", False, True),  # pre-rollover: mis-decoding this as 98 vs 122 flips both
    ],
)
def test_setting_inert_g560_firmware_boundary(version, equalizer_inert, bass_inert):
    device = FakeDevice(firmware=_firmware(version))

    assert device_quirks.setting_inert(device, "equalizer") is equalizer_inert
    assert device_quirks.setting_inert(device, "bass_tone") is bass_inert


def test_setting_inert_folds_hundreds_digit_from_name_prefix():
    """The G560 reports version 122 on the wire as name "U1 " plus number 22."""
    device = FakeDevice(firmware=(common.FirmwareInfo(common.FirmwareKind.Firmware, "U1 ", "22.04.B0370", None),))

    assert device_quirks.setting_inert(device, "equalizer") is True
    assert device_quirks.setting_inert(device, "bass_tone") is False


def test_setting_inert_uses_highest_main_firmware():
    device = FakeDevice(firmware=_firmware("122.02.B0001", "122.04.B0370"))

    assert device_quirks.setting_inert(device, "equalizer") is True


def test_setting_inert_ignores_non_main_firmware():
    device = FakeDevice(firmware=_firmware("122.04.B0370", kind=common.FirmwareKind.Bootloader) + _firmware("122.02.B0001"))

    assert device_quirks.setting_inert(device, "equalizer") is False


@pytest.mark.parametrize(
    "device",
    [
        FakeDevice(firmware=()),  # firmware unreadable
        FakeDevice(firmware=_firmware("nonsense")),  # firmware unparsable
        FakeDevice(firmware=_firmware("122.04.B0370", kind=common.FirmwareKind.Bootloader)),
        FakeDevice(model_id="", firmware=_firmware("122.04.B0370")),
        FakeDevice(model_id="B38940B4C355", firmware=_firmware("122.04.B0370")),  # unlisted model
    ],
)
def test_setting_inert_fails_open(device):
    assert device_quirks.setting_inert(device, "equalizer") is False
    assert device_quirks.setting_inert(device, "bass_tone") is False


def test_setting_inert_unlisted_setting():
    device = FakeDevice(firmware=_firmware("122.04.B0370"))

    assert device_quirks.setting_inert(device, "sidetone") is False


def test_setting_inert_experimental_bypass(monkeypatch):
    monkeypatch.setenv("SOLAAR_EXPERIMENTAL", "1")
    device = FakeDevice(firmware=_firmware("122.04.B0370"))

    assert device_quirks.setting_inert(device, "equalizer") is False


def _g560_equalizer_device(version):
    """A G560 reporting the EQ capabilities from its docs/devices scan."""
    device = fake_hidpp.Device(
        feature=SupportedFeature.EQUALIZER,
        responses=[
            fake_hidpp.Response("021A00EC06", 0x0400),
            fake_hidpp.Response("0000200040", 0x0410, "00"),
        ],
    )
    device.modelId = G560
    device.firmware = _firmware(version)
    return device


def test_equalizer_suppressed_on_stubbed_firmware():
    assert settings_templates.Equalizer.build(_g560_equalizer_device("122.04.B0370")) is None


def test_equalizer_built_on_firmware_with_hardware_eq():
    assert settings_templates.Equalizer.build(_g560_equalizer_device("122.03.B0022")) is not None
