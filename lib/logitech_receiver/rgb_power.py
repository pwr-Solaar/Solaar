## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""Software-driven RGB power management for devices that hand off LED
control to the host (RGB_EFFECTS / 0x8071).

Handles the firmware onUserActivity events, the two-stage idle effect
(smooth dim ramp or animation), and the software sleep timer that fires
after idle_timeout has elapsed.
"""

from __future__ import annotations

import logging

from time import sleep

from . import exceptions
from . import hidpp20_constants
from . import settings
from . import special_keys
from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

try:
    from gi.repository import GLib

    _has_glib = True
except ImportError:
    _has_glib = False


# SetSWControl flag bits for RGB_EFFECTS (0x8071).
FLAG_EFFECT = 0x01
FLAG_POWER = 0x02
FLAG_NVCONFIG = 0x04

# SetSWControl payloads: [subfn=set, mode=3, flags]
SW_ACTIVE = bytes([0x01, 0x03, FLAG_NVCONFIG])  # firmware monitors idle
SW_IDLE = bytes([0x01, 0x03, FLAG_POWER])  # firmware monitors activity
SW_RELEASE = bytes([0x01, 0x00, 0x00])


_managers = {}  # keyed by id(device)


def get_manager(device):
    """Return the active RGBPowerManager for `device`, or None."""
    return _managers.get(id(device))


def on_user_activity(device, activity_type):
    """Dispatch firmware onUserActivity events to the device's power manager."""
    mgr = _managers.get(id(device))
    if mgr:
        mgr.on_user_activity(activity_type)


def translate_color_for_display(color, state, dim_pct, dim_step, dim_steps):
    """Map a saved (undimmed) color to the display color for `state`.
    Returns None for SLEEPING."""
    if state == RGBPowerManager.ACTIVE:
        return color
    if state == RGBPowerManager.SLEEPING:
        return None
    target = RGBPowerManager._compute_dim_color(color, dim_pct)
    if state == RGBPowerManager.IDLE:
        return target
    # DIMMING — interpolate from saved toward dimmed target by ramp progress.
    t = (dim_step / dim_steps) if dim_steps else 1.0
    return RGBPowerManager._interpolate_color(color, target, t)


def translate_for_device(device, color):
    """Translate `color` through the device's RGBPowerManager state, or
    return it unchanged when no manager is registered. None signals SLEEPING."""
    mgr = _managers.get(id(device))
    if mgr is None:
        return color
    return mgr.translate_color(color)


_EFFECT_STATIC = 0x01


def perkey_has_paint(device):
    """Return ``(perkey_setting, has_paint)``. has_paint is True when the
    per-key buffer has at least one real color, a usable zone set, and the
    user has *explicitly enabled* per-key via the lock icon (sensitivity
    is True). Default-sensitivity (False) and ignore both yield False so
    zone effects remain the primary mechanism on devices where the user
    hasn't opted in to per-key dominance."""
    perkey = None
    for s in getattr(device, "settings", []) or []:
        if s.name == "per-key-lighting":
            perkey = s
            break
    if perkey is None:
        return None, False
    validator = getattr(perkey, "_validator", None)
    choices = getattr(validator, "choices", None)
    if not choices:
        return perkey, False
    # Apply path runs rgb_zone_ before per-key, so _value may still be None
    # when this gate is consulted — fall back to the persister.
    value = getattr(perkey, "_value", None)
    persister = getattr(device, "persister", None)
    if value is None and persister is not None:
        value = persister.get("per-key-lighting")
    if not value:
        return perkey, False
    no_change = special_keys.COLORSPLUS["No change"]
    if not any(c != no_change and isinstance(c, int) and c >= 0 for c in value.values()):
        return perkey, False
    if persister is None or persister.get_sensitivity("per-key-lighting") is not True:
        return perkey, False
    return perkey, True


def zone_effect_is_static(device):
    """True when the persisted zone effect is Static, or when no
    rgb_zone_* setting exists at all (per-key-only hardware)."""
    has_zone = False
    persister = getattr(device, "persister", None)
    for s in getattr(device, "settings", []) or []:
        if s.name.startswith("rgb_zone_"):
            has_zone = True
            value = getattr(s, "_value", None)
            if value is None and persister is not None:
                value = persister.get(s.name)
            if value is not None and int(getattr(value, "ID", 0) or 0) == _EFFECT_STATIC:
                return True
    return not has_zone


