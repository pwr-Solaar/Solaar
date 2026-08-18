"""Per-device-model quirks for RGB lighting and firmware-gated settings.

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

* **Settings a firmware revision stubbed out** — default-ALLOW, suppressed only
  over the firmware ranges named in ``SETTING_INERT_FIRMWARE``. A feature that
  is advertised and round-trips cleanly but does nothing is indistinguishable
  from a working one over the wire, so the version boundary has to be recorded
  by hand.

Setting ``SOLAAR_EXPERIMENTAL`` truthy bypasses the allowlists entirely — for
testers / reverse-engineering on devices not yet validated.

Entries are hand-curated; document the observation in a comment.
"""

from __future__ import annotations

import logging
import os

from . import common

logger = logging.getLogger(__name__)

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


# Settings the firmware only backs over part of a device's version history.
# modelId -> setting name -> (inert_from, inert_before), each a
# (number, revision, build) tuple or None for an open end. The setting is
# suppressed at or above `inert_from`, and below `inert_before`.
SETTING_INERT_FIRMWARE: dict[str, dict[str, tuple[tuple | None, tuple | None]]] = {
    # G560 Gaming Speaker — firmware 122.3.23 retired the hardware equalizer
    # (0x8310) and brought up subwoofer level (0x8305). From that version on
    # the EQ still advertises and round-trips but is audibly silent; verified
    # inert on 122.4.370, where bass does work. Older firmware appears not to
    # carry 0x8305 at all, so that bound is defensive.
    "000000000A78": {
        "equalizer": ((122, 3, 23), None),
        "bass_tone": (None, (122, 3, 23)),
    },
}


def _main_firmware_version(device) -> tuple[int, int, int] | None:
    """Highest main-firmware version on the device, the entity G HUB reports."""
    versions = [
        version
        for fw in getattr(device, "firmware", None) or ()
        if fw.kind == common.FirmwareKind.Firmware
        for version in (common.firmware_version_tuple(fw),)
        if version is not None
    ]
    return max(versions, default=None)


def setting_inert(device, setting_name: str) -> bool:
    """True when this device's firmware is known not to back the named setting.

    Fails open: firmware that can't be read or parsed exposes the setting rather
    than risk hiding a working control.
    """
    if _experimental():
        return False
    model_id = getattr(device, "modelId", None) or ""
    bounds = SETTING_INERT_FIRMWARE.get(model_id, {}).get(setting_name)
    if bounds is None:
        return False
    version = _main_firmware_version(device)
    if version is None:
        return False
    inert_from, inert_before = bounds
    inert = (inert_from is not None and version >= inert_from) or (inert_before is not None and version < inert_before)
    if inert:
        logger.info(
            "%s: hiding %s — firmware %s does not back it",
            model_id,
            setting_name,
            ".".join(str(part) for part in version),
        )
    return inert


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
