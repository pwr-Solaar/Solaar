## Copyright (C) 2012-2013  Daniel Pavel
## Copyright (C) 2014-2024  Solaar Contributors https://pwr-solaar.github.io/Solaar/
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

import errno as _errno
import logging
import subprocess
import time

from collections import namedtuple
from functools import partial

import gi
import logitech_receiver.device as _device
import logitech_receiver.receiver as _receiver

from logitech_receiver import base as _base
from logitech_receiver import exceptions
from logitech_receiver import hidpp10_constants as _hidpp10_constants
from logitech_receiver import listener as _listener
from logitech_receiver import notifications as _notifications

from . import configuration
from . import dbus
from . import i18n

gi.require_version("Gtk", "3.0")  # NOQA: E402
from gi.repository import GLib  # NOQA: E402 # isort:skip

logger = logging.getLogger(__name__)

_R = _hidpp10_constants.REGISTERS
_IR = _hidpp10_constants.INFO_SUBREGISTERS


_GHOST_DEVICE = namedtuple("_GHOST_DEVICE", ("receiver", "number", "name", "kind", "online"))
_GHOST_DEVICE.__bool__ = lambda self: False
_GHOST_DEVICE.__nonzero__ = _GHOST_DEVICE.__bool__


def _ghost(device):
    return _GHOST_DEVICE(receiver=device.receiver, number=device.number, name=device.name, kind=device.kind, online=False)


