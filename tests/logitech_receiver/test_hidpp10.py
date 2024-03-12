import pytest

from lib.logitech_receiver import hidpp10
from lib.logitech_receiver import hidpp10_constants


class FakeDevice:
    kind = "fake"
    online = True
    registers = [hidpp10_constants.REGISTERS.three_leds]

    def request(self, *params):
        return b"fake request"

    def read_register(self, register_number, *params):
        return "fake register"


@pytest.fixture
def setup_hidpp10():
    device = FakeDevice()
    hid = hidpp10.Hidpp10()

    yield device, hid


def test_hidpp10(setup_hidpp10):
    device, hid = setup_hidpp10

    firmwares = hid.get_firmware(device)

    assert len(firmwares) == 3
    for firmware in firmwares:
        assert firmware.kind in ["Firmware", "Bootloader", "Other"]


def test_set_3leds(setup_hidpp10, mocker):
    device, hid = setup_hidpp10
    spy_write_register = mocker.spy(hidpp10, "write_register")

    hid.set_3leds(device)

    spy_write_register.assert_called_once_with(device, hidpp10_constants.REGISTERS.three_leds, 17, 17)
