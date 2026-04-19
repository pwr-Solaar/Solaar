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

V2 wire format: 5-byte band stride [filter_type, freq_hi, freq_lo,
gain_hi, gain_lo] with NO header. Filter types are 0x00=HP (cutoff),
0x78=peaking. Frequency is raw BE u16 in Hz. Gain is signed BE int16
× step_db (step_db from getEQInfos). No Q on the wire — firmware-fixed
per filter type. getEQInfos returns 13 bytes with gain bounds + step
count, format enum, XY-support flag, and onboard preset counts.

Authoritative source: HEADSET_ADVANCED_PARA_EQ_WIRE_PROTOCOL.md (the
V2 layout was confirmed via live G522 probe — the default EQ is one
HP filter at 20 Hz plus nine peaking filters at ISO centers 50, 125,
250, 500, 1000, 2500, 5000, 10000, 20000 Hz with all gains at zero).
"""

from __future__ import annotations

import logging
import struct

from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

DIRECTION_PLAYBACK = 0
DIRECTION_CAPTURE = 1

# V2 filter-type taxonomy (byte [+0] of each band).
FILTER_TYPE_HP = 0x00
FILTER_TYPE_PEAKING = 0x78
FILTER_TYPE_NAMES = {
    FILTER_TYPE_HP: "HP",
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
            "presets_ro=%d presets_custom=%d raw=%s",
            gain_min,
            gain_max,
            gain_steps,
            step_db,
            fmt,
            supports_xy,
            ro_presets,
            custom_presets,
            result.hex(),
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
        "AdvancedParaEQ getEQInfos V%d: bands=%d dbRange=%d caps=0x%02X gain=[%d,%d] raw=%s",
        version,
        band_count,
        db_range,
        caps,
        gain_min,
        gain_max,
        result.hex(),
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
    logger.info("AdvancedParaEQ getActiveEQ(dir=%d): slot=%d raw=%s", direction, result[0], result.hex())
    return result[0]


def parse_v2_bands(result: bytes, step_db: float):
    """Parse a V2 getCustomEQ/getEQDefaults response.

    Returns list of (filter_type_byte, freq_hz, gain_db) tuples, or None.
    Response is N × 5 bytes with no header. Each band is
    [filter_type, freq_hi, freq_lo, gain_hi, gain_lo].
    """
    if result is None or len(result) == 0:
        return None
    if len(result) % 5 != 0:
        return None
    bands = []
    for i in range(len(result) // 5):
        e = result[i * 5 : (i + 1) * 5]
        filter_type = e[0]
        freq_hz = (e[1] << 8) | e[2]
        gain_int16 = struct.unpack(">h", bytes(e[3:5]))[0]
        gain_db = gain_int16 * step_db
        bands.append((filter_type, freq_hz, gain_db))
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
        step_db = info["step_db"] if info and "step_db" in info else 1.0
        bands = parse_v2_bands(result, step_db)
        if bands is None:
            logger.info(
                "AdvancedParaEQ getEQDefaults V2 (dir=%d slot=%d): payload not multiple of 5 raw=%s",
                direction,
                slot,
                result.hex(),
            )
            return None
        logger.info(
            "AdvancedParaEQ getEQDefaults V2 (dir=%d slot=%d): %d band(s) %s raw=%s",
            direction,
            slot,
            len(bands),
            [_band_label(t, f) + f" {round(g, 2)}dB" for t, f, g in bands],
            result.hex(),
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
        "AdvancedParaEQ getEQDefaults V%d (dir=%d slot=%d): %d band(s) raw=%s",
        version,
        direction,
        slot,
        len(bands),
        result.hex(),
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


def probe_all_presets(device, direction=DIRECTION_PLAYBACK):
    """Read every factory + custom preset slot and log name + band data at INFO.

    Diagnostic probe — intended to run once at HeadsetAdvancedEQ.build() time.
    The logged corpus is useful for spotting filter-type or frequency pattern
    differences between named presets.
    """
    info = getattr(device, "_advanced_eq_info", None)
    if not info:
        return
    ro_count = info.get("onboard_ro_preset_count", 0)
    custom_count = info.get("onboard_custom_preset_count", 0)
    for slot in range(ro_count):
        name = get_advanced_eq_friendly_name(device, direction=direction, slot=slot)
        bands = get_advanced_eq_defaults(device, direction=direction, slot=slot)
        if bands is None:
            continue
        logger.info(
            "AdvancedParaEQ factory preset %d/%d (dir=%d) name=%r: %s",
            slot,
            ro_count,
            direction,
            name,
            [f"{_band_label(t, f)} {round(g, 2)}dB" for t, f, g in bands],
        )
    for slot in range(custom_count):
        name = get_advanced_eq_friendly_name(device, direction=direction, slot=slot)
        bands = get_advanced_eq_params(device, direction=direction, slot=slot)
        if bands is None:
            continue
        logger.info(
            "AdvancedParaEQ custom preset %d/%d (dir=%d) name=%r: %s",
            slot,
            custom_count,
            direction,
            name,
            [f"{_band_label(t, f)} {round(g, 2)}dB" for t, f, g in bands],
        )


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
        step_db = info["step_db"] if info and "step_db" in info else 1.0
        if step_db == 1.0 and not info:
            logger.warning(
                "AdvancedParaEQ getCustomEQ V2: no cached getEQInfos — gain values will use step_db=1.0 and be wrong"
            )
        bands = parse_v2_bands(result, step_db)
        if bands is None:
            logger.info(
                "AdvancedParaEQ getCustomEQ V2 (dir=%d slot=%d): payload not multiple of 5 raw=%s",
                direction,
                slot,
                result.hex(),
            )
            return None
        logger.info(
            "AdvancedParaEQ getCustomEQ V2 (dir=%d slot=%d): %d band(s) step_db=%.4f %s raw=%s",
            direction,
            slot,
            len(bands),
            step_db,
            [f"{_band_label(t, f)} {round(g, 2)}dB" for t, f, g in bands],
            result.hex(),
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
        "AdvancedParaEQ getCustomEQ V%d (dir=%d slot=%d): parsed %d band(s) %s raw=%s",
        version,
        direction,
        slot,
        len(bands),
        bands,
        result.hex(),
    )
    return bands
