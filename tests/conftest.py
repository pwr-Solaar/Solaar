import pytest

from .fakes import hidpp20_device


@pytest.fixture
def device():
    yield hidpp20_device.Hidpp20Device()
