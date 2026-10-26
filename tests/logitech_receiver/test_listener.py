## Copyright (C) 2026  Solaar Contributors https://pwr-solaar.github.io/Solaar/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import time

import pytest

from logitech_receiver import base
from logitech_receiver import device
from logitech_receiver import exceptions
from logitech_receiver import hidpp20
from logitech_receiver import listener
from logitech_receiver.hidpp20_constants import ErrorCode

_hidpp20 = hidpp20.Hidpp20()


class BluetoothMouse:
    """A directly connected HID++ 2.0 mouse, like an MX Master 4 on Bluetooth right after it connects.

    Its first answer to ROOT.GetFeature(DEVICE_NAME) carries the FEATURE_SET index (1), so the
    device kind request goes to the wrong feature and is rejected with INVALID_FUNCTION.
    Later lookups return the real index (3), unless stale is set."""

    isDevice = True
    online = True
    protocol = 2.0
    centurion = False
    path = "/dev/hidraw-test"

    feature_request = device.Device.feature_request

    def __init__(self, stale=False):
        self.handle = 1
        self.features = hidpp20.FeaturesArray(self)
        self.stale = stale
        self.device_name_lookups = 0
        self.changes = []

    def request(self, request_id, *params, no_reply=False):
        params = b"".join(params)
        if request_id == 0x0000 and params == b"\x00\x01":  # ROOT.GetFeature(FEATURE_SET)
            return bytes.fromhex("010000")
        if request_id == 0x0100:  # FEATURE_SET.GetCount
            return bytes.fromhex("04")
        if request_id == 0x0000 and params == b"\x00\x05":  # ROOT.GetFeature(DEVICE_NAME)
            self.device_name_lookups += 1
            return bytes.fromhex("010000" if self.stale or self.device_name_lookups == 1 else "030000")
        if request_id == 0x0120:  # function 2 at the FEATURE_SET index
            raise exceptions.FeatureCallError(number=0xFF, request=0x012B, error=ErrorCode.INVALID_FUNCTION, params=b"")
        if request_id == 0x0320:  # DEVICE_NAME.GetDeviceType
            return bytes.fromhex("03")  # mouse

    def ping(self):
        return True

    def changed(self, active=None, alert=None, reason=None, push=False):
        self.changes.append((active, reason))


class KindListener(listener.EventsListener):
    """Reads the device kind at start-up, as SolaarListener does through device.kind."""

    def __init__(self, receiver):
        super().__init__(receiver, lambda n: None)
        self.starts = 0
        self.kind = None

    def has_started(self):
        self.starts += 1
        self.kind = _hidpp20.get_kind(self.receiver)


@pytest.fixture
def no_input(monkeypatch):
    """No notifications from the device, and quick start-up retries."""

    def read(handle, timeout=0):
        time.sleep(0.005)

    monkeypatch.setattr(base, "read", read)
    monkeypatch.setattr(listener, "_START_RETRY_DELAY", 0.01, raising=False)
    monkeypatch.setattr(listener, "_START_RETRIES", 3, raising=False)


def run_until(thread, condition, timeout=2.0):
    thread.start()
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        time.sleep(0.01)


def test_listener_retries_failed_start_up(no_input):
    mouse = BluetoothMouse()
    events = KindListener(mouse)
    try:
        run_until(events, lambda: mouse.changes)

        assert events.is_alive()
        assert events.starts == 2
        assert events.kind == "mouse"
        assert mouse.changes == [(True, "initialization")]
    finally:
        events.stop()
        events.join(2)
    assert not events.is_alive()


def test_listener_stops_retrying_but_keeps_running(no_input):
    mouse = BluetoothMouse(stale=True)
    events = KindListener(mouse)
    try:
        run_until(events, lambda: events.starts > 3)
        time.sleep(0.1)

        assert events.is_alive()
        assert events.starts == 4
        assert events.kind is None
        assert mouse.changes == []
    finally:
        events.stop()
        events.join(2)
