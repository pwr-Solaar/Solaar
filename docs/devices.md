---
title: Supported Devices
layout: page
---

# Supported receivers and devices

Solaar only supports Logitech receivers and devices that use the Logitech proprietary HID++ protocol.

Solaar supports most Logitech Nano, Unifying, and Bolt receivers.
Solaar supports some Lightspeed receivers.
See the receiver table below for the list of currently supported receivers.

Solaar supports most recent and many older Logitech devices
(keyboards, mice, trackballs, touchpads, and headsets)
that can connect to supported receivers.
Solaar supports many recent Logitech devices that can connect via a USB cable,
but some such Logitech devices are not suited for use in Solaar because they do not use the HID++ protocol.
One example is the MX518 Gaming Mouse.
Solaar supports most recent Logitech devices that can connect via Bluetooth.

The best way to determine whether Solaar supports a device is to run Solaar while the device is connected.
If the device is supported, it will show up in the Solaar main window.
If it is not, and there is no issue about the device in the Solaar GitHub repository,
open an enhancement issue requesting that it be supported.

The directory <https://github.com/pwr-Solaar/Solaar/tree/master/docs/devices> contains edited output
of `solaar show` on many devices and can be used to see what Solaar can do with the device.


## Adding new devices

Most new HID++ devices do not need to be known to Solaar to work.
You should be able to just run Solaar and the device will show up.

If your device does not show up,
either it doesn't use HID++ or the interface it uses isn't the one Solaar normally uses.
To start the process of support for a Logitech device open an enhancement issue for Solaar and
follow these steps:

1. Make sure the receiver or device is connected and active.

2. Look at the output of `grep -H . /sys/class/hidraw/hidraw*/device/uevent` to find
where information about the device is kept.
You are looking for a line like `/sys/class/hidraw/hidrawN/device/uevent:HID_NAME=<NAME>`
where \<NAME\> is the name of your receiver or device.
N is the current HID raw number of your receiver or device.

3. Provide the contents of the file `/sys/class/hidraw/hidrawN/device/uevent` where N was found
above.

4. Also attach the contents of the file `/sys/class/hidraw/hidrawN/device/report_descriptor`
to the enhancement request.
You will have to copy the contents to a file with txt extension before attaching it.
Or, better, install hidrd-convert and attach the output of
`hidrd-convert -o spec /sys/class/hidraw/hidrawN/device/report_descriptor`
(To install hidrd on Fedora use  `sudo dnf install hidrd`.)

5. If your device or receiver connects via USB, look at the output of `lsusb`
to find the ID of the device or receiver and also provide the output of
`lsusb -vv -d xxxx:yyyy` where xxxx:yyyy is the ID of the device or receiver.

If your device can connect in multiple ways - via a receiver, via USB (not just charging via a USB cable),
via Bluetooth - do this for each way it can connect.

### Adding information about a new device to the Solaar code

The _D function in `../lib/logitech_receiver/descriptors.py` makes a device known to Solaar.
The usual arguments to the _D function are the device's long name, its short name
(codename), and its HID++ protocol version.
Devices that use HID++ 1.0 need a tuple of known registers (registers) and settings (settings).
Settings can be provided for Devices that use HID++ 2.0 or later,
but Solaar can determine these from the device.
If the device can connect to a receiver, provide its wireless product ID (wpid),
If the device can connect via Bluetooth, provide its Bluetooth product ID (btid).
If the device can connect via a USB cable, provide its USB product ID (usbid),
and the interface it uses to send and receiver HID++ messages (interface - default 2).
The use of a non-default USB interface is the main reason for requiring information about
modern devices to be added to Solaar.


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



## Supported Devices

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
| MX Master 3      | 4082 | 4.5   |
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
