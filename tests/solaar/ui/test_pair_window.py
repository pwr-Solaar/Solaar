from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import List
from typing import Optional

import gi
import pytest

from logitech_receiver import receiver
from solaar.ui import pair_window

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # NOQA: E402

gtk_init = Gtk.init_check()[0]


@dataclass
class Device:
    name: str = "test device"
    kind: str = "test kind"


@dataclass
class Receiver:
    name: str
    receiver_kind: str
    _set_lock: bool = True
    pairing: receiver.Pairing = field(default_factory=receiver.Pairing)
    pairable: bool = True
    _remaining_pairings: Optional[int] = None

    def reset_pairing(self):
        self.receiver = receiver.Pairing()

    def remaining_pairings(self, cache=True):
        return self._remaining_pairings

    def set_lock(self, value=False, timeout=0):
        self.pairing.lock_open = self._set_lock
        return self._set_lock

    def discover(self, cancel=False, timeout=30):
        self.pairing.discovering = self._set_lock
        return self._set_lock

    def pair_device(self, pair=True, slot=0, address=b"\0\0\0\0\0\0", authentication=0x00, entropy=20, force=False):
        print("PD", self.pairable)
        return self.pairable


@dataclass
class Assistant:
    drawable: bool = True
    pages: List[Any] = field(default_factory=list)

    def is_drawable(self):
        return self.drawable

    def next_page(self):
        return True

    def set_page_complete(self, page, b):
        return True

    def commit(self):
        return True

    def append_page(self, page):
        self.pages.append(page)

    def remove_page(self, page):
        return True

    def set_page_type(self, page, type):
        return True

    def destroy(self):
        pass


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
@pytest.mark.parametrize(
    "receiver, lock_open, discovering, page_type",
    [
        (Receiver("unifying", "unifying", True), True, False, Gtk.AssistantPageType.PROGRESS),
        (Receiver("unifying", "unifying", False), False, False, Gtk.AssistantPageType.SUMMARY),
        (Receiver("nano", "nano", True, _remaining_pairings=5), True, False, Gtk.AssistantPageType.PROGRESS),
        (Receiver("nano", "nano", False), False, False, Gtk.AssistantPageType.SUMMARY),
        (Receiver("bolt", "bolt", True), False, True, Gtk.AssistantPageType.PROGRESS),
        (Receiver("bolt", "bolt", False), False, False, Gtk.AssistantPageType.SUMMARY),
    ],
)
def test_create(receiver, lock_open, discovering, page_type):
    assistant = pair_window.create(receiver)

    assert assistant is not None
    assert assistant.get_page_type(assistant.get_nth_page(0)) == page_type

    assert receiver.pairing.lock_open == lock_open
    assert receiver.pairing.discovering == discovering


@pytest.mark.parametrize(
    "receiver, expected_result, expected_error",
    [
        (Receiver("unifying", "unifying", True), True, False),
        (Receiver("unifying", "unifying", False), False, True),
        (Receiver("bolt", "bolt", True), True, False),
        (Receiver("bolt", "bolt", False), False, True),
    ],
)
def test_prepare(receiver, expected_result, expected_error):
    result = pair_window.prepare(receiver)

    assert result == expected_result
    assert bool(receiver.pairing.error) == expected_error


