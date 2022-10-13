import errno as _errno
import threading as _threading

from logging import INFO as _INFO
from logging import getLogger
from typing import Optional

import hidapi as _hid
import solaar.configuration as _configuration

from . import base as _base
from . import descriptors as _descriptors
from . import hidpp10 as _hidpp10
from . import hidpp20 as _hidpp20
from .common import strhex as _strhex
from .settings_templates import check_feature_settings as _check_feature_settings

_log = getLogger(__name__)
del getLogger

_R = _hidpp10.REGISTERS
_IR = _hidpp10.INFO_SUBREGISTERS

KIND_MAP = {kind: _hidpp10.DEVICE_KIND[str(kind)] for kind in _hidpp20.DEVICE_KIND}

#
#
#


class Device:
    instances = []
    read_register = _hidpp10.read_register
    write_register = _hidpp10.write_register

    def __init__(self, receiver, number, link_notification=None, info=None, path=None, handle=None):
        assert receiver or info
        Device.instances.append(self)
        self.receiver = receiver
        self.may_unpair = False
        self.isDevice = True  # some devices act as receiver so we need a property to distinguish them
        self.path = path
        self.handle = handle
        self.product_id = None
        self.hidpp_short = info.hidpp_short if info else None
        self.hidpp_long = info.hidpp_long if info else None

        if receiver:
            assert number > 0 and number <= 15  # some receivers have devices past their max # of devices
        self.number = number  # will be None at this point for directly connected devices
        # 'device active' flag; requires manual management.
        self.online = None

        # the Wireless PID is unique per device model
        self.wpid = None
        self.descriptor = None
        # Bluetooth connections need long messages
        self.bluetooth = False
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
        # unit id (distinguishes within a model - the same as serial)
        self._unitId = None
        # model id (contains identifiers for the transports of the device)
        self._modelId = None
        # map from transports to product identifiers
        self._tid_map = None
        # persister holds settings
        self._persister = None

        self._firmware = None
        self._keys = None
        self._remap_keys = None
        self._gestures = None
        self._gestures_lock = _threading.Lock()
        self._registers = None
        self._settings = None
        self._feature_settings_checked = False
        self._settings_lock = _threading.Lock()

        # Misc stuff that's irrelevant to any functionality, but may be
        # displayed in the UI and caching it here helps.
        self._polling_rate = None
        self._power_switch = None

        # See `add_notification_handler`
        self._notification_handlers = {}

        # if _log.isEnabledFor(_DEBUG):
        #     _log.debug("new Device(%s, %s, %s)", receiver, number, link_notification)

        if not self.path:
            self.path = _hid.find_paired_node(receiver.path, number, 1) if receiver else info.path
        if not self.handle:
            try:
                self.handle = _base.open_path(self.path) if self.path else None
            except Exception:  # maybe the device wasn't set up
                try:
                    import time
                    time.sleep(1)
                    self.handle = _base.open_path(self.path) if self.path else None
                except Exception:  # give up
                    self.handle = None

        if receiver:
            if link_notification is not None:
                self.online = not bool(ord(link_notification.data[0:1]) & 0x40)
                self.wpid = _strhex(link_notification.data[2:3] + link_notification.data[1:2])
                # assert link_notification.address == (0x04 if unifying else 0x03)
                kind = ord(link_notification.data[0:1]) & 0x0F
                # get 27Mhz wpid and set kind based on index
                if receiver.receiver_kind == '27Mhz':  # 27 Mhz receiver
                    self.wpid = '00' + _strhex(link_notification.data[2:3])
                    kind = self.get_kind_from_index(number, receiver)
                self._kind = _hidpp10.DEVICE_KIND[kind]
            else:
                # Not a notification, force a reading of pairing information
                self.online = True
                self.update_pairing_information()
                self.update_extended_pairing_information()
                if not self.wpid and not self._serial:  # if neither then the device almost certainly wasn't found
                    raise _base.NoSuchDevice(number=number, receiver=receiver, error='no wpid or serial')

            # the wpid is set to None on this object when the device is unpaired
            assert self.wpid is not None, 'failed to read wpid: device %d of %s' % (number, receiver)

            self.descriptor = _descriptors.get_wpid(self.wpid)
            if self.descriptor is None:
                # Last chance to correctly identify the device; many Nano receivers do not support this call.
                codename = self.receiver.device_codename(self.number)
                if codename:
                    self._codename = codename
                    self.descriptor = _descriptors.get_codename(self._codename)
        else:
            self.online = None  # a direct connected device might not be online (as reported by user)
            self.product_id = info.product_id
            self.bluetooth = info.bus_id == 0x0005
            self.descriptor = _descriptors.get_btid(self.product_id) if self.bluetooth else \
                _descriptors.get_usbid(self.product_id)
            if self.number is None:  # for direct-connected devices get 'number' from descriptor protocol else use 0xFF
                self.number = 0x00 if self.descriptor and self.descriptor.protocol and self.descriptor.protocol < 2.0 else 0xFF

        if self.descriptor:
            self._name = self.descriptor.name
            if self.descriptor.protocol:
                self._protocol = self.descriptor.protocol
            if self._codename is None:
                self._codename = self.descriptor.codename
            if self._kind is None:
                self._kind = self.descriptor.kind

        if self._protocol is not None:
            self.features = None if self._protocol < 2.0 else _hidpp20.FeaturesArray(self)
        else:
            # may be a 2.0 device; if not, it will fix itself later
            self.features = _hidpp20.FeaturesArray(self)

    @classmethod
    def find(self, serial):
        assert serial, 'need serial number or unit ID to find a device'
        result = None
        for device in Device.instances:
            if device.online and (device.unitId == serial or device.serial == serial):
                result = device
        return result

    @property
    def protocol(self):
        if not self._protocol and self.online:
            self._protocol = _base.ping(
                self.handle or self.receiver.handle, self.number, long_message=self.bluetooth or self.hidpp_short is False
            )
            # if the ping failed, the peripheral is (almost) certainly offline
            self.online = self._protocol is not None

            # if _log.isEnabledFor(_DEBUG):
            #     _log.debug("device %d protocol %s", self.number, self._protocol)
        return self._protocol or 0

    @property
    def codename(self):
        if not self._codename:
            if self.online and self.protocol >= 2.0:
                self._codename = _hidpp20.get_friendly_name(self)
                if not self._codename:
                    self._codename = self.name.split(' ', 1)[0] if self.name else None
            elif self.receiver:
                codename = self.receiver.device_codename(self.number)
                if codename:
                    self._codename = codename
                elif self.protocol < 2.0:
                    self._codename = '? (%s)' % (self.wpid or self.product_id)
        return self._codename if self._codename else '?? (%s)' % (self.wpid or self.product_id)

    @property
    def name(self):
        if not self._name:
            if self.online and self.protocol >= 2.0:
                self._name = _hidpp20.get_name(self)
        return self._name or self._codename or ('Unknown device %s' % (self.wpid or self.product_id))

    def get_ids(self):
        ids = _hidpp20.get_ids(self)
        if ids:
            self._unitId, self._modelId, self._tid_map = ids
            if _log.isEnabledFor(_INFO) and self._serial and self._serial != self._unitId:
                _log.info('%s: unitId %s does not match serial %s', self, self._unitId, self._serial)

    @property
    def unitId(self):
        if not self._unitId and self.online and self.protocol >= 2.0:
            self.get_ids()
        return self._unitId

    @property
    def modelId(self):
        if not self._modelId and self.online and self.protocol >= 2.0:
            self.get_ids()
        return self._modelId

    @property
    def tid_map(self):
        if not self._tid_map and self.online and self.protocol >= 2.0:
            self.get_ids()
        return self._tid_map

    def update_pairing_information(self):
        if self.receiver and (not self.wpid or self._kind is None or self._polling_rate is None):
            wpid, kind, polling_rate = self.receiver.device_pairing_information(self.number)
            if not self.wpid:
                self.wpid = wpid
            if not self._kind:
                self._kind = kind
            if not self._polling_rate:
                self._polling_rate = polling_rate

    def update_extended_pairing_information(self):
        if self.receiver:
            serial, power_switch = self.receiver.device_extended_pairing_information(self.number)
            if not self._serial:
                self._serial = serial
            if not self._power_switch:
                self._power_switch = power_switch

    @property
    def kind(self):
        if not self._kind:
            self.update_pairing_information()
            if not self._kind and self.protocol >= 2.0:
                kind = _hidpp20.get_kind(self)
                self._kind = KIND_MAP[kind] if kind else None
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
        if not self._serial:
            self.update_extended_pairing_information()
        return self._serial or ''

    @property
    def id(self):
        if not self.serial:
            if self.persister and self.persister.get('_serial', None):
                self._serial = self.persister.get('_serial', None)
        return self.unitId or self.serial

    @property
    def power_switch_location(self):
        if not self._power_switch:
            self.update_extended_pairing_information()
        return self._power_switch

    @property
    def polling_rate(self):
        if not self._polling_rate:
            self.update_pairing_information()
        if self.protocol >= 2.0:
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
    def remap_keys(self):
        if self._remap_keys is None:
            if self.online and self.protocol >= 2.0:
                self._remap_keys = _hidpp20.get_remap_keys(self) or ()
        return self._remap_keys

    @property
    def gestures(self):
        if self._gestures is None:
            with self._gestures_lock:
                if self._gestures is None:
                    if self.online and self.protocol >= 2.0:
                        self._gestures = _hidpp20.get_gestures(self) or ()
        return self._gestures

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
        if not self._settings:
            with self._settings_lock:
                if not self._settings:
                    settings = []
                    if self.persister and self.descriptor and self.descriptor.settings:
                        for sclass in self.descriptor.settings:
                            try:
                                setting = sclass.build(self)
                            except Exception as e:  # Do nothing if the device is offline
                                setting = None
                                if self.online:
                                    raise e
                            if setting is not None:
                                settings.append(setting)
                    self._settings = settings
        if not self._feature_settings_checked:
            with self._settings_lock:
                if not self._feature_settings_checked:
                    self._feature_settings_checked = _check_feature_settings(self, self._settings)
        return self._settings

    @property
    def persister(self):
        if not self._persister:
            self._persister = _configuration.persister(self)
        return self._persister

    def battery(self):  # None  or  level, next, status, voltage
        if self.protocol < 2.0:
            return _hidpp10.get_battery(self)
        else:
            battery_feature = self.persister.get('_battery', None) if self.persister else None
            if battery_feature != 0:
                result = _hidpp20.get_battery(self, battery_feature)
                try:
                    feature, level, next, status, voltage = result
                    if self.persister and battery_feature is None:
                        self.persister['_battery'] = feature
                    return level, next, status, voltage
                except Exception:
                    if self.persister and battery_feature is None:
                        self.persister['_battery'] = result

    def enable_connection_notifications(self, enable=True):
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

    def add_notification_handler(self, id: str, fn):
        """Adds the notification handling callback `fn` to this device under name `id`.
        If a callback has already been registered under this name, it's replaced with
        the argument.
        The callback will be invoked whenever the device emits an event message, and
        the resulting notification hasn't been handled by another handler on this device
        (order is not guaranteed, so handlers should not overlap in functionality).
        The callback should have type `(PairedDevice, Notification) -> Optional[bool]`.
        It should return `None` if it hasn't handled the notification, return `True`
        if it did so successfully and return `False` if an error should be reported
        (malformed notification, etc).
        """
        self._notification_handlers[id] = fn

    def remove_notification_handler(self, id: str):
        """Unregisters the notification handler under name `id`."""

        if id not in self._notification_handlers and _log.isEnabledFor(_INFO):
            _log.info(f'Tried to remove nonexistent notification handler {id} from device {self}.')
        else:
            del self._notification_handlers[id]

    def handle_notification(self, n) -> Optional[bool]:
        for h in self._notification_handlers.values():
            ret = h(self, n)
            if ret is not None:
                return ret
        return None

    def request(self, request_id, *params, no_reply=False):
        if self:
            return _base.request(
                self.handle or self.receiver.handle,
                self.number,
                request_id,
                *params,
                no_reply=no_reply,
                long_message=self.bluetooth or self.hidpp_short is False or self.protocol >= 2.0,
                protocol=self.protocol
            )

    def feature_request(self, feature, function=0x00, *params, no_reply=False):
        if self.protocol >= 2.0:
            return _hidpp20.feature_request(self, feature, function, *params, no_reply=no_reply)

    def ping(self):
        """Checks if the device is online, returns True of False"""
        long = self.bluetooth or self._protocol is not None and self._protocol >= 2.0
        protocol = _base.ping(self.handle or self.receiver.handle, self.number, long_message=long)
        self.online = protocol is not None
        if protocol:
            self._protocol = protocol
        return self.online

    def __index__(self):
        return self.number

    __int__ = __index__

    def __eq__(self, other):
        return other is not None and self._kind == other._kind and self.wpid == other.wpid

    def __ne__(self, other):
        return other is None or self.kind != other.kind or self.wpid != other.wpid

    def __hash__(self):
        return self.wpid.__hash__()

    def __bool__(self):
        return self.wpid is not None and self.number in self.receiver if self.receiver else self.handle is not None

    __nonzero__ = __bool__

    def __str__(self):
        return '<Device(%d,%s,%s,%s)>' % (
            self.number, self.wpid or self.product_id, self.name or self.codename or '?', self.serial
        )

    __repr__ = __str__

    def notify_devices(self):  # no need to notify, as there are none
        pass

    @classmethod
    def open(self, device_info):
        """Opens a Logitech Device found attached to the machine, by Linux device path.
        :returns: An open file handle for the found receiver, or ``None``.
        """
        try:
            handle = _base.open_path(device_info.path)
            if handle:
                return Device(None, None, info=device_info, handle=handle, path=device_info.path)
        except OSError as e:
            _log.exception('open %s', device_info)
            if e.errno == _errno.EACCES:
                raise
        except Exception:
            _log.exception('open %s', device_info)

    def close(self):
        handle, self.handle = self.handle, None
        if self in Device.instances:
            Device.instances.remove(self)
        return (handle and _base.close(handle))

    def __del__(self):
        self.close()
