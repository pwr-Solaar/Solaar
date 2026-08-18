import pytest

from solaar.ui.perkey.binding import bind
from solaar.ui.perkey.layouts import keyboard_ansi
from solaar.ui.perkey.layouts import keyboard_iso_azerty
from solaar.ui.perkey.layouts import keyboard_iso_qwerty
from solaar.ui.perkey.layouts import keyboard_iso_qwertz
from solaar.ui.perkey.layouts import keyboard_jis
from solaar.ui.perkey.layouts import layout_for

# PRO X RAPID hardware-probed media zones (board-specific, not canonical 153-158).
_RAPID_MEDIA = {150, 152, 153, 154, 155}
# Phantom zones this board shares with the G515 (not physical keys).
_SHARED_PHANTOMS = {47, 97}


def _rapid_hint(name="PRO X RAPID", country=1):
    return {
        "kind": "keyboard",
        "wpid": "C35B",
        "codename": name,
        "name": name,
        "keyboard_layout": country,  # 1 = ANSI
        "zones": [38, 55, 66, *sorted(_RAPID_MEDIA), *sorted(_SHARED_PHANTOMS)],
        "zone_count": 9,
    }


def test_pro_x_rapid_gets_media_top_row():
    layout = layout_for(0x8081, _rapid_hint())

    assert layout.description == "PRO X RAPID"
    media = {c.zone_id: (c.row, c.col, c.label) for c in layout.cells if c.group == "media"}
    assert media == {
        150: (0, 5, "Bright"),
        155: (0, 10, "Prev"),
        152: (0, 11, "Play"),
        154: (0, 12, "Next"),
        153: (0, 13, "Mute"),
    }
    # The generated base is pushed down one row to make room for the media row.
    esc = next(c for c in layout.cells if c.zone_id == 38)
    assert esc.row == 1


def test_pro_x_rapid_media_keys_are_paintable_and_phantoms_dropped():
    layout = layout_for(0x8081, _rapid_hint())
    bound = bind(layout, _rapid_hint()["zones"], lambda z: f"KEY {z}")

    media_bound = {bc.cell.zone_id: bc.bound for bc in bound.matrix if bc.cell.group == "media"}
    assert media_bound == {z: True for z in _RAPID_MEDIA}
    # Shared phantoms must not surface as paintable strip swatches.
    strip_zones = {bc.cell.zone_id for bc in bound.strip}
    assert _SHARED_PHANTOMS.isdisjoint(strip_zones)


def test_pro_x_rapid_still_regional():
    # ISO country code still routes to the ISO main block, with the media row on top.
    iso = layout_for(0x8081, _rapid_hint(country=2))  # 2 = ISO QWERTY
    assert iso.description == "PRO X RAPID"
    assert any(c.group == "media" for c in iso.cells)


def test_non_rapid_tkl_unaffected():
    # A G515 TKL keeps the generic layout: no media top row.
    layout = layout_for(0x8081, _rapid_hint(name="G515 LS TKL"))

    assert layout.description != "PRO X RAPID"
    assert not any(c.group == "media" for c in layout.cells)


# --- Keyboard family routing (0x4540 country codes) ---
# Codes are Logitech-private (official-app enum), NOT HID HUT codes.

_FULL_ZONES = [80, 95]  # numpad zones flag a full-size board


def _family_hint(country_code, full_size=True):
    return {
        "kind": "keyboard",
        "keyboard_layout": country_code,
        "zones": _FULL_ZONES if full_size else [1, 2, 3],
    }


_EXPECTED_FAMILY = [
    (0x01, keyboard_ansi.LAYOUT_FULL),  # US
    (0x03, keyboard_iso_qwerty.LAYOUT_FULL),  # UK
    (0x04, keyboard_iso_qwertz.LAYOUT_FULL),  # German
    (0x05, keyboard_iso_azerty.LAYOUT_FULL),  # French
    (0x09, keyboard_ansi.LAYOUT_FULL),  # Korean
    (0x0A, keyboard_jis.LAYOUT_FULL),  # Japanese
    (0x0D, keyboard_iso_qwertz.LAYOUT_FULL),  # Swiss
    (0x11, keyboard_iso_azerty.LAYOUT_FULL),  # Belgian
    (0x38, keyboard_iso_qwerty.LAYOUT_FULL),  # Brazilian ABNT2 (hardware-confirmed)
    (None, keyboard_ansi.LAYOUT_FULL),  # missing code defaults to ANSI
    (0x7F, keyboard_ansi.LAYOUT_FULL),  # unknown code defaults to ANSI
]