@pytest.mark.parametrize("assistant, expected_result", [(Assistant(True), True), (Assistant(False), False)])
def test_check_lock_state_drawable(assistant, expected_result):
    r = Receiver("succeed", "unifying", True, receiver.Pairing(lock_open=True))

    result = pair_window.check_lock_state(assistant, r, 2)

    assert result == expected_result


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
@pytest.mark.parametrize(
    "receiver, count, expected_result",
    [
        (Receiver("fail", "unifying", False, receiver.Pairing(lock_open=False)), 2, False),
        (Receiver("succeed", "unifying", True, receiver.Pairing(lock_open=True)), 1, True),
        (Receiver("error", "unifying", True, receiver.Pairing(error="error")), 0, False),
        (Receiver("new device", "unifying", True, receiver.Pairing(new_device=Device())), 2, False),
        (Receiver("closed", "unifying", True, receiver.Pairing()), 2, False),
        (Receiver("closed", "unifying", True, receiver.Pairing()), 1, False),
        (Receiver("closed", "unifying", True, receiver.Pairing()), 0, False),
        (Receiver("fail bolt", "bolt", False), 1, False),
        (Receiver("succeed bolt", "bolt", True, receiver.Pairing(lock_open=True)), 0, True),
        (Receiver("error bolt", "bolt", True, receiver.Pairing(error="error")), 2, False),
        (Receiver("new device", "bolt", True, receiver.Pairing(lock_open=True, new_device=Device())), 1, False),
        (Receiver("discovering", "bolt", True, receiver.Pairing(lock_open=True)), 1, True),
        (Receiver("closed", "bolt", True, receiver.Pairing()), 2, False),
        (Receiver("closed", "bolt", True, receiver.Pairing()), 1, False),
        (Receiver("closed", "bolt", True, receiver.Pairing()), 0, False),
        (
            Receiver(
                "pass1",
                "bolt",
                True,
                receiver.Pairing(lock_open=True, device_passkey=50, device_authentication=0x01),
            ),
            0,
            True,
        ),
        (
            Receiver(
                "pass2",
                "bolt",
                True,
                receiver.Pairing(lock_open=True, device_passkey=50, device_authentication=0x02),
            ),
            0,
            True,
        ),
        (
            Receiver(
                "adt",
                "bolt",
                True,
                receiver.Pairing(discovering=True, device_address=2, device_name=5),
                pairable=True,
            ),
            2,
            True,
        ),
        (
            Receiver(
                "adf",
                "bolt",
                True,
                receiver.Pairing(discovering=True, device_address=2, device_name=5),
                pairable=False,
            ),
            2,
            False,
        ),
        (Receiver("add fail", "bolt", False, receiver.Pairing(device_address=2, device_passkey=5)), 2, False),
    ],
)
def test_check_lock_state(receiver, count, expected_result):
    assistant = Assistant(True)

    check_state = pair_window._check_lock_state(assistant, receiver, count)

    assert check_state == expected_result


@pytest.mark.parametrize(
    "receiver, pair_device, set_lock, discover, error",
    [
        (
            Receiver("unifying", "unifying", pairing=receiver.Pairing(lock_open=False, error="error")),
            0,
            0,
            0,
            None,
        ),
        (
            Receiver("unifying", "unifying", pairing=receiver.Pairing(lock_open=True, error="error")),
            0,
            1,
            0,
            "error",
        ),
        (Receiver("bolt", "bolt", pairing=receiver.Pairing(lock_open=False, error="error")), 0, 0, 0, None),
        (Receiver("bolt", "bolt", pairing=receiver.Pairing(lock_open=True, error="error")), 1, 0, 0, "error"),
        (Receiver("bolt", "bolt", pairing=receiver.Pairing(discovering=True, error="error")), 0, 0, 1, "error"),
    ],
)
def test_finish(receiver, pair_device, set_lock, discover, error, mocker):
    spy_pair_device = mocker.spy(receiver, "pair_device")
    spy_set_lock = mocker.spy(receiver, "set_lock")
    spy_discover = mocker.spy(receiver, "discover")
    assistant = Assistant(True)

    pair_window._finish(assistant, receiver)

    assert spy_pair_device.call_count == pair_device
    assert spy_set_lock.call_count == set_lock
    assert spy_discover.call_count == discover
    assert receiver.pairing.error == error


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
@pytest.mark.parametrize("error", ["timeout", "device not supported", "too many devices"])
def test_create_failure_page(error, mocker):
    spy_create = mocker.spy(pair_window, "_create_page")

    pair_window._pairing_failed(Assistant(True), Receiver("nano", "nano"), error)

    assert spy_create.call_count == 1


@pytest.mark.parametrize(
    "passkey, authentication, expected",
    [
        ("50", 0x02, ["left"] * 4 + ["right"] * 2 + ["left"] * 2 + ["right"] + ["left"] + ["both"]),
        (50, 0x02, ["left"] * 4 + ["right"] * 2 + ["left"] * 2 + ["right"] + ["left"] + ["both"]),
        ("0", 0x02, ["left"] * 10 + ["both"]),
        ("1023", 0x02, ["right"] * 10 + ["both"]),
        ("000918", 0x01, ["0", "0", "0", "9", "1", "8", "enter"]),
        ("abcdef", 0x02, None),
        ("", 0x02, None),
        (None, 0x02, None),
    ],
)
def test_passkey_steps(passkey, authentication, expected):
    assert pair_window._passkey_steps(passkey, authentication) == expected


def test_passkey_steps_bit_polarity():
    """The receiver never reports which button was pressed, so this mapping cannot be
    validated from inside Solaar and must not be flipped without hardware evidence."""
    steps = pair_window._passkey_steps(f"{0b1010101010:d}", 0x02)

    assert steps == ["right", "left"] * 5 + ["both"]


