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

"""LogiVoice (0x0900 + 0x0901-0x0907) read helpers.

Each LogiVoice processing module exposes the same 5-function API:

  fn 0 SetState
  fn 1 GetState       -> u8 state (boolean)
  fn 2 SetParameters
  fn 3 GetParameters  -> module-specific payload (see PARAMETERS_FIELDS)
  fn 4 GetInfo        -> per-field [min, max] bounds (see parse_info)

All multi-byte integers on the wire are big-endian. Parameters layouts are
module-specific; PARAMETERS_FIELDS encodes per-field offset / width /
signedness / range / label metadata. The first field is at offset 0 — there
is no leading "state" byte (the state toggle is on fn 0/1 only).

Writes are NOT implemented yet. State toggles via fn 0x00/0x10 are
shipping as boolean settings; per-field Parameters writes need a live
round-trip verification before they're safe to expose.
"""

from __future__ import annotations

import logging
import struct

from typing import Iterable

from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

# Wire function IDs (standard across all LogiVoice modules).
FN_SET_STATE = 0x00
FN_GET_STATE = 0x10
FN_SET_PARAMETERS = 0x20
FN_GET_PARAMETERS = 0x30
FN_GET_INFO = 0x40

# Human-readable names for the modules Solaar may see on a LogiVoice device.
MODULE_NAMES = {
    SupportedFeature.LOGIVOICE: "LogiVoice",
    SupportedFeature.LOGIVOICE_NOISE_REDUCTION: "Noise Reduction",
    SupportedFeature.LOGIVOICE_NOISE_GATE: "Noise Gate",
    SupportedFeature.LOGIVOICE_COMPRESSOR: "Compressor",
    SupportedFeature.LOGIVOICE_DE_ESSER: "De-esser",
    SupportedFeature.LOGIVOICE_DE_POPPER: "De-popper",
    SupportedFeature.LOGIVOICE_LIMITER: "Limiter",
    SupportedFeature.LOGIVOICE_HIGH_PASS_FILTER: "High Pass Filter",
}

# Short slugs used in Solaar setting IDs (`logivoice-<slug>-<field>`).
MODULE_SLUGS = {
    SupportedFeature.LOGIVOICE_NOISE_REDUCTION: "nr",
    SupportedFeature.LOGIVOICE_NOISE_GATE: "ng",
    SupportedFeature.LOGIVOICE_COMPRESSOR: "comp",
    SupportedFeature.LOGIVOICE_DE_ESSER: "deesser",
    SupportedFeature.LOGIVOICE_DE_POPPER: "depopper",
    SupportedFeature.LOGIVOICE_LIMITER: "limiter",
    SupportedFeature.LOGIVOICE_HIGH_PASS_FILTER: "hpf",
}


class Field:
    """Metadata for one decoded Parameters field.

    offset:     byte offset within the GetParameters payload.
    byte_count: width (1 or 2 for fields we currently decode).
    signed:     whether to interpret as signed int.
    min_value/max_value: range for the Solaar slider validator. For opaque
                fields, use the full representable range (0..255 or 0..65535).
    label:      human-readable name for UI.
    opaque:     True if the field's wire encoding isn't pinned down — label
                shows raw units and the caller should treat as round-trip.
    """

    def __init__(self, name, offset, byte_count, signed, min_value, max_value, label, opaque=False):
        self.name = name
        self.offset = offset
        self.byte_count = byte_count
        self.signed = signed
        self.min_value = min_value
        self.max_value = max_value
        self.label = label
        self.opaque = opaque


