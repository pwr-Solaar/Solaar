## Copyright (C) Solaar contributors
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

"""Tests for the display-state-aware color translation in rgb_power.

These cover the pure math (`translate_color_for_display`) and the small
manager hooks that PerKeyLighting calls into (`translate_color`,
`notify_perkey_changed`) without requiring a GLib main loop.
"""

import pytest

from logitech_receiver import rgb_power

M = rgb_power.RGBPowerManager


# --- translate_color_for_display (pure function) ----------------------------


@pytest.mark.parametrize(
    "color",
    [0x000000, 0x123456, 0xFF0000, 0xFFFFFF],
)
def test_translate_active_is_identity(color):
    assert rgb_power.translate_color_for_display(color, M.ACTIVE, 50, 0, 25) == color


def test_translate_idle_50pct():
    # 255 * 50 // 100 == 127
    assert rgb_power.translate_color_for_display(0xFFFFFF, M.IDLE, 50, 0, 25) == 0x7F7F7F


def test_translate_idle_25pct_on_ff8800():
    # 0xFF * 25 // 100 = 63 (0x3F); 0x88 * 25 // 100 = 34 (0x22); 0 stays 0
    assert rgb_power.translate_color_for_display(0xFF8800, M.IDLE, 25, 0, 25) == 0x3F2200


def test_translate_dimming_start_is_saved_color():
    # t = 0/25 = 0 → interpolation returns the start (saved) color
    assert rgb_power.translate_color_for_display(0xABCDEF, M.DIMMING, 50, 0, 25) == 0xABCDEF


def test_translate_dimming_end_equals_idle():
    # t = 25/25 = 1 → interpolation returns the target (fully dimmed)
    idle = rgb_power.translate_color_for_display(0xFFFFFF, M.IDLE, 50, 0, 25)
    dimming_end = rgb_power.translate_color_for_display(0xFFFFFF, M.DIMMING, 50, 25, 25)
    assert dimming_end == idle


def test_translate_dimming_midramp_between_full_and_dim():
    # At t=12/25 (≈0.48), white interpolates between 0xFF and 0x7F (50% target).
    # Expected r = 255 + (127 - 255) * 12/25 = 255 - 61.44 → int(193.56) = 193 (0xC1)
    assert rgb_power.translate_color_for_display(0xFFFFFF, M.DIMMING, 50, 12, 25) == 0xC1C1C1


def test_translate_sleeping_returns_none():
    assert rgb_power.translate_color_for_display(0xFFFFFF, M.SLEEPING, 50, 0, 25) is None


# --- translate_for_device (manager lookup) ----------------------------------


def test_translate_for_device_no_manager_is_identity():
    # An arbitrary object with no manager registered → returns input unchanged.
    fake = object()
    assert rgb_power.translate_for_device(fake, 0xABCDEF) == 0xABCDEF


def _dim(intensity):
    """Shortcut: build a Dim-mode LEDEffectSetting for tests that used to
    pass a bare dim-percent int as `_idle_effect`."""
    from logitech_receiver import hidpp20

    return hidpp20.LEDEffectSetting(ID=0x80, intensity=intensity)


def _install_manager(monkeypatch, state, idle_effect=None, dim_step=0):
    """Build an RGBPowerManager with state injected and register it for a
    fake device id. Cleanup happens via monkeypatch's _managers swap.

    `idle_effect` defaults to Dim 50%. Pass a bare int (legacy) and it
    will be wrapped as a Dim-mode LEDEffectSetting; pass an
    LEDEffectSetting directly to use as-is.
    """
    from logitech_receiver import hidpp20

    fake_device = object()

    class _Dev:
        pass

    mgr = M.__new__(M)  # bypass __init__ (no GLib needed)
    mgr._device = _Dev()
    mgr._state = state
    if idle_effect is None:
        mgr._idle_effect = _dim(50)
    elif isinstance(idle_effect, int):
        mgr._idle_effect = _dim(idle_effect)
    else:
        mgr._idle_effect = idle_effect
    mgr._dim_step = dim_step
    mgr._dim_perkey = None
    # Avoid circular import surprise — make sure the LEDEffectSetting is
    # imported here so type checks in helpers don't crash.
    _ = hidpp20.LEDEffectSetting

    saved_managers = dict(rgb_power._managers)
    monkeypatch.setattr(rgb_power, "_managers", {id(fake_device): mgr})
    yield_data = (fake_device, mgr, saved_managers)
    return yield_data


