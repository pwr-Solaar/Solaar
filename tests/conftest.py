import pytest

from fakes import hidpp10_device

from .fakes import hidpp20_device


@pytest.fixture
def device_hidpp10():
    yield hidpp10_device.Hidpp10Device()


@pytest.fixture
def device():
    yield hidpp20_device.Hidpp20Device()
