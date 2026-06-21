"""Per-device-model quirks for RGB lighting.

Keyed by ``device.modelId``. For normal HID++ devices that is the string
Logitech composes by concatenating every transport PID (btid + btleid + wpid
+ usbid) — one entry covers the model on any transport. For Centurion
headsets it is the firmware-stable model byte (G522 ``"32"``, G325 ``"44"``);
see ``device._get_ids_centurion``.

Two postures, by feature class:

* **Effect parameters that do NOT persist** (zone effects, LED directions) —
  default-ALLOW. Those are validated and low-harm (a wrong value is cosmetic
  and transient). They use blocklists elsewhere, e.g. ``LedDirectionBlocklist``
  in ``hidpp20.py``. Nothing of that kind lives here.

* **NVconfig-saved colors** (0x8071 RGBEffects boot effects, 0x0622 HeadsetRGB
  signature effects) — default-DENY. Those writes persist to non-volatile
  storage, so an unvalidated control can durably misconfigure a device. Every
  field is hidden and every slot suppressed unless the exact model is listed
  here as known-good.

Setting ``SOLAAR_EXPERIMENTAL`` truthy bypasses the allowlists entirely — for
testers / reverse-engineering on devices not yet validated.

Entries are hand-curated; document the observation in a comment.
"""

from __future__ import annotations

import os

_ALL_NVCONFIG_FIELDS = {"color1", "color2", "speed"}


def _experimental() -> bool:
    """True when SOLAAR_EXPERIMENTAL is set truthy — bypasses allowlist masking."""
    return os.environ.get("SOLAAR_EXPERIMENTAL", "").strip().lower() in ("1", "true", "yes", "on")


# Feature 0x8071 RGBEffects, Function 3 NvConfig — persistent boot/shutdown
# effects. Default-DENY allowlist: modelId -> cap_id -> set of color fields
# the firmware is KNOWN to honor. A listed cap shows the setting (its On/Off
# toggle plus the listed color pickers); an empty set shows the toggle only.
# An unlisted cap or unlisted model suppresses the setting entirely.
RGB_EFFECTS_NVCONFIG_ALLOWED: dict[str, dict[int, set[str]]] = {
    # G502 X PLUS — startup (0x0001): color bytes are inert, only the enabled
    # flag is honored, so no color fields are allowed (toggle only). Shutdown
    # (0x0040) is not supported and is suppressed by build()-time probe anyway.
    "4099C0950000": {0x0001: set()},
    # G515 LIGHTSPEED TKL — startup and shutdown both honor both colors.
    "B38940B4C355": {0x0001: {"color1", "color2"}, 0x0040: {"color1", "color2"}},
}

# Feature 0x0622 HeadsetRGB signature effects — persistent startup / shutdown
# / passive effects. Default-DENY allowlist: modelId -> effect_id -> set of
# fields the firmware is KNOWN to honor. An unlisted effect_id or model
# suppresses that signature-effect setting entirely.
HEADSET_SIGNATURE_EFFECTS_ALLOWED: dict[str, dict[int, set[str]]] = {
    # G522 LIGHTSPEED (Centurion model byte 0x32, from DeviceInfo func 0;
    # confirmed against multiple diagnostic logs). Verified against user
    # reports: startup honors only the primary color (secondary unused, speed
    # has no effect); shutdown honors both colors (speed has no effect). The
    # passive slot (effect_id 2) is omitted — its behavior is not understood,
    # so the whole passive setting is suppressed.
    "32": {
        0: {"color1"},
        1: {"color1", "color2"},
    },
}


# Keyboards whose firmware breaks the F-row / media keys when the RGB
# SW-control claim switches them to host mode (ONBOARD_PROFILES fn 0x10 mode
# 0x02) — Solaar #1100. A USB capture of G HUB's bring-up shows it drives the
# LEDs from onboard mode via the RGB SetSWControl claim alone, never making
# that switch. For these models the claim keeps onboard mode, which also avoids
# the host-mode transition that made the firmware re-assert the M/MR indicator
# over a per-key cell (the G915 TKL F4 blackout).
RGB_CLAIM_KEEPS_ONBOARD_MODE: set[str] = {
    "B35F408EC343",  # G915 TKL LIGHTSPEED — verified: host mode disables F-keys/media keys
}

# Keyboards where switching onboard profiles drops the software per-key/zone
# paint (the firmware loads the switched-to profile's own onboard lighting).
# For these, re-assert the claim + repaint on a profile-change notification so
# an accidental profile switch doesn't strand the user's software scheme.
RGB_REPAINT_ON_PROFILE_CHANGE: set[str] = {
    "B35F408EC343",  # G915 TKL LIGHTSPEED
}


def rgb_claim_keeps_onboard_mode(device) -> bool:
    """True when the RGB SW-control claim must NOT switch this model to host
    mode (it would disable the F-row / media keys)."""
    return (getattr(device, "modelId", None) or "") in RGB_CLAIM_KEEPS_ONBOARD_MODE


def rgb_repaint_on_profile_change(device) -> bool:
    """True when a profile-change notification should re-apply the claimed
    software RGB state on this model (the switch drops the per-key paint)."""
    return (getattr(device, "modelId", None) or "") in RGB_REPAINT_ON_PROFILE_CHANGE


def rgb_effects_nvconfig_allowed_fields(device, cap_id: int) -> set[str] | None:
    """Color fields to expose for an 0x8071 NvConfig boot effect.

    Returns the allowed field set (possibly empty — On/Off toggle only), or
    ``None`` to suppress the setting entirely.
    """
    if _experimental():
        return set(_ALL_NVCONFIG_FIELDS)
    model_id = getattr(device, "modelId", None) or ""
    return RGB_EFFECTS_NVCONFIG_ALLOWED.get(model_id, {}).get(cap_id)


def headset_signature_allowed_fields(device, effect_id: int) -> set[str] | None:
    """Fields to expose for an 0x0622 signature effect slot.

    Returns the allowed field set, or ``None`` to suppress the slot entirely.
    """
    if _experimental():
        return set(_ALL_NVCONFIG_FIELDS)
    model_id = getattr(device, "modelId", None) or ""
    return HEADSET_SIGNATURE_EFFECTS_ALLOWED.get(model_id, {}).get(effect_id)