def test_translate_for_device_idle_routes_through_manager(monkeypatch):
    fake_device, mgr, _ = _install_manager(monkeypatch, M.IDLE, idle_effect=50)
    assert rgb_power.translate_for_device(fake_device, 0xFFFFFF) == 0x7F7F7F


def test_translate_for_device_sleeping_returns_none(monkeypatch):
    fake_device, _, _ = _install_manager(monkeypatch, M.SLEEPING)
    assert rgb_power.translate_for_device(fake_device, 0xFFFFFF) is None


def test_current_dim_pct_falls_back_to_100_for_non_dim_effects():
    from logitech_receiver import hidpp20

    mgr = M.__new__(M)
    # Dim is the only host-side idle effect — it's the only one Solaar can
    # render itself (by interpolating colors toward a dimmer target on a
    # Static zone color or in the per-key buffer). Disabled does nothing.
    # Breathe and Ripple hand off to the firmware effect engine, which
    # runs the animation at its own brightness; Solaar applies no dim
    # translation in those cases, so _current_dim_pct returns 100.
    for fw_or_disabled in (0x00, 0x0A, 0x0B):
        mgr._idle_effect = hidpp20.LEDEffectSetting(ID=fw_or_disabled)
        assert mgr._current_dim_pct() == 100
    # Dim mode — intensity carries the dim percentage.
    for dim_pct in (25, 50, 75):
        mgr._idle_effect = hidpp20.LEDEffectSetting(ID=0x80, intensity=dim_pct)
        assert mgr._current_dim_pct() == dim_pct


# --- notify_perkey_changed --------------------------------------------------


def test_notify_perkey_changed_updates_dim_map_during_dimming():
    mgr = M.__new__(M)
    mgr._state = M.DIMMING
    mgr._idle_effect = _dim(50)
    mgr._dim_perkey = {5: (0xFFFFFF, 0x7F7F7F)}
    mgr.notify_perkey_changed(5, 0x00FF00)
    start, target = mgr._dim_perkey[5]
    assert start == 0x00FF00
    # target = dim(0x00FF00, 50) = (0, 0xFF*50//100, 0) = (0, 0x7F, 0)
    assert target == 0x007F00


def test_notify_perkey_changed_noop_when_not_dimming():
    mgr = M.__new__(M)
    mgr._state = M.IDLE
    mgr._idle_effect = _dim(50)
    mgr._dim_perkey = {5: (0xFFFFFF, 0x7F7F7F)}
    mgr.notify_perkey_changed(5, 0x00FF00)
    assert mgr._dim_perkey[5] == (0xFFFFFF, 0x7F7F7F)


def test_notify_perkey_changed_noop_for_unknown_zone():
    mgr = M.__new__(M)
    mgr._state = M.DIMMING
    mgr._idle_effect = _dim(50)
    mgr._dim_perkey = {5: (0xFFFFFF, 0x7F7F7F)}
    mgr.notify_perkey_changed(99, 0x00FF00)  # not in _dim_perkey
    assert mgr._dim_perkey == {5: (0xFFFFFF, 0x7F7F7F)}


def test_notify_perkey_bulk_changed_skips_no_change():
    from logitech_receiver import special_keys

    no_change = special_keys.COLORSPLUS["No change"]
    mgr = M.__new__(M)
    mgr._state = M.DIMMING
    mgr._idle_effect = _dim(50)
    mgr._dim_perkey = {5: (0xFFFFFF, 0x7F7F7F), 7: (0x000000, 0x000000)}
    mgr.notify_perkey_bulk_changed({5: 0x00FF00, 7: no_change})
    # Zone 5 updated, zone 7 (No change) left alone.
    assert mgr._dim_perkey[5][0] == 0x00FF00
    assert mgr._dim_perkey[7] == (0x000000, 0x000000)


# --- notify_zone_changed (zone-effect dim ramp) -----------------------------


class _FakeZone:
    """Minimal stand-in for hidpp20.LEDZoneInfo — only `.index` is consulted
    by RGBPowerManager.notify_zone_changed."""

    def __init__(self, index):
        self.index = index


