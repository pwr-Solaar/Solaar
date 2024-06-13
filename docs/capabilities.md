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


## Pairing and Unpairing

Solaar is able to pair and unpair devices with
receivers as supported by the device and receiver.

For Unifying receivers, pairing adds a new paired device, but
only if there is an open slot on the receiver. So these receivers need to
be able to unpair devices that they have been paired with or else they will
not have any open slots for pairing. Some other receivers, like the
Nano receiver with USB ID `046d:c534`, can only pair with particular kinds of
devices and pairing a new device replaces whatever device of that kind was
previously paired to the receiver. These receivers cannot unpair. Further,
some receivers can pair an unlimited number of times but others can only
pair a limited number of times.

Bolt receivers add an authentication phase to pairing,
where the user has type a passcode or click some buttons to authenticate the device.

Only some connections between receivers and devices are possible. In should
be possible to connect any device with a Unifying logo on it to any receiver
with a Unifying logo on it. Receivers without the Unifying logo probably
can connect only to the kind of devices they were bought with and devices
without the Unifying logo can probably only connect to the kind of receiver
that they were bought with.


## Device Settings

Solaar can display quite a few changeable settings of receivers and devices.
For a list of HID++ features and their support see [the features page](features.md).

Solaar does not do much beyond using the HID++ protocol to change the
behavior of receivers and devices via changing their settings.
In particular, Solaar cannot change how
the operating system turns the keycodes that a keyboard produces into
characters that are sent to programs. That is the province of HID device
drivers and other software (such as X11).

Settings can only be changed in the Solaar GUI when they are unlocked.
To unlock a setting click on the icon at the right-hand edge of the setting
until an unlocked lock appears (with tooltop "Changes allowed").

Solaar keeps track of most of the changeable settings of a device.
Devices forget most changed settings when the device is turned off
or goes into a power-saving mode.
Exceptions include the setting to change the host the device is connected to,
the setting to persistently change what a key or button does,
and, for some devices, the fn-swap setting.
When Solaar starts, it restores on-line devices to their previously-known state
except for host connection and persistent key and button changes and while running Solaar restores
devices to their previously-known state when the device itself comes on line.
Setting information is stored in the file `~/.config/solaar/config.yaml`.

Updating of a setting can be turned off in the Solaar GUI by clicking on the icon
at the right-hand edge of the setting until a red icon appears (with tooltip
"Ignore this setting").

