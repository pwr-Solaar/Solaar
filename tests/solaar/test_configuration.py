from dataclasses import dataclass

import pytest

from solaar import configuration


@dataclass
class FakeDevice:
    name: str
    wpid: str
    _serial: str
    modelId: str
    unitId: str
    online: bool = True

    @property
    def _name(self):
        return self.name

    @property
    def serial(self):
        return self._serial


@pytest.fixture(autouse=True)
def reset_config():
    original_config = configuration._config
    configuration._config = ["test-version"]
    yield
    configuration._config = original_config


def test_persister_matches_receiver_serial_to_direct_unit_id():
    direct_entry = configuration._DeviceEntry(
        _NAME="G502 X LIGHTSPEED",
        _wpid="409F",
        _modelId="409FC0980000",
        _unitId="92050B60",
        sensitivity=1200,
    )
    configuration._config.append(direct_entry)

    receiver_device = FakeDevice(
        name="G502 X LIGHTSPEED",
        wpid="409F",
        _serial="92050B60",
        modelId="409FC0980000",
        unitId=None,
    )

    entry = configuration.persister(receiver_device)

    assert entry is direct_entry
    assert entry["sensitivity"] == 1200
    assert entry["_serial"] == "92050B60"


def test_persister_matches_direct_unit_id_to_receiver_serial():
    receiver_entry = configuration._DeviceEntry(
        _NAME="G502 X LIGHTSPEED",
        _wpid="409F",
        _serial="92050B60",
        sensitivity=1200,
    )
    configuration._config.append(receiver_entry)

    direct_device = FakeDevice(
        name="G502 X LIGHTSPEED",
        wpid="409F",
        _serial=None,
        modelId="409FC0980000",
        unitId="92050B60",
    )

    entry = configuration.persister(direct_device)

    assert entry is receiver_entry
    assert entry["sensitivity"] == 1200
    assert entry["_modelId"] == "409FC0980000"
    assert entry["_unitId"] == "92050B60"
