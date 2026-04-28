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

"""AdvancedParaEQ (0x020D) helpers.

The device handles biquad coefficient computation — we transmit only
per-band filter-type + frequency + gain; the DSP does the rest.

V0/V1 wire format: 3-byte band stride [freq_hi, freq_lo, gain_i8],
gain is whole dB; getEQInfos returns 5 bytes [bandCount, dbRange,
caps, dbMin, dbMax].

V2 wire format: 3-byte header [direction_echo, slot_echo,
band_count_max], then N × 5-byte band stride [filter_type, gain_hi,
gain_lo, freq_hi, freq_lo], then 0..2 trailer bytes (opaque, ignored).
band_count_max is the device's max-bands capacity, NOT how many bands
are populated — the parser consumes 5-byte chunks until <5 bytes
remain. Frequency u16 BE in Hz, with freq=0 marking end-of-bands.
Gain is **offset-binary**: raw 0..(steps-1) maps linearly to
gain_min..gain_max (so on G522 with steps=241 / gain=[-6..6], raw=120
= 0 dB). getEQInfos returns 13 bytes with gain bounds + step count,
format enum, XY-support flag, and onboard preset counts.
"""

from __future__ import annotations

import logging
import struct

from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

DIRECTION_PLAYBACK = 0
DIRECTION_CAPTURE = 1

# V2 filter-type taxonomy (byte [+0] of each band). 0x16 is observed on
# G522 for every band of its factory custom slot at ISO third-octave
# centers, treated as peaking. Other filter kinds (LP, shelf, notch …)
# need a live probe per device firmware to enumerate.
FILTER_TYPE_HP = 0x00
FILTER_TYPE_PEAKING_G522 = 0x16
FILTER_TYPE_PEAKING = 0x78
FILTER_TYPE_NAMES = {
    FILTER_TYPE_HP: "HP",
    FILTER_TYPE_PEAKING_G522: "peaking",
    FILTER_TYPE_PEAKING: "peaking",
}


def _get_version(device) -> int:
    return device.features.get_feature_version(SupportedFeature.HEADSET_ADVANCED_PARA_EQ) or 0


def get_advanced_eq_info(device):
    """Query getEQInfos (function 0). Returns a dict or None.

    Common fields:
      version       int      feature version (0, 1, 2)
      gain_min_db   int      signed whole-dB min
      gain_max_db   int      signed whole-dB max
      step_db       float    dB per raw LSB (1.0 on V0/V1)

    V0/V1 only:
      band_count    int      number of bands (from wire byte 0)
      db_range      int      raw byte 1
      capabilities  int      raw byte 2

    V2 only:
      gain_steps    int      discrete gain positions
      format        int      0=CLASSIC, 1=STYLES
      supports_xy   bool
      onboard_ro_preset_count     int  factory preset slots
      onboard_custom_preset_count int  user-writable preset slots
    """
    version = _get_version(device)
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x00)
    if result is None:
        logger.info("AdvancedParaEQ getEQInfos V%d: feature_request returned None", version)
        return None

    if version >= 2:
        if len(result) < 13:
            logger.info("AdvancedParaEQ getEQInfos V2: short response len=%d %s", len(result), result.hex())
            return None
        gain_min = struct.unpack("b", bytes([result[2]]))[0]
        gain_max = struct.unpack("b", bytes([result[3]]))[0]
        gain_steps = struct.unpack(">H", result[4:6])[0]
        fmt = result[6]
        supports_xy = bool(result[7])
        ro_presets = result[9]
        custom_presets = result[10]
        step_db = (gain_max - gain_min) / max(1, gain_steps - 1)
        info = {
            "version": 2,
            "gain_min_db": gain_min,
            "gain_max_db": gain_max,
            "gain_steps": gain_steps,
            "step_db": step_db,
            "format": fmt,
            "supports_xy": supports_xy,
            "onboard_ro_preset_count": ro_presets,
            "onboard_custom_preset_count": custom_presets,
        }
        logger.info(
            "AdvancedParaEQ getEQInfos V2: gain=[%d,%d] steps=%d step_db=%.4f format=%d xy=%s "
            "presets_ro=%d presets_custom=%d",
            gain_min,
            gain_max,
            gain_steps,
            step_db,
            fmt,
            supports_xy,
            ro_presets,
            custom_presets,
        )
        return info

    # V0 / V1
    if len(result) < 5:
        logger.info("AdvancedParaEQ getEQInfos V%d: short response len=%d %s", version, len(result), result.hex())
        return None
    band_count = result[0]
    db_range = result[1]
    caps = result[2]
    gain_min = struct.unpack("b", bytes([result[3]]))[0]
    gain_max = struct.unpack("b", bytes([result[4]]))[0]
    info = {
        "version": version,
        "band_count": band_count,
        "db_range": db_range,
        "capabilities": caps,
        "gain_min_db": gain_min,
        "gain_max_db": gain_max,
        "step_db": 1.0,
    }
    logger.info(
        "AdvancedParaEQ getEQInfos V%d: bands=%d dbRange=%d caps=0x%02X gain=[%d,%d]",
        version,
        band_count,
        db_range,
        caps,
        gain_min,
        gain_max,
    )
    return info


