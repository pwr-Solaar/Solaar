from logitech_receiver.listener import EventsListener


def test_events_listener(mocker):
    receiver = mocker.MagicMock()
    receiver.handle = 1
    receiver.path = "pathname"
    status_callback = mocker.MagicMock()
    low_level_mock = mocker.MagicMock()

    e = EventsListener(receiver, status_callback, low_level_mock)
    e.start()

    assert bool(e)

    e.stop()