@pytest.mark.parametrize("steps, expected_cells", [(["left"] * 10 + ["both"], 11), (["1", "2", "enter"], 3)])
def test_step_strip_cells(steps, expected_cells):
    cells, separator_y, width, height = pair_window._step_strip_cells(steps)

    assert [cell.step for cell in cells] == steps
    assert [cell.index for cell in cells] == list(range(expected_cells))
    assert cells[-1].width > cells[0].width  # the final step is drawn larger
    assert cells[-1].y > separator_y  # and below the separator
    assert width > 0 and height > cells[-1].y


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_show_passcode_appends_a_single_page():
    """The periodic check keeps running while the passkey is shown, so the page has to
    be created once and refreshed afterwards instead of being appended again."""
    r = Receiver(
        "passcode",
        "bolt",
        True,
        receiver.Pairing(lock_open=True, device_passkey="50", device_authentication=0x02),
    )
    assistant = Assistant(True)

    first = pair_window._check_lock_state(assistant, r, 0)
    second = pair_window._check_lock_state(assistant, r, 0)

    assert first is True
    assert second is True
    assert len(assistant.pages) == 1


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_show_passcode_updates_status_in_place():
    r = Receiver(
        "passcode",
        "bolt",
        True,
        receiver.Pairing(lock_open=True, device_passkey="50", device_authentication=0x02),
    )
    assistant = Assistant(True)

    pair_window._check_lock_state(assistant, r, 0)
    page = getattr(assistant, pair_window._PASSKEY_PAGE)
    waiting = page.status.get_label()

    r.pairing.passkey_entered = 4
    pair_window._check_lock_state(assistant, r, 0)
    counted = page.status.get_label()

    r.pairing.passkey_complete = True
    pair_window._check_lock_state(assistant, r, 0)
    checking = page.status.get_label()

    assert waiting != counted != checking
    assert "4" in counted
    assert getattr(page.strip, pair_window._PROGRESS) == len(getattr(page.strip, pair_window._STEPS))
    assert len(assistant.pages) == 1


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_show_passcode_clamps_overshoot():
    """The receiver owns the verdict, so more presses than steps must not raise."""
    r = Receiver(
        "passcode",
        "bolt",
        True,
        receiver.Pairing(lock_open=True, device_passkey="50", device_authentication=0x02, passkey_entered=99),
    )
    assistant = Assistant(True)

    assert pair_window._check_lock_state(assistant, r, 0) is True

    page = getattr(assistant, pair_window._PASSKEY_PAGE)
    assert getattr(page.strip, pair_window._PROGRESS) == 99  # clamped when drawn, not when stored


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_show_passcode_survives_unreadable_passkey():
    r = Receiver(
        "passcode",
        "bolt",
        True,
        receiver.Pairing(lock_open=True, device_passkey="oops", device_authentication=0x02),
    )
    assistant = Assistant(True)

    assert pair_window._check_lock_state(assistant, r, 0) is True
    assert pair_window._check_lock_state(assistant, r, 0) is True
    assert len(assistant.pages) == 1


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_pair_device_issued_once(mocker):
    r = Receiver("discovered", "bolt", True, receiver.Pairing(discovering=True, device_address=2, device_name=5))
    spy_pair_device = mocker.spy(r, "pair_device")
    assistant = Assistant(True)

    first = pair_window._check_lock_state(assistant, r, 2)
    second = pair_window._check_lock_state(assistant, r, 2)

    assert first is True
    assert second is True
    assert spy_pair_device.call_count == 1


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
@pytest.mark.parametrize("progress", [None, 0, 5, 10, 11, 15])
@pytest.mark.parametrize("passkey, authentication", [("50", 0x02), ("000918", 0x01)])
def test_draw_step_strip(passkey, authentication, progress):
    """Draws against an image surface, so cairo misuse and a bad highlight clamp are
    caught without needing a display."""
    import cairo

    steps = pair_window._passkey_steps(passkey, authentication)
    strip = pair_window._create_step_strip(steps, "sequence")
    _cells, _separator_y, width, height = pair_window._step_strip_cells(steps)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
    setattr(strip, pair_window._PROGRESS, progress)

    assert pair_window._draw_step_strip(strip, cairo.Context(surface)) is False


@pytest.mark.skipif(not gtk_init, reason="requires Gtk")
def test_draw_step_strip_without_steps():
    import cairo

    strip = Gtk.DrawingArea()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 10, 10)

    assert pair_window._draw_step_strip(strip, cairo.Context(surface)) is False
