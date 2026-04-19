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
per-band frequency, gain, and (on V2) Q-factor; the DSP does the rest.

V0/V1 wire format: 3-byte band stride [freq_hi, freq_lo, gain_i8];
getEQInfos returns 5 bytes [bandCount, dbRange, caps, dbMin, dbMax].

V2 wire format: 5-byte band stride [freq_hi, freq_lo, gain_i8, q_hi,
q_lo]; getEQInfos returns 13 bytes with gain bounds + step count,
format enum, XY-support flag, and onboard preset counts. Frequency and
Q are opaque u16 round-trip values — the u16→Hz / u16→Q mappings are
unconfirmed and need a LGHUB pcap to pin down. See
HEADSET_ADVANCED_PARA_EQ_WIRE_PROTOCOL.md.
"""

from __future__ import annotations

import logging
import struct

from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

DIRECTION_PLAYBACK = 0
DIRECTION_CAPTURE = 1


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


def _parse_v2_band_payload(result: bytes):
    """Locate and parse the 5-byte band stride inside a V2 getCustomEQ response.

    Header length before the first band is not yet nailed down (see
    HEADSET_ADVANCED_PARA_EQ_WIRE_PROTOCOL.md section on band header).
    Try candidate lengths {5, 2, 0} and pick the first where the tail is
    a clean multiple of 5.

    Returns (bands_bytes, header_len) or (None, None).
    """
    for hl in (5, 2, 0):
        tail = result[hl:]
        if tail and len(tail) % 5 == 0 and 1 <= len(tail) // 5 <= 64:
            return tail, hl
    return None, None


def parse_v2_bands(result: bytes, step_db: float):
    """Parse a V2 getCustomEQ response. Returns list of (freq_u16, gain_db, q_u16).

    Trailing all-zero bands (terminators) are stripped.
    """
    payload, header_len = _parse_v2_band_payload(result)
    if payload is None:
        return None, None
    bands = []
    for i in range(len(payload) // 5):
        e = payload[i * 5 : (i + 1) * 5]
        freq_u16 = (e[0] << 8) | e[1]
        gain_raw = struct.unpack("b", bytes([e[2]]))[0]
        q_u16 = (e[3] << 8) | e[4]
        bands.append((freq_u16, gain_raw * step_db, q_u16))
    while bands and bands[-1] == (0, 0.0, 0):
        bands.pop()
    return bands, header_len


def get_advanced_eq_params(device, direction=DIRECTION_PLAYBACK, slot=0):
    """Query getCustomEQ (function 1). Returns list of (freq, gain_db, q) or None.

    V0/V1: freq is raw Hz (u16), q is always 0 (V0/V1 has no Q).
    V2: freq is opaque u16 bin index (Hz mapping unconfirmed), q is opaque u16
    round-trip value (scale unconfirmed). See wire-protocol doc.

    step_db for V2 is derived from getEQInfos; the caller should pass it via
    `device._advanced_eq_info` (set by get_advanced_eq_info) or we fall back
    to 1.0 and log a warning.
    """
    version = _get_version(device)
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x10, direction, slot)
    if result is None:
        logger.info("AdvancedParaEQ getCustomEQ V%d (dir=%d slot=%d): feature_request returned None", version, direction, slot)
        return None

    if version >= 2:
        info = getattr(device, "_advanced_eq_info", None)
        step_db = info["step_db"] if info and "step_db" in info else 1.0
        if step_db == 1.0 and not info:
            logger.warning(
                "AdvancedParaEQ getCustomEQ V2: no cached getEQInfos — gain values will use step_db=1.0 and be wrong"
            )
        bands, header_len = parse_v2_bands(result, step_db)
        if bands is None:
            logger.info("AdvancedParaEQ getCustomEQ V2: couldn't locate band payload raw=%s", result.hex())
            return None
        logger.info(
            "AdvancedParaEQ getCustomEQ V2 (dir=%d slot=%d): parsed %d band(s) header_len=%d step_db=%.4f raw=%s",
            direction,
            slot,
            len(bands),
            header_len,
            step_db,
            result.hex(),
        )
        return bands

    # V0 / V1: 3-byte stride, freq is raw Hz, gain is whole dB, no Q.
    bands = []
    offset = 0
    while offset + 3 <= len(result):
        freq = struct.unpack(">H", result[offset : offset + 2])[0]
        if freq == 0:
            break
        gain_db = struct.unpack("b", bytes([result[offset + 2]]))[0]
        bands.append((freq, float(gain_db), 0))
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
