import platform

from unittest import mock

import pytest

from solaar.ui import diversion_rules


@pytest.mark.skipif(
    platform.system() == "Linux",
    reason="Not functional on Linux yet",
)
@pytest.mark.parametrize(
    "component, left_label, right_label, icon_name",
    [
        ("RuleComponentUI", "RuleComponentUI", "", ""),
        ("RuleUI", "Rule", "", "format-justify-fill"),
        ("AndUI", "And", "", ""),
        ("OrUI", "Or", "", ""),
        ("LaterUI", "Later", "delay123", ""),
        ("NotUI", "Not", "", ""),
        ("ActionUI", "ActionUI", "", "go-next"),
    ],
)
def test_rule_component_ui_classes(
    component,
    left_label,
    right_label,
    icon_name,
):
    cls = getattr(diversion_rules, component)
    default_mock = mock.PropertyMock(delay="delay123")

    rule_comp = cls(mock.MagicMock())

    assert cls.left_label(rule_comp) == left_label
    assert cls.right_label(default_mock) == right_label
    assert cls.icon_name() == icon_name


def test_device_info():
    expected_serial = "Serial123"

    device_info = diversion_rules.DeviceInfo(serial=expected_serial)

    assert device_info.serial == expected_serial


@pytest.mark.parametrize(
    "serial, expected",
    [
        ("Serial12", False),
        ("Serial123", True),
        ("Serial1234", False),
    ],
)
def test_device_info_matches(serial, expected):
    device_info = diversion_rules.DeviceInfo(serial=serial)

    result = device_info.matches("Serial123")

    assert result == expected


def test_device_info_update():
    expected_serial = "Serial123"
    expected_unit_id = "Id123"
    device_update = diversion_rules.DeviceInfo(
        serial=expected_serial,
        unitId=expected_unit_id,
    )
    device_info = diversion_rules.DeviceInfo()

    device_info.update(device_update)

    assert device_info.serial == expected_serial
    assert device_info.unitId == expected_unit_id
    assert device_info.identifiers == [expected_serial, expected_unit_id]
    assert device_info.display_name == f" ({expected_serial})"