def test_notify_zone_changed_updates_matching_cluster_during_dimming():
    mgr = M.__new__(M)
    mgr._state = M.DIMMING
    mgr._idle_effect = _dim(50)
    zone_a = _FakeZone(0)
    zone_b = _FakeZone(1)
    mgr._dim_zones = [
        (zone_a, 0xFFFFFF, 0x7F7F7F),
        (zone_b, 0xFF0000, 0x7F0000),
    ]
    mgr.notify_zone_changed(1, 0x00FF00)
    # zone_a unchanged
    assert mgr._dim_zones[0] == (zone_a, 0xFFFFFF, 0x7F7F7F)
    # zone_b updated: new start + recomputed target at 50%
    zone, start, target = mgr._dim_zones[1]
    assert zone is zone_b
    assert start == 0x00FF00
    # _compute_dim_color(0x00FF00, 50) = (0, 0xFF*50//100, 0) = (0, 0x7F, 0)
    assert target == 0x007F00


def test_notify_zone_changed_noop_when_not_dimming():
    mgr = M.__new__(M)
    mgr._state = M.IDLE
    mgr._idle_effect = _dim(50)
    zone = _FakeZone(0)
    mgr._dim_zones = [(zone, 0xFFFFFF, 0x7F7F7F)]
    mgr.notify_zone_changed(0, 0x00FF00)
    assert mgr._dim_zones[0] == (zone, 0xFFFFFF, 0x7F7F7F)


def test_notify_zone_changed_noop_for_unknown_cluster():
    mgr = M.__new__(M)
    mgr._state = M.DIMMING
    mgr._idle_effect = _dim(50)
    zone = _FakeZone(0)
    mgr._dim_zones = [(zone, 0xFFFFFF, 0x7F7F7F)]
    mgr.notify_zone_changed(99, 0x00FF00)  # cluster 99 not in _dim_zones
    assert mgr._dim_zones[0] == (zone, 0xFFFFFF, 0x7F7F7F)


def test_notify_zone_changed_noop_when_dim_zones_empty():
    mgr = M.__new__(M)
    mgr._state = M.DIMMING
    mgr._idle_effect = _dim(50)
    mgr._dim_zones = []  # e.g. per-key active, zone path skipped
    mgr.notify_zone_changed(0, 0x00FF00)  # should not raise
    assert mgr._dim_zones == []


# --- perkey_has_paint / zone_effect_is_static (module-level predicates) -----


class _FakePerKey:
    """Minimal stand-in for PerKeyLighting: holds a _value map and a
    _validator with .choices that perkey_has_paint inspects."""

    name = "per-key-lighting"

    def __init__(self, value, choices=(1, 2, 3)):
        self._value = value

        class _V:
            pass

        self._validator = _V()
        self._validator.choices = list(choices)


class _FakeZoneSetting:
    """Minimal stand-in for an RGBEffectSetting child instance: holds a
    name starting with "rgb_zone_" and a _value with an .ID attribute."""

    def __init__(self, name, value):
        self.name = name
        self._value = value


class _ValueWithID:
    """Stand-in for hidpp20.LEDEffectSetting — only .ID is consulted by
    zone_effect_is_static."""

    def __init__(self, ID):
        self.ID = ID


class _FakePersister:
    def __init__(self, sensitivities=None):
        self._s = sensitivities or {}

    def get_sensitivity(self, name):
        return self._s.get(name, False)


class _FakeDevice:
    def __init__(self, settings_list, persister=None):
        self.settings = settings_list
        self.persister = persister


def test_perkey_has_paint_with_real_colors():
    pk = _FakePerKey({1: 0xFF0000, 2: -1, 3: -1})  # one real color, rest "No change"
    dev = _FakeDevice([pk], _FakePersister({"per-key-lighting": True}))
    found, has_paint = rgb_power.perkey_has_paint(dev)
    assert found is pk
    assert has_paint is True


def test_perkey_has_paint_with_locked_sensitivity():
    # False (locked) still counts as paint — only IGNORE opts out.
    pk = _FakePerKey({1: 0xFF0000})
    dev = _FakeDevice([pk], _FakePersister())  # sensitivity defaults to False
    _, has_paint = rgb_power.perkey_has_paint(dev)
    assert has_paint is True


def test_perkey_has_paint_only_no_change():
    pk = _FakePerKey({1: -1, 2: -1, 3: -1})  # all "No change"
    dev = _FakeDevice([pk])
    found, has_paint = rgb_power.perkey_has_paint(dev)
    assert found is pk
    assert has_paint is False