# Per-module field layout for GetParameters / SetParameters payload. Each
# module's struct is the union of named fields below; there is no separate
# "state" byte at offset 0 — that toggle is only on fn 0x00/0x10. Field
# encodings (signedness, byte order, units) and value ranges come from the
# device's GetInfo response (see parse_info) and are confirmed against
# captured bring-up bytes; ranges hardcoded here are the bounds the device
# reports and the values it ships as factory defaults.
#
# `opaque=True` is reserved for fields whose unit scale isn't pinned down
# (currently width_q on De-esser / De-popper — the host-side scale constant
# is loaded at runtime and not statically resolvable). Treat opaque values
# as monotonic raw integers until a live probe anchors the units.
PARAMETERS_FIELDS: dict[SupportedFeature, list[Field]] = {
    SupportedFeature.LOGIVOICE_NOISE_REDUCTION: [
        Field("sensitivity", 0, 1, False, 0, 40, "Sensitivity"),
        Field("release", 1, 2, False, 1, 1000, "Release (ms)"),
        Field("bias", 3, 1, False, 0, 5, "Bias"),
        Field("attenuation", 4, 1, True, -20, 0, "Attenuation (dB)"),
    ],
    SupportedFeature.LOGIVOICE_NOISE_GATE: [
        Field("threshold", 0, 1, True, -60, -35, "Threshold (dB)"),
        Field("attenuation", 1, 1, True, -50, -3, "Attenuation (dB)"),
        Field("attack", 2, 2, False, 1, 200, "Attack (ms)"),
        Field("hold", 4, 2, False, 1, 1000, "Hold (ms)"),
        Field("release", 6, 2, False, 1, 1000, "Release (ms)"),
    ],
    SupportedFeature.LOGIVOICE_COMPRESSOR: [
        Field("threshold", 0, 1, True, -40, 0, "Threshold (dB)"),
        Field("attack", 1, 2, False, 1, 200, "Attack (ms)"),
        Field("release", 3, 2, False, 50, 1000, "Release (ms)"),
        Field("post_gain", 5, 1, True, -12, 12, "Post Gain (dB)"),
        Field("pre_gain", 6, 1, True, -12, 12, "Pre Gain (dB)"),
        # Ratio reports min=1 max=20 from GetInfo; whether the device interprets
        # it as a literal X:1 ratio or a curve-table index is unconfirmed.
        Field("ratio", 7, 1, False, 1, 20, "Ratio"),
    ],
    SupportedFeature.LOGIVOICE_DE_ESSER: [
        Field("threshold", 0, 1, True, -50, 0, "Threshold (dB)"),
        Field("frequency", 1, 2, False, 1000, 10000, "Frequency (Hz)"),
        # width_q is a Q-format quantization with a device-loaded scale we
        # don't know; range/default come straight from GetInfo.
        Field("width_q", 3, 1, False, 2, 120, "Width/Q", opaque=True),
        Field("attack", 4, 2, False, 1, 200, "Attack (ms)"),
        Field("release", 6, 2, False, 20, 1000, "Release (ms)"),
        Field("attenuation", 8, 1, True, -40, 0, "Attenuation (dB)"),
    ],
    SupportedFeature.LOGIVOICE_DE_POPPER: [
        Field("threshold", 0, 1, True, -50, 0, "Threshold (dB)"),
        Field("frequency", 1, 2, False, 60, 500, "Frequency (Hz)"),
        Field("width_q", 3, 1, False, 2, 120, "Width/Q", opaque=True),
        Field("attack", 4, 2, False, 1, 200, "Attack (ms)"),
        Field("release", 6, 2, False, 20, 1000, "Release (ms)"),
        Field("attenuation", 8, 1, True, -40, 0, "Attenuation (dB)"),
    ],
    SupportedFeature.LOGIVOICE_LIMITER: [
        Field("boost", 0, 1, True, -128, 127, "Boost (dB)"),
        Field("attack", 1, 2, False, 1, 65535, "Attack (ms)"),
        Field("release", 3, 2, False, 1, 65535, "Release (ms)"),
    ],
    SupportedFeature.LOGIVOICE_HIGH_PASS_FILTER: [
        Field("frequency", 0, 2, False, 60, 300, "Cutoff (Hz)"),
    ],
}


def expected_payload_length(feature: SupportedFeature) -> int:
    fields = PARAMETERS_FIELDS.get(feature)
    if not fields:
        return 0
    return max(f.offset + f.byte_count for f in fields)


def get_state(device, feature: SupportedFeature):
    """Read the module's on/off state via fn 1. Returns int 0-255 or None."""
    result = device.feature_request(feature, FN_GET_STATE)
    if result is None or len(result) < 1:
        return None
    return result[0]


def get_parameters(device, feature: SupportedFeature):
    """Read the module's Parameters struct via fn 3. Returns raw bytes or None."""
    result = device.feature_request(feature, FN_GET_PARAMETERS)
    if result is None:
        return None
    return bytes(result)