class SolaarListener(_listener.EventsListener):
    """Keeps the status of a Receiver or Device (member name is receiver but it can also be a device)."""

    def __init__(self, receiver, status_changed_callback):
        assert status_changed_callback
        super().__init__(receiver, self._notifications_handler)
        self.status_changed_callback = status_changed_callback
        receiver.status_callback = self._status_changed

    def has_started(self):
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: notifications listener has started (%s)", self.receiver, self.receiver.handle)
        nfs = self.receiver.enable_connection_notifications()
        if logger.isEnabledFor(logging.WARNING):
            if not self.receiver.isDevice and not ((nfs if nfs else 0) & _hidpp10_constants.NOTIFICATION_FLAG.wireless):
                logger.warning(
                    "Receiver on %s might not support connection notifications, GUI might not show its devices",
                    self.receiver.path,
                )
        self.receiver.notification_flags = nfs
        self.receiver.notify_devices()
        self._status_changed(self.receiver)

    def has_stopped(self):
        r, self.receiver = self.receiver, None
        assert r is not None
        if logger.isEnabledFor(logging.INFO):
            logger.info("%s: notifications listener has stopped", r)

        # because udev is not notifying us about device removal, make sure to clean up in _all_listeners
        _all_listeners.pop(r.path, None)

        # this causes problems but what is it doing (pfps) - r.status = _('The receiver was unplugged.')
        if r:
            try:
                r.close()
            except Exception:
                logger.exception(f"closing receiver {r.path}")
        self.status_changed_callback(r)

    def _status_changed(self, device, alert=None, reason=None):
        assert device is not None
        if logger.isEnabledFor(logging.INFO):
            try:
                if device.kind is None:
                    logger.info(
                        "status_changed %r: %s (%X) %s",
                        device,
                        "present" if bool(device) else "removed",
                        alert if alert is not None else 0,
                        reason or "",
                    )
                else:
                    device.ping()
                    logger.info(
                        "status_changed %r: %s %s (%X) %s",
                        device,
                        "paired" if bool(device) else "unpaired",
                        "online" if device.online else "offline",
                        alert if alert is not None else 0,
                        reason or "",
                    )
            except Exception as e:
                logger.info("status_changed for unknown device: %s", e)

        if device.kind is None:
            assert device == self.receiver
            # the status of the receiver changed
            self.status_changed_callback(device, alert, reason)
            return

        # not true for wired devices - assert device.receiver == self.receiver
        if not device:
            # Device was unpaired, and isn't valid anymore.
            # We replace it with a ghost so that the UI has something to work with while cleaning up.
            if logger.isEnabledFor(logging.INFO):
                logger.info("device %s was unpaired, ghosting", device)
            device = _ghost(device)

        self.status_changed_callback(device, alert, reason)

        if not device:
            # the device was just unpaired, need to update the status of the receiver as well
            self.status_changed_callback(self.receiver)

    def _notifications_handler(self, n):
        assert self.receiver
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug("%s: handling %s", self.receiver, n)
        if n.devnumber == 0xFF:
            # a receiver notification
            _notifications.process(self.receiver, n)
            return

        # a notification that came in to the device listener - strange, but nothing needs to be done here
        if self.receiver.isDevice:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Notification %s via device %s being ignored.", n, self.receiver)
            return

        # DJ pairing notification - ignore - hid++ 1.0 pairing notification is all that is needed
        if n.sub_id == 0x41 and n.report_id == _base.DJ_MESSAGE_ID:
            if logger.isEnabledFor(logging.INFO):
                logger.info("ignoring DJ pairing notification %s", n)
            return

        # a device notification
        if not (0 < n.devnumber <= 16):  # some receivers have devices past their max # devices
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Unexpected device number (%s) in notification %s.", n.devnumber, n)
            return
        already_known = n.devnumber in self.receiver

        # FIXME: hacky fix for kernel/hardware race condition
        # If the device was just turned on or woken up from sleep, it may not be ready to receive commands.
        # The "payload" bit of the wireless tatus notification seems to tell us this. If this is the case, we
        # must wait a short amount of time to avoid causing a broken pipe error.
        device_ready = not bool(ord(n.data[0:1]) & 0x80) or n.sub_id != 0x41
        if not device_ready:
            time.sleep(0.01)

        if n.sub_id == 0x40 and not already_known:
            return  # disconnecting something that is not known - nothing to do

        if n.sub_id == 0x41:
            if not already_known:
                if n.address == 0x0A and not self.receiver.receiver_kind == "bolt":
                    # some Nanos send a notification even if no new pairing - check that there really is a device there
                    if self.receiver.read_register(_R.receiver_info, _IR.pairing_information + n.devnumber - 1) is None:
                        return
                dev = self.receiver.register_new_device(n.devnumber, n)
            elif self.receiver.pairing.lock_open and self.receiver.re_pairs and not ord(n.data[0:1]) & 0x40:
                dev = self.receiver[n.devnumber]
                del self.receiver[n.devnumber]  # get rid of information on device re-paired away
                self._status_changed(dev)  # signal that this device has changed
                dev = self.receiver.register_new_device(n.devnumber, n)
                self.receiver.pairing.new_device = self.receiver[n.devnumber]
            else:
                dev = self.receiver[n.devnumber]
        else:
            dev = self.receiver[n.devnumber]

        if not dev:
            logger.warning("%s: received %s for invalid device %d: %r", self.receiver, n, n.devnumber, dev)
            return

        # Apply settings every time the device connects
        if n.sub_id == 0x41:
            if logger.isEnabledFor(logging.INFO):
                try:
                    dev.ping()
                    logger.info("connection %s for %r", n, dev)
                except Exception:
                    logger.info("connection %s for unknown device, number %s", n, n.devnumber)
            # If there are saved configs, bring the device's settings up-to-date.
            # They will be applied when the device is marked as online.
            configuration.attach_to(dev)
            dev.status_callback = self._status_changed
            # the receiver changed status as well
            self._status_changed(self.receiver)

        _notifications.process(dev, n)

        if self.receiver.pairing.lock_open and not already_known:
            # this should be the first notification after a device was paired
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("first notification was not a connection notification")
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s: pairing detected new device", self.receiver)
            self.receiver.pairing.new_device = dev
        elif dev.online is None:
            dev.ping()

    def __str__(self):
        return f"<SolaarListener({self.receiver.path},{self.receiver.handle})>"


def _process_bluez_dbus(device, path, dictionary, signature):
    """Process bluez dbus property changed signals for device status changes to discover disconnections and connections"""
    if device:
        if dictionary.get("Connected") is not None:
            connected = dictionary.get("Connected")
            if logger.isEnabledFor(logging.INFO):
                logger.info("bluez dbus for %s: %s", device, "CONNECTED" if connected else "DISCONNECTED")
            device.changed(connected, reason=i18n._("connected") if connected else i18n._("disconnected"))
    elif device is not None:
        if logger.isEnabledFor(logging.INFO):
            logger.info("bluez cleanup for %s", device)
        _cleanup_bluez_dbus(device)


