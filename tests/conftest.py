import importlib

from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def isolate_solaar_configuration(tmp_path, monkeypatch):
    """Redirect solaar.configuration at a throwaway path for every test.

    Tests build FakeDevices named 'TestDevice'; any that touch device.settings
    or device.persister without mocking call the real configuration.persister(),
    which loads and rewrites ~/.config/solaar/config.yaml — appending a fresh
    un-matchable TestDevice entry on every run. Pointing the paths at tmp_path
    and clearing the cached _config keeps each test off the real config and
    isolated from every other test."""
    from solaar import configuration

    monkeypatch.setattr(configuration, "_yaml_file_path", str(tmp_path / "config.yaml"))
    monkeypatch.setattr(configuration, "_json_file_path", str(tmp_path / "config.json"))
    monkeypatch.setattr(configuration, "_config", [])


@pytest.fixture(autouse=True)
def mock_desktop_notifications(monkeypatch):
    """Swap the libnotify backend for a mock in both desktop_notifications
    modules. Tests still exercise the real init/alert/show code paths, but
    Notification.show() never reaches the daemon — without this the suite
    raises real 'MockDevice' / 'unknown' notifications on every run.

    Returns the Notify mock so notification tests can assert against it."""
    notify = mock.MagicMock(name="Notify")
    notify.is_initted.return_value = True
    notify.init.return_value = True
    for modname in ("solaar.ui.desktop_notifications", "logitech_receiver.desktop_notifications"):
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue
        monkeypatch.setattr(module, "Notify", notify, raising=False)
        monkeypatch.setattr(module, "_notifications", {}, raising=False)
    return notify
