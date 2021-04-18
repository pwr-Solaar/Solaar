---
title: Solaar Capabilities
layout: page
---

# Solaar Capabilities

[**Solaar**][solaar] reports on and controls [Logitech][logitech] devices
(keyboards, mice, and trackballs) that connect to your computer via a
Logitech USB receiver (a very small piece of hardware that plugs into one of
your USB ports).
Solaar is designed to detect all connected devices,
and at the very least display some basic information about them.
At this moment, all [Unifying][unifying] receivers are supported (e.g., devices
with USB ID `046d:c52b` or `046d:c532`) as are several Lightspeed Receivers
and many Nano receivers.

Solaar also reports on and controls some Logitech devices that directly connect
to your computer using a USB cable or via Bluetooth.
Not all such devices supported in Solaar as information needs to be added to Solaar
for each device type that directly connects.


## HID++

The devices that Solaar handles use Logitech's HID++ protocol.

HID++ is a Logitech-proprietary protocol that extends the standard HID
protocol for interfacing with receivers, keyboards, mice, and so on. It allows
Logitech receivers to communicate with multiple devices and modify some
features of the device. As the HID++ protocol is
proprietary, many aspects of it are unknown. Some information about HID++
has been obtained from Logitech but even that is subject to change and
extension.

There are several versions of HID++ and many Logitech
receivers and devices that utilize it. Different receivers and devices
implement different portions of HID++ so even if two devices appear to be
the same in both physical appearance and behavior they may work
differently underneath. (For example, there are versions of the
M510 mouse that use different versions of the HID++ protocol.)
Contrariwise, two different devices may appear different physically but
actually look the same to software. (For example, some M185 mice look the
same to software as some M310 mice.)

The software identity of a receiver can be determined by its USB product ID
(reported by Solaar and also viewable in Linux using `lsusb`). The software
identity of a device that connects to a receiver can be determined by
its wireless PID as reported by Solaar.  The software identity of devices that
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


## Supported Features

Solaar uses the HID++ protocol to pair devices to receivers and unpair
devices from receivers, and also uses the HID++ protocol to display
features of receivers and devices. Currently it only displays some
features, and can modify even fewer. For a list of HID++ features
and their support see [the features page](features).

Solaar does not do much beyond using the HID++ protocol to change the
behavior of receivers and devices via changing their settings.
In particular, Solaar cannot change how
the operating system turns the keycodes that a keyboard produces into
characters that are sent to programs. That is the province of HID device
drivers and other software (such as X11).

Settings can only be changed in the Solaar GUI when they are unlocked.
To unlock a setting click on the icon at the right-hand edge of the setting
until an unlocked lock appears (with tooltop "Changes allowed").

Solaar keep tracks of the changeable settings of a device.
Most devices forget changed settings when the are turned off
or go into a power-saving mode.  When Solaar starts, it restores on-line
devices to their previously-known state, and while running it restores
devices to their previously-known state when the device itself comes on line.
This information is stored in the file `~/.config/solaar/config.json`.

Updating of settings can be turned off in the Solaar GUI by clicking on the icon
at the right-hand edge of the setting until a red icon appears (with tooltip
"Ignore this setting" ).

Solaar keeps track of settings independently on each computer.
As a result if a device is switched between different computers
Solaar may apply different settings for it on the different computers

Querying a device for its current state can require quite a few HID++
interactions. These interactions can temporarily slow down the device, so
Solaar tries to internally cache information about devices while it is
running.  If the device
state is changed by some other means, even sometimes by another invocation
of Solaar, this cached information may become incorrect. Currently there is
no way to force an update of the cached information besides restarting Solaar.

Logitech receivers and devices have firmware in them. Some firmware
can be updated using Logitech software in Windows. For example, there are
security issues with some Logitech receivers and devices and Logitech has
firmware updates to alleviate these problems. Some Logitech firmware can
also be updated in Linux using `fwupdmgr`.
WARNING: Updating firmware can cause a piece of hardware to become
permanently non-functional if something goes wrong with the update or the
update installs the wrong firmware.

## Other Solaar Capabilities

Solaar has a few capabilities that go beyond simply changing device settings.

### Rule-based Processing of HID++ Notifications

Solaar can process HID++ Notifications from devices to, for example,
change the speed of some thumb wheels.  These notifications are only sent
for actions that are set in Solaar to their HID++ setting (also known as diverted).
For more information on this capability of Solaar see
[the rules page](https://pwr-solaar.github.io/Solaar/rules).  As much of rule processing
depends on X11, this capability is only when running under X11.

Users can edit rules using a GUI by clicking on the `Edit Rule` button in the Solaar main window.

Solaar rules is an experimental feature.  Significant changes might be made in response to problems.

### Sliding DPI

A few mice (such as the MX Vertical) have a button that is supposed to be used to change
the sensitivity (DPI) of the mouse by pressing the button and moving the mouse left and right.
Other mice (such as the MX Master 3) don't have a button specific for this purpose
but have buttons that can be used for it.

The DPI Sliding Adjustment setting assigns a button for this purpose.
Pressing the button, if the button is diverted, causes the mouse pointer to stop moving.
When the button is released a new Sensitivity (DPI) value is applied to the mouse,
depending on how far right or left the mouse is moved.   If the mouse is moved only a little bit
the previous value that was set is applied to the mouse.
Notifications from Solaar are displayed while the mouse button is done
showing the setting that will be applied.


### Mouse Gestures

Some mice (such as the MX Master 3) have a button that is supposed to be used to
create up/down/left/right mouse gestures.  Other mice (such as the MX Vertical) don't
have a button specific for this purpose but have buttons that can be used for it.

The Mouse Gestures setting assigns a button for this purpose.
Pressing the button, if the button is diverted, causes the mouse pointer to stop moving.
When the button is released a MOUSE_GESTURE notification with the total mouse movement
while the button was pressed is sent to the Solaar rule system.

Mouse gestures is an experimental feature.
Significant changes might be made to it in the future.


## System Tray

Solaar's GUI normally uses an icon in the system tray.
This allows users to close Solaar and reopen from the tray.
This aspect of Solaar depends on having an active system tray which may
require some special setup when using Gnome, particularly under Wayland.

If you are running gnome, you most likely need the
`gnome-shell-extension-appindicator` package installed.
In Fedora, this can be done by running
```
sudo dnf install gnome-shell-extension-appindicator
```
The likely command in Ubuntu and related distributions is
```
sudo apt install gnome-shell-extension-appindicator
```
You may have to log out and log in again before the system tray shows up.


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
