## Copyright (C) 2012-2013  Daniel Pavel
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

from logitech_receiver import common
from logitech_receiver import exceptions
from logitech_receiver import hidpp10
from logitech_receiver import hidpp10_constants
from logitech_receiver import hidpp20
from logitech_receiver import hidpp20_constants
from logitech_receiver import receiver
from logitech_receiver import settings_templates
from logitech_receiver.common import LOGITECH_VENDOR_ID
from logitech_receiver.common import NamedInt
from logitech_receiver.common import strhex
from logitech_receiver.hidpp20_constants import SupportedFeature

from solaar import NAME
from solaar import __version__

_hidpp10 = hidpp10.Hidpp10()
_hidpp20 = hidpp20.Hidpp20()


def _print_receiver(receiver):
    paired_count = receiver.count()

    print(receiver.name)
    print("  Device path  :", receiver.path)
    print(f"  USB id       : {LOGITECH_VENDOR_ID:04x}:{receiver.product_id}")
    print("  Serial       :", receiver.serial)
    pending = hidpp10.get_configuration_pending_flags(receiver)
    if pending:
        print(f"  C Pending    : {pending:02x}")
    if receiver.firmware:
        for f in receiver.firmware:
            print("    %-11s: %s" % (f.kind, f.version))

    print("  Has", paired_count, f"paired device(s) out of a maximum of {int(receiver.max_devices)}.")
    if receiver.remaining_pairings() and receiver.remaining_pairings() >= 0:
        print(f"  Has {int(receiver.remaining_pairings())} successful pairing(s) remaining.")

    notification_flags = _hidpp10.get_notification_flags(receiver)
    if notification_flags is not None:
        if notification_flags:
            notification_names = hidpp10_constants.NotificationFlag.flag_names(notification_flags)
            print(f"  Notifications: {', '.join(notification_names)} (0x{notification_flags:06X})")
        else:
            print("  Notifications: (none)")

    activity = receiver.read_register(hidpp10_constants.Registers.DEVICES_ACTIVITY)
    if activity:
        activity = [(d, ord(activity[d - 1 : d])) for d in range(1, receiver.max_devices)]
        activity_text = ", ".join(f"{int(d)}={int(a)}" for d, a in activity if a > 0)
        print("  Device activity counters:", activity_text or "(empty)")


def _battery_text(level) -> str:
    if level is None:
        return "N/A"
    elif isinstance(level, NamedInt):
        return str(level)
    else:
        return f"{int(level)}%"


def _battery_line(dev):
    battery = dev.battery()
    if battery is not None:
        level, nextLevel, status, voltage = battery.level, battery.next_level, battery.status, battery.voltage
        text = _battery_text(level)
        if voltage is not None:
            text = text + f" {voltage}mV "
        nextText = "" if nextLevel is None else ", next level " + _battery_text(nextLevel)
        print(f"     Battery: {text}, {status}{nextText}.")
    else:
        print("     Battery status unavailable.")


