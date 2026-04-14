## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

"""OnboardEQ (0x0636) biquad coefficient math and payload builders.

Pure computation — no device or transport dependencies beyond feature_request().
"""

from __future__ import annotations

import math
import struct

from .hidpp20_constants import SupportedFeature

# Mystery bytes observed in every LGHUB pcap EQ write between band params
# and coefficient header.  Purpose not fully understood — possibly a null-band
# terminator for DSPs that support >5 bands (advanced 10-band mode).
# First byte matches band_count; bytes 2-3 look like LE16 coeff blob size.
# Hardcoded from pcap for initial bring-up; revisit once device-tested.
_EQ_MYSTERY_BYTES = b"\x05\x5a\xe3\x00"


def _peaking_eq_biquad(freq_hz, gain_db, Q, sample_rate=48000.0):
    """Compute peaking EQ biquad coefficients (Audio EQ Cookbook).

    Returns (b0/a0, b1/a0, b2/a0, a1/a0, a2/a0) normalised coefficients.
    """
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq_hz / sample_rate
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2.0 * Q)
    a0 = 1.0 + alpha / A
    return (
        (1.0 + alpha * A) / a0,
        (-2.0 * cos_w0) / a0,
        (1.0 - alpha * A) / a0,
        (-2.0 * cos_w0) / a0,
        (1.0 - alpha / A) / a0,
    )


def _quantize_coeffs(b0, b1, b2, a1, a2):
    """Quantize biquad coefficients to mixed Q1.31 / Q2.30 fixed-point.

    b0, b2, a2 use Q1.31 (x 2^31); b1, a1 use Q2.30 (x 2^30).
    Values are truncated to 24-bit precision (low byte zeroed) matching
    the device DSP's internal format.
    Returns list of 10 uint16 values (5 coefficients x 2 LE words each,
    high word first).
    """
    scales = [2**31, 2**30, 2**31, 2**30, 2**31]  # b0, b1, b2, a1, a2
    words = []
    for val, scale in zip([b0, b1, b2, a1, a2], scales):
        q = int(round(val * scale))
        q = max(-(1 << 31), min((1 << 31) - 1, q))
        q = q & 0xFFFFFF00  # 24-bit precision (low byte always zero)
        words.append((q >> 16) & 0xFFFF)  # high word
        words.append(q & 0xFFFF)  # low word
    return words


def _build_coeff_section(bands, sample_rate, section_type=1):
    """Build one coefficient section for a DSP processing block.

    Returns bytes: 4-byte section header + coefficient data as LE uint16 words.
    Section header: [type, 0x00, count_lo, count_hi].

    Coefficients are normalized by a rescale factor to prevent Q1.31 overflow.
    Only feedforward coefficients (b0, b1, b2) are divided by rescale; feedback
    coefficients (a1, a2) are left unchanged. The DSP multiplies the output by
    rescale to restore correct gain.
    """
    _HEADROOM = 1.19  # 19% headroom margin (matches LGHUB)
    num_bands = len(bands)
    all_words = [num_bands]  # first uint16 = num_bands

    # First pass: compute raw biquad coefficients for all bands
    raw_coeffs = []
    for freq, gain, Q in bands:
        raw_coeffs.append(_peaking_eq_biquad(freq, gain, max(Q, 0.1), sample_rate))

    # Compute rescale: ensure max |b0| fits in Q1.31 with headroom
    max_b0 = max(abs(c[0]) for c in raw_coeffs)
    rescale = max(1.0, max_b0) * _HEADROOM

    # Second pass: normalize b-coefficients and quantize
    for b0, b1, b2, a1, a2 in raw_coeffs:
        all_words.extend(_quantize_coeffs(b0 / rescale, b1 / rescale, b2 / rescale, a1, a2))

    # Rescale factor as Q6.26, 24-bit precision
    rs = int(round(rescale * (1 << 26)))
    rs = max(-(1 << 31), min((1 << 31) - 1, rs)) & 0xFFFFFF00
    all_words.append((rs >> 16) & 0xFFFF)
    all_words.append(rs & 0xFFFF)

    coeff_count = num_bands * 10 + 3  # num_bands word + 10 per band + 2 rescale words
    hdr = bytes([section_type, 0x00, coeff_count & 0xFF, (coeff_count >> 8) & 0xFF])
    data = struct.pack(f"<{len(all_words)}H", *all_words)
    return hdr + data


def _build_eq_coeffs_payload(bands):
    """Build the full EQCoeffs wire payload for SetEQParameters.

    Two coefficient sections: type=1 (48 kHz playback) and type=2 (16 kHz mic).
    Returns bytes: 7-byte header + sections (no trailing padding).
    """
    section_count = 2
    header = bytes([0x03, 0x0E, 0x00, section_count, 0x00, 0x00, 0x00])
    sections = _build_coeff_section(bands, 48000.0, section_type=1)
    sections += _build_coeff_section(bands, 16000.0, section_type=2)
    return header + sections


def _build_set_eq_payload(slot, bands):
    """Build complete SetEQParameters payload: band params + biquad coefficients.

    bands: list of (freq_hz, gain_db, Q) tuples.
    Returns bytes ready to send as sub-device params.
    """
    params = bytes([slot, len(bands)])
    for freq, gain, Q in bands:
        params += struct.pack(">H", freq) + bytes([gain & 0xFF, Q & 0xFF])
    params += _EQ_MYSTERY_BYTES
    params += _build_eq_coeffs_payload(bands)
    return params


def get_onboard_eq_info(device):
    """Query HEADSET_ONBOARD_EQ GetEQInfos (function 0).

    Returns (has_hw_eq, num_bands) or None.
    """
    result = device.feature_request(SupportedFeature.HEADSET_ONBOARD_EQ, 0x00)
    if result is None or len(result) < 5:
        return None
    has_hw_eq = bool(result[0] & 0x80)
    num_bands = result[4]
    return (has_hw_eq, num_bands)


def get_onboard_eq_params(device, slot=0x00):
    """Query HEADSET_ONBOARD_EQ GetEQParameters (function 0x10).

    Returns list of (freq_hz, gain_db, q) tuples, or None.
    """
    result = device.feature_request(SupportedFeature.HEADSET_ONBOARD_EQ, 0x10, slot)
    if result is None or len(result) < 2:
        return None
    band_count = result[1]
    bands = []
    offset = 2
    for _i in range(band_count):
        if offset + 4 > len(result):
            break
        freq_hz = struct.unpack(">H", result[offset : offset + 2])[0]
        gain_db = struct.unpack("b", bytes([result[offset + 2]]))[0]  # signed
        q = result[offset + 3]
        bands.append((freq_hz, gain_db, q))
        offset += 4
    return bands


def set_onboard_eq_params(device, bands, slot=0x00):
    """Send HEADSET_ONBOARD_EQ SetEQParameters (function 0x20).

    bands: list of (freq_hz, gain_db, Q) tuples.
    Returns response or None.
    """
    payload = _build_set_eq_payload(slot, bands)
    return device.feature_request(SupportedFeature.HEADSET_ONBOARD_EQ, 0x20, payload)