def get_advanced_eq_active_slot(device, direction=DIRECTION_PLAYBACK):
    """Query getActiveEQ (function 3). Returns the active slot index, or None."""
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x30, direction)
    if result is None:
        logger.info("AdvancedParaEQ getActiveEQ(dir=%d): feature_request returned None", direction)
        return None
    if len(result) < 1:
        logger.info("AdvancedParaEQ getActiveEQ(dir=%d): empty response", direction)
        return None
    logger.info("AdvancedParaEQ getActiveEQ(dir=%d): slot=%d", direction, result[0])
    return result[0]


def parse_v2_bands(result: bytes, info: dict | None):
    """Parse a V2 getCustomEQ / getEQDefaults response.

    Wire layout (see module docstring):
      [direction_echo, slot_echo, band_count_max]    (3-byte header)
      N × [filter_type, gain_hi, gain_lo, freq_hi, freq_lo]   (5 bytes)
      [trailer …]                                     (0..2 bytes, ignored)

    Gain is offset-binary against `info`'s gain bounds:
      gain_db = gain_min + (gain_max - gain_min) * raw / (steps - 1)

    `info` is the dict returned by `get_advanced_eq_info`. If absent we
    fall back to step_db=1.0 (and log via the caller, not here) which is
    wrong but won't crash.

    Returns list of (filter_type_byte, freq_hz, gain_db) tuples, or None
    if the payload is too short to contain a header. Empty payload with
    valid header returns []. Bands with freq=0 are treated as the
    end-of-bands sentinel (matches V0/V1 behavior at lines below).
    """
    if result is None or len(result) < 3:
        return None
    payload = result[3:]  # skip [dir_echo, slot_echo, band_count_max]
    band_size = 5
    if info:
        gain_min = info.get("gain_min_db", -6)
        gain_max = info.get("gain_max_db", 6)
        steps = info.get("gain_steps", 241)
    else:
        gain_min, gain_max, steps = 0, 0, 1  # produces gain_db=0 for any raw
    bands = []
    for i in range(len(payload) // band_size):
        e = payload[i * band_size : (i + 1) * band_size]
        filter_type = e[0]
        gain_raw = (e[1] << 8) | e[2]
        freq_hz = (e[3] << 8) | e[4]
        if freq_hz == 0:
            break  # disabled band — end-of-bands sentinel
        if steps > 1:
            gain_db = gain_min + (gain_max - gain_min) * gain_raw / (steps - 1)
        else:
            gain_db = 0.0
        bands.append((filter_type, freq_hz, float(gain_db)))
    return bands


def _band_label(filter_type_byte: int, freq_hz: int) -> str:
    kind = FILTER_TYPE_NAMES.get(filter_type_byte, f"type-0x{filter_type_byte:02X}")
    if filter_type_byte == FILTER_TYPE_HP:
        return f"HP {freq_hz} Hz"
    return f"{freq_hz} Hz" if kind == "peaking" else f"{kind} {freq_hz} Hz"


def get_advanced_eq_defaults(device, direction=DIRECTION_PLAYBACK, slot=0):
    """Query getEQDefaults (function 5). Same per-band layout as getCustomEQ.

    Returns list of (filter_type_byte, freq_hz, gain_db) tuples, or None.
    V0/V1 callers receive (FILTER_TYPE_PEAKING, freq_hz, gain_db) for
    compatibility with the V2 tuple shape.
    """
    version = _get_version(device)
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x50, direction, slot)
    if result is None:
        logger.info(
            "AdvancedParaEQ getEQDefaults V%d (dir=%d slot=%d): feature_request returned None",
            version,
            direction,
            slot,
        )
        return None
    if version >= 2:
        info = getattr(device, "_advanced_eq_info", None)
        bands = parse_v2_bands(result, info)
        if bands is None:
            logger.info(
                "AdvancedParaEQ getEQDefaults V2 (dir=%d slot=%d): payload too short raw=%s",
                direction,
                slot,
                result.hex(),
            )
            return None
        # Log raw=... too — getEQDefaults appears to use a different header
        # framing than getCustomEQ on G522 (decoded values come out shifted
        # by a byte). Capture the raw bytes so we can pin down the actual
        # layout difference and adjust the parser accordingly.
        logger.info(
            "AdvancedParaEQ getEQDefaults V2 (dir=%d slot=%d): %d band(s) raw=%s %s",
            direction,
            slot,
            len(bands),
            result.hex(),
            [_band_label(t, f) + f" {round(g, 2)}dB" for t, f, g in bands],
        )
        return bands
    # V0/V1 legacy 3-byte stride.
    bands = []
    offset = 0
    while offset + 3 <= len(result):
        freq = struct.unpack(">H", result[offset : offset + 2])[0]
        if freq == 0:
            break
        gain_db = struct.unpack("b", bytes([result[offset + 2]]))[0]
        bands.append((FILTER_TYPE_PEAKING, freq, float(gain_db)))
        offset += 3
    logger.info(
        "AdvancedParaEQ getEQDefaults V%d (dir=%d slot=%d): %d band(s)",
        version,
        direction,
        slot,
        len(bands),
    )
    return bands


