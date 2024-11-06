from logitech_receiver.listener import EventsListener


def test_events_listener(mocker):
    receiver = mocker.MagicMock()
    status_callback = mocker.MagicMock()

    e = EventsListener(receiver, status_callback)
    e.start()

    assert bool(e)

    e.stop()

    assert not bool(e)
    assert status_callback.call_count == 0
