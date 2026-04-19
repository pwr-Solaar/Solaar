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

Unlike OnboardEQ (0x0636) which requires host-computed biquad coefficients,
AdvancedParaEQ is handled entirely by the device — we send frequency + gain
per band and the device applies them. Band entries are 3 bytes each:
[freq_hi, freq_lo, value] where value is the signed int8 gain in dB.
"""

from __future__ import annotations

import logging
import struct

from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

# Direction parameter for getCustomEQ / getActiveEQ etc.
DIRECTION_PLAYBACK = 0
DIRECTION_CAPTURE = 1


def get_advanced_eq_info(device):
    """Query HEADSET_ADVANCED_PARA_EQ getEQInfos (function 0).

    Returns (band_count, db_range, capabilities, db_min, db_max) or None.
    """
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x00)
    if result is None:
        logger.info("AdvancedParaEQ getEQInfos: feature_request returned None")
        return None
    if len(result) < 5:
        logger.info("AdvancedParaEQ getEQInfos: short response (len=%d) %s", len(result), result.hex())
        return None
    band_count = result[0]
    db_range = result[1]
    capabilities = result[2]
    # dbMin / dbMax are signed int8 in the doc.
    db_min = struct.unpack("b", bytes([result[3]]))[0]
    db_max = struct.unpack("b", bytes([result[4]]))[0]
    logger.info(
        "AdvancedParaEQ getEQInfos: bands=%d dbRange=%d caps=0x%02X dbMin=%d dbMax=%d raw=%s",
        band_count,
        db_range,
        capabilities,
        db_min,
        db_max,
        result.hex(),
    )
    return (band_count, db_range, capabilities, db_min, db_max)


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


def get_advanced_eq_params(device, direction=DIRECTION_PLAYBACK, slot=0):
    """Query getCustomEQ (function 1) for the given direction and slot.

    Returns a list of (freq_hz, gain_db) tuples, or None.
    """
    result = device.feature_request(SupportedFeature.HEADSET_ADVANCED_PARA_EQ, 0x10, direction, slot)
    if result is None:
        logger.info("AdvancedParaEQ getCustomEQ(dir=%d slot=%d): feature_request returned None", direction, slot)
        return None
    bands = []
    offset = 0
    # Response is a tight-packed series of 3-byte band entries:
    # [freq_hi, freq_lo, value].
    while offset + 3 <= len(result):
        freq = struct.unpack(">H", result[offset : offset + 2])[0]
        if freq == 0:
            # Trailing padding — stop parsing.
            break
        gain_db = struct.unpack("b", bytes([result[offset + 2]]))[0]
        bands.append((freq, gain_db))
        offset += 3
    logger.info(
        "AdvancedParaEQ getCustomEQ(dir=%d slot=%d): parsed %d band(s) %s raw=%s",
        direction,
        slot,
        len(bands),
        bands,
        result.hex(),
    )
    return bands
