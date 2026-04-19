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
  fn 1 GetState       -> u8 state
  fn 2 SetParameters
  fn 3 GetParameters  -> module-specific payload
  fn 4 GetInfo        -> device capability / bounds (opaque here)

All multi-byte integers on the wire are big-endian. Parameters layouts
are module-specific; PARAMETERS_FIELDS below encodes the per-field
offset/width/signedness/range metadata we display read-only. Some
fields are intentionally flagged `opaque=True` because their scale
factor or bit layout isn't pinned down yet — we still expose the raw
value so users/screenshots can build a corpus.

Writes are NOT implemented yet. This is a read-only pass for data
collection and visibility; write support can be added per-field once
each encoding is verified live.
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


# Per-module field layout for GetParameters response. Table-driven so adding
# a new module or adjusting a field is a one-line change. Fields flagged
# opaque=True have unknown scale / bit layout; we expose the raw bytes so a
# future pass can pin them down from live data.
PARAMETERS_FIELDS: dict[SupportedFeature, list[Field]] = {
    SupportedFeature.LOGIVOICE_NOISE_REDUCTION: [
        Field("state", 0, 1, False, 0, 255, "State"),
        Field("sensitivity", 2, 2, False, 0, 65535, "Sensitivity"),
        # NR serializer emits 5 bytes; byte 4 is a single-byte release surrogate.
        Field("release_byte", 4, 1, False, 0, 255, "Release (raw)", opaque=True),
    ],
    SupportedFeature.LOGIVOICE_NOISE_GATE: [
        Field("state", 0, 1, False, 0, 255, "State"),
        Field("threshold", 1, 1, True, -128, 127, "Threshold (raw)", opaque=True),
        Field("attenuation", 2, 2, False, 0, 65535, "Attenuation (raw)", opaque=True),
        Field("attack", 4, 2, False, 0, 65535, "Attack (raw)", opaque=True),
        Field("hold", 6, 2, False, 0, 65535, "Hold (raw)", opaque=True),
    ],
    SupportedFeature.LOGIVOICE_COMPRESSOR: [
        Field("state", 0, 1, False, 0, 255, "State"),
        Field("threshold", 2, 2, True, -32768, 32767, "Threshold (raw)", opaque=True),
        Field("attack", 4, 2, False, 0, 65535, "Attack (raw)", opaque=True),
        Field("post_gain", 6, 1, True, -128, 127, "Post Gain (raw)", opaque=True),
        # Byte 7 packs pre_gain + ratio; bit layout unknown. Display raw byte.
        Field("byte7_packed", 7, 1, False, 0, 255, "Byte 7 (pre_gain/ratio packed)", opaque=True),
    ],
    SupportedFeature.LOGIVOICE_DE_ESSER: [
        Field("state", 0, 1, False, 0, 255, "State"),
        Field("threshold", 1, 2, True, -32768, 32767, "Threshold (raw)", opaque=True),
        # Frequency compressed from float to u8 with device-specific scale.
        Field("frequency_raw", 3, 1, False, 0, 255, "Frequency (raw u8)", opaque=True),
        Field("width_q_raw", 4, 2, False, 0, 65535, "Width/Q (raw u16)", opaque=True),
        Field("attack", 6, 2, False, 0, 65535, "Attack (raw)", opaque=True),
        Field("release", 8, 1, True, -128, 127, "Release (raw)", opaque=True),
    ],
    SupportedFeature.LOGIVOICE_DE_POPPER: [
        Field("state", 0, 1, False, 0, 255, "State"),
        Field("threshold", 1, 2, True, -32768, 32767, "Threshold (raw)", opaque=True),
        Field("frequency_raw", 3, 1, False, 0, 255, "Frequency (raw u8)", opaque=True),
        Field("width_q_raw", 4, 2, False, 0, 65535, "Width/Q (raw u16)", opaque=True),
        Field("attack", 6, 2, False, 0, 65535, "Attack (raw)", opaque=True),
        Field("release", 8, 1, True, -128, 127, "Release (raw)", opaque=True),
    ],
    SupportedFeature.LOGIVOICE_LIMITER: [
        Field("state", 0, 1, False, 0, 255, "State"),
        Field("boost", 2, 2, True, -32768, 32767, "Boost (raw)", opaque=True),
        Field("bytes4_5_packed", 4, 2, False, 0, 65535, "Bytes 4-5 (attack/release packed)", opaque=True),
    ],
    SupportedFeature.LOGIVOICE_HIGH_PASS_FILTER: [
        # HPF has no state byte in Parameters — state lives on fn 0/1 only.
        Field("frequency", 0, 2, False, 0, 65535, "Cutoff (Hz)"),
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

    Per-module Info layout isn't decoded yet — we log the raw hex for corpus.
    """
    result = device.feature_request(feature, FN_GET_INFO)
    if result is None:
        return None
    return bytes(result)


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
    """One-shot corpus probe. Logs state + raw parameters + parsed + raw info."""
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
