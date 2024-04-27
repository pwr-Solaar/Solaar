import textwrap

from unittest import mock
from unittest.mock import mock_open

import pytest

from logitech_receiver import diversion


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