def zone_effect_is_ignored(device):
    """True when every rgb_zone_* setting on `device` is marked
    SENSITIVITY_IGNORE in the persister."""
    persister = getattr(device, "persister", None)
    if persister is None:
        return False
    zones = [s for s in getattr(device, "settings", []) or [] if s.name.startswith("rgb_zone_")]
    if not zones:
        return False
    return all(persister.get_sensitivity(s.name) == settings.SENSITIVITY_IGNORE for s in zones)


def effective_zone_base_color(device):
    """Color to use for per-key unset cells: 0 (off/black) when the zone
    effect is ignored (or unavailable), the persisted zone color otherwise.
    Reads through the persister so we still get the saved color even before
    apply has populated _value.

    During an idle-Static transition the saved color is substituted with
    the idle effect's color so unset cells track the idle primary. Reverts
    on wake when state returns to ACTIVE."""
    if zone_effect_is_ignored(device):
        return 0
    mgr = _managers.get(id(device))
    if mgr is not None and mgr._state == RGBPowerManager.IDLE and mgr._idle_effect_id() == 0x01:
        return int(getattr(mgr._idle_effect, "color", 0) or 0)
    persister = getattr(device, "persister", None)
    for s in getattr(device, "settings", []) or []:
        if not s.name.startswith("rgb_zone_"):
            continue
        value = getattr(s, "_value", None)
        if value is None and persister is not None:
            value = persister.get(s.name)
        if value is not None:
            color = getattr(value, "color", None)
            if isinstance(color, int):
                return int(color)
    return 0


_RETRY_BUSY_BACKOFF_MS = (30, 60, 90)


def feature_request_acked(device, feature, function, data=b"", retries=3):
    """feature_request with BUSY/timeout retries. Returns reply bytes
    on ACK, None on hard failure (logged WARNING)."""
    busy_attempt = 0
    max_busy = len(_RETRY_BUSY_BACKOFF_MS)
    for attempt in range(retries + 1):
        try:
            reply = device.feature_request(feature, function, data)
        except exceptions.FeatureCallError as e:
            if getattr(e, "error", None) == hidpp20_constants.ErrorCode.BUSY and busy_attempt < max_busy:
                delay_ms = _RETRY_BUSY_BACKOFF_MS[busy_attempt]
                busy_attempt += 1
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "%s: feature 0x%04x fn 0x%02x BUSY, retry %d/%d after %dms",
                        device,
                        int(feature),
                        function,
                        busy_attempt,
                        max_busy,
                        delay_ms,
                    )
                sleep(delay_ms / 1000.0)
                continue
            logger.warning("%s: feature 0x%04x fn 0x%02x rejected: %s", device, int(feature), function, e)
            return None
        if reply is not None:
            if (attempt > 0 or busy_attempt > 0) and logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "%s: feature 0x%04x fn 0x%02x succeeded after %d timeout retries, %d BUSY retries",
                    device,
                    int(feature),
                    function,
                    attempt,
                    busy_attempt,
                )
            return reply
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: feature 0x%04x fn 0x%02x timed out (attempt %d/%d)",
                device,
                int(feature),
                function,
                attempt + 1,
                retries + 1,
            )
    logger.warning("%s: feature 0x%04x fn 0x%02x no ACK after %d attempts", device, int(feature), function, retries + 1)
    return None


def _probe_tmpl_bytes(device):
    """GetEffectSpecificInfo page 1: returns (tmpl_0, tmpl_1) or
    (None, None) if the device has no firmware effect cards."""
    try:
        reply = device.feature_request(SupportedFeature.RGB_EFFECTS, 0x00, 0xFF, 0x00, 0x01, 0x00, 0x01)
    except exceptions.FeatureCallError:
        return (None, None)
    if reply is None or len(reply) < 12:
        return (None, None)
    return (reply[10], reply[11])


def push_artanis_perkey_prep(device):
    """Disable the firmware effects engine on mice with firmware effect cards.
    Returns True if the call ACKed."""
    infos = getattr(device, "led_effects", None)
    if not infos or not infos.zones:
        return False
    num_effects = len(infos.zones[0].effects)
    # SetEffectByIndex: cluster + effectIdx + 10 param bytes + persist.
    # Shipping with call 2 only — sufficient on tested hardware (G502 X PLUS).
    # Call 1 (TMPL-handshake) left commented for reactivation if broader
    # testing turns up a device that needs it; uncomment the _probe_tmpl_bytes
    # use and the call1 block together.
    # tmpl_0, tmpl_1 = _probe_tmpl_bytes(device)
    # if tmpl_0 is None:
    #     return False
    # call1 = b"\xff\x02" + b"\x00" * 6 + bytes([tmpl_0, tmpl_1]) + b"\x00\x00" + b"\x01"
    # if feature_request_acked(device, SupportedFeature.RGB_EFFECTS, 0x10, call1) is None:
    #     return False
    call2 = b"\xff" + bytes([num_effects]) + b"\x00" * 10 + b"\x01"
    return feature_request_acked(device, SupportedFeature.RGB_EFFECTS, 0x10, call2) is not None


