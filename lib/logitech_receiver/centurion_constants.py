"""Centurion transport-specific constants.

Feature IDs that collide with HID++ 2.0 core features live here
so they can coexist with SupportedFeature (which requires unique values).
"""

from __future__ import annotations

from enum import IntEnum

from .hidpp20_constants import SupportedFeature


class CenturionCoreFeature(IntEnum):
    """Centurion transport-specific features that collide with HID++ 2.0 core IDs."""

    CENTURION_ROOT = 0x0000
    CENTURION_FEATURE_SET = 0x0001
    CENT_PP_BRIDGE = 0x0003
    MULTI_HOST_CONTROL = 0x0005
    KEEP_ALIVE = 0x0007

    def __str__(self):
        return self.name.replace("_", " ")


def resolve_feature(feat_id: int, centurion: bool = False):
    """Resolve a feature ID to the appropriate enum, checking centurion-specific
    features first when on the centurion transport."""
    if centurion:
        try:
            return CenturionCoreFeature(feat_id)
        except ValueError:
            pass
    try:
        return SupportedFeature(feat_id)
    except ValueError:
        return None
