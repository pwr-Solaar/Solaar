"""Per-device-model quirks.

Keyed by ``device.modelId``, which Logitech composes by concatenating every
transport-specific PID (btid + btleid + wpid + usbid) for a single physical
model. That makes one entry cover the same device regardless of how it is
currently connected — no transport-aliasing gotchas.

Quirks are hand-curated. Devices do not self-report behaviors like "this
firmware ignores the bytes I wrote", so each entry is observation-derived.
Keep entries narrow and document the observation in a comment.
"""

from __future__ import annotations

# Quirk keys are named after the doc-canonical feature/function path so a
# grep for the HID++ feature name (e.g. "RGBEffects", "NvConfig") lands here.
#
# Default-allow: each quirk lists what is KNOWN to be broken or ignored on
# that device model. Unlisted models / unlisted entries get the full UI.
#
#   rgb_effects_nvconfig_colors_inert
#       Feature 0x8071 RGBEffects, Function 3 NvConfig — cap-id → set of
#       color slot names ({"color1", "color2"}) whose bytes the firmware
#       accepts but does not visibly apply. UI hides color pickers for
#       slots in the set.
QUIRKS: dict[str, dict[str, object]] = {
    # G502 X PLUS — RGBEffects NvConfig startup effect (cap 0x0001): color
    # bytes are entirely ignored; only the enabled flag is honored. Shutdown
    # cap (0x0040) is not supported and is suppressed via build()-time probe.
    "4099C0950000": {
        "rgb_effects_nvconfig_colors_inert": {
            0x0001: {"color1", "color2"},
        },
    },
}


def get(device, key, default=None):
    """Look up a quirk by key for the device's model.

    Returns ``default`` when either the model has no quirks entry or the
    entry lacks the requested key.
    """
    model_id = getattr(device, "modelId", None)
    if not model_id:
        return default
    return QUIRKS.get(model_id, {}).get(key, default)
