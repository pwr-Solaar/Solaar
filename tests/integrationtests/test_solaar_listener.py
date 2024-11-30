from solaar.listener import SolaarListener


# @pytest.mark.skip(reason="Unstable")
def test_solaar_listener(mocker):
    receiver = mocker.MagicMock()
    receiver.handle = mocker.MagicMock()
    receiver.path = "dsda"
    status_callback = mocker.MagicMock()
    low_level_mock = mocker.MagicMock()

    rl = SolaarListener(receiver, status_callback, low_level_mock)
    rl.start()
    rl.stop()

    rl.join()

    assert not rl.is_alive()
    assert status_callback.call_count == 0