def _print_device(dev, num=None):
    assert dev is not None
    # try to ping the device to see if it actually exists and to wake it up
    try:
        dev.ping()
    except exceptions.NoSuchDevice:
        print(f"  {num}: Device not found" or dev.number)
        return

    if num or dev.number < 8:
        print(f"  {int(num or dev.number)}: {dev.name}")
    else:
        print(f"{dev.name}")
    print("     Device path  :", dev.path)
    if dev.wpid:
        print(f"     WPID         : {dev.wpid}")
    if dev.product_id:
        print(f"     USB id       : {LOGITECH_VENDOR_ID:04x}:{dev.product_id}")
    print("     Codename     :", dev.codename)
    print("     Kind         :", dev.kind)
    if dev.protocol:
        print(f"     Protocol     : HID++ {dev.protocol:1.1f}")
    else:
        print("     Protocol     : unknown (device is offline)")
    if dev.polling_rate:
        print("     Report Rate :", dev.polling_rate)
    print("     Serial number:", dev.serial)
    if dev.modelId:
        print("     Model ID:     ", dev.modelId)
    if dev.unitId:
        print("     Unit ID:      ", dev.unitId)
    if dev.firmware:
        for fw in dev.firmware:
            print(f"       {fw.kind:11}:", (fw.name + " " + fw.version).strip())

    if dev.power_switch_location:
        print(f"     The power switch is located on the {dev.power_switch_location}.")

    if dev.online:
        notification_flags = _hidpp10.get_notification_flags(dev)
        if notification_flags is not None:
            if notification_flags:
                notification_names = hidpp10_constants.NOTIFICATION_FLAG.flag_names(notification_flags)
                print(f"     Notifications: {', '.join(notification_names)} (0x{notification_flags:06X}).")
            else:
                print("     Notifications: (none).")
        device_features = _hidpp10.get_device_features(dev)
        if device_features is not None:
            if device_features:
                device_features_names = hidpp10_constants.DEVICE_FEATURES.flag_names(device_features)
                print(f"     Features: {', '.join(device_features_names)} (0x{device_features:06X})")
            else:
                print("     Features: (none)")

    if dev.online and dev.features:
        print(f"     Supports {len(dev.features)} HID++ 2.0 features:")
        dev_settings = []
        settings_templates.check_feature_settings(dev, dev_settings)
        for feature, index in dev.features.enumerate():
            if isinstance(feature, str):
                feature_bytes = bytes.fromhex(feature[-4:])
            else:
                feature_bytes = feature.to_bytes(2, byteorder="little")
            feature_int = int.from_bytes(feature_bytes, byteorder="little")
            flags = dev.request(0x0000, feature_bytes)
            flags = 0 if flags is None else ord(flags[1:2])
            flags = common.flag_names(hidpp20_constants.FeatureFlag, flags)
            version = dev.features.get_feature_version(feature_int)
            version = version if version else 0
            print("        %2d: %-22s {%04X} V%s    %s " % (index, feature, feature_int, version, ", ".join(flags)))
            if feature == SupportedFeature.HIRES_WHEEL:
                wheel = _hidpp20.get_hires_wheel(dev)
                if wheel:
                    multi, has_invert, has_switch, inv, res, target, ratchet = wheel
                    print(f"            Multiplier: {multi}")
                    if has_invert:
                        print("            Has invert:", "Inverse wheel motion" if inv else "Normal wheel motion")
                    if has_switch:
                        print("            Has ratchet switch:", "Normal wheel mode" if ratchet else "Free wheel mode")
                    if res:
                        print("            High resolution mode")
                    else:
                        print("            Low resolution mode")
                    if target:
                        print("            HID++ notification")
                    else:
                        print("            HID notification")
            elif feature == SupportedFeature.MOUSE_POINTER:
                mouse_pointer = _hidpp20.get_mouse_pointer_info(dev)
                if mouse_pointer:
                    print(f"            DPI: {mouse_pointer['dpi']}")
                    print(f"            Acceleration: {mouse_pointer['acceleration']}")
                    if mouse_pointer["suggest_os_ballistics"]:
                        print("            Use OS ballistics")
                    else:
                        print("            Override OS ballistics")
                    if mouse_pointer["suggest_vertical_orientation"]:
                        print("            Provide vertical tuning, trackball")
                    else:
                        print("            No vertical tuning, standard mice")
            elif feature == SupportedFeature.VERTICAL_SCROLLING:
                vertical_scrolling_info = _hidpp20.get_vertical_scrolling_info(dev)
                if vertical_scrolling_info:
                    print(f"            Roller type: {vertical_scrolling_info['roller']}")
                    print(f"            Ratchet per turn: {vertical_scrolling_info['ratchet']}")
                    print(f"            Scroll lines: {vertical_scrolling_info['lines']}")
            elif feature == SupportedFeature.HI_RES_SCROLLING:
                scrolling_mode, scrolling_resolution = _hidpp20.get_hi_res_scrolling_info(dev)
                if scrolling_mode:
                    print("            Hi-res scrolling enabled")
                else:
                    print("            Hi-res scrolling disabled")
                if scrolling_resolution:
                    print(f"            Hi-res scrolling multiplier: {scrolling_resolution}")
            elif feature == SupportedFeature.POINTER_SPEED:
                pointer_speed = _hidpp20.get_pointer_speed_info(dev)
                if pointer_speed:
                    print(f"            Pointer Speed: {pointer_speed}")
            elif feature == SupportedFeature.LOWRES_WHEEL:
                wheel_status = _hidpp20.get_lowres_wheel_status(dev)
                if wheel_status:
                    print(f"            Wheel Reports: {wheel_status}")
            elif feature == SupportedFeature.NEW_FN_INVERSION:
                inversion = _hidpp20.get_new_fn_inversion(dev)
                if inversion:
                    inverted, default_inverted = inversion
                    print("            Fn-swap:", "enabled" if inverted else "disabled")
                    print("            Fn-swap default:", "enabled" if default_inverted else "disabled")
            elif feature == SupportedFeature.HOSTS_INFO:
                host_names = _hidpp20.get_host_names(dev)
                for host, (paired, name) in host_names.items():
                    print(f"            Host {host} ({'paired' if paired else 'unpaired'}): {name}")
            elif feature == SupportedFeature.DEVICE_NAME:
                print(f"            Name: {_hidpp20.get_name(dev)}")
                print(f"            Kind: {_hidpp20.get_kind(dev)}")
            elif feature == SupportedFeature.DEVICE_FRIENDLY_NAME:
                print(f"            Friendly Name: {_hidpp20.get_friendly_name(dev)}")
            elif feature == SupportedFeature.DEVICE_FW_VERSION:
                for fw in _hidpp20.get_firmware(dev):
                    extras = strhex(fw.extras) if fw.extras else ""
                    print(f"            Firmware: {fw.kind} {fw.name} {fw.version} {extras}")
                ids = _hidpp20.get_ids(dev)
                if ids:
                    unitId, modelId, tid_map = ids
                    print(f"            Unit ID: {unitId}  Model ID: {modelId}  Transport IDs: {tid_map}")
            elif feature == SupportedFeature.REPORT_RATE or feature == SupportedFeature.EXTENDED_ADJUSTABLE_REPORT_RATE:
                print(f"            Report Rate: {_hidpp20.get_polling_rate(dev)}")
            elif feature == SupportedFeature.CONFIG_CHANGE:
                response = dev.feature_request(SupportedFeature.CONFIG_CHANGE, 0x00)
                print(f"            Configuration: {response.hex()}")
            elif feature == SupportedFeature.REMAINING_PAIRING:
                print(f"            Remaining Pairings: {int(_hidpp20.get_remaining_pairing(dev))}")
            elif feature == SupportedFeature.ONBOARD_PROFILES:
                if _hidpp20.get_onboard_mode(dev) == hidpp20_constants.OnboardMode.MODE_HOST:
                    mode = "Host"
                else:
                    mode = "On-Board"
                print(f"            Device Mode: {mode}")
            elif hidpp20.battery_functions.get(feature, None):
                print("", end="       ")
                _battery_line(dev)
            for setting in dev_settings:
                if setting.feature == feature:
                    if (
                        setting._device
                        and getattr(setting._device, "persister", None)
                        and setting._device.persister.get(setting.name) is not None
                    ):
                        v = setting.val_to_string(setting._device.persister.get(setting.name))
                        print(f"            {setting.label} (saved): {v}")
                    try:
                        v = setting.val_to_string(setting.read(False))
                    except exceptions.FeatureCallError as e:
                        v = "HID++ error " + str(e)
                    except AssertionError as e:
                        v = "AssertionError " + str(e)
                    print(f"            {setting.label}        : {v}")

    if dev.online and dev.keys:
        print(f"     Has {len(dev.keys)} reprogrammable keys:")
        for k in dev.keys:
            # TODO: add here additional variants for other REPROG_CONTROLS
            if dev.keys.keyversion == SupportedFeature.REPROG_CONTROLS_V2:
                print("        %2d: %-26s => %-27s   %s" % (k.index, k.key, k.default_task, ", ".join(k.flags)))
            if dev.keys.keyversion == SupportedFeature.REPROG_CONTROLS_V4:
                print("        %2d: %-26s, default: %-27s => %-26s" % (k.index, k.key, k.default_task, k.mapped_to))
                gmask_fmt = ",".join(k.group_mask)
                gmask_fmt = gmask_fmt if gmask_fmt else "empty"
                flag_names = list(common.flag_names(hidpp20.KeyFlag, k.flags.value))
                print(
                    f"             {', '.join(flag_names)}, pos:{int(k.pos)}, group:{int(k.group):1}, group mask:{gmask_fmt}"
                )
                report_fmt = list(common.flag_names(hidpp20.MappingFlag, k.mapping_flags.value))
                report_fmt = report_fmt if report_fmt else "default"
                print(f"             reporting: {report_fmt}")
    if dev.online and dev.remap_keys:
        print(f"     Has {len(dev.remap_keys)} persistent remappable keys:")
        for k in dev.remap_keys:
            print("        %2d: %-26s => %s%s" % (k.index, k.key, k.action, " (remapped)" if k.cidStatus else ""))
    if dev.online and dev.gestures:
        print(
            "     Has %d gesture(s), %d param(s) and %d spec(s):"
            % (len(dev.gestures.gestures), len(dev.gestures.params), len(dev.gestures.specs))
        )
        for k in dev.gestures.gestures.values():
            print(
                "        %-26s Enabled(%4s): %-5s  Diverted:(%4s) %s"
                % (k.gesture, k.index, k.enabled(), k.diversion_index, k.diverted())
            )
        for k in dev.gestures.params.values():
            print("        %-26s Value  (%4s): %s [Default: %s]" % (k.param, k.index, k.value, k.default_value))
        for k in dev.gestures.specs.values():
            print("        %-26s Spec   (%4s): %s" % (k.spec, k.id, k.value))
    if dev.online:
        _battery_line(dev)
    else:
        print("     Battery: unknown (device is offline).")


def run(devices, args, find_receiver, find_device):
    assert devices
    assert args.device

    print(f"{NAME.lower()} version {__version__}")
    print("")

    device_name = args.device.lower()

    if device_name == "all":
        for d in devices:
            if isinstance(d, receiver.Receiver):
                _print_receiver(d)
                count = d.count()
                if count:
                    for dev in d:
                        print("")
                        _print_device(dev, dev.number)
                        count -= 1
                        if not count:
                            break
                print("")
            else:
                print("")
                _print_device(d)
        return

    dev = find_receiver(devices, device_name)
    if dev and not dev.isDevice:
        _print_receiver(dev)
        return

    dev = next(find_device(devices, device_name), None)
    if not dev:
        raise Exception(f"no device found matching '{device_name}'")

    _print_device(dev)
