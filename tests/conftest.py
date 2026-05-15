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
