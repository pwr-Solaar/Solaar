# -*- python-mode -*-
# -*- coding: UTF-8 -*-

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

from __future__ import absolute_import, division, print_function, unicode_literals

from logitech_receiver import hidpp10 as _hidpp10
from logitech_receiver import hidpp20 as _hidpp20
from logitech_receiver import settings_templates as _settings_templates
from logitech_receiver import special_keys as _special_keys
from logitech_receiver.common import NamedInt as _NamedInt


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


def _print_device(dev):
    assert dev
    # check if the device is online
    dev.ping()

    print('  %d: %s' % (dev.number, dev.name))
    print('     Codename     :', dev.codename)
    print('     Kind         :', dev.kind)
    print('     Wireless PID :', dev.wpid)
    if dev.protocol:
        print('     Protocol     : HID++ %1.1f' % dev.protocol)
    else:
        print('     Protocol     : unknown (device is offline)')
    if dev.polling_rate:
        print('     Polling rate :', dev.polling_rate, 'ms (%dHz)' % (1000 // dev.polling_rate))
    print('     Serial number:', dev.serial)
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
        dev.persister = None  # Give the device a fake persister
        dev_settings = []
        _settings_templates.check_feature_settings(dev, dev_settings)
        for index, feature in enumerate(dev.features):
            feature = dev.features[index]
            flags = dev.request(0x0000, feature.bytes(2))
            flags = 0 if flags is None else ord(flags[1:2])
            flags = _hidpp20.FEATURE_FLAG.flag_names(flags)
            print('        %2d: %-22s {%04X}   %s' % (index, feature, feature, ', '.join(flags)))
            if feature == _hidpp20.FEATURE.HIRES_WHEEL:
                wheel = _hidpp20.get_hires_wheel(dev)
                if wheel:
                    multi, has_invert, has_switch, inv, res, target, ratchet = wheel
                    print('            Multiplier: %s' % multi)
                    if has_invert:
                        print('            Has invert')
                        if inv:
                            print('              Inverse wheel motion')
                        else:
                            print('              Normal wheel motion')
                    if has_switch:
                        print('            Has ratchet switch')
                        if ratchet:
                            print('              Normal wheel mode')
                        else:
                            print('              Free wheel mode')
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
            if feature == _hidpp20.FEATURE.VERTICAL_SCROLLING:
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
                inverted, default_inverted = _hidpp20.get_new_fn_inversion(dev)
                print('            Fn-swap:', 'enabled' if inverted else 'disabled')
                print('            Fn-swap default:', 'enabled' if default_inverted else 'disabled')
            elif feature == _hidpp20.FEATURE.HOSTS_INFO:
                host_names = _hidpp20.get_host_names(dev)
                for host, (paired, name) in host_names.items():
                    print('            Host %s (%s): %s' % (host, 'paired' if paired else 'unpaired', name))
            for setting in dev_settings:
                if setting.feature == feature:
                    v = setting.read(False)
                    print('            %s: %s' % (setting.label, v))

    if dev.online and dev.keys:
        print('     Has %d reprogrammable keys:' % len(dev.keys))
        for k in dev.keys:
            flags = _special_keys.KEY_FLAG.flag_names(k.flags)
            # TODO: add here additional variants for other REPROG_CONTROLS
            if dev.keys.keyversion == 1:
                print('        %2d: %-26s => %-27s   %s' % (k.index, k.key, k.task, ', '.join(flags)))
            if dev.keys.keyversion == 4:
                print('        %2d: %-26s, default: %-27s => %-26s' % (k.index, k.key, k.task, k.remapped))
                print('             %s, pos:%d, group:%1d, gmask:%d' % (', '.join(flags), k.pos, k.group, k.group_mask))
    if dev.online:
        battery = _hidpp20.get_battery(dev)
        if battery is None:
            battery = _hidpp10.get_battery(dev)
        if battery is not None:
            level, status, nextLevel = battery
            text = _battery_text(level)
            nextText = '' if nextLevel is None else ', next level ' + _battery_text(nextLevel)
            print('     Battery: %s, %s%s.' % (text, status, nextText))
        else:
            battery_voltage = _hidpp20.get_voltage(dev)
            if battery_voltage:
                (level, status, voltage, charge_sts, charge_type) = battery_voltage
                print('     Battery: %smV, %s, %s.' % (voltage, status, level))
            else:
                print('     Battery status unavailable.')
    else:
        print('     Battery: unknown (device is offline).')


def run(receivers, args, find_receiver, find_device):
    assert receivers
    assert args.device

    device_name = args.device.lower()

    if device_name == 'all':
        for r in receivers:
            _print_receiver(r)
            count = r.count()
            if count:
                for dev in r:
                    print('')
                    _print_device(dev)
                    count -= 1
                    if not count:
                        break
            print('')
        return

    dev = find_receiver(receivers, device_name)
    if dev:
        _print_receiver(dev)
        return

    dev = find_device(receivers, device_name)
    assert dev
    _print_device(dev)