def get_advanced_eq_friendly_name(device, direction=DIRECTION_PLAYBACK, slot=0):
    """Query getEQFriendlyName (function 6). Returns the UTF-8 preset name or None."""
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x60, direction, slot)
    if result is None or len(result) < 1:
        return None
    name_len = result[0]
    if 1 + name_len > len(result):
        name_len = len(result) - 1
    try:
        name = bytes(result[1 : 1 + name_len]).decode("utf-8", errors="replace")
    except Exception:
        name = result[1 : 1 + name_len].hex()
    return name


def probe_advanced_eq_slots(device, direction=DIRECTION_PLAYBACK, info=None):
    """Probe every advertised EQ slot via getCustomEQ and cache which respond.

    Some firmware (G522) advertises N slots via getEQInfos but only honors a
    subset for getCustomEQ / setActiveEQ — the rest return 0x0B NOT_SUPPORTED.
    This iterates 0..total-1 and records which slots actually have data.

    Result is cached on `device._advanced_eq_working_slots` as a list of
    `(slot_index, name, bands)` tuples. The HeadsetActiveEQPreset selector
    builds its choices from this list; the HeadsetAdvancedEQ panel uses it
    to skip dead slots in its diagnostic output.

    Logs each working slot's bands at INFO and a summary line indicating
    how many of the advertised slots are actually accessible.
    """
    cached = getattr(device, "_advanced_eq_working_slots", None)
    if cached is not None:
        return cached
    if info is None:
        info = getattr(device, "_advanced_eq_info", None) or get_advanced_eq_info(device)
    if not info:
        return []
    ro_count = info.get("onboard_ro_preset_count", 0) or 0
    custom_count = info.get("onboard_custom_preset_count", 0) or 0
    total = ro_count + custom_count
    if total == 0:
        return []
    working = []
    for slot in range(total):
        bands = get_advanced_eq_params(device, direction=direction, slot=slot)
        if bands is None:
            continue
        name = get_advanced_eq_friendly_name(device, direction=direction, slot=slot)
        kind = "factory" if slot < ro_count else "custom"
        logger.info(
            "AdvancedParaEQ %s preset slot=%d (dir=%d) name=%r: %s",
            kind,
            slot,
            direction,
            name,
            [f"{_band_label(t, f)} {round(g, 2)}dB" for t, f, g in bands],
        )
        working.append((slot, name, bands))
    device._advanced_eq_working_slots = working
    logger.info(
        "AdvancedParaEQ working slots on dir=%d: %d of %d advertised %s",
        direction,
        len(working),
        total,
        [w[0] for w in working],
    )
    return working


