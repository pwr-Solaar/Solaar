## Copyright (C) 2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

import pytest

from logitech_receiver import device_quirks

G915_TKL = "B35F408EC343"
G502_X_PLUS = "4099C0950000"  # a mouse, listed for another quirk but not this one


class FakeDevice:
    def __init__(self, model_id):
        self.modelId = model_id


@pytest.mark.parametrize(
    "model_id, expected",
    [
        (G915_TKL, 12),  # F-row is G1..G12
        (G502_X_PLUS, 0),
        ("", 0),
        ("NOTAMODEL", 0),
    ],
)
def test_gkeys_are_fkeys(model_id, expected):
    assert device_quirks.gkeys_are_fkeys(FakeDevice(model_id=model_id)) == expected


def test_gkeys_are_fkeys_ignores_experimental(monkeypatch):
    """A compatibility shim, not a safety allowlist — SOLAAR_EXPERIMENTAL must not
    hand the quirk to a device that was never listed for it."""
    monkeypatch.setenv("SOLAAR_EXPERIMENTAL", "1")

    assert device_quirks.gkeys_are_fkeys(FakeDevice(model_id=G502_X_PLUS)) == 0
    assert device_quirks.gkeys_are_fkeys(FakeDevice(model_id=G915_TKL)) == 12


def test_gkeys_are_fkeys_missing_model_id():
    assert device_quirks.gkeys_are_fkeys(object()) == 0