def test_perkey_has_paint_no_perkey_setting():
    dev = _FakeDevice([])
    found, has_paint = rgb_power.perkey_has_paint(dev)
    assert found is None
    assert has_paint is False


def test_perkey_has_paint_validator_choices_empty():
    pk = _FakePerKey({1: 0xFF0000}, choices=())
    dev = _FakeDevice([pk])
    found, has_paint = rgb_power.perkey_has_paint(dev)
    assert found is pk
    assert has_paint is False


def test_perkey_has_paint_user_ignores_perkey():
    from logitech_receiver import settings as _settings

    pk = _FakePerKey({1: 0xFF0000})
    dev = _FakeDevice([pk], _FakePersister({"per-key-lighting": _settings.SENSITIVITY_IGNORE}))
    found, has_paint = rgb_power.perkey_has_paint(dev)
    assert found is pk
    assert has_paint is False


def test_perkey_has_paint_with_no_persister():
    # No persister, no IGNORE flag — treat as paint present.
    pk = _FakePerKey({1: 0xFF0000})
    dev = _FakeDevice([pk], persister=None)
    _, has_paint = rgb_power.perkey_has_paint(dev)
    assert has_paint is True


def test_zone_effect_is_static_true_for_static():
    z = _FakeZoneSetting("rgb_zone_1", _ValueWithID(0x01))
    assert rgb_power.zone_effect_is_static(_FakeDevice([z])) is True


def test_zone_effect_is_static_false_for_animated():
    for eff_id in (0x02, 0x03, 0x0A, 0x0B, 0x0E, 0x15):
        z = _FakeZoneSetting("rgb_zone_1", _ValueWithID(eff_id))
        assert rgb_power.zone_effect_is_static(_FakeDevice([z])) is False, eff_id


def test_zone_effect_is_static_false_for_disabled():
    # Disabled (0x00) means the user wants no zone effect — including
    # suppressing the per-key paint, since per-key push would re-light
    # the device.
    z = _FakeZoneSetting("rgb_zone_1", _ValueWithID(0x00))
    assert rgb_power.zone_effect_is_static(_FakeDevice([z])) is False


def test_zone_effect_is_static_true_when_no_zone_setting():
    # Devices that only enumerate PER_KEY_LIGHTING_V2 (no RGB_EFFECTS) have
    # no zone-effect setting at all — per-key paint should be free to drive.
    assert rgb_power.zone_effect_is_static(_FakeDevice([])) is True


def test_zone_effect_is_static_true_when_any_zone_is_static():
    # Multi-zone device with one Static and one Cycle zone — at least one
    # Static slot is enough for per-key to overlay on.
    a = _FakeZoneSetting("rgb_zone_1", _ValueWithID(0x01))  # Static
    b = _FakeZoneSetting("rgb_zone_2", _ValueWithID(0x03))  # Cycle
    assert rgb_power.zone_effect_is_static(_FakeDevice([a, b])) is True


# --- RGBEffectSetting.write divert / push --------------------------------


def _make_rgb_effect_setting(device, current_value):
    """Build a partial RGBEffectSetting bound to `device` without running the
    setup classmethod (which requires a real led_effects descriptor). Only
    the fields touched by RGBEffectSetting.write are populated."""
    from unittest.mock import MagicMock

    from logitech_receiver import settings_templates

    s = settings_templates.RGBEffectSetting.__new__(settings_templates.RGBEffectSetting)
    s._device = device
    s._value = current_value
    s._rw = MagicMock()
    s._rw.prefix = b"\x01"
    s._validator = MagicMock()
    s._validator.needs_current_value = False
    # update() persists onto _value; mimic with a simple assignment.
    s.update = lambda v, save=True: setattr(s, "_value", v)
    return s


