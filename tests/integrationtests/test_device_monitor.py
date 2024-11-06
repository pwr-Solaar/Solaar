import platform
import time

import pytest


@pytest.mark.skipif(platform.system() == "Linux", reason="Test for non Linux platforms")
def test_device_monitor(mocker):
    from hidapi.hidapi_impl import DeviceMonitor

    mock_callback = mocker.Mock()
    monitor = DeviceMonitor(device_callback=mock_callback, polling_delay=1)
    monitor.start()

    while not monitor.is_alive():
        time.sleep(0.1)

    assert monitor.alive

    monitor.stop()

    while monitor.is_alive():
        time.sleep(0.1)

    assert not monitor.alive