def _cleanup_bluez_dbus(device):
    """Remove dbus signal receiver for device"""
    if logger.isEnabledFor(logging.INFO):
        logger.info("bluez cleanup for %s", device)
    dbus.watch_bluez_connect(device.hid_serial, None)


_all_listeners = {}  # all known receiver listeners, listeners that stop on their own may remain here


def _start(device_info):
    assert _status_callback and _setting_callback
    isDevice = device_info.isDevice
    if not isDevice:
        receiver = _receiver.ReceiverFactory.create_receiver(device_info, _setting_callback)
    else:
        receiver = _device.DeviceFactory.create_device(device_info, _setting_callback)
        if receiver:
            configuration.attach_to(receiver)
            if receiver.bluetooth and receiver.hid_serial:
                dbus.watch_bluez_connect(receiver.hid_serial, partial(_process_bluez_dbus, receiver))
                receiver.cleanups.append(_cleanup_bluez_dbus)

    if receiver:
        rl = SolaarListener(receiver, _status_callback)
        rl.start()
        _all_listeners[device_info.path] = rl
        return rl

    logger.warning("failed to open %s", device_info)


def start_all():
    stop_all()  # just in case this it called twice in a row...
    if logger.isEnabledFor(logging.INFO):
        logger.info("starting receiver listening threads")
    for device_info in _base.receivers_and_devices():
        _process_receiver_event("add", device_info)


def stop_all():
    listeners = list(_all_listeners.values())
    _all_listeners.clear()
    if listeners:
        if logger.isEnabledFor(logging.INFO):
            logger.info("stopping receiver listening threads %s", listeners)
        for listener_thread in listeners:
            listener_thread.stop()
    configuration.save()
    if listeners:
        for listener_thread in listeners:
            listener_thread.join()


# after a resume, the device may have been off so mark its saved status to ensure
# that the status is pushed to the device when it comes back
def ping_all(resuming=False):
    if logger.isEnabledFor(logging.INFO):
        logger.info("ping all devices%s", " when resuming" if resuming else "")
    for listener_thread in _all_listeners.values():
        if listener_thread.receiver.isDevice:
            if resuming:
                listener_thread.receiver._active = None  # ensure that settings are pushed
            if listener_thread.receiver.ping():
                listener_thread.receiver.changed(active=True, push=True)
            listener_thread._status_changed(listener_thread.receiver)
        else:
            count = listener_thread.receiver.count()
            if count:
                for dev in listener_thread.receiver:
                    if resuming:
                        dev._active = None  # ensure that settings are pushed
                    if dev.ping():
                        dev.changed(active=True, push=True)
                    listener_thread._status_changed(dev)
                    count -= 1
                    if not count:
                        break


_status_callback = None  # GUI callback to change UI in response to changes to receiver or device status
_setting_callback = None  # GUI callback to change UI in response to changes to status
_error_callback = None  # GUI callback to report errors


def setup_scanner(status_changed_callback, setting_changed_callback, error_callback):
    global _status_callback, _error_callback, _setting_callback
    assert _status_callback is None, "scanner was already set-up"
    _status_callback = status_changed_callback
    _setting_callback = setting_changed_callback
    _error_callback = error_callback
    _base.notify_on_receivers_glib(_process_receiver_event)


def _process_add(device_info, retry):
    try:
        _start(device_info)
    except OSError as e:
        if e.errno == _errno.EACCES:
            try:
                output = subprocess.check_output(["/usr/bin/getfacl", "-p", device_info.path], text=True)
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("Missing permissions on %s\n%s.", device_info.path, output)
            except Exception:
                pass
            if retry:
                GLib.timeout_add(2000.0, _process_add, device_info, retry - 1)
            else:
                _error_callback("permissions", device_info.path)
        else:
            _error_callback("nodevice", device_info.path)
    except exceptions.NoReceiver:
        _error_callback("nodevice", device_info.path)


# receiver add/remove events will start/stop listener threads
def _process_receiver_event(action, device_info):
    assert action is not None
    assert device_info is not None
    assert _error_callback
    if logger.isEnabledFor(logging.INFO):
        logger.info("receiver event %s %s", action, device_info)
    # whatever the action, stop any previous receivers at this path
    listener_thread = _all_listeners.pop(device_info.path, None)
    if listener_thread is not None:
        assert isinstance(listener_thread, SolaarListener)
        listener_thread.stop()
    if action == "add":
        _process_add(device_info, 3)
    return False
