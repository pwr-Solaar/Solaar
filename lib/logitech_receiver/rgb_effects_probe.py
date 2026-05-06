"""Read-only corpus probe for the headset RGB feature triplet:

  - HEADSET_RGB_ONBOARD_EFFECTS  (0x0621)
  - HEADSET_RGB_SIGNATURE_EFFECTS (0x0622)
  - HEADSET_RGB_0623             (0x0623, function set unmapped)

Logs raw response bytes and lengths at INFO so field testers without
``-dd`` can still capture the data. All calls are strictly read-side —
no setters are invoked. If a feature isn't present the probe
short-circuits cleanly.

Pcap analysis of G HUB's color-set traffic confirmed that on 0x0621,
``setRGBClusterEffect`` (fn 0x30) takes a 10-byte payload
``[cluster, effect_id_BE_u16, R, G, B, ...]`` where ``effect_id=0x0000``
means "Static (with RGB)" — this is also the slot-0 entry in the
fn 0x10 ``getRGBClusterInfo`` reply, which we decode structurally so
the test corpus shows effect-id semantics in plaintext.
"""

from __future__ import annotations

import logging

from . import exceptions
from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)


def _hex_or_none(data) -> str | None:
    return data.hex() if data else None


def _format_feature(feat) -> str:
    """Render a feature for the log: 0x{id:04X}{:NAME} when known, else raw.

    Unknown features are stored as the string "unknown:HHHH" by the feature
    discovery code, so handle that shape explicitly — int(feat) on those
    raises ValueError. Wrap the rest in a broad except so a future unhandled
    feature shape can't kill the whole table dump.
    """
    if feat is None:
        return "?"
    if isinstance(feat, str):
        if feat.startswith("unknown:") and len(feat) > 8:
            return f"0x{feat[8:].upper()}"
        return feat
    try:
        return f"0x{int(feat):04X}:{feat.name}"
    except (AttributeError, TypeError, ValueError):
        try:
            return f"0x{int(feat):04X}"
        except (TypeError, ValueError):
            return repr(feat)


def _log_feature_table(device) -> None:
    if not device.features:
        return
    try:
        # Parent features live in FeaturesArray.inverse, indexed by their
        # parent feature-set position. On Centurion devices these are the
        # ones the dongle itself exposes (typically 5-6 entries).
        parent = []
        for idx in range(len(device.features)):
            parent.append(f"{idx}:{_format_feature(device.features[idx])}")
        logger.info("RGB probe: parent features for %s: %s", device, ", ".join(parent))

        # Centurion sub-device features live in FeaturesArray.sub_inverse,
        # keyed by sub-device feature index. These are where the actual
        # headset features (0x0620/0x0621/0x0622, LogiVoice, EQ, mic mute,
        # …) live — without dumping them the log shows only the dongle's
        # parent features and gives the wrong impression that the device
        # has nothing else.
        sub_inverse = getattr(device.features, "sub_inverse", None)
        if sub_inverse:
            sub = [f"{idx}:{_format_feature(feat)}" for idx, feat in sorted(sub_inverse.items())]
            logger.info("RGB probe: sub-device features for %s: %s", device, ", ".join(sub))
    except Exception as e:
        logger.info("RGB probe: feature-table dump failed: %s", e)


def _call(device, feature: SupportedFeature, fn: int, *params):
    """Wrap feature_request with uniform INFO logging.

    Returns the raw bytes on success, None on transport/no-feature, and
    doesn't raise — FeatureCallError is caught and logged as an error code.
    """
    label = f"0x{int(feature):04X}.fn{fn:02X}"
    if params:
        label += "(" + ",".join(f"{b:02X}" for b in params) + ")"
    try:
        resp = device.feature_request(feature, fn, *params)
    except exceptions.FeatureCallError as e:
        logger.info("RGB probe: %s err=0x%02X", label, getattr(e, "error", 0) & 0xFF)
        return None
    except Exception as e:
        logger.info("RGB probe: %s raised %r", label, e)
        return None
    if resp is None:
        logger.info("RGB probe: %s no reply (feature unsupported or transport failure)", label)
        return None
    logger.info("RGB probe: %s resp=%s len=%d", label, _hex_or_none(resp), len(resp))
    return resp


# Names for known effect_ids on the headset RGB cluster. Confirmed via
# pcap analysis of G HUB color-set traffic: setRGBClusterEffect with
# effect_id=0x0000 + RGB writes a static color, so 0x0000 is "Static"
# rather than the "Off / Disabled" we'd guessed from cluster ordering.
# Other ids haven't been observed on the wire yet — names are placeholder
# until further pcap traffic confirms them.
_EFFECT_ID_NAMES = {
    0x0000: "Static",
    0x0001: "Effect 0x0001",
    0x0006: "Effect 0x0006",
    0x0007: "Effect 0x0007",
    0x000F: "Effect 0x000F",
    0x007F: "Effect 0x007F",
}


