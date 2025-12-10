from logitech_receiver.hidpp10_constants import Registers


class Hidpp10Device:
    def __init__(self):
        self._iteration = 0

    @property
    def kind(self):
        pass

    def request(self, request_id, *params, no_reply=False):
        if request_id == 0x8100 + Registers.BATTERY_STATUS:
            return b"fff"
        elif request_id == 0x8000:
            return bytes([0x10, 0x10, 0x00])

        raise RuntimeError(f"Unsupported feature: {request_id:04X}")
