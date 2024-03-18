from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from gi.repository import Gtk
from logitech_receiver import common
from logitech_receiver import hidpp10_constants
from logitech_receiver import receiver
from solaar.ui import pair_window


@dataclass
class TestReceiver:
    name: str
    receiver_kind: common.NamedInt
    _remaining_pairings: Optional[int] = None
    pairing: receiver.Pairing = field(default_factory=receiver.Pairing)

    def reset_pairing(self):
        self.receiver = receiver.Pairing()

    def remaining_pairings(self):
        return self._remaining_pairings

    def set_lock(self, value, timeout=0):
        return True


def test_create():
    test_receiver = TestReceiver("test keyboard", hidpp10_constants.DEVICE_KIND.keyboard)
    test_receiver.pairing.lock_open = True
    assert test_receiver.pairing.lock_open is True

    Gtk.init_check()

    assistant = pair_window.create(test_receiver)

    print("ASSISTANT", assistant)
    print("ASSISTANT ROLE", assistant.get_role())
    print("ASSISTANT CHILDREN", assistant.get_children())
    print("ASSISTANT CHILDREN", assistant.get_children()[0].get_children())
    assert assistant is not None
    assert test_receiver.pairing.lock_open is True

    assistant.show()
    print(assistant.get_children())
    print(assistant.get_children()[0].get_children())

    assistant.emit("prepare", assistant.get_nth_page(0))
    assistant.emit("prepare", assistant.get_nth_page(0))
    assistant.emit("prepare", assistant.get_nth_page(0))
    assistant.emit("prepare", assistant.get_nth_page(0))