def test_rgb_effect_write_static_to_static_repaints_unset_zones(monkeypatch):
    """User tweaks the Static base color while per-key is the visible
    layer: persist, repaint per-key's unset zones, send FrameEnd. No
    SetEffectByIndex (would reclaim the engine and overwrite per-key).
    Also notifies any in-flight dim ramp so unset cells' start_color
    tracks the new base."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    perkey._fill_unset_zones_with_base_color.return_value = True
    perkey._send_with_retry.return_value = True
    perkey._unset_zone_ids.return_value = [5, 7, 9]
    device = MagicMock()
    device.online = True

    mgr = MagicMock()
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, True))
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: mgr)

    old = hidpp20.LEDEffectSetting(ID=1, color=0xFF0000)
    new = hidpp20.LEDEffectSetting(ID=1, color=0x00FF00)
    s = _make_rgb_effect_setting(device, old)

    result = s.write(new)

    assert result is new
    assert s._value is new
    perkey._fill_unset_zones_with_base_color.assert_called_once()
    perkey._send_with_retry.assert_called_once_with(0x70, b"\x00")
    s._rw.write.assert_not_called()
    # No follow-up per-key push — we were already in Static.
    perkey.write.assert_not_called()
    # In-flight dim ramp gets notified that unset cells now interpolate
    # from the new base (0x00FF00) rather than the old.
    mgr.notify_perkey_bulk_changed.assert_called_once_with({5: 0x00FF00, 7: 0x00FF00, 9: 0x00FF00})


def test_rgb_effect_write_static_to_static_no_notify_when_no_unset_zones(monkeypatch):
    """If every per-key cell is user-painted, _unset_zone_ids returns
    [] and the dim-ramp notification is skipped (nothing to update)."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    perkey._fill_unset_zones_with_base_color.return_value = True
    perkey._send_with_retry.return_value = True
    perkey._unset_zone_ids.return_value = []
    device = MagicMock()
    device.online = True

    mgr = MagicMock()
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, True))
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: mgr)

    old = hidpp20.LEDEffectSetting(ID=1, color=0xFF0000)
    new = hidpp20.LEDEffectSetting(ID=1, color=0x00FF00)
    s = _make_rgb_effect_setting(device, old)

    s.write(new)

    mgr.notify_perkey_bulk_changed.assert_not_called()


def test_rgb_effect_write_static_to_static_unchanged_is_noop(monkeypatch):
    """Same value persisted: no repaint, no FrameEnd, no wire write."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    device = MagicMock()
    device.online = True
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, True))

    same = hidpp20.LEDEffectSetting(ID=1, color=0xFF0000)
    s = _make_rgb_effect_setting(device, same)

    s.write(same)

    perkey._fill_unset_zones_with_base_color.assert_not_called()
    perkey._send_with_retry.assert_not_called()
    s._rw.write.assert_not_called()


def test_rgb_effect_write_static_to_animation_pushes_wire(monkeypatch):
    """User switches the zone effect dropdown from Static to an animation
    while per-key has paint: push the new value to wire so the animation
    starts. Per-key is a sub-mode of Static — animations take over the
    visible layer when selected."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    perkey._value = {1: 0xFF0000}
    device = MagicMock()
    device.online = True
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, True))
    monkeypatch.setattr(rgb_power, "translate_for_device", lambda d, c: c)
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: None)

    old = hidpp20.LEDEffectSetting(ID=0x01, color=0xFF0000)
    new = hidpp20.LEDEffectSetting(ID=0x0A, color=0x00FF00)
    s = _make_rgb_effect_setting(device, old)
    s._validator.prepare_write.return_value = b"prepared"
    s._rw.write.return_value = b"ack"

    s.write(new)

    s._rw.write.assert_called_once()
    perkey._fill_unset_zones_with_base_color.assert_not_called()