def _decode_cluster_info(resp) -> str | None:
    """Decode a 0x0621 fn 0x10 getRGBClusterInfo reply into a readable
    summary. Best-effort — returns None on unexpected length/shape.

    Observed shape on G522: 4-byte records (effect_id LE u16, slot_idx
    LE u16). The effect_id at slot 0 is 0x0000 = "Static" (with RGB),
    confirmed by pcap of G HUB color-set traffic. Records continue
    until trailing-zero padding.

    Note: most HID++ multi-byte fields are BE, but this particular
    response uses LE — confirmed against captured factory-default bytes
    on G522 where the values 0x0001 / 0x000F / 0x007F appear at byte 0
    of each record with byte 1 = 0x00 (consistent with LE u16).
    """
    if not resp or len(resp) < 4:
        return None
    effects = []
    seen_static = False
    for i in range(0, len(resp) - 3, 4):
        eid = resp[i] | (resp[i + 1] << 8)
        slot = resp[i + 2] | (resp[i + 3] << 8)
        # Skip purely-zero padding once we've seen the (effect=0, slot=0) entry.
        if eid == 0 and slot == 0:
            if seen_static:
                continue
            seen_static = True
        name = _EFFECT_ID_NAMES.get(eid, f"0x{eid:04X}")
        effects.append(f"slot={slot}:{name}")
    return ", ".join(effects) if effects else None


def probe_onboard_effects(device) -> None:
    """Probe 0x0621 RGBOnboardEffects read-side functions."""
    feature = SupportedFeature.HEADSET_RGB_ONBOARD_EFFECTS
    if not device.features or feature not in device.features:
        return
    logger.info("RGB probe: 0x0621 HEADSET_RGB_ONBOARD_EFFECTS present on %s", device)

    # fn 0x00 getInfo — empty payload
    _call(device, feature, 0x00)

    # fn 0x10 getRGBClusterInfo — iterate cluster indexes 0..7, stop on error.
    for cluster_idx in range(8):
        resp = _call(device, feature, 0x10, cluster_idx)
        if resp is None:
            break
        decoded = _decode_cluster_info(resp)
        if decoded:
            logger.info("RGB probe: 0x0621.fn10(%02X) decoded: %s", cluster_idx, decoded)

    # fn 0x20 getRGBClusterEffect — current state per cluster.
    for cluster_idx in range(8):
        resp = _call(device, feature, 0x20, cluster_idx)
        if resp is None:
            break

    # fn 0x40 getRGBCustomEffectName — single call, documented.
    _call(device, feature, 0x40)


def probe_unknown_0623(device) -> None:
    """Probe 0x0623 (purpose unmapped) — present on G522 sub-device.

    Function set unknown. Try a small window of low function indexes to
    capture whatever responds. Strictly read-side; we don't know what
    arguments the functions take so we just call each with no payload
    and let the device 0x0A any function that needs args.
    """
    feature = SupportedFeature.HEADSET_RGB_0623
    if not device.features or feature not in device.features:
        return
    logger.info("RGB probe: 0x0623 HEADSET_RGB_0623 present on %s", device)
    # Functions 0..7 covers the typical "info / get* / get*" range; if
    # anything responds we'll have first bytes to triangulate against.
    for fn_idx in range(8):
        _call(device, feature, fn_idx << 4)


def probe_signature_effects(device) -> None:
    """Probe 0x0622 RGBSignatureEffects read-side functions."""
    feature = SupportedFeature.HEADSET_RGB_SIGNATURE_EFFECTS
    if not device.features or feature not in device.features:
        return
    logger.info("RGB probe: 0x0622 HEADSET_RGB_SIGNATURE_EFFECTS present on %s", device)

    # fn 0x00 getSignatureEffectsInfo.
    _call(device, feature, 0x00)

    # fn 0x10 getSignatureEffectParams — iterate effectId 0..2 (Startup/Shutdown/Passive).
    # effectId is u16 BE.
    for eid in range(3):
        _call(device, feature, 0x10, (eid >> 8) & 0xFF, eid & 0xFF)

    # fn 0x30 getSignatureEffectState — same effectId range.
    for eid in range(3):
        _call(device, feature, 0x30, (eid >> 8) & 0xFF, eid & 0xFF)


def probe(device) -> None:
    """Run both read-only RGB-effects probes once per device.

    Gated via ``_rgb_effects_probed`` so re-entry on reconnect / setting
    rebuild doesn't spam the log with duplicate corpus dumps.
    """
    if getattr(device, "_rgb_effects_probed", False):
        return
    device._rgb_effects_probed = True
    _log_feature_table(device)
    try:
        probe_onboard_effects(device)
    except Exception as e:
        logger.info("RGB probe: onboard-effects probe raised %r", e)
    try:
        probe_signature_effects(device)
    except Exception as e:
        logger.info("RGB probe: signature-effects probe raised %r", e)
    try:
        probe_unknown_0623(device)
    except Exception as e:
        logger.info("RGB probe: 0x0623 probe raised %r", e)