def start(device):
    """Begin software RGB power management for `device`. No-op without GLib."""
    if not _has_glib:
        return
    key = id(device)
    if key not in _managers:
        mgr = RGBPowerManager(device)
        _managers[key] = mgr
        mgr.start()
    else:
        mgr = _managers[key]
        mgr.reset()
    # Push persisted settings into the manager. Settings marked ignore via the
    # lock icon are skipped so the manager keeps its built-in default.
    from . import hidpp20

    persister = getattr(device, "persister", None)

    def _ignored(name):
        return persister is not None and persister.get_sensitivity(name) == settings.SENSITIVITY_IGNORE

    for s in device.settings:
        if _ignored(s.name):
            continue
        if s.name == "rgb_idle_timeout":
            val = s._value if s._value is not None else 60
            mgr.set_idle_timeout(int(val))
        elif s.name == "rgb_sleep_timeout":
            val = s._value if s._value is not None else 300
            mgr.set_sleep_timeout(int(val))
        elif s.name == "rgb_idle_effect":
            val = s._value if s._value is not None else hidpp20.LEDEffectSetting(ID=0x80, intensity=50)
            mgr.set_idle_effect(val)


def stop(device):
    """End software RGB power management for `device`."""
    key = id(device)
    mgr = _managers.pop(key, None)
    if mgr:
        mgr.stop()


def cleanup(device):
    """device.cleanups handler — restore firmware control on device close.

    On devices that support NvConfig cap 0x0040 (shutdown effect), also fires
    SetRgbPowerMode(0) as the final step so the firmware plays the configured
    shutdown animation during the active→off transition. If the cap is
    disabled, the firmware powers down LEDs silently. Matches LGHUB exit.
    See solaar_shutdown_effect_trigger_spec.md.
    """
    stop(device)
    try:
        device.feature_request(SupportedFeature.RGB_EFFECTS, 0x50, SW_RELEASE)
        if device.features and SupportedFeature.PROFILE_MANAGEMENT in device.features:
            device.feature_request(SupportedFeature.PROFILE_MANAGEMENT, 0x60, b"\x03")
        elif device.features and SupportedFeature.ONBOARD_PROFILES in device.features:
            device.feature_request(SupportedFeature.ONBOARD_PROFILES, 0x10, b"\x01")
    except Exception:
        pass  # Device may already be offline
    if getattr(device, "_rgb_has_shutdown_cap", False):
        try:
            # SetRgbPowerMode(set=1, mode=0) — firmware off transition.
            # no_reply: device goes offline; don't block waiting for an ACK.
            device.feature_request(SupportedFeature.RGB_EFFECTS, 0x90, b"\x01\x00", no_reply=True)
        except Exception:
            pass


