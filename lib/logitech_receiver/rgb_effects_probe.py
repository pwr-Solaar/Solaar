"""Read-only corpus probe for HEADSET_RGB_ONBOARD_EFFECTS (0x0621) and
HEADSET_RGB_SIGNATURE_EFFECTS (0x0622).

Logs raw response bytes and lengths at INFO so field testers without
``-dd`` can still capture the data. All calls are strictly read-side —
no setters are invoked. If either feature isn't present the probe
short-circuits cleanly.
"""

from __future__ import annotations

import logging

from . import exceptions
from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)


def _hex_or_none(data) -> str | None:
    return data.hex() if data else None


def _log_feature_table(device) -> None:
    if not device.features:
        return
    try:
        pairs = []
        for idx in range(len(device.features)):
            feat = device.features[idx]
            pairs.append(f"{idx}:0x{int(feat):04X}" if feat is not None else f"{idx}:?")
        logger.info("RGB probe: feature table for %s: %s", device, ", ".join(pairs))
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

    # fn 0x20 getRGBClusterEffect — current state per cluster.
    for cluster_idx in range(8):
        resp = _call(device, feature, 0x20, cluster_idx)
        if resp is None:
            break

    # fn 0x40 getRGBCustomEffectName — single call, documented.
    _call(device, feature, 0x40)


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