def test_rgb_effect_write_repaints_perkey_unset_on_color_change(monkeypatch):
    """When per-key has paint and the zone's color changes, repaint the
    per-key unset cells with the new base so the visible result tracks
    the user's color choice."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    perkey._value = {1: 0xFF0000, 2: -1}
    perkey._fill_unset_zones_with_base_color.return_value = True
    perkey._unset_zone_ids.return_value = [2]
    device = MagicMock()
    device.online = True
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, True))
    monkeypatch.setattr(rgb_power, "translate_for_device", lambda d, c: c)
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: None)

    old = hidpp20.LEDEffectSetting(ID=0x01, color=0xFF0000)
    new = hidpp20.LEDEffectSetting(ID=0x01, color=0x00FF00)
    s = _make_rgb_effect_setting(device, old)
    s._validator.prepare_write.return_value = b"prepared"
    s._rw.write.return_value = b"ack"

    s.write(new)

    s._rw.write.assert_not_called()
    perkey._fill_unset_zones_with_base_color.assert_called_once()
    perkey._send_with_retry.assert_called_once_with(0x70, b"\x00")


def test_rgb_effect_write_apply_path_suppressed_when_perkey_has_paint(monkeypatch):
    """save=False is the apply_all_settings path. When per-key has paint and
    is opted in, per-key fully owns the visible layer — the zone wire push
    is suppressed here too, not just on the save path."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    device = MagicMock()
    device.online = True
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, True))
    monkeypatch.setattr(rgb_power, "translate_for_device", lambda d, c: c)
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: None)

    new = hidpp20.LEDEffectSetting(ID=0x01, color=0x00FF00)
    s = _make_rgb_effect_setting(device, None)
    s._validator.prepare_write.return_value = b"prepared"
    s._rw.write.return_value = b"ack"

    s.write(new, save=False)

    s._rw.write.assert_not_called()
    # Apply path doesn't repaint either — that's reserved for explicit user
    # color changes via save=True.
    perkey._fill_unset_zones_with_base_color.assert_not_called()


def test_rgb_effect_write_inactive_perkey_falls_through(monkeypatch):
    """No per-key paint (or per-key feature absent): existing
    translate-through-power-state wire path runs unchanged."""
    from unittest.mock import MagicMock

    from logitech_receiver import hidpp20

    perkey = MagicMock()
    device = MagicMock()
    device.online = True
    monkeypatch.setattr(rgb_power, "perkey_has_paint", lambda d: (perkey, False))
    monkeypatch.setattr(rgb_power, "translate_for_device", lambda d, c: c)
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: None)

    new = hidpp20.LEDEffectSetting(ID=0x01, color=0x00FF00)
    s = _make_rgb_effect_setting(device, None)
    s._validator.prepare_write.return_value = b"prepared"
    s._rw.write.return_value = b"ack"

    s.write(new)

    s._rw.write.assert_called_once()
    perkey._fill_unset_zones_with_base_color.assert_not_called()
    perkey.write.assert_not_called()


# --- PerKeyLighting.write defers to firmware animations -------------------


def test_perkey_write_skipped_when_zone_is_animation(monkeypatch):
    """Per-key is a sub-mode of Static. When the saved zone effect is an
    animation (Breathe etc.), the firmware engine owns the visible layer
    and per-key writes do not go to the wire."""
    from unittest.mock import MagicMock

    from logitech_receiver import settings_templates

    breathe_zone = _FakeZoneSetting("rgb_zone_1", _ValueWithID(0x0A))

    s = settings_templates.PerKeyLighting.__new__(settings_templates.PerKeyLighting)
    device = MagicMock()
    device.online = True
    device.settings = [breathe_zone]
    s._device = device
    s._value = {}
    s._has_rgb_effects = True
    s._ensure_sw_control = MagicMock()
    s._send_with_retry = MagicMock(return_value=True)
    s._fill_unset_zones_with_base_color = MagicMock(return_value=True)
    monkeypatch.setattr(rgb_power, "translate_for_device", lambda d, c: c)
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: None)
    s.update = lambda m, save=True: None

    s.write({1: 0xFF0000})

    s._send_with_retry.assert_not_called()


def test_perkey_write_key_value_skipped_when_zone_is_animation(monkeypatch):
    """Same: write_key_value defers to firmware animations."""
    from unittest.mock import MagicMock

    from logitech_receiver import settings_templates

    breathe_zone = _FakeZoneSetting("rgb_zone_1", _ValueWithID(0x0A))

    s = settings_templates.PerKeyLighting.__new__(settings_templates.PerKeyLighting)
    device = MagicMock()
    device.online = True
    device.settings = [breathe_zone]
    s._device = device
    s._value = {}
    s._has_rgb_effects = True
    s._ensure_sw_control = MagicMock()
    s._send_with_retry = MagicMock(return_value=True)
    s._send_zone_color = MagicMock(return_value=True)
    s._fill_unset_zones_with_base_color = MagicMock(return_value=True)
    monkeypatch.setattr(rgb_power, "translate_for_device", lambda d, c: c)
    monkeypatch.setattr(rgb_power, "get_manager", lambda d: None)
    s.update_key_value = lambda k, v, save=True: None

    s.write_key_value(7, 0xFF0000)

    s._send_zone_color.assert_not_called()
