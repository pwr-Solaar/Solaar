from hid_parser.data import Button
from hid_parser.data import Consumer


def test_consumer():
    consumer = Consumer()

    assert consumer.PLAY_PAUSE == 0xCD


def test_button():
    button = Button()

    assert button.NO_BUTTON == 0x0
    assert button.BUTTON_1 == 0x1
