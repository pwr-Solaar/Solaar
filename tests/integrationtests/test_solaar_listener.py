from solaar.listener import SolaarListener


def test_solaar_listener(mocker):
    receiver = mocker.MagicMock()
    receiver.handle = 1
    receiver.path = "dsda"
    status_callback = mocker.MagicMock()

    rl = SolaarListener(receiver, status_callback)
    # rl.run()
    # rl.stop()

    assert not rl.is_alive()
    assert status_callback.call_count == 0