class RGBPowerManager:
    """Two-stage idle handler driven by firmware onUserActivity events.

    State machine: ACTIVE → DIMMING → IDLE → SLEEPING.
    Stage 1 (idle) runs a host-side dim ramp or hands off to a firmware
    animation. Stage 2 (sleep) is a software timer that fires
    sleep_timeout - idle_timeout after IDLE.
    """

    ACTIVE = 0
    DIMMING = 1
    IDLE = 2
    SLEEPING = 3

    _DIM_INTERVAL_MS = 200
    _DIM_STEPS = 25  # ~5s dim ramp

    def __init__(self, device):
        self._device = device
        self._state = self.ACTIVE
        self._idle_timeout = 60
        self._sleep_timeout = 300
        # LEDEffectSetting with ID in {0x00 Disabled, 0x80 Dim, 0x0A
        # Breathe, 0x0B Ripple}. Populated by start() from the persister.
        self._idle_effect = None
        self._sleep_timer_id = None
        self._dim_timer_id = None
        self._dim_step = 0
        self._dim_zones = []
        self._dim_perkey = None

    def start(self):
        self._state = self.ACTIVE
        self._read_firmware_timers()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: RGB power manager started (firmware idle=%ds, sleep=%ds)",
                self._device,
                self._idle_timeout,
                self._sleep_timeout,
            )

    def stop(self):
        self._cancel_dim_timer()
        self._cancel_sleep_timer()
        if self._state != self.ACTIVE:
            try:
                self._wake()
            except Exception:
                pass  # Best effort during shutdown
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB power manager stopped", self._device)

    def reset(self):
        """Reset to ACTIVE on device reconnect. Re-reads firmware timers so
        externally-updated values (other tool wrote NV between sessions)
        are picked up even when our settings are ignored."""
        self._cancel_dim_timer()
        self._cancel_sleep_timer()
        self._state = self.ACTIVE
        self._read_firmware_timers()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB power manager reset to ACTIVE", self._device)

    def set_idle_timeout(self, seconds):
        self._idle_timeout = seconds
        self._cancel_sleep_timer()
        if seconds == 0 and self._state in (self.DIMMING, self.IDLE):
            self._wake()
        self._write_firmware_idle_timeout(seconds)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB idle timeout set to %ss", self._device, seconds)

    def set_sleep_timeout(self, seconds):
        """0 disables sleep."""
        self._sleep_timeout = seconds
        self._cancel_sleep_timer()
        if seconds == 0 and self._state == self.SLEEPING:
            self._wake()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("%s: RGB sleep timeout set to %ss", self._device, seconds)

    def set_idle_effect(self, effect):
        """`effect` is an LEDEffectSetting. Wake immediately if the user
        switched to Disabled while we're mid-idle."""
        self._idle_effect = effect
        if self._idle_effect_id() == 0x00 and self._state in (self.DIMMING, self.IDLE):
            self._wake()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s: RGB idle effect set to ID=0x%02X (period=%s, intensity=%s)",
                self._device,
                self._idle_effect_id(),
                getattr(self._idle_effect, "period", None),
                getattr(self._idle_effect, "intensity", None),
            )

    def _idle_effect_id(self):
        """Return the ID of the current idle effect, or 0 if unset."""
        return int(getattr(self._idle_effect, "ID", 0) or 0)

    # --- Firmware activity events ---

    def on_user_activity(self, activity_type):
        """Handle firmware onUserActivity event from RGB_EFFECTS (0x8071).

        activity_type=0: IDLE — user stopped typing, firmware idle timer expired.
        activity_type!=0: ACTIVE — user resumed typing after being idle.

        The firmware sends a burst of ~8 events with exponential backoff.
        Only the first event matters; subsequent events for the same transition are ignored.
        """
        if not self._device.online:
            return

        if activity_type == 0:
            # IDLE event — firmware detected inactivity at idle_timeout
            if self._state != self.ACTIVE:
                return  # Already idle/dimming/sleeping, ignore burst
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: firmware IDLE event — starting idle sequence", self._device)
            # Switch to flags=3 so firmware monitors for activity during dim/idle
            try:
                self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x50, SW_IDLE)
            except Exception:
                pass
            idle_enabled = self._idle_effect_id() != 0 and self._idle_timeout > 0 and not self._is_ignored("rgb_idle_effect")
            if idle_enabled:
                self._start_idle_effect()
            else:
                self._state = self.IDLE
            # Sleep is host-driven only — schedule whenever _sleep_timeout > 0,
            # regardless of the setting's ignore flag (which only blocks pushing
            # the user value to firmware, see start()).
            sleep_enabled = self._sleep_timeout > 0
            if sleep_enabled:
                delay = max(self._sleep_timeout - self._idle_timeout, 0)
                if delay == 0:
                    self._start_sleep()
                else:
                    self._sleep_timer_id = GLib.timeout_add_seconds(delay, self._sleep_timer_fired)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("%s: sleep timer scheduled in %ds", self._device, delay)
        else:
            # ACTIVE event — user resumed typing
            if self._state == self.ACTIVE:
                return  # Already active, ignore burst
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: firmware ACTIVE event — waking", self._device)
            self._cancel_sleep_timer()
            self._wake()

    def _sleep_timer_fired(self):
        """GLib callback — software sleep timer expired after IDLE."""
        self._sleep_timer_id = None
        if self._state in (self.IDLE, self.DIMMING) and self._device.online:
            self._start_sleep()
        return False  # One-shot timer

    def _cancel_sleep_timer(self):
        if self._sleep_timer_id is not None:
            GLib.source_remove(self._sleep_timer_id)
            self._sleep_timer_id = None

    def _read_firmware_timers(self):
        """Read idle/sleep timeouts from firmware as the manager's defaults."""
        try:
            resp = self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x70, b"\x00")
            if resp and len(resp) >= 7:
                idle_s = (resp[3] << 8) | resp[4]
                sleep_s = (resp[5] << 8) | resp[6]
                if idle_s > 0:
                    self._idle_timeout = idle_s
                if sleep_s > 0:
                    self._sleep_timeout = sleep_s
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "%s: firmware timers: idle=%ds, sleep=%ds",
                        self._device,
                        idle_s,
                        sleep_s,
                    )
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: could not read firmware timers, using defaults: %s", self._device, e)

    def _write_firmware_idle_timeout(self, seconds):
        """Push idle/sleep timeouts back to firmware so it fires IDLE on time."""
        try:
            idle_hi = (seconds >> 8) & 0xFF
            idle_lo = seconds & 0xFF
            sleep_hi = (self._sleep_timeout >> 8) & 0xFF
            sleep_lo = self._sleep_timeout & 0xFF
            payload = bytes([0x01, 0x00, 0x00, idle_hi, idle_lo, sleep_hi, sleep_lo])
            self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x70, payload)
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: could not write firmware idle timeout: %s", self._device, e)

    # --- Idle effect ---

    def _start_idle_effect(self):
        idle_id = self._idle_effect_id()
        if idle_id == 0x80:  # Dim
            dim_pct = int(getattr(self._idle_effect, "intensity", 50) or 50)
            self._start_dim_ramp(dim_pct)
        elif idle_id == 0x01:  # Static — snap to idle color
            self._start_static_idle()
        elif idle_id != 0x00:
            self._apply_animation(idle_id)

    def _start_static_idle(self):
        """Snap to the idle effect's color exactly as if the user had set
        the active Static zone color to it. Per-key paint continues to
        display; unset cells repaint to the idle primary color via
        effective_zone_base_color's IDLE-state substitution. No animation
        — instant transition. Wake reverts via _restore_colors()."""
        idle_color = int(getattr(self._idle_effect, "color", 0) or 0)
        infos = getattr(self._device, "led_effects", None)
        if not infos or not infos.zones:
            self._state = self.IDLE
            return
        self._state = self.IDLE
        perkey_setting, has_paint = perkey_has_paint(self._device)
        perkey_dominates = has_paint and zone_effect_is_static(self._device)
        if perkey_dominates and perkey_setting is not None:
            # Per-key is the visible layer — repaint unset cells with the
            # idle color (effective_zone_base_color now returns it because
            # state == IDLE and idle effect ID == Static).
            try:
                if perkey_setting._fill_unset_zones_with_base_color():
                    perkey_setting._send_with_retry(0x70, b"\x00")  # FrameEnd
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: static idle per-key repaint failed: %s", self._device, e)
            return
        # Zone is the visible layer — push Static at idle.color to each zone.
        for zone in infos.zones:
            if 0x01 in (e.ID for e in zone.effects):
                try:
                    self._push_static_effect(zone, idle_color)
                except Exception as e:
                    if logger.isEnabledFor(logging.WARNING):
                        logger.warning("%s: static idle zone push failed: %s", self._device, e)

    def _start_dim_ramp(self, dim_pct):
        """Smooth ~5s dim ramp. Dims the per-key buffer when it's the visible
        layer (any real per-key paint), otherwise the zone effect."""
        infos = getattr(self._device, "led_effects", None)
        if not infos or not infos.zones:
            self._state = self.IDLE
            return

        perkey_setting, has_paint = perkey_has_paint(self._device)
        # Per-key only dominates when zone is Static. Under animations, the
        # firmware engine owns the visible layer — dim the zone instead.
        perkey_active = has_paint and zone_effect_is_static(self._device)

        self._dim_perkey = None
        if perkey_active:
            self._dim_zones = []
            self._dim_perkey = self._build_full_perkey_dim_map(perkey_setting, dim_pct)
            if self._dim_perkey:
                # Push base color to unset cells first so they don't start from stale.
                self._init_unset_perkey_zones(perkey_setting)
        else:
            self._dim_zones = []
            for zone in infos.zones:
                if 0x01 in (e.ID for e in zone.effects):
                    start_color = self._get_zone_color(zone)
                    target_color = self._compute_dim_color(start_color, dim_pct)
                    self._dim_zones.append((zone, start_color, target_color))

        if not self._dim_zones and not self._dim_perkey:
            self._state = self.IDLE
            return
        self._dim_step = 0
        self._state = self.DIMMING
        self._dim_timer_id = GLib.timeout_add(self._DIM_INTERVAL_MS, self._dim_ramp_step)
        if logger.isEnabledFor(logging.DEBUG):
            n_zones = len(self._dim_zones)
            n_perkey = len(self._dim_perkey) if self._dim_perkey else 0
            logger.debug(
                "%s: starting dim ramp to %d%% brightness (%d zones, %d per-key%s)",
                self._device,
                dim_pct,
                n_zones,
                n_perkey,
                ", per-key masking zones" if perkey_active else "",
            )

    def _dim_ramp_step(self):
        if self._state != self.DIMMING or not self._device.online:
            self._dim_timer_id = None
            return False
        self._dim_step += 1
        t = self._dim_step / self._DIM_STEPS
        for zone, start_color, target_color in self._dim_zones:
            try:
                self._push_static_effect(zone, self._interpolate_color(start_color, target_color, t))
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: dim ramp step failed for zone %s: %s", self._device, zone.index, e)
        if self._dim_perkey:
            try:
                self._push_perkey_dimmed(t)
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: dim ramp step failed for per-key: %s", self._device, e)
        if self._dim_step >= self._DIM_STEPS:
            self._state = self.IDLE
            self._dim_timer_id = None
            return False
        return True

    def _push_static_effect(self, zone, color):
        """Non-persistent Static effect, one zone."""
        static_effect = next((e for e in zone.effects if e.ID == 0x01), None)
        if static_effect is None:
            return
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        params = bytes([r, g, b, 0, 0, 0, 0, 0, 0, 0])
        payload = bytes([zone.index, static_effect.index]) + params + b"\x01"
        self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x10, payload)

    def _push_perkey_dimmed(self, t):
        """Push interpolated per-key colors for one dim ramp step.

        Groups keys by their interpolated color and uses SetRgbZonesSingleValue
        (0x8081 function 6) for efficient bulk writes — up to 13 zone IDs per
        HID message when multiple keys share the same dimmed color.
        """
        # Build color -> [zone_ids] map for this interpolation step
        color_groups = {}
        for zone_id, (start_color, target_color) in self._dim_perkey.items():
            color = self._interpolate_color(start_color, target_color, t)
            if color not in color_groups:
                color_groups[color] = []
            color_groups[color].append(zone_id)

        feat = SupportedFeature.PER_KEY_LIGHTING_V2
        for color, zone_ids in color_groups.items():
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            # Function 6: SetRgbZonesSingleValue — color(3) + zone_ids (up to 13 per report)
            while zone_ids:
                batch = zone_ids[:13]
                zone_ids = zone_ids[13:]
                data = bytes([r, g, b]) + bytes(batch)
                self._device.feature_request(feat, 0x60, data)
        # Commit the frame
        self._device.feature_request(feat, 0x70, b"\x00\x00\x00\x00\x00")

    def _apply_animation(self, effect_id):
        """Hand off to a firmware animation. Generic over any effect in
        hidpp20.LEDEffects: builds the 10-byte param block from the
        effect's param map, sourcing color from the zone and other
        params from the persisted _idle_effect."""
        from . import hidpp20

        infos = getattr(self._device, "led_effects", None)
        if not infos or not infos.zones:
            self._state = self.IDLE
            return
        entry = hidpp20.LEDEffects.get(effect_id)
        if entry is None:
            self._state = self.IDLE
            return
        param_map = entry[1]
        for zone in infos.zones:
            effect_info = next((e for e in zone.effects if e.ID == effect_id), None)
            if effect_info is None:
                continue
            color = self._get_zone_color(zone)
            params = bytearray(10)
            if hidpp20.LEDParam.color in param_map:
                offset = param_map[hidpp20.LEDParam.color]
                params[offset] = (color >> 16) & 0xFF
                params[offset + 1] = (color >> 8) & 0xFF
                params[offset + 2] = color & 0xFF
            for pname, poff in param_map.items():
                if pname == hidpp20.LEDParam.color:
                    continue
                psize = hidpp20.LEDParamSize.get(pname, 1)
                user_val = getattr(self._idle_effect, str(pname), None)
                if user_val is None:
                    user_val = effect_info.period or 3000 if pname == hidpp20.LEDParam.period else 0
                params[poff : poff + psize] = int(user_val).to_bytes(psize, "big")
            if effect_id == 0x01:
                params[3] = 0x02  # Static fixed-color marker
            payload = bytes([zone.index, effect_info.index]) + bytes(params) + b"\x01"
            try:
                self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x10, payload)
            except Exception as exc:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning(
                        "%s: failed to apply animation 0x%02x to zone %d: %s",
                        self._device,
                        effect_id,
                        zone.index,
                        exc,
                    )
        self._state = self.IDLE

    # --- Sleep ---

    def _start_sleep(self):
        """Enter firmware-managed sleep. Firmware fades from current level."""
        self._cancel_dim_timer()
        try:
            self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x80, b"\x01\x03\x00")
            self._state = self.SLEEPING
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("%s: RGB entering sleep (firmware power-down)", self._device)
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: failed to enter RGB sleep: %s", self._device, e)

    # --- Wake ---

    def _wake(self):
        """Restore full lighting from any non-ACTIVE state."""
        if self._state == self.ACTIVE:
            return
        prev_state = self._state
        self._cancel_dim_timer()
        self._cancel_sleep_timer()
        # State must be ACTIVE before _restore_colors() — the paint paths
        # translate through it, and writes would otherwise go at the old dim.
        self._state = self.ACTIVE
        try:
            if prev_state == self.SLEEPING:
                self._set_power_mode_with_retry(1)
            # Re-claim full LED pipeline control
            self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x50, SW_ACTIVE)
            # Firmware engine has re-engaged during sleep — re-arm per-key
            # one-shots so the next write re-fires the prep + double-send.
            for s in self._device.settings:
                if s.name == "per-key-lighting":
                    s._frame_settled = False
                    s._prep_pushed = False
                    break
            self._restore_colors()
            if logger.isEnabledFor(logging.DEBUG):
                state_names = {self.DIMMING: "dimming", self.IDLE: "idle", self.SLEEPING: "sleep"}
                logger.debug("%s: RGB woken from %s", self._device, state_names.get(prev_state, "unknown"))
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("%s: failed to wake RGB LEDs: %s", self._device, e)

    def _cancel_dim_timer(self):
        if self._dim_timer_id is not None:
            GLib.source_remove(self._dim_timer_id)
            self._dim_timer_id = None

    def _get_zone_color(self, zone):
        location = int(zone.location)
        setting_name = f"rgb_zone_{location}"
        for s in self._device.settings:
            if s.name == setting_name and s._value is not None:
                return getattr(s._value, "color", 0xFFFFFF)
        return 0xFFFFFF

    def _get_zone_base_color(self):
        """Color used as the base for unset per-key cells. Black when the
        zone effect is marked ignore, the saved zone color otherwise."""
        return effective_zone_base_color(self._device)

    @staticmethod
    def _has_real_perkey_colors(perkey_setting):
        if not perkey_setting._value:
            return False
        no_change = special_keys.COLORSPLUS["No change"]
        return any(color != no_change and isinstance(color, int) and color >= 0 for color in perkey_setting._value.values())

    def _build_full_perkey_dim_map(self, perkey_setting, dim_pct):
        """{zone_id: (start, target)} for every zone — user-set keys from
        their color, unset from the zone base."""
        no_change = special_keys.COLORSPLUS["No change"]
        zone_base = self._get_zone_base_color()
        user_colors = {int(k): c for k, c in perkey_setting._value.items() if c != no_change and isinstance(c, int) and c >= 0}
        return {
            int(k): (start, self._compute_dim_color(start, dim_pct))
            for k in perkey_setting._validator.choices
            for start in (user_colors.get(int(k), zone_base),)
        }

    def _init_unset_perkey_zones(self, perkey_setting):
        """Push the zone base color to per-key cells the user hasn't painted —
        avoids the white-default flash when per-key takes over the buffer."""
        no_change = special_keys.COLORSPLUS["No change"]
        zone_base = self._get_zone_base_color()
        r = (zone_base >> 16) & 0xFF
        g = (zone_base >> 8) & 0xFF
        b = zone_base & 0xFF

        user_set = {int(k) for k, c in perkey_setting._value.items() if c != no_change and isinstance(c, int) and c >= 0}
        unset_zones = [int(k) for k in perkey_setting._validator.choices if int(k) not in user_set]
        if not unset_zones:
            return

        feat = SupportedFeature.PER_KEY_LIGHTING_V2
        remaining = list(unset_zones)
        try:
            while remaining:
                batch = remaining[:13]
                remaining = remaining[13:]
                self._device.feature_request(feat, 0x60, bytes([r, g, b]) + bytes(batch))
            self._device.feature_request(feat, 0x70, b"\x00\x00\x00\x00\x00")
        except exceptions.FeatureCallError as e:
            logger.warning("%s: per-key zone init failed (device busy?): %s", self._device, e)

    @staticmethod
    def _compute_dim_color(color, dim_pct):
        r = ((color >> 16) & 0xFF) * dim_pct // 100
        g = ((color >> 8) & 0xFF) * dim_pct // 100
        b = (color & 0xFF) * dim_pct // 100
        return (r << 16) | (g << 8) | b

    @staticmethod
    def _interpolate_color(start, target, t):
        r_s, g_s, b_s = (start >> 16) & 0xFF, (start >> 8) & 0xFF, start & 0xFF
        r_t, g_t, b_t = (target >> 16) & 0xFF, (target >> 8) & 0xFF, target & 0xFF
        r = int(r_s + (r_t - r_s) * t)
        g = int(g_s + (g_t - g_s) * t)
        b = int(b_s + (b_t - b_s) * t)
        return (r << 16) | (g << 8) | b

    def _current_dim_pct(self):
        """100 unless we're in Dim mode — animations run at firmware brightness."""
        if self._idle_effect_id() != 0x80:
            return 100
        return int(getattr(self._idle_effect, "intensity", 50) or 50)

    def translate_color(self, color):
        """Map a saved (undimmed) per-key color to what should be displayed
        on the device right now, given the current power-management state.
        Returns None to signal SLEEPING — caller should persist and skip the
        wire write; _restore_colors on wake will re-push the saved value."""
        # Static idle is a color swap, not a brightness change — user-painted
        # cells render their saved color unchanged, and the unset-cell
        # substitution happens upstream via effective_zone_base_color.
        if self._state == self.IDLE and self._idle_effect_id() == 0x01:
            return color
        return translate_color_for_display(color, self._state, self._current_dim_pct(), self._dim_step, self._DIM_STEPS)

    def notify_perkey_changed(self, zone_id, new_color):
        """Resync a per-key zone's dim ramp entry to a user-repainted color."""
        if self._state != self.DIMMING or not self._dim_perkey or zone_id not in self._dim_perkey:
            return
        self._dim_perkey[zone_id] = (
            new_color,
            self._compute_dim_color(new_color, self._current_dim_pct()),
        )

    def notify_perkey_bulk_changed(self, color_map):
        """Bulk notify_perkey_changed, skipping 'No change' entries."""
        if self._state != self.DIMMING or not self._dim_perkey:
            return
        no_change = special_keys.COLORSPLUS["No change"]
        for zone_id, color in color_map.items():
            if color == no_change or not isinstance(color, int) or color < 0:
                continue
            self.notify_perkey_changed(int(zone_id), int(color))

    def notify_zone_changed(self, cluster_index, new_color):
        """Resync a zone-effect dim ramp entry to a user-repainted color."""
        if self._state != self.DIMMING or not self._dim_zones:
            return
        dim_pct = self._current_dim_pct()
        for i, (zone, _start, _target) in enumerate(self._dim_zones):
            if int(zone.index) == int(cluster_index):
                self._dim_zones[i] = (zone, new_color, self._compute_dim_color(new_color, dim_pct))
                return

    def _set_power_mode_with_retry(self, mode):
        """First command after wake may fail; retry."""
        params = bytes([0x01, mode, 0x00])
        for attempt in range(3):
            try:
                self._device.feature_request(SupportedFeature.RGB_EFFECTS, 0x80, params)
                return
            except Exception:
                if attempt == 2:
                    raise
                import time as _time

                _time.sleep(0.1)

    def _is_ignored(self, setting_name):
        """True if marked ignore via the lock icon."""
        persister = getattr(self._device, "persister", None)
        if persister is None:
            return False
        return persister.get_sensitivity(setting_name) == settings.SENSITIVITY_IGNORE

    def _restore_colors(self):
        """Re-push lighting state after waking. Per-key dominates only when
        zone is Static — under animations, the zone wire push goes through
        and per-key is skipped."""
        _perkey_setting, has_paint = perkey_has_paint(self._device)
        zone_static = zone_effect_is_static(self._device)
        perkey_dominates = has_paint and zone_static
        for s in self._device.settings:
            if s._value is None:
                continue
            if self._is_ignored(s.name):
                continue
            if s.name == "per-key-lighting":
                if not self._has_real_perkey_colors(s):
                    continue
                if not zone_static:
                    continue  # firmware animation owns the visible layer
            elif s.name.startswith("rgb_zone_"):
                if perkey_dominates:
                    continue
            else:
                continue
            try:
                s.write(s._value, save=False)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("%s: restored %s after wake", self._device, s.name)
            except Exception as e:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("%s: failed to restore %s: %s", self._device, s.name, e)
