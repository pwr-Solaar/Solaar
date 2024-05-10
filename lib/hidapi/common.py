import dataclasses


@dataclasses.dataclass
class DeviceInfo:
    path: str
    bus_id: str
    vendor_id: str
    product_id: str
    interface: str
    driver: str
    manufacturer: str
    product: str
    serial: str
    release: str
    isDevice: bool
    hidpp_short: str
    hidpp_long: str