Solaar keeps track of settings independently on each computer.
As a result if a device is switched between different computers
Solaar may apply different settings for it on the different computers.

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
[the rules page](https://pwr-solaar.github.io/Solaar/rules).

Users can edit rules using a GUI by clicking on the `Rule Editor` button in the Solaar main window.

### Sliding DPI

A few mice (such as the MX Vertical) have a button that is supposed to be used to change
the sensitivity (DPI) of the mouse by pressing the button and moving the mouse left and right.
Other mice (such as the MX Master 3) don't have a button specific for this purpose
but have buttons that can be used for it.

The `Key/Button Diversion` setting can assign buttons to adjust sensitivity by setting the value for the button to `Sliding DPI`.
This capability is only present if the device supports changing the DPI in this way.

Pressing a button when it is set to `Sliding DPI` causes the mouse pointer to stop moving.
When the button is released a new Sensitivity (DPI) value is applied to the mouse,
depending on how far right or left the mouse is moved.   If the mouse is moved only a little bit
the previous value that was set is applied to the mouse.
Notifications from Solaar are displayed showing the setting that will be applied.

### Mouse Gestures

Some mice (such as the MX Master 3) have a button that is supposed to be used to
create up/down/left/right mouse gestures.  Other mice (such as the MX Vertical) don't
have a button specific for this purpose but have buttons that can be used for it.

The `Key/Button Diversion` setting can assign buttons to initiate mouse gestures by setting the value for the button to `Mouse Gestures`.
This capability is only present if the device can support it.

Pressing a button when it is set to `Mouse Gestures` causes the mouse pointer to stop moving.
When the button is released a `MOUSE_GESTURE` notification with the mouse movements and diverted key presses
is sent to the Solaar rule system so that rules can detect these notifications.
For more information on Mouse Gestures rule conditions see
[the rules page](https://pwr-solaar.github.io/Solaar/rules).

### Keyboard Key Names and Locations

Solaar uses the standard Logitech names for keyboard keys.  Some Logitech keyboards have different icons on some of their keys and have different functionality than suggested by these names.

Solaar is uses the standard US keyboard layout.  This currently only matters for the `Per-key Lighting` setting.  Users who want to have the key names for this setting reflect the keyboard layout that they use can create and edit `~/.config/solaar/keys.yaml` which contains a YAML dictionary of key names and locations.  For example, switching the `Y` and `Z` keys can be done  as:

	Z: 25
	Y: 26

This is an experimental feature and may be modified or even eliminated.


### Device Profiles

Some mice store one or more profiles, which control aspects of the behavior of the device.

Profiles can control the rate at which the mouse reports movement, the resolution of the the movement reports, what the mouse buttons do, and its LED effects.  Solaar can dump the entire set of profiles into a YAML file can load an entire set of profiles from a file.  Users can edit the file to effect changes to the profiles.  Solaar has a setting that switches between profiles or disables all profiles.  When switching between profiles or using a button to change resolution Solaar keeps track of the changes in the settings for these features.

When profiles are active changes cannot be made to the Report Rate setting.   Changes can be made to the Sensitivity setting and to LED settings.  To keep the profile values make these setting ignored.

A profile file has some bookkeeping information, including profile version and the name of the device, and a sequence of profiles.

Each profile has the following fields:
- enabled: Whether the profile is enabled.
- sector: Where the profile is stored in device memory.  Sectors greater than 0xFF are in ROM and cannot be written (use the low byte as the sector to write to Flash).
- name: A memonic name for the profile.
- report_rate: A report rate in milliseconds from 1 to 8.
- resolutions: A sequence of five sensor resolutions in DPI.
- resolution_default_index: The index of the default sensor resolution (0 to 4).
- resolution_shift_index: The index of the sensor resolution used when the DPI Shift button is pressed (0 to 4).
- buttons: The action for each button on the mouse in normal mode.
- gbuttons: The action for each button on the mouse in G-Shift mode.
- angle_snap: Enable angle snapping for devices.
- red, blue, green: Color indicator for the profile.
- lighting: Lighting information for logo and side LEDs in normal mode, then for power saving mode.
- ps_timeout: Delay in ms to go into power saving mode.
- po_timeout: Delay in ms to go from power saving mode to fully off.
- power_mode: Unknown purpose.
- write count: Unknown purpose.
Missing or unused parts of a profile are often a sequence of 0xFF bytes.

Button actions can either perform a function (behavior: 9) or send a button click or key press (behaviour: 8).
Functions are:
- 0: No Action - do nothing
- 1: Tilt Left
- 2: Tilt Right
- 3: Next DPI - change device resolution to the next DPI
- 4: Previous DPI - change device resolution to the previous DPI
- 5: Cycle DPI - change device resolution to the next DPI considered as a cycle
- 6: Default_DPI - change device resolution to the default resolution
- 7: Shift_DPI - change device resolution to the shift resolution
- 8: Next Profile - change to the next enabled profile
- 9: Previous Profile - change to the previous enabled profile
- 10: Cycle Profile - change to the next enabled profile considered as a cycle
- 11: G-Shift - change all buttons to their G-Shift state
- 12: Battery Status - show battery status on the device LEDs
- 13: Profile Select - select the n'th enabled profile
- 14: Mode Switch
- 15: Host Button - switch between hosts (unverified)
- 16: Scroll Down
- 17: Scroll Up
Some devices might not be able to perform all functions.

Buttons can send (type):
- 0: Don't send anything.
- 1: A button click (value) as a 16-bit bitmap, i.e., 1 is left click, 2 is right, 4 is middle, etc.
- 2: An 8-bit USB HID keycode (value) plus an 8-bit modifier bitmap (modifiers), i.e., 0 for no modifiers, 1 for control, 2 for shift, etc.
- 3: A 16-bit HID Consumer keycode (value).

See USB_HID_KEYCODES and HID_CONSUMERCODES in lib/logitech_receiver/special_keys.py for values to use for keycodes.

Buttons can also execute macros but Solaar does not provide any support for macros.

Lighting information is a sequence of lighting effects, with the first for the logo LEDs and the second for the side LEDs.

The fields possible in an effect are:
- ID: The kind of effect:
- color: A color parameter for the effect as a 24-bit RGB value.
- intensity: How intense to make the color (1%-100%), 0 for the default (usually 100%).
- speed: How fast to pulse in ms (one byte).
- ramp: How to change to the color (0=default, 1=ramp up/down, 2=no ramping).
- period: How fast to perform the effect in ms (two bytes).
- form: The form of the breathe effect.
- bytes: The raw bytes of other effects.

The possible effects and the fields the use are:
- 0x0: Disable - No fields.
- 0x1: Fixed color - color, whether to ramp.
- 0x2: Pulse a color - color, speed.
- 0x3 Cycle through the spectrum - period, intensity, form.
- 0x8; A boot effect - No fields.
- 0x9: A demo effect - NO fields.
- 0xa: breathe a color (like pulse) - color, period.
- 0xb: Ripple - color, period.
- null: An unknown effect.
Only effects supported by the device can be used.

To set up profiles, first run `solaar profiles <device name>`, which will output a YAML dump of the profiles on the device. Then store the YAML dump into a file and edit the file to make changes. Finally run `solaar profiles <device name> <file name>` to load the profiles back onto the device. Profiles are stored in flash memory and persist when the device is inactive or turned off. When loading profiles Solaar is careful to only write the flash memory sectors that need to be changed. Solaar also checks for correct profile version and device name before loading a profile into a device.

Keep a copy of the initial dump of profiles so that it can be loaded back to the device if problems are encountered with the edited profiles. The safest changes are to take an unused or unenabled profile sector and create a new profile in it, likely mostly copying parts of another profile.


## System Tray

Solaar's GUI normally uses an icon in the system tray.
This allows users to close Solaar and reopen from the tray.
This aspect of Solaar depends on having an active system tray which may
require some special setup when using Gnome, particularly under Wayland.

If you are running Gnome, you most likely need the
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
several heuristics determined which icon names to use for this purpose,
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