@pytest.mark.parametrize("country_code, expected_layout", _EXPECTED_FAMILY)
@pytest.mark.parametrize("feature", [0x8080, 0x8081])
def test_keyboard_family_routing(feature, country_code, expected_layout):
    assert layout_for(feature, _family_hint(country_code)) is expected_layout


@pytest.mark.parametrize("feature", [0x8080, 0x8081])
def test_tkl_routing(feature):
    assert layout_for(feature, _family_hint(0x01, full_size=False)) is keyboard_ansi.LAYOUT_TKL


# --- G512/G513 (0x8080) indicator LEDs ---


def _g512_hint(name="G512 SE", country=0x38):
    return {
        "kind": "keyboard",
        "codename": name,
        "name": name,
        "keyboard_layout": country,
        "zones": [1, 2, 80, 95, 241, 242],
    }


def test_g512_gets_positioned_indicators():
    layout = layout_for(0x8080, _g512_hint())

    assert layout.description == "G512"
    indicators = {c.zone_id: (c.row, c.col) for c in layout.cells if c.zone_id in (241, 242)}
    # Caps above Num Lock, Game Mode above numpad / (hardware-reported order).
    assert indicators == {242: (0, 17), 241: (0, 18)}
    # ABNT2 country code still routes the ISO QWERTY main block underneath.
    assert any(c.zone_id == 97 for c in layout.cells)


def test_g512_indicators_are_8080_only():
    # The same name on a 0x8081 board keeps the generic regional layout.
    assert layout_for(0x8081, _g512_hint()) is keyboard_iso_qwerty.LAYOUT_FULL


def test_unknown_8080_fullsize_keeps_generic_layout():
    # Extras wiring is per-model; unknown boards keep the generic layout.
    hint = _g512_hint(name="G-UNKNOWN", country=0x01)
    assert layout_for(0x8080, hint) is keyboard_ansi.LAYOUT_FULL


# --- G810/G610, G910, G Pro (0x8080) special-key strips ---


def _cells_by_zone(layout):
    return {c.zone_id: (c.row, c.col) for c in layout.cells}


def test_g810_gets_top_strip():
    layout = layout_for(0x8080, _g512_hint(name="G810 Orion Spectrum", country=0x01))

    assert layout.description == "G810/G610"
    cells = _cells_by_zone(layout)
    assert cells[210] == (0, 0)  # logo
    assert cells[244] == (0, 12) and cells[242] == (0, 13) and cells[243] == (0, 14)  # num/caps/scroll
    assert cells[241] == (0, 16) and cells[240] == (0, 18)  # game mode, lighting
    assert cells[156] == (0, 19)  # mute above the media block
    assert cells[155] == (1, 17) and cells[159] == (1, 18)  # play, stop
    assert cells[158] == (1, 19) and cells[157] == (1, 20)  # previous, next
    assert cells[38] == (1, 0)  # Esc pushed down one row


def test_g610_shares_g810_strip():
    layout = layout_for(0x8080, _g512_hint(name="G610 Orion Brown", country=0x01))
    assert layout.description == "G810/G610"


def test_g910_gets_side_strip():
    layout = layout_for(0x8080, _g512_hint(name="G910 Orion Spark", country=0x01))

    assert layout.description == "G910"
    cells = _cells_by_zone(layout)
    assert cells[38] == (1, 1)  # Esc pushed down and right
    assert cells[210] == (1, 0)  # logo left of Esc
    # G6-G9 directly above F1-F4 (F1 lands at row 1, col 3 after the shifts).
    assert cells[55] == (1, 3)
    assert {z: cells[z] for z in (185, 186, 187, 188)} == {185: (0, 3), 186: (0, 4), 187: (0, 5), 188: (0, 6)}
    # G1-G5 down the left edge, nameplate on its own bottom row.
    assert {z: cells[z] for z in (180, 181, 182, 183, 184)} == {
        180: (2, 0),
        181: (3, 0),
        182: (4, 0),
        183: (5, 0),
        184: (6, 0),
    }
    assert cells[211] == (7, 4)
    # Media cluster is deliberately absent (on/off backlight, not RGB).
    assert 155 not in cells and 156 not in cells


def test_gpro_tkl_gets_top_strip():
    hint = _g512_hint(name="Pro Gaming Keyboard", country=0x01)
    hint["zones"] = [1, 2, 38]  # no numpad -> TKL
    layout = layout_for(0x8080, hint)

    assert layout.description == "G PRO"
    cells = _cells_by_zone(layout)
    assert cells[210] == (0, 0)
    assert cells[242] == (0, 12) and cells[243] == (0, 13)
    assert cells[241] == (0, 15) and cells[240] == (0, 16)
    assert 244 not in cells  # no Num Lock indicator on a TKL
    assert cells[38] == (1, 0)