# Backward-compat alias kept until external callers are migrated.
probe_all_presets = probe_advanced_eq_slots


def get_advanced_eq_params(device, direction=DIRECTION_PLAYBACK, slot=0):
    """Query getCustomEQ (function 1). Returns list of (filter_type, freq_hz, gain_db) or None.

    V0/V1: filter_type is always FILTER_TYPE_PEAKING (synthesized), freq is
    raw Hz from wire, gain is whole dB.
    V2: filter_type comes from the wire (0x00=HP, 0x78=peaking), freq is raw
    Hz, gain is int16 × step_db.

    step_db for V2 is cached on the device by get_advanced_eq_info.
    """
    version = _get_version(device)
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x10, direction, slot)
    if result is None:
        logger.info(
            "AdvancedParaEQ getCustomEQ V%d (dir=%d slot=%d): feature_request returned None",
            version,
            direction,
            slot,
        )
        return None

    if version >= 2:
        info = getattr(device, "_advanced_eq_info", None)
        if not info:
            logger.warning("AdvancedParaEQ getCustomEQ V2: no cached getEQInfos — gain values will be wrong")
        bands = parse_v2_bands(result, info)
        if bands is None:
            logger.info(
                "AdvancedParaEQ getCustomEQ V2 (dir=%d slot=%d): payload too short raw=%s",
                direction,
                slot,
                result.hex(),
            )
            return None
        step_db = info["step_db"] if info and "step_db" in info else 1.0
        # Log raw=... too so we can compare wire shapes across firmware
        # variants and across get-fns (getCustomEQ vs getEQDefaults).
        logger.info(
            "AdvancedParaEQ getCustomEQ V2 (dir=%d slot=%d): %d band(s) step_db=%.4f raw=%s %s",
            direction,
            slot,
            len(bands),
            step_db,
            result.hex(),
            [f"{_band_label(t, f)} {round(g, 2)}dB" for t, f, g in bands],
        )
        return bands

    # V0 / V1
    bands = []
    offset = 0
    while offset + 3 <= len(result):
        freq = struct.unpack(">H", result[offset : offset + 2])[0]
        if freq == 0:
            break
        gain_db = struct.unpack("b", bytes([result[offset + 2]]))[0]
        bands.append((FILTER_TYPE_PEAKING, freq, float(gain_db)))
        offset += 3
    logger.info(
        "AdvancedParaEQ getCustomEQ V%d (dir=%d slot=%d): parsed %d band(s) %s",
        version,
        direction,
        slot,
        len(bands),
        bands,
    )
    return bands
