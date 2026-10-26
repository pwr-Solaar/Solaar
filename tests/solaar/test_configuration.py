import errno
import logging
import os

import yaml

from solaar import configuration


def _set_config(dpi):
    configuration._config[:] = ["1.1.20", configuration._DeviceEntry(_NAME="Test Mouse", _wpid="1234", dpi=dpi)]


def test_do_save_writes_config(tmp_path):
    _set_config(1600)

    configuration.do_save()

    with open(configuration._yaml_file_path) as config_file:
        assert yaml.safe_load(config_file) == ["1.1.20", {"_NAME": "Test Mouse", "_wpid": "1234", "dpi": 1600}]
    assert os.listdir(tmp_path) == ["config.yaml"]


def test_do_save_failure_keeps_previous_config(tmp_path, monkeypatch, caplog):
    _set_config(1600)
    configuration.do_save()
    with open(configuration._yaml_file_path) as config_file:
        previous = config_file.read()

    def dump_until_disk_full(data, stream, **kwargs):
        stream.write("- 1.1.20\n- _NAME: Test")
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

    monkeypatch.setattr(configuration.yaml, "dump", dump_until_disk_full)
    _set_config(800)

    with caplog.at_level(logging.ERROR, logger=configuration.__name__):
        configuration.do_save()

    with open(configuration._yaml_file_path) as config_file:
        assert config_file.read() == previous
    assert os.listdir(tmp_path) == ["config.yaml"]
    assert "failed to save to" in caplog.text


def test_do_save_keeps_symlink_and_mode(tmp_path, monkeypatch):
    target_dir = tmp_path / "dotfiles"
    target_dir.mkdir()
    target = target_dir / "config.yaml"
    target.write_text("[]\n")
    target.chmod(0o600)
    link = tmp_path / "solaar" / "config.yaml"
    link.parent.mkdir()
    link.symlink_to(target)
    monkeypatch.setattr(configuration, "_yaml_file_path", str(link))
    _set_config(1600)

    configuration.do_save()

    assert link.is_symlink()
    assert yaml.safe_load(target.read_text())[1]["dpi"] == 1600
    assert target.stat().st_mode & 0o777 == 0o600
    assert os.listdir(target_dir) == ["config.yaml"]
