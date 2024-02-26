---
title: Supported Devices
layout: page
---

# Supported receivers and devices

Solaar only supports Logitech receivers and devices that use the Logitech proprietary HID++ protocol.

Solaar supports most Logitech Nano, Unifying, and Bolt receivers.
Solaar supports some Lightspeed receivers.
See the receiver table below for the list of currently supported receivers.

Solaar supports all Logitech devices (keyboards, mice, trackballs, touchpads, and headsets)
that can connect to supported receivers.
Solaar supports all Logitech devices that can connect via a USB cable or via Bluetooth,
as long as the device uses the HID++ protocol.

The best way to determine whether Solaar supports a device is to run Solaar while the device is connected.
If the device is supported, it will show up in the Solaar main window.

The directory <https://github.com/pwr-Solaar/Solaar/tree/master/docs/devices> contains edited output
of `solaar show` on many devices and can be used to see what Solaar can do with the device.


## Supporting old devices

Some old Logitech devices use an old version of HID++.
For Solaar to support these devices well, Solaar needs some information about them.

If you have an old Logitech device that shows up in Solaar but has no settings
and you feel that Solaar should be able to do more with the device you can
open an enhancement request for Solaar to better support the device.


## Adding new receivers

Adding a new receiver requires knowing whether the receiver is a regular
Unifying receiver, a Nano receiver, a Bolt receiver, or a Lightspeed receiver.
This can generally be found using `lsusb`.

To add a new receiver to the Solaar code
add a line to `../lib/logitech_receiver/base_usb.py` defining the receiver as one of these.
If the receiver has an unusual number of pairing slots, then this also needs
to be specified. Then add the receiver to the tuple of receivers (ALL).

### Supported Receivers

| USB ID    | Kind       | Max Paired Devices |
------------|------------|--------------------|
| 046d:c517 | 27MHz      | 4                  |
| 046d:c518 | Nano       | 1                  |
| 046d:c51a | Nano       | 1                  |
| 046d:c51b | Nano       | 1                  |
| 046d:c521 | Nano       | 1                  |
| 046d:c525 | Nano       | 1                  |
| 046d:c526 | Nano       | 1                  |
| 046d:c52b | Unifying   | 6                  |
| 046d:c52e | Nano       | 1                  |
| 046d:c52f | Nano       | 1                  |
| 046d:c531 | Nano       | 1                  |
| 046d:c532 | Unifying   | 6                  |
| 046d:c534 | Nano       | 2                  |
| 046d:c537 | Nano       | 2                  |
| 046d:c539 | Lightspeed | 1                  |
| 046d:c53a | Lightspeed | 1                  |
| 046d:c53d | Lightspeed | 1                  |
| 046d:c53f | Lightspeed | 1                  |
| 046d:c541 | Lightspeed | 1                  |
| 046d:c542 | Nano       | 1                  |
| 046d:c545 | Lightspeed | 1                  |
| 046d:c547 | Lightspeed | 1                  |
| 046d:c548 | Bolt       | 6                  |
| 17ef:6042 | Nano       | 1                  |

Some Nano receivers are only partly supported
as they do not implement the full HID++ 1.0 protocol.
Some Nano receivers are not supported as they do not implement the HID++ protocol at all.
Receivers with USB ID 046d:c542 fall into this category.

The receiver with USB ID 046d:c517 is an old 27 MHz receiver, supporting only
a subset of the HID++ 1.0 protocol. Only hardware pairing is supported.



## Supported Devices (Historical Interest Only)

The device tables below  provide a list of some of the devices that Solaar supports,
giving their product name, WPID product number, and HID++ protocol information.
The tables concentrate on older devices that have explicit support information in Solaar
and are not being updated for new devices that are supported by Solaar.

Note that Logitech has the annoying habit of reusing Device names (e.g., M185)
so what is important for support is the USB WPID or Bluetooth model ID.

### Keyboards (Unifying)

| Device           | WPID | HID++ |
|------------------|------|-------|
| K230             | 400D | 2.0   |
| K270             | 4003 | 2.0   |
| K340             | 2007 | 1.0   |
| K350             | 200A | 1.0   |
| K360             | 4004 | 2.0   |
| K375s            | 4071 |       |
| K400 Touch       | 400E | 2.0   |
| K400 Touch       | 4024 | 2.0   |
| K400 Plus        | 404D | 2.0   |
| K520             | 2011 | 1.0   |
| K600 TV          | 4078 | 2.0   |
| K750 Solar       | 4002 | 2.0   |
| K780             | 405B | 2.0   |
| K800 Illuminated | 2010 | 1.0   |
| K800 (new ver)   | 406E | 2.0   |
| K830 Illuminated | 4032 | 2.0   |
| MX Keys          | 408A | 2.0   |
| N545             | 2006 |       |
| TK820            |      | 2.0   |
| Craft            | 4066 | 2.0   |


