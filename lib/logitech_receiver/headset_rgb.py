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

"""Shared helpers for devices exposing Feature 0x0620 HEADSET_RGB_HOSTMODE.

The G522 is currently the only Solaar-supported device advertising this
feature, but anything else presenting 0x0620 will pick the same code path
automatically. The module deliberately avoids G522-specific assumptions
so future RGB-capable headsets can reuse it.

Two entry points the settings templates rely on:

- `discover_zones(device)` — one-shot zone enumeration run at setting
  build time. Briefly claims Solaar host control so GetRGBZoneInfo
  returns a non-empty zone list, then restores the previous host-mode
  state. Result is cached on the device.
- `write_zone_map(device, zone_color_map)` — the shared write path used
  by both the "LEDs Primary" and "Per-zone Lighting" settings. Groups
  zones by final RGB color and emits one SetRgbZonesSingleValue per
  unique color, then a single FrameEnd to commit.
"""

from __future__ import annotations

import logging

from typing import Iterable

from .hidpp20_constants import SupportedFeature

logger = logging.getLogger(__name__)

# Function IDs on Feature 0x0620 we actually use.
FN_GET_RGB_ZONE_INFO = 0x10
FN_SET_RGB_ZONES_SINGLE = 0x50
FN_FRAME_END = 0x60
FN_GET_HOST_MODE_STATE = 0x70
FN_SET_HOST_MODE_STATE = 0x80

# Frame type sent with FrameEnd. 0x01 = transient commit (re-applies on the
# next refresh). 0x02 would be persistent, but G522 firmware rejects it
# with LOGITECH_INTERNAL (0x05) unless an onboard profile precondition we
# haven't mapped yet is satisfied.
FRAME_TYPE_TRANSIENT = 0x01

_HOST_MODE_SOLAAR = 1
_HOST_MODE_DEVICE = 0


def _device_cache_attr() -> str:
    return "_headset_rgb_zone_ids"


def _read_host_mode(device) -> int | None:
    """Read the current host-mode state byte, or None on any failure."""
    try:
        resp = device.feature_request(SupportedFeature.HEADSET_RGB_HOSTMODE, FN_GET_HOST_MODE_STATE)
    except Exception as e:
        logger.warning("headset_rgb: GetHostModeState raised %s", e)
        return None
    if not resp or len(resp) < 1:
        return None
    return resp[0]


def _set_host_mode(device, value: int) -> bool:
    try:
        device.feature_request(SupportedFeature.HEADSET_RGB_HOSTMODE, FN_SET_HOST_MODE_STATE, bytes([value & 0xFF]))
    except Exception as e:
        logger.warning("headset_rgb: SetHostModeState(%d) raised %s", value, e)
        return False
    return True


def _parse_zone_info(resp: bytes) -> list[int]:
    """Parse a GetRGBZoneInfo response into a zone-id list.

    Two formats observed: "tight" ([count, zone_ids...]) on G522, and
    the canonical protocol-doc layout (3-byte gap + 1-byte reserved
    before zone IDs). Both are tried; whichever yields exactly `count`
    IDs wins. Zone id 0 isn't filtered — some devices may use it.
    """
    if not resp or len(resp) < 1:
        return []
    zone_count = resp[0]
    tight = list(resp[1 : 1 + zone_count]) if 1 <= zone_count <= len(resp) - 1 else []
    if tight and len(tight) == zone_count:
        return tight
    gap = list(resp[5 : 5 + zone_count]) if len(resp) >= 5 + zone_count else []
    if gap and len(gap) == zone_count:
        return gap
    return []


def discover_zones(device) -> list[int] | None:
    """Return the list of RGB zone IDs on `device`, or None on failure.

    Caches the result on `device._headset_rgb_zone_ids` so subsequent
    callers don't repeat the round-trip. Briefly claims Solaar host mode
    if needed — GetRGBZoneInfo has been observed to return count=0 when
    the device is still under firmware control — and restores the prior
    state afterward so user-configured onboard effects resume.
    """
    cached = getattr(device, _device_cache_attr(), None)
    if cached:
        return cached
    if not getattr(device, "online", False):
        return None

    prior_mode = _read_host_mode(device)
    claimed = False
    if prior_mode != _HOST_MODE_SOLAAR:
        if not _set_host_mode(device, _HOST_MODE_SOLAAR):
            return None
        claimed = True

    try:
        try:
            resp = device.feature_request(SupportedFeature.HEADSET_RGB_HOSTMODE, FN_GET_RGB_ZONE_INFO)
        except Exception as e:
            logger.warning("headset_rgb: GetRGBZoneInfo raised %s", e)
            return None
        zones = _parse_zone_info(bytes(resp) if resp else b"")
        if not zones:
            logger.warning(
                "headset_rgb: GetRGBZoneInfo returned no zones (raw=%s)",
                resp.hex() if resp else resp,
            )
            return None
        logger.info("headset_rgb: discovered %d zone(s) %s", len(zones), [f"0x{z:02X}" for z in zones])
        setattr(device, _device_cache_attr(), zones)
        return zones
    finally:
        if claimed and prior_mode is not None:
            _set_host_mode(device, prior_mode)


def _split_rgb(color_int: int) -> tuple[int, int, int]:
    return (color_int >> 16) & 0xFF, (color_int >> 8) & 0xFF, color_int & 0xFF


def write_zone_map(device, zone_color_map: dict) -> bool:
    """Apply a zone->RGB mapping to the device.

    `zone_color_map` maps zone id (int) to 24-bit RGB color (int,
    `(r<<16)|(g<<8)|b`). Claims host mode, groups zones by color,
    emits one SetRgbZonesSingleValue per unique color, then a single
    FrameEnd. Returns True on success, False on any transport error.
    """
    if not zone_color_map:
        return False
    if not getattr(device, "online", False):
        logger.info("headset_rgb: device offline, skipping write")
        return False

    # Group zones by color for batched writes.
    groups: dict[int, list[int]] = {}
    for zone, color in zone_color_map.items():
        groups.setdefault(int(color), []).append(int(zone))

    try:
        _set_host_mode(device, _HOST_MODE_SOLAAR)
        for color_int, zones in groups.items():
            r, g, b = _split_rgb(color_int)
            # SetRgbZonesSingleValue: [R, G, B, count, zone_ids...]
            payload = bytes([r, g, b, len(zones)]) + bytes(zones)
            device.feature_request(SupportedFeature.HEADSET_RGB_HOSTMODE, FN_SET_RGB_ZONES_SINGLE, payload)
            logger.info(
                "headset_rgb: set (%02X,%02X,%02X) on %d zone(s) %s",
                r,
                g,
                b,
                len(zones),
                [f"0x{z:02X}" for z in zones],
            )
        # FrameEnd commits the pending per-zone updates. Transient commit
        # only — persistent (0x02) requires onboard-profile preconditions
        # that aren't mapped yet.
        device.feature_request(
            SupportedFeature.HEADSET_RGB_HOSTMODE,
            FN_FRAME_END,
            bytes([FRAME_TYPE_TRANSIENT, 0x00, 0x00, 0x00]),
        )
    except Exception as e:
        logger.warning("headset_rgb: write_zone_map failed: %s", e)
        return False
    return True


def zone_named_ints(zones: Iterable[int]):
    """Build a list of NamedInt keys suitable for a ChoicesMap setting.

    Factored out so settings code can import without pulling common.NamedInt
    at module-load time if preferred.
    """
    from . import common

    return [common.NamedInt(int(z), f"Zone {int(z)}") for z in zones]
