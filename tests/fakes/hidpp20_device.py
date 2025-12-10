from logitech_receiver.hidpp20_constants import SupportedFeature


class Hidpp20Device:
    def __init__(self):
        self._iteration = 0

    def feature_request(self, feature, function: int = 0x00, *params, no_reply: bool = False) -> bytes:
        self._iteration += 1
        if feature == SupportedFeature.DEVICE_FW_VERSION:
            if function == 0x00:
                self._iteration = 1
                return bytes([0x02, 0xFF, 0xFF])
            elif self._iteration == 2 and function == 0x10:
                return bytes.fromhex("01414243030401000101000102030405")
            elif self._iteration == 3:
                self._iteration = 0
                return bytes.fromhex("02414243030401000101000102030405")
        elif feature == SupportedFeature.DEVICE_NAME:
            if function == 0x00:
                self._iteration = 1
                return bytes([0x12])
            elif function == 0x10:
                if self._iteration == 2:
                    return bytes.fromhex("4142434445464748494A4B4C4D4E4F")
                elif self._iteration == 3:
                    return bytes.fromhex("505152530000000000000000000000")
            elif function == 0x20:
                keyboard = 0x00
                return bytes([keyboard])
        elif feature == SupportedFeature.DEVICE_FRIENDLY_NAME:
            if function == 0x00:
                self._iteration = 1
                return bytes([0x12])
            elif function == 0x10:
                if self._iteration == 2:
                    return bytes.fromhex("004142434445464748494A4B4C4D4E")
                elif self._iteration == 3:
                    return bytes.fromhex("0E4F50515253000000000000000000")
        elif feature == SupportedFeature.BATTERY_STATUS:
            if function == 0x00:
                return bytes.fromhex("502000FFFF")
        elif feature == SupportedFeature.VERTICAL_SCROLLING:
            roller_type = 0x01
            num_of_ratchet_by_turn = 0x08
            scroll_lines = 0x0C
            return bytes([roller_type, num_of_ratchet_by_turn, scroll_lines])
        elif feature == SupportedFeature.HI_RES_SCROLLING:
            mode = 0x01
            resolution = 0x02
            return bytes([mode, resolution])
        elif feature == SupportedFeature.MOUSE_POINTER:
            sensor_resolution_msb = 0x01
            sensor_resolution_lsb = 0x00
            flags = 0x0A
            return bytes([sensor_resolution_msb, sensor_resolution_lsb, flags])
        elif feature == SupportedFeature.POINTER_SPEED:
            pointer_speed_high = 0x01
            pointer_speed_low = 0x03
            return bytes([pointer_speed_high, pointer_speed_low])

        raise RuntimeError(f"Unsupported feature: {feature.name}, func=0x{function:02X}")