### Keyboards (Lightspeed)

| Device           | WPID | HID++ |
|------------------|------|-------|
| G915 TKL         | 408E | 4.2   |

### Mice (Unifying)

| Device           | WPID | HID++ |
|------------------|------|-------|
| M150             | 4022 | 2.0   |
| M185             | 4055 | 2.0   |
| M310             | 4031 | 2.0   |
| M310             | 4055 | 2.0   |
| M317             |      |       |
| M325             | 400A | 2.0   |
| M330             |      | 2.0   |
| M345             | 4017 | 2.0   |
| M350             | 101C | 1.0   |
| M350             | 4080 | 2.0   |
| M505             | 101D | 1.0   |
| M510             | 1025 | 1.0   |
| M510             | 4051 | 2.0   |
| M515 Couch       | 4007 | 2.0   |
| M525             | 4013 | 2.0   |
| M560             |      | 2.0   |
| M585             | 406B | 2.0   |
| M590             | 406B | 2.0   |
| M600 Touch       | 401A | 2.0   |
| M705 Marathon    | 101B | 1.0   |
| M705 Marathon    | 406D | 2.0   |
| M720 Triathlon   | 405E | 2.0   |
| T400 Zone Touch  |      | 2.0   |
| T620 Touch       |      | 2.0   |
| Performance MX   | 101A | 1.0   |
| Anywhere MX      | 1017 | 1.0   |
| Anywhere MX 2    | 404A | 2.0   |
| MX Master        | 4041 | 2.0   |
| MX Master 2S     | 4069 | 2.0   |
| Cube             |      | 2.0   |
| MX Vertical      | 407B | 2.0   |

### Mice (Nano)

| Device           | WPID | HID++ |
|------------------|------|-------|
| G7               | 1002 | 1.0   |
| G700             | 1023 | 1.0   |
| G700s            | 102A | 1.0   |
| V450 Nano        | 1011 | 1.0   |
| V550 Nano        | 1013 | 1.0   |
| VX Nano          | 100B | 1.0   |
| VX Nano          | 100F | 1.0   |
| M175             | 4008 |       |
| M185 (old)       | 4038 | 2.0   |
| M185 (new)       | 4054 | 2.0   |
| M187             | 4019 | 2.0   |
| M215             | 1020 | 1.0   |
| M235             | 4055 | 2.0   |
| M305             | 101F | 1.0   |
| M310             | 1024 | 1.0   |
| M315             |      |       |
| M330             |      | ?.?   |
| MX 1100          | 1014 | 1.0   |

* (old): M185 with P/N: 810-003496
* (new): M185 with P/N: 810-005238 or 810-005232

### Mice (Mini)

| Device            | WPID | HID++ |
|-------------------|------|-------|
| MX610             | 1001 | 1.0   |
| MX610 left handed | 1004 | 1.0   |
| MX620             | 100A | 1.0   |
| MX620             | 1016 | 1.0   |
| V400              | 1003 | 1.0   |
| V450              | 1005 | 1.0   |
| VX Revolution     | 1006 | 1.0   |
| VX Revolution     | 100D | 1.0   |
| MX Air            | 1007 | 1.0   |
| MX Air            | 100E | 1.0   |
| MX Revolution     | 1008 | 1.0   |
| MX Revolution     | 100C | 1.0   |


### Mice (Lightspeed)

| Device                       | WPID | HID++ |
|------------------------------|------|-------|
| PRO X Superlight Wireless    | 4093 | 4.2   |

### Trackballs (Unifying)

| Device            | WPID | HID++ |
|-------------------|------|-------|
| M570 Trackball    |      | 1.0   |
| MX Ergo Trackball |      | 2.0   |

### Touchpads (Unifying)

| Device           | WPID | HID++ |
|------------------|------|-------|
| Wireless Touch   | 4011 | 2.0   |
| T650 Touchpad    | 4101 | 2.0   |

### Mice and Keyboards sold as combos

| Device           | WPID | HID++ |
|------------------|------|-------|
| MK220            |      | 2.0   |
| MK270            | 4023 | 2.0   |
| MK320            | 200F |       |
| MK330            |      |       |
| MK345            | 4023 | 2.0   |
| MK520            |      | M2/K1 |
| MK550            |      |       |
| MK700            | 2008 | 1.0   |
| MK710            |      | 1.0   |
| EX100 keyboard   | 0065 | 1.0   |
| EX100 mouse      | 003f | 1.0   |

* The EX100 is an old, pre-Unifying receiver and device set, supporting only some HID++ 1.0 features
