from unittest import mock

import pytest

from solaar.ui import rule_conditions


@pytest.mark.parametrize(
    "component, left_label, right_label, icon_name",
    [
        ("ConditionUI", "ConditionUI", "", "dialog-question"),
        ("ProcessUI", "Process", "process123", "dialog-question"),
        ("MouseProcessUI", "MouseProcess", "process123", "dialog-question"),
        ("FeatureUI", "Feature", "12 (000C)", "dialog-question"),
        ("ReportUI", "Report", "report123", "dialog-question"),
        ("ModifiersUI", "Modifiers", "None", "dialog-question"),
        ("KeyUI", "Key", "123 (007B) (action123)", "dialog-question"),
        ("KeyIsDownUI", "KeyIsDown", "123 (007B)", "dialog-question"),
        ("TestUI", "Test", "test123 'param'", "dialog-question"),
        ("TestBytesUI", "Test bytes", "test123", "dialog-question"),
        ("MouseGestureUI", "Mouse Gesture", "No-op", "dialog-question"),
    ],
)
def test_rule_component_ui_classes(
    component,
    left_label,
    right_label,
    icon_name,
):
    cls = getattr(rule_conditions, component)
    process_mock = mock.PropertyMock(
        process="process123",
        feature="12",
        report="report123",
        action="action123",
        parameter="param",
        key="123",
        test="test123",
        __add__="",
    )

    rule_comp = cls(mock.MagicMock())

    assert cls.left_label(rule_comp) == left_label
    assert cls.right_label(process_mock) == right_label
    assert cls.icon_name() == icon_name