def get_info(device, feature: SupportedFeature):
    """Read module capability info via fn 4. Returns raw bytes or None.

    Decoded per-field bounds are available via parse_info().
    """
    result = device.feature_request(feature, FN_GET_INFO)
    if result is None:
        return None
    return bytes(result)


def _decode_field(chunk: bytes, byte_count: int, signed: bool) -> int:
    """Decode `byte_count` bytes from `chunk` as an integer per the field's wire
    encoding. Multi-byte values are big-endian (matches Parameters)."""
    if byte_count == 1:
        return struct.unpack("b" if signed else "B", chunk[:1])[0]
    if byte_count == 2:
        return struct.unpack(">h" if signed else ">H", chunk[:2])[0]
    return int.from_bytes(chunk[:byte_count], "big", signed=signed)


def parse_info(feature: SupportedFeature, payload: bytes) -> dict:
    """Decode a GetInfo response into per-field {min, max} bounds.

    Layout: for each field in PARAMETERS_FIELDS in order, the payload carries
    [min_value, max_value] back-to-back using the field's wire encoding (so
    a u16 field contributes 4 bytes — 2 for min, 2 for max). Trailing bytes
    in the response are pad/zero.

    Returns a dict mapping field name to {"min": int, "max": int}. Fields
    that don't fit in the payload are omitted.
    """
    fields = PARAMETERS_FIELDS.get(feature)
    if not fields or not payload:
        return {}
    out = {}
    offset = 0
    for f in fields:
        end = offset + 2 * f.byte_count
        if end > len(payload):
            break
        min_val = _decode_field(payload[offset : offset + f.byte_count], f.byte_count, f.signed)
        max_val = _decode_field(payload[offset + f.byte_count : end], f.byte_count, f.signed)
        out[f.name] = {"min": min_val, "max": max_val}
        offset = end
    return out


def parse_parameters(feature: SupportedFeature, payload: bytes) -> dict:
    """Decode Parameters bytes into a dict per the per-module field table.

    Returns {} on unknown feature or short payload — caller still has the raw
    hex via get_parameters() for corpus logging.
    """
    fields = PARAMETERS_FIELDS.get(feature)
    if not fields or payload is None:
        return {}
    parsed = {}
    for f in fields:
        end = f.offset + f.byte_count
        if end > len(payload):
            continue
        chunk = payload[f.offset : end]
        if f.byte_count == 1:
            val = struct.unpack("b" if f.signed else "B", chunk)[0]
        elif f.byte_count == 2:
            val = struct.unpack(">h" if f.signed else ">H", chunk)[0]
        else:
            val = int.from_bytes(chunk, "big", signed=f.signed)
        parsed[f.name] = val
    return parsed


def probe_module(device, feature: SupportedFeature) -> None:
    """One-shot corpus probe. Logs state + raw parameters + parsed + raw info
    + decoded info bounds."""
    name = MODULE_NAMES.get(feature, f"0x{int(feature):04X}")
    state = get_state(device, feature)
    params = get_parameters(device, feature)
    info = get_info(device, feature)
    logger.info(
        "LogiVoice %s [0x%04X]: state=%s parameters=%s info=%s",
        name,
        int(feature),
        state,
        params.hex() if params else None,
        info.hex() if info else None,
    )
    parsed = parse_parameters(feature, params) if params else {}
    if parsed:
        logger.info("LogiVoice %s parsed: %s", name, parsed)
    bounds = parse_info(feature, info) if info else {}
    if bounds:
        logger.info("LogiVoice %s info bounds: %s", name, bounds)


def probe_all_modules(device, features: Iterable[SupportedFeature]) -> None:
    """Probe every LogiVoice module present on the device.

    Call once at device-bring-up so the -dd corpus has a full snapshot.
    Caller passes whichever subset of LogiVoice features are actually
    discovered (usually derived from device.features).
    """
    for feature in features:
        if feature not in PARAMETERS_FIELDS and feature != SupportedFeature.LOGIVOICE:
            continue
        try:
            probe_module(device, feature)
        except Exception as e:
            logger.info("LogiVoice probe_module(%s) raised %s", feature, e)
