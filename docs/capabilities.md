---
title: Solaar Capabilities
layout: page
---

# Solaar capabilities

[**Solaar**][solaar] reports on and controls [Logitech][logitech] devices
(keyboards, mice, and trackballs) that connect to your computer via a
Logitech USB receiver (a very small piece of hardware that plugs into one of
your USB ports).
Solaar is designed to detect all connected devices,
and at the very least display some basic information about them.
At this moment, all [Unifying][unifying] receivers are supported (devices
with USB ID `046d:c52b` or `046d:c532`) as are several Lightspeed Receivers
and a dozen Nano receivers.

Solaar also reports on and controls some Logitech devices that directly connect
to your computer using a USB cable or via Bluetooth.
Not all such devices supported in Solaar as information needs to be added to Solaar
for each device type that directly connects.

Most devices forget changed settings when the are turned off
or go into a power-saving mode.
Solaar keeps track of the settings that it has changed.
The Solaar GUI application notices when devices reconnect and
applies the remembered settings to the device.
This is done independently on each computer that Solaar runs on.
As a result if a device is switched between different computers
Solaar can apply different settings on different computers.

## HID++

The devices that Solaar handles use Logitech's HID++ protocol.

HID++ is a Logitech-proprietary protocol that extends the standard HID
protocol for interfacing with keyboards, mice, and so on. It allows
Logitech receivers to communicate with multiple devices and modify some
features of the device on the device itself. As the HID++ protocol is
proprietary, many aspects of it are unknown. Some information about HID++
has been obtained from Logitech but even that is subject to change and
extension.

There are several versions of the HID++ and many Logitech
receivers and devices that utilize it. Different receivers and devices
implement different portions of HID++ so even if two devices appear to be
the same in both physical appearance and behavior they may work
completely differently underneath. (For example, there are versions of the
M510 mouse that use different versions of the HID++ protocol.)
Contrariwise, two different devices may appear different physically but
actually look the same to software. (For example, some M185 mice look the
same to software as some M310 mice.)

The software identity of a receiver can be determined by its USB product ID
(reported by Solaar and also viewable in Linux using `lsusb`). The software
identity of a device that connects to a receiver can be determined by
its Wireless PID as reported by Solaar.  The software identity of devices that
connect via a USB cable or via bluetooth can be determined by their USB or
Bluetooth product ID.

Even something as fundamental as pairing works differently for different
receivers. For Unifying receivers, pairing adds a new paired device, but
only if there is an open slot on the receiver. So these receivers need to
be able to unpair devices that they have been paired with or else they will
not have any open slots for pairing. Some other receivers, like the
Nano receiver with USB ID `046d:c534`, can only pair with particular kinds of
devices and pairing a new device replaces whatever device of that kind was
previously paired to the receiver. These receivers cannot unpair. Further,
some receivers can pair an unlimited number of times but others can only
pair a limited number of times.

Only some connections between receivers and devices are possible. In should
be possible to connect any device with a Unifying logo on it to any receiver
with a Unifying logo on it. Receivers without the Unifying logo probably
can connect only to the kind of devices they were bought with and devices
without the Unifying logo can probably only connect to the kind of receiver
that they were bought with.

## Supported features

Solaar uses the HID++ protocol to pair devices to receivers and unpair
devices from receivers, and also uses the HID++ protocol to display
features of receivers and devices. Currently it only displays some
features, and can modify even fewer. For a list of HID++ features
and their support see [the features page](features).

Solaar does not do anything beyond using the HID++ protocol to change the
behavior of receivers and devices. In particular, it cannot change how
the operating system turns the keycodes that a keyboard produces into
characters that are sent to programs. That is the province of HID device
drivers and other software (such as X11).

Logitech receivers and devices have firmware in them. Some firmware
can be updated using Logitech software in Windows. For example, there are
security issues with some Logitech receivers and devices and Logitech has
firmware updates to alleviate these problems. Some Logitech firmware can
also be updated in Linux using `fwupdmgr`.
WARNING: Updating firmware can cause a piece of hardware to become
permanently non-functional if something goes wrong with the update or the
update installs the wrong firmware.

Solaar does keep track of some changeable settings of a device between
invocations. When it starts, it restores on-line devices to their
previously-known state, and while running it restores devices to
their previously-known state when the device itself comes on line.
This information is stored in the file `~/.config/solaar/config.json`.

Querying a device for its current state can require quite a few HID++
interactions. These interactions can temporarily slow down the device, so
Solaar tries to internally cache information about devices. If the device
state is changed by some other means, even sometimes by another invocation
of the program, this cached information may become incorrect. Currently there is
no way to force an update of the cached information besides restarting the
program.


## Rule-based Processing of HID++ Feature Notifications

Solaar can process HID++ Feature Notifications from devices to, for example,
change the speed of some thumb wheels.  For more information on this capability of Solaar see
[the rules page](https://pwr-solaar.github.io/Solaar/rules).  As much of rule processing
depends on X11, this capability is only when running under X11.

Users can edit rules using a GUI by clicking on the `Edit Rule` button in the Solaar main window.

Solaar rules is an experimental feature.  Significant changes might be made in response to problems.


## Battery Icons

For many devices, Solaar shows the approximate battery level via icons that
show up in both the main window and the system tray. In previous versions
several heuristics to determine which icon names to use for this purpose,
but as more and more battery icon schemes have been developed this has
become impossible to do well. Solaar now uses the eleven standard
battery icon names `battery-{full,good,low,critical,empty}[-charging]` and
`battery-missing`.

Solaar will use the symbolic versions of these icons if started with the
option `--battery-icons=symbolic`. Because of external bugs,
these symbolic icons may be nearly invisible in dark themes.

[solaar]: https://github.com/pwr-Solaar/Solaar
[logitech]: https://www.logitech.com
[unifying]: https://en.wikipedia.org/wiki/Logitech_Unifying_receiver
