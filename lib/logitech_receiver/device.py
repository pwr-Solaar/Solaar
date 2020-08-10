from __future__ import absolute_import, division, print_function, unicode_literals

from logging import INFO as _INFO
from logging import getLogger

import hidapi as _hid

from . import base as _base
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import strhex as _strhex
from .descriptors import DEVICES as _DESCRIPTORS
from .i18n import _
from .settings_templates import check_feature_settings as _check_feature_settings

_log = getLogger(__name__)
del getLogger

_R = _hidpp10.REGISTERS

#
#
#


class Device(object):

    read_register = _hidpp10.read_register
    write_register = _hidpp10.write_register

    def __init__(self, receiver, number, link_notification=None, info=None):
        assert receiver or info
        self.receiver = receiver

        if receiver:
            assert number > 0 and number <= receiver.max_devices
        else:
            assert number == 0
        # Device number, 1..6 for unifying devices, 1 otherwise.
        self.number = number
        # 'device active' flag; requires manual management.
        self.online = None

        # the Wireless PID is unique per device model
        self.wpid = None
        self.descriptor = None

        # mouse, keyboard, etc (see _hidpp10.DEVICE_KIND)
        self._kind = None
        # Unifying peripherals report a codename.
        self._codename = None
        # the full name of the model
        self._name = None
        # HID++ protocol version, 1.0 or 2.0
        self._protocol = None
        # serial number (an 8-char hex string)
        self._serial = None

        self._firmware = None
        self._keys = None
        self._registers = None
        self._settings = None
        self._feature_settings_checked = False

        # Misc stuff that's irrelevant to any functionality, but may be
        # displayed in the UI and caching it here helps.
        self._polling_rate = None
        self._power_switch = None

        self.handle = None
        self.path = None
        self.product_id = None

        # if _log.isEnabledFor(_DEBUG):
        #     _log.debug("new Device(%s, %s, %s)", receiver, number, link_notification)

        if receiver:
            if link_notification is not None:
                self.online = not bool(ord(link_notification.data[0:1]) & 0x40)
                self.wpid = _strhex(link_notification.data[2:3] + link_notification.data[1:2])
                # assert link_notification.address == (0x04
                # if unifying else 0x03)
                kind = ord(link_notification.data[0:1]) & 0x0F
                # fix EX100 wpid
                if receiver.ex100_wpid_fix:  # EX100 receiver
                    self.wpid = _strhex(link_notification.data[2:3]) + '00'
                    # workaround for EX100 switched kind
                    if self.wpid == '3F00':
                        kind = 2
                    if self.wpid == '6500':
                        kind = 1
                self._kind = _hidpp10.DEVICE_KIND[kind]
            else:
                # force a reading of the wpid
                pair_info = self.receiver.read_register(_R.receiver_info, 0x20 + number - 1)
                if pair_info:
                    # may be either a Unifying receiver, or an Unifying-ready
                    # receiver
                    self.wpid = _strhex(pair_info[3:5])
                    kind = ord(pair_info[7:8]) & 0x0F
                    self._kind = _hidpp10.DEVICE_KIND[kind]
                elif receiver.ex100_wpid_fix:
                    # ex100 receiver, fill fake device_info with known wpid's
                    # accordingly to drivers/hid/hid-logitech-dj.c
                    # index 1 or 2 always mouse, index 3 always the keyboard,
                    # index 4 is used for an optional separate numpad
                    if number == 1:  # mouse
                        self.wpid = '3F00'
                        self._kind = _hidpp10.DEVICE_KIND[2]
                    elif number == 3:  # keyboard
                        self.wpid = '6500'
                        self._kind = _hidpp10.DEVICE_KIND[1]
                    else:  # unknown device number on EX100
                        _log.error('failed to set fake EX100 wpid for device %d of %s', number, receiver)
                        raise _base.NoSuchDevice(number=number, receiver=receiver, error='Unknown EX100 device')
                else:
                    # unifying protocol not supported, must be a Nano receiver
                    device_info = self.receiver.read_register(_R.receiver_info, 0x04)
                    if device_info is None:
                        _log.error('failed to read Nano wpid for device %d of %s', number, receiver)
                        raise _base.NoSuchDevice(number=number, receiver=receiver, error='read Nano wpid')

                    self.wpid = _strhex(device_info[3:5])
                    self._power_switch = '(' + _('unknown') + ')'

            # the wpid is necessary to properly identify wireless link on/off
            # notifications also it gets set to None on this object when the
            # device is unpaired
            assert self.wpid is not None, 'failed to read wpid: device %d of %s' % (number, receiver)

            serial = self.serial
            for dev in _hid.enumerate({
                'vendor_id': 0x046d,
                'product_id': int(self.receiver.product_id, 16),
                'usb_interface': 2
            }):
                self.handle = _hid.open_path(dev.path)
                if serial == self.serial and dev.serial.startswith(self.wpid):
                    self.path = dev.path
                    break
                else:
                    _hid.close(self.handle)
                    self.handle = None

            self.descriptor = _DESCRIPTORS.get(self.wpid)
            if self.descriptor is None:
                # Last chance to correctly identify the device; many Nano
                # receivers do not support this call.
                codename = self.receiver.read_register(_R.receiver_info, 0x40 + self.number - 1)
                if codename:
                    codename_length = ord(codename[1:2])
                    codename = codename[2:2 + codename_length]
                    self._codename = codename.decode('ascii')
                    self.descriptor = _DESCRIPTORS.get(self._codename)

            if self.descriptor:
                self._name = self.descriptor.name
                self._protocol = self.descriptor.protocol
                if self._codename is None:
                    self._codename = self.descriptor.codename
                if self._kind is None:
                    self._kind = self.descriptor.kind
        else:
            self.path = info.path
            self.handle = _hid.open_path(self.path)
            self.product_id = info.product_id

        if self._protocol is not None:
            self.features = None if self._protocol < 2.0 else _hidpp20.FeaturesArray(self)
        else:
            # may be a 2.0 device; if not, it will fix itself later
            self.features = _hidpp20.FeaturesArray(self)

    @property
    def protocol(self):
        if not self._protocol and self.online:
            self._protocol = _base.ping(self.handle or self.receiver.handle, self.number)
            # if the ping failed, the peripheral is (almost) certainly offline
            self.online = self._protocol is not None

            # if _log.isEnabledFor(_DEBUG):
            #     _log.debug("device %d protocol %s", self.number, self._protocol)
        return self._protocol or 0

    @property
    def codename(self):
        if not self._codename:
            codename = self.receiver.read_register(_R.receiver_info, 0x40 + self.number - 1) if self.receiver else None
            if codename:
                codename_length = ord(codename[1:2])
                codename = codename[2:2 + codename_length]
                self._codename = codename.decode('ascii')
                # if _log.isEnabledFor(_DEBUG):
                #     _log.debug("device %d codename %s", self.number, self._codename)
            else:
                self._codename = '? (%s)' % self.wpid
        return self._codename

    @property
    def name(self):
        if not self._name:
            if self.online and self.protocol >= 2.0:
                self._name = _hidpp20.get_name(self)
        return self._name or self.codename or ('Unknown device %s' % self.wpid)

    @property
    def kind(self):
        if not self._kind:
            pair_info = self.receiver.read_register(_R.receiver_info, 0x20 + self.number - 1) if self.receiver else None
            if pair_info:
                kind = ord(pair_info[7:8]) & 0x0F
                self._kind = _hidpp10.DEVICE_KIND[kind]
            elif self.online and self.protocol >= 2.0:
                self._kind = _hidpp20.get_kind(self)
        return self._kind or '?'

    @property
    def firmware(self):
        if self._firmware is None and self.online:
            if self.protocol >= 2.0:
                self._firmware = _hidpp20.get_firmware(self)
            else:
                self._firmware = _hidpp10.get_firmware(self)
        return self._firmware or ()

    @property
    def serial(self):
        if self.receiver:
            serial = self.receiver.read_register(_R.receiver_info, 0x30 + self.number - 1)
            if serial:
                ps = ord(serial[9:10]) & 0x0F
                self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps]
            else:
                # some Nano receivers?
                serial = self.receiver.read_register(0x2D5)

            if serial:
                self._serial = _strhex(serial[1:5])
            else:
                # fallback...
                self._serial = self.receiver.serial
        return self._serial or '?'

    @property
    def power_switch_location(self):
        if not self._power_switch and self.receiver:
            ps = self.receiver.read_register(_R.receiver_info, 0x30 + self.number - 1)
            if ps:
                ps = ord(ps[9:10]) & 0x0F
                self._power_switch = _hidpp10.POWER_SWITCH_LOCATION[ps]
            else:
                self._power_switch = '(unknown)'
        return self._power_switch

    @property
    def polling_rate(self):
        if not self._polling_rate and self.receiver:
            pair_info = self.receiver.read_register(_R.receiver_info, 0x20 + self.number - 1)
            if pair_info:
                self._polling_rate = ord(pair_info[2:3])
            else:
                self._polling_rate = 0
        if self.online and self.protocol >= 2.0 and self.features and _hidpp20.FEATURE.REPORT_RATE in self.features:
            rate = _hidpp20.get_polling_rate(self)
            self._polling_rate = rate if rate else self._polling_rate
        return self._polling_rate

    @property
    def keys(self):
        if not self._keys:
            if self.online and self.protocol >= 2.0:
                self._keys = _hidpp20.get_keys(self) or ()
        return self._keys

    @property
    def registers(self):
        if not self._registers:
            if self.descriptor and self.descriptor.registers:
                self._registers = list(self.descriptor.registers)
            else:
                self._registers = []
        return self._registers

    @property
    def settings(self):
        if self._settings is None:
            self._settings = []
            if self.descriptor and self.descriptor.settings:
                self._settings = []
                for s in self.descriptor.settings:
                    try:
                        setting = s(self)
                    except Exception as e: # Do nothing if the device is offline
                        setting = None
                        if self.online:
                            raise e
                    if setting is not None:
                        self._settings.append(setting)
        if not self._feature_settings_checked:
            self._feature_settings_checked = _check_feature_settings(self, self._settings)
        return self._settings

    def enable_notifications(self, enable=True):
        """Enable or disable device (dis)connection notifications on this
        receiver."""
        if not bool(self.receiver) or self.protocol >= 2.0:
            return False

        if enable:
            set_flag_bits = (
                _hidpp10.NOTIFICATION_FLAG.battery_status
                | _hidpp10.NOTIFICATION_FLAG.keyboard_illumination
                | _hidpp10.NOTIFICATION_FLAG.wireless
                | _hidpp10.NOTIFICATION_FLAG.software_present
            )
        else:
            set_flag_bits = 0
        ok = _hidpp10.set_notification_flags(self, set_flag_bits)
        if not ok:
            _log.warn('%s: failed to %s device notifications', self, 'enable' if enable else 'disable')

        flag_bits = _hidpp10.get_notification_flags(self)
        flag_names = None if flag_bits is None else tuple(_hidpp10.NOTIFICATION_FLAG.flag_names(flag_bits))
        if _log.isEnabledFor(_INFO):
            _log.info('%s: device notifications %s %s', self, 'enabled' if enable else 'disabled', flag_names)
        return flag_bits if ok else None

    def request(self, request_id, *params, no_reply=False):
        return _base.request(self.handle or self.receiver.handle, self.number, request_id, *params, no_reply=no_reply)

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        if self.protocol >= 2.0:
            return _hidpp20.feature_request(self, feature, function, *params, no_reply=no_reply)

    def ping(self):
        """Checks if the device is online, returns True of False"""
        protocol = _base.ping(self.handle or self.receiver.handle, self.number)
        self.online = protocol is not None
        if protocol:
            self._protocol = protocol
        return self.online

    def __index__(self):
        return self.number

    __int__ = __index__

    def __eq__(self, other):
        return other is not None and self.kind == other.kind and self.wpid == other.wpid

    def __ne__(self, other):
        return other is None or self.kind != other.kind or self.wpid != other.wpid

    def __hash__(self):
        return self.wpid.__hash__()

    __bool__ = __nonzero__ = lambda self: self.wpid is not None and self.number in self.receiver

    def __str__(self):
        return '<Device(%d,%s,%s,%s)>' % (
            self.number, self.wpid or self.product_id, self.name or self.codename or '?', self.serial
        )

    __unicode__ = __repr__ = __str__
