import textwrap

from unittest import mock
from unittest.mock import mock_open

import pytest

from logitech_receiver import diversion
from logitech_receiver.base import HIDPPNotification
from logitech_receiver.hidpp20_constants import SupportedFeature


@pytest.fixture
def rule_config():
    rule_content = """
    %YAML 1.3
    ---
    - MouseGesture: Mouse Left
    - KeyPress:
      - [Control_L, Alt_L, Left]
      - click
    ...
    ---
    - MouseGesture: Mouse Up
    - KeyPress:
      - [Super_L, Up]
      - click
    ...
    ---
    - Test: [thumb_wheel_up, 10]
    - KeyPress:
      - [Control_L, Page_Down]
      - click
    ...
    ---
    """
    return textwrap.dedent(rule_content)


def test_load_rule_config(rule_config):
    expected_rules = [
        [
            diversion.MouseGesture,
            diversion.KeyPress,
        ],
        [diversion.MouseGesture, diversion.KeyPress],
        [diversion.Test, diversion.KeyPress],
    ]

    with mock.patch("builtins.open", new=mock_open(read_data=rule_config)):
        loaded_rules = diversion._load_rule_config(file_path=mock.Mock())

    assert len(loaded_rules.components) == 2  # predefined and user configured rules
    user_configured_rules = loaded_rules.components[0]
    assert isinstance(user_configured_rules, diversion.Rule)

    for components, expected_components in zip(user_configured_rules.components, expected_rules):
        for component, expected_component in zip(components.components, expected_components):
            assert isinstance(component, expected_component)


def test_diversion_rule():
    args = [
        {
            "Rule": [  # Implement problematic keys for Craft and MX Master
                {"Rule": [{"Key": ["Brightness Down", "pressed"]}, {"KeyPress": "XF86_MonBrightnessDown"}]},
                {"Rule": [{"Key": ["Brightness Up", "pressed"]}, {"KeyPress": "XF86_MonBrightnessUp"}]},
            ]
        },
    ]

    rule = diversion.Rule(args)

    assert len(rule.components) == 1
    root_rule = rule.components[0]
    assert isinstance(root_rule, diversion.Rule)

    assert len(root_rule.components) == 2
    for component in root_rule.components:
        assert isinstance(component, diversion.Rule)
        assert len(component.components) == 2

        key = component.components[0]
        assert isinstance(key, diversion.Key)
        key = component.components[1]
        assert isinstance(key, diversion.KeyPress)


def test_key_is_down():
    result = diversion.key_is_down(key=diversion.CONTROL.G2)

    assert result is False


def test_feature():
    expected_data = {"Feature": "CONFIG CHANGE"}

    result = diversion.Feature("CONFIG_CHANGE")

    assert result.data() == expected_data


@pytest.mark.parametrize(
    "feature, data",
    [
        (
            SupportedFeature.REPROG_CONTROLS_V4,
            [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08],
        ),
        (SupportedFeature.GKEY, [0x01, 0x02, 0x03, 0x04]),
        (SupportedFeature.MKEYS, [0x01, 0x02, 0x03, 0x04]),
        (SupportedFeature.MR, [0x01, 0x02, 0x03, 0x04]),
        (SupportedFeature.THUMB_WHEEL, [0x01, 0x02, 0x03, 0x04, 0x05]),
        (SupportedFeature.DEVICE_UNIT_ID, [0x01, 0x02, 0x03, 0x04, 0x05]),
    ],
)
def test_process_notification(feature, data):
    device_mock = mock.Mock()
    notification = HIDPPNotification(
        report_id=0x01,
        devnumber=1,
        sub_id=0x13,
        address=0x00,
        data=bytes(data),
    )

    diversion.process_notification(device_mock, notification, feature)


def test_update_active_window():
    """Test that update_active_window caches the window information."""
    # Clear any cached value
    diversion._cached_active_window = None

    # Update the cached active window
    test_wm_class = "test_application"
    diversion.update_active_window(test_wm_class)

    # Verify it was cached
    assert diversion._cached_active_window == test_wm_class


def test_update_pointer_over_window():
    """Test that update_pointer_over_window caches the window information."""
    # Clear any cached value
    diversion._cached_pointer_over_window = None

    # Update the cached pointer-over window
    test_wm_class = "test_pointer_application"
    diversion.update_pointer_over_window(test_wm_class)

    # Verify it was cached
    assert diversion._cached_pointer_over_window == test_wm_class


def test_get_active_window_info_with_cache():
    """Test that get_active_window_info returns cached value when available."""
    # Set a cached value
    test_wm_class = "cached_app"
    diversion._cached_active_window = test_wm_class

    # Get window info
    result = diversion.get_active_window_info()

    # Should return the cached value as a tuple
    assert result == (test_wm_class,)

    # Clean up
    diversion._cached_active_window = None


def test_get_pointer_window_info_with_cache():
    """Test that get_pointer_window_info returns cached value when available."""
    # Set a cached value
    test_wm_class = "cached_pointer_app"
    diversion._cached_pointer_over_window = test_wm_class

    # Get window info
    result = diversion.get_pointer_window_info()

    # Should return the cached value as a tuple
    assert result == (test_wm_class,)

    # Clean up
    diversion._cached_pointer_over_window = None


def test_process_condition_with_cached_window():
    """Test that Process condition works with cached window information."""
    # Set up cached window
    test_wm_class = "firefox"
    diversion._cached_active_window = test_wm_class

    # Create Process condition
    process_condition = diversion.Process("fire", warn=False)

    # Create mock notification and device
    notification = mock.Mock()
    device = mock.Mock()

    # Evaluate - should match because "firefox" starts with "fire"
    result = process_condition.evaluate(None, notification, device, None)
    assert result is True

    # Test non-matching case
    process_condition2 = diversion.Process("chrome", warn=False)
    result2 = process_condition2.evaluate(None, notification, device, None)
    assert result2 is False

    # Clean up
    diversion._cached_active_window = None


def test_mouse_process_condition_with_cached_window():
    """Test that MouseProcess condition works with cached window information."""
    # Set up cached window
    test_wm_class = "konsole"
    diversion._cached_pointer_over_window = test_wm_class

    # Create MouseProcess condition
    mouse_process_condition = diversion.MouseProcess("kon", warn=False)

    # Create mock notification and device
    notification = mock.Mock()
    device = mock.Mock()

    # Evaluate - should match because "konsole" starts with "kon"
    result = mouse_process_condition.evaluate(None, notification, device, None)
    assert result is True

    # Test non-matching case
    mouse_process_condition2 = diversion.MouseProcess("term", warn=False)
    result2 = mouse_process_condition2.evaluate(None, notification, device, None)
    assert result2 is False

    # Clean up
    diversion._cached_pointer_over_window = None
