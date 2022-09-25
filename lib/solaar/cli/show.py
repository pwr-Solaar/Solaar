# -*- python-mode -*-

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

from logitech_receiver import hidpp10 as _hidpp10
from logitech_receiver import hidpp20 as _hidpp20
from logitech_receiver import receiver as _receiver
from logitech_receiver import settings_templates as _settings_templates
from logitech_receiver.common import NamedInt as _NamedInt
from logitech_receiver.common import strhex as _strhex
from solaar import NAME, __version__

_F = _hidpp20.FEATURE


def _print_receiver(receiver):
    paired_count = receiver.count()

    print(receiver.name)
    print('  Device path  :', receiver.path)
    print('  USB id       : 046d:%s' % receiver.product_id)
    print('  Serial       :', receiver.serial)
    if receiver.firmware:
        for f in receiver.firmware:
            print('    %-11s: %s' % (f.kind, f.version))

    print('  Has', paired_count, 'paired device(s) out of a maximum of %d.' % receiver.max_devices)
    if receiver.remaining_pairings() and receiver.remaining_pairings() >= 0:
        print('  Has %d successful pairing(s) remaining.' % receiver.remaining_pairings())

    notification_flags = _hidpp10.get_notification_flags(receiver)
    if notification_flags is not None:
        if notification_flags:
            notification_names = _hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
            print('  Notifications: %s (0x%06X)' % (', '.join(notification_names), notification_flags))
        else:
            print('  Notifications: (none)')

    activity = receiver.read_register(_hidpp10.REGISTERS.devices_activity)
    if activity:
        activity = [(d, ord(activity[d - 1:d])) for d in range(1, receiver.max_devices)]
        activity_text = ', '.join(('%d=%d' % (d, a)) for d, a in activity if a > 0)
        print('  Device activity counters:', activity_text or '(empty)')


def _battery_text(level):
    if level is None:
        return 'N/A'
    elif isinstance(level, _NamedInt):
        return str(level)
    else:
        return '%d%%' % level


def _battery_line(dev):
    battery = dev.battery()
    if battery is not None:
        level, nextLevel, status, voltage = battery
        text = _battery_text(level)
        if voltage is not None:
            text = text + (' %smV ' % voltage)
        nextText = '' if nextLevel is None else ', next level ' + _battery_text(nextLevel)
        print('     Battery: %s, %s%s.' % (text, status, nextText))
    else:
        print('     Battery status unavailable.')


