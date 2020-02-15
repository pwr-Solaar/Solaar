---
title: Solaar Capabilities
layout: page
---
# Solaar capabilities

[**Solaar**][solaar] reports on and controls [Logitech][logitech] devices
(keyboards, mice, and trackballs) that connect to your computer via a
Logitech USB receiver (a very small piece of hardware that plugs into one of
your USB ports) and communicate with the receiver using Logitech's HID++
protocol.  Solaar is designed to detect all devices paired with your
receivers, and at the very least display some basic information about them.

At this moment, all [Unifying][unifying] receivers are supported (devices
with USB ID `046d:c52b` or `046d:c532`) as are several Lightspeed Receivers
and a dozen Nano receivers.

## HID++

HID++ is a Logitech-proprietary protocol that extends the standard HID
protocol for interfacing with keyboards, mice, and so on.  HID++ allows
Logitech receivers to communicate with multiple devices and modify some
features of the device on the device itself.  As the HID++ protocol is
proprietary many aspects of it are unknown.  Some information about HID++
has been obtained from Logitech but even that is subject to change and
extension.

There are several versions of the HID++ and many different Logitech
receivers and devices that utilize it.  Different receivers and devices
implement different portions of HID++ so even if two devices appear to be
the same in both physical appearance and behavior they may working
completely differently underneath.  (For example, there are versions of the
M510 mouse that use different versions of the HID++ protocol.)
Contrariwise, two different devices may appear different physically but
actually look the same to software.  (For example, some M185 mice look the
same to software as some M310 mice.)

The software identity of a receiver can be determined by its USB id
(reported by Solaar and also viewable in Linux using `lsusb`).  The software
identity of a device can be determined by its Wireless PID as reported by
Solaar.

Even something as fundamental as pairing works differently for different
receivers.  For Unifying receivers, pairing adds a new paired device, but
only if there is an open slot on the receiver.  So these receivers need to
be able to unpair devices that they have been paired with or else they will
not have any open slots for pairing.  Some other receivers, like the
Nano receiver with USB ID `046d:c534`, can only pair with particular kinds of
devices and pairing a new device replaces whatever device of that kind was
previously paired to the receiver.  These receivers cannot unpair.  Further,
some receivers can pair an unlimited number of times but others can only
pair a limited number of times.

Only some connections between receivers and devices are possible.  In should
be possible to connect any device with a Unifying logo on it to any receiver
with a Unifying logo on it.  Receivers without the Unifying logo probably
can connect only to the kind of devices they were bought with and devices
without the Unifying logo can probably only connect to the kind of receiver
that they were bought with.


## Supported features

Solaar uses the HID++ protocol to pair devices to receivers and unpair
devices from receivers.  Solaar also uses the HID++ protocol to display
features of receivers and devices.  Solaar can modify some of the features
of devices.  Solaar currently only displays some features and can modify
even fewer.

Solaar does not do anything beyond using the HID++ protocol to change the
behavior of receivers and devices.  In particular, Solaar cannot change how
the operating system turns the keycodes that a keyboard produces into
characters that are sent to programs.  That is the province of HID device
drivers and other software (such as X11).

Logitech receivers and devices have firmware in them.  Some of the firmware
can be updated using Logitech software in Windows.  For example, there are
security issues with some Logitech receivers and devices and Logitech has
firmware updates to alleviate these problems.  Some Logitech firmware can
also be updated in Linux using `fwupdmgr`.
WARNING: Updating firmware can cause a piece of hardware to to become
permanently non-functional if something goes wrong with the update or the
update installs the wrong firmware.

Solaar does keep track of some of the changeable state of a device between
invocations.  When Solaar starts it restores on-line devices to their
previously-known state.  Also, while running Solaar restores devices to
their previously-known state when the device comes on line.

Querying a device for its current state can require quite a few HID++
interactions.  These interactions can temporarily slow down the device, so
Solaar tries to internally cache information about devices.  If the device
state is changed by some other means, even sometimes by another invocation
of Solaar, this cached information may become incorrect.  Currently there is
no way to force an update of the cached information besides terminating
Solaar and starting it again.


[solaar]: https://github.com/pwr-Solaar/Solaar
[logitech]: https://www.logitech.com
[unifying]: https://en.wikipedia.org/wiki/Logitech_Unifying_receiver
