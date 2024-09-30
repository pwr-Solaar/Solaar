from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class DeviceInfo:
    path: str
    bus_id: str | None
    vendor_id: str
    product_id: str
    interface: str | None
    driver: str | None
    manufacturer: str | None
    product: str | None
    serial: str | None
    release: str | None
    isDevice: bool
    hidpp_short: str | None
    hidpp_long: str | None