def _print_device(dev, num=None):
    assert dev is not None
    # check if the device is online
    dev.ping()

    print('  %d: %s' % (num or dev.number, dev.name))
    print('     Device path  :', dev.path)
    if dev.wpid:
        print('     WPID         : %s' % dev.wpid)
    if dev.product_id:
        print('     USB id       : 046d:%s' % dev.product_id)
    print('     Codename     :', dev.codename)
    print('     Kind         :', dev.kind)
    if dev.protocol:
        print('     Protocol     : HID++ %1.1f' % dev.protocol)
    else:
        print('     Protocol     : unknown (device is offline)')
    if dev.polling_rate:
        print('     Polling rate :', dev.polling_rate, 'ms (%dHz)' % (1000 // dev.polling_rate))
    print('     Serial number:', dev.serial)
    if dev.modelId:
        print('     Model ID:     ', dev.modelId)
    if dev.unitId:
        print('     Unit ID:      ', dev.unitId)
    if dev.firmware:
        for fw in dev.firmware:
            print('       %11s:' % fw.kind, (fw.name + ' ' + fw.version).strip())

    if dev.power_switch_location:
        print('     The power switch is located on the %s.' % dev.power_switch_location)

    if dev.online:
        notification_flags = _hidpp10.get_notification_flags(dev)
        if notification_flags is not None:
            if notification_flags:
                notification_names = _hidpp10.NOTIFICATION_FLAG.flag_names(notification_flags)
                print('     Notifications: %s (0x%06X).' % (', '.join(notification_names), notification_flags))
            else:
                print('     Notifications: (none).')
        device_features = _hidpp10.get_device_features(dev)
        if device_features is not None:
            if device_features:
                device_features_names = _hidpp10.DEVICE_FEATURES.flag_names(device_features)
                print('     Features: %s (0x%06X)' % (', '.join(device_features_names), device_features))
            else:
                print('     Features: (none)')

    if dev.online and dev.features:
        print('     Supports %d HID++ 2.0 features:' % len(dev.features))
        dev_settings = []
        _settings_templates.check_feature_settings(dev, dev_settings)
        for feature, index in dev.features.enumerate():
            flags = dev.request(0x0000, feature.bytes(2))
            flags = 0 if flags is None else ord(flags[1:2])
            flags = _hidpp20.FEATURE_FLAG.flag_names(flags)
            version = dev.features.get_feature_version(int(feature))
            version = version if version else 0
            print('        %2d: %-22s {%04X} V%s    %s ' % (index, feature, feature, version, ', '.join(flags)))
            if feature == _hidpp20.FEATURE.HIRES_WHEEL:
                wheel = _hidpp20.get_hires_wheel(dev)
                if wheel:
                    multi, has_invert, has_switch, inv, res, target, ratchet = wheel
                    print('            Multiplier: %s' % multi)
                    if has_invert:
                        print('            Has invert:', 'Inverse wheel motion' if inv else 'Normal wheel motion')
                    if has_switch:
                        print('            Has ratchet switch:', 'Normal wheel mode' if ratchet else 'Free wheel mode')
                    if res:
                        print('            High resolution mode')
                    else:
                        print('            Low resolution mode')
                    if target:
                        print('            HID++ notification')
                    else:
                        print('            HID notification')
            elif feature == _hidpp20.FEATURE.MOUSE_POINTER:
                mouse_pointer = _hidpp20.get_mouse_pointer_info(dev)
                if mouse_pointer:
                    print('            DPI: %s' % mouse_pointer['dpi'])
                    print('            Acceleration: %s' % mouse_pointer['acceleration'])
                    if mouse_pointer['suggest_os_ballistics']:
                        print('            Use OS ballistics')
                    else:
                        print('            Override OS ballistics')
                    if mouse_pointer['suggest_vertical_orientation']:
                        print('            Provide vertical tuning, trackball')
                    else:
                        print('            No vertical tuning, standard mice')
            elif feature == _hidpp20.FEATURE.VERTICAL_SCROLLING:
                vertical_scrolling_info = _hidpp20.get_vertical_scrolling_info(dev)
                if vertical_scrolling_info:
                    print('            Roller type: %s' % vertical_scrolling_info['roller'])
                    print('            Ratchet per turn: %s' % vertical_scrolling_info['ratchet'])
                    print('            Scroll lines: %s' % vertical_scrolling_info['lines'])
            elif feature == _hidpp20.FEATURE.HI_RES_SCROLLING:
                scrolling_mode, scrolling_resolution = _hidpp20.get_hi_res_scrolling_info(dev)
                if scrolling_mode:
                    print('            Hi-res scrolling enabled')
                else:
                    print('            Hi-res scrolling disabled')
                if scrolling_resolution:
                    print('            Hi-res scrolling multiplier: %s' % scrolling_resolution)
            elif feature == _hidpp20.FEATURE.POINTER_SPEED:
                pointer_speed = _hidpp20.get_pointer_speed_info(dev)
                if pointer_speed:
                    print('            Pointer Speed: %s' % pointer_speed)
            elif feature == _hidpp20.FEATURE.LOWRES_WHEEL:
                wheel_status = _hidpp20.get_lowres_wheel_status(dev)
                if wheel_status:
                    print('            Wheel Reports: %s' % wheel_status)
            elif feature == _hidpp20.FEATURE.NEW_FN_INVERSION:
                inversion = _hidpp20.get_new_fn_inversion(dev)
                if inversion:
                    inverted, default_inverted = inversion
                    print('            Fn-swap:', 'enabled' if inverted else 'disabled')
                    print('            Fn-swap default:', 'enabled' if default_inverted else 'disabled')
            elif feature == _hidpp20.FEATURE.HOSTS_INFO:
                host_names = _hidpp20.get_host_names(dev)
                for host, (paired, name) in host_names.items():
                    print('            Host %s (%s): %s' % (host, 'paired' if paired else 'unpaired', name))
            elif feature == _hidpp20.FEATURE.DEVICE_NAME:
                print('            Name: %s' % _hidpp20.get_name(dev))
                print('            Kind: %s' % _hidpp20.get_kind(dev))
            elif feature == _hidpp20.FEATURE.DEVICE_FRIENDLY_NAME:
                print('            Friendly Name: %s' % _hidpp20.get_friendly_name(dev))
            elif feature == _hidpp20.FEATURE.DEVICE_FW_VERSION:
                for fw in _hidpp20.get_firmware(dev):
                    extras = _strhex(fw.extras) if fw.extras else ''
                    print('            Firmware: %s %s %s %s' % (fw.kind, fw.name, fw.version, extras))
                ids = _hidpp20.get_ids(dev)
                if ids:
                    unitId, modelId, tid_map = ids
                    print('            Unit ID: %s  Model ID: %s  Transport IDs: %s' % (unitId, modelId, tid_map))
            elif feature == _hidpp20.FEATURE.REPORT_RATE:
                print('            Polling Rate (ms): %d' % _hidpp20.get_polling_rate(dev))
            elif feature == _hidpp20.FEATURE.REMAINING_PAIRING:
                print('            Remaining Pairings: %d' % _hidpp20.get_remaining_pairing(dev))
            elif feature == _hidpp20.FEATURE.ONBOARD_PROFILES:
                if _hidpp20.get_onboard_mode(dev) == _hidpp20.ONBOARD_MODES.MODE_HOST:
                    mode = 'Host'
                else:
                    mode = 'On-Board'
                print('            Device Mode: %s' % mode)
            elif _hidpp20.battery_functions.get(feature, None):
                print('', end='       ')
                _battery_line(dev)
            for setting in dev_settings:
                if setting.feature == feature:
                    if setting._device and getattr(setting._device, 'persister', None) and \
                       setting._device.persister.get(setting.name) is not None:
                        v = setting.val_to_string(setting._device.persister.get(setting.name))
                        print('            %s (saved): %s' % (setting.label, v))
                    try:
                        v = setting.val_to_string(setting.read(False))
                    except _hidpp20.FeatureCallError as e:
                        v = e
                    print('            %s        : %s' % (setting.label, v))

    if dev.online and dev.keys:
        print('     Has %d reprogrammable keys:' % len(dev.keys))
        for k in dev.keys:
            # TODO: add here additional variants for other REPROG_CONTROLS
            if dev.keys.keyversion == _hidpp20.FEATURE.REPROG_CONTROLS_V2:
                print('        %2d: %-26s => %-27s   %s' % (k.index, k.key, k.default_task, ', '.join(k.flags)))
            if dev.keys.keyversion == _hidpp20.FEATURE.REPROG_CONTROLS_V4:
                print('        %2d: %-26s, default: %-27s => %-26s' % (k.index, k.key, k.default_task, k.mapped_to))
                gmask_fmt = ','.join(k.group_mask)
                gmask_fmt = gmask_fmt if gmask_fmt else 'empty'
                print('             %s, pos:%d, group:%1d, group mask:%s' % (', '.join(k.flags), k.pos, k.group, gmask_fmt))
                report_fmt = ', '.join(k.mapping_flags)
                report_fmt = report_fmt if report_fmt else 'default'
                print('             reporting: %s' % (report_fmt))
    if dev.online and dev.remap_keys:
        print('     Has %d persistent remappable keys:' % len(dev.remap_keys))
        for k in dev.remap_keys:
            print('        %2d: %-26s => %s%s' % (k.index, k.key, k.action, ' (remapped)' if k.cidStatus else ''))
    if dev.online and dev.gestures:
        print(
            '     Has %d gesture(s), %d param(s) and %d spec(s):' %
            (len(dev.gestures.gestures), len(dev.gestures.params), len(dev.gestures.specs))
        )
        for k in dev.gestures.gestures.values():
            print(
                '        %-26s Enabled(%4s): %-5s  Diverted:(%4s) %s' %
                (k.gesture, k.index, k.enabled(), k.diversion_index, k.diverted())
            )
        for k in dev.gestures.params.values():
            print('        %-26s Value  (%4s): %s [Default: %s]' % (k.param, k.index, k.value, k.default_value))
        for k in dev.gestures.specs.values():
            print('        %-26s Spec   (%4s): %s' % (k.spec, k.id, k.value))
    if dev.online:
        _battery_line(dev)
    else:
        print('     Battery: unknown (device is offline).')


def run(devices, args, find_receiver, find_device):
    assert devices
    assert args.device

    print('%s version %s' % (NAME, __version__))
    print('')

    device_name = args.device.lower()

    if device_name == 'all':
        dev_num = 1
        for d in devices:
            if isinstance(d, _receiver.Receiver):
                _print_receiver(d)
                count = d.count()
                if count:
                    for dev in d:
                        print('')
                        _print_device(dev)
                        count -= 1
                        if not count:
                            break
                print('')
            else:
                if dev_num == 1:
                    print('USB and Bluetooth Devices')
                print('')
                _print_device(d, num=dev_num)
                dev_num += 1
        return

    dev = find_receiver(devices, device_name)
    if dev and not dev.isDevice:
        _print_receiver(dev)
        return

    dev = next(find_device(devices, device_name), None)
    if not dev:
        raise Exception("no device found matching '%s'" % device_name)

    _print_device(dev)
