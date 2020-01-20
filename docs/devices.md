---
title: Supported Devices
layout: page
---

# Supported devices and receivers

These tables list Logitech receivers and devices and to what degree their features are supported by Solaar.  The information in these tables is incomplete, based on what devices users have been able to test Solaar with.  If your device works with Solaar, but its supported features are not correctly specified here, please open an issue on the [Solaar github repository][solaar] with the pleasant news.


The HID++ column specifies the device's HID++ version.  Some devices report version 4.5, but that is the same as version 2.0 as listed here.

The Battery column specifies if Solaar is able to read the device's battery
level.

For mice, the DPI column specifies if the mouse's sensitivity is fixed (`-`),
can only be read (`R`), or can be read and changed by Solaar (`R/W`).

The reprog(rammable) keys feature is currently not fully supported by Solaar.
You are able to read this feature using command-line interface of Solaar, but it is not possible to assign different keys.


### Receivers:

| USB ID    | Kind       | Max Paired Devices |
------------|------------|--------------------|
| 046d:c517 | Nano       | 1                  |
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
| 064d:c534 | Nano       | 2                  |
| 064d:c539 | Lightspeed | 1                  |
| 064d:c53a | Lightspeed | 1                  |
| 064d:c53f | Lightspeed | 1                  |
| 17ef:6042 | Nano       | 1                  |



### Keyboards (Unifying):

| Device           | WPID | HID++ | Battery | Other supported features                |
|------------------|------|-------|---------|-----------------------------------------|
| K230             | 400D | 2.0   | yes     |                                         |
| K270             | 4003 | 2.0   | yes     |                                         |
| K340             | 2007 | 1.0   | yes     |                                         |
| K350             | 200A | 1.0   | yes     |                                         |
| K360             | 4004 | 2.0   | yes     | FN swap, reprog keys                    |
| K375s            | 4071 |       |         | FN swap                                 |
| K400 Touch       | 400E | 2.0   | yes     | FN swap                                 |
| K400 Touch       | 4024 | 2.0   | yes     | FN swap                                 |
| K400 Plus        | 404D | 2.0   |         | FN swap                                 |
| K520             | 2011 | 1.0   | yes     | FN swap                                 |
| K750 Solar       | 4002 | 2.0   | yes     | FN swap, Lux reading, light button      |
| K780             | 405B | 2.0   | yes     | FN swap                                 |
| K800 Illuminated | 2010 | 1.0   | yes     | FN swap, reprog keys, LEDs              |
| K800 (new ver)   | 406E | 2.0   | yes     | FN swap                                 |
| K830 Illuminated | 4032 | 2.0   | yes     | FN swap                                 |
| N545             | 2006 |       | yes     |                                         |
| TK820            |      | 2.0   | yes     | FN swap                                 |
| Craft            | 4066 | 2.0   |         |                                         |

* The [K750 Solar Keyboard][K750] can be queried for its solar charge status.
  Pressing the `Light-Check` button on the keyboard will pop-up the application
  window and display the current lighting value (Lux) as reported by the
  keyboard, similar to Logitech's *Solar.app* for Windows.

* FN swap changes the way the function keys (`F1`..`F12`) work, i.e., whether holding `FN` while pressing the function keys will generate the standard `Fx` keycodes or the special function (yellow icons) keycodes.


### Mice (Unifying):

| Device           | WPID | HID++ | Battery | DPI   | Other supported features        |
|------------------|------|-------|---------|-------|---------------------------------|
| M150             | 4022 | 2.0   |         |       |                                 |
| M185             | 4055 | 2.0   |         | R/W   | smooth scrolling                |
| M310             | 4031 | 2.0   | yes     |       |                                 |
| M310             | 4055 | 2.0   |         | R/W   | smooth scrolling                |
| M317             |      |       |         |       |                                 |
| M325             | 400A | 2.0   | yes     | 1000  | smooth scrolling                |
| M330             |      | 2.0   | yes     | 1000  | smooth scrolling                |
| M345             | 4017 | 2.0   | yes     | -     | smooth scrolling                |
| M350             | 101C | 1.0   | yes     |       |                                 |
| M505             | 101D | 1.0   | yes     |       | smooth scrolling, side scrolling|
| M510             | 1025 | 1.0   | yes     |       | smooth scrolling, side scrolling|
| M510             | 4051 | 2.0   | yes     |       | smooth scrolling                |
| M515 Couch       | 4007 | 2.0   | yes     | -     | smooth scrolling                |
| M525             | 4013 | 2.0   | yes     | -     | smooth scrolling                |
| M560             |      | 2.0   | yes     | -     | smooth scrolling                |
| M585             | 406B | 2.0   | yes     | R/W   | smooth scrolling                |
| M590             | 406B | 2.0   | yes     | R/W   | smooth scrolling                |
| M600 Touch       | 401A | 2.0   | yes     |       |                                 |
| M705 Marathon    | 101B | 1.0   | yes     | -     | smooth scrolling, side scrolling|
| M705 Marathon    | 406D | 2.0   | yes     | R/W   | smooth scrolling                |
| T400 Zone Touch  |      | 2.0   | yes     |       | smooth scrolling                |
| T620 Touch       |      | 2.0   | yes     |       |                                 |
| Performance MX   | 101A | 1.0   | yes     | R/W   | smooth scrolling, side scrolling|
| Anywhere MX      | 1017 | 1.0   | yes     | R/W   | smooth scrolling, side scrolling|
| Anywhere MX 2    | 404A | 2.0   | yes     | R/W   | smooth scrolling                |
| MX Master        | 4041 | 2.0   | yes     | R/W   | smooth scrolling, smart shift   |
| MX Master 25     | 4069 | 2.0   | yes     | R/W   | smooth scrolling, smart shift   |
| Cube             |      | 2.0   | yes     |       |                                 |


### Mice (Nano):

| Device           | WPID | HID++ | Battery | DPI   | Other supported features        |
|------------------|------|-------|---------|-------|---------------------------------|
| G7               | 1002 | 1.0   | yes     | -     |                                 |
| G700             | 1023 | 1.0   | yes     | -     | smooth scrolling, side scrolling|
| G700s            | 102A | 1.0   | yes     | -     | smooth scrolling, side scrolling|
| V450 Nano        | 1011 | 1.0   | yes     | -     | smooth scrolling                |
| V550 Nano        | 1013 | 1.0   | yes     | -     | smooth scrolling, side scrolling|
| VX Nano          | 100B | 1.0   | yes     | -     | smooth scrolling, side scrolling|
| VX Nano          | 100F | 1.0   | yes     | -     | smooth scrolling, side scrolling|
| M175             | 4008 |       | yes     |       |                                 |
| M185 (old)       | 4038 | 2.0   | yes     | R/W   | smooth scrolling (note)         |
| M185 (new)       | 4054 | 2.0   | no      | R/W   | smooth scrolling (note)         |
| M187             | 4019 | 2.0   | yes     |       |                                 |
| M215             | 1020 | 1.0   | yes     |       |                                 |
| M235             | 4055 | 2.0   | yes     | R/W   | smooth scrolling                |
| M305             | 101F | 1.0   | yes     |       | side scrolling                  |
| M310             | 1024 | 1.0   | yes     |       |                                 |
| M315             |      |       | yes     |       |                                 |
| M330             |      | ?.?   | yes     | ?     | smooth scrolling                |
| MX 1100          | 1014 | 1.0   | yes     | -     | smooth scrolling, side scrolling|

(old): M185 with P/N: 810-003496

(new): M185 with P/N: 810-005238 or 810-005232

(note): Currently, smooth scrolling events are not processed in xfce and this
setting is useful only to disable smooth scrolling.


### Mice (Mini):

| Device           | WPID | HID++ | Battery | DPI   | Other supported features        |
|------------------|------|-------|---------|-------|---------------------------------|
| MX610            | 1001 | 1.0   | yes     |       |                                 |
| MX610 lefthanded | 1004 | 1.0   | yes     |       |                                 |
| MX620            | 100A | 1.0   | yes     |       |                                 |
| MX620            | 1016 | 1.0   | yes     |       |                                 |
| V400             | 1003 | 1.0   | yes     |       |                                 |
| V450             | 1005 | 1.0   | yes     |       |                                 |
| VX Revolution    | 1006 | 1.0   | yes     |       |                                 |
| VX Revolution    | 100D | 1.0   | yes     |       |                                 |
| MX Air           | 1007 | 1.0   | yes     |       |                                 |
| MX Air           | 100E | 1.0   | yes     |       |                                 |
| MX Revolution    | 1008 | 1.0   | yes     |       |                                 |
| MX Revolution    | 100C | 1.0   | yes     |       |                                 |


### Trackballs (Unifying):

| Device            | WPID | HID++ | Battery | DPI   | Other supported features        |
|-------------------|------|-------|---------|-------|---------------------------------|
| M570 Trackball    |      | 1.0   | yes     | -     |                                 |
| MX Ergo Trackball |      | 2.0   | yes     | -     |                                 |

### Touchpads (Unifying):

| Device           | WPID | HID++ | Battery | DPI   | Other supported features        |
|------------------|------|-------|---------|-------|---------------------------------|
| Wireless Touch   | 4011 | 2.0   | yes     |       |                                 |
| T650 Touchpad    | 4101 | 2.0   | yes     |       | smooth scrolling                |


### Mice and Keyboards sold as combos:

| Device           | WPID | HID++ | Battery | Other supported features                |
|------------------|------|-------|---------|-----------------------------------------|
| MK220            |      | 2.0   | yes     |                                         |
| MK270            | 4023 | 2.0   | yes     | reprog keys                             |
| MK320            | 200F |       |         |                                         |
| MK330            |      |       |         |                                         |
| MK520            |      | M2/K1 | yes     | FN swap, reprog keys                    |
| MK550            |      |       |         |                                         |
| MK700            | 2008 | 1.0   | yes     | FN swap, reprog keys                    |
| MK710            |      | 1.0   | yes     | FN swap, reprog keys                    |


[solaar]: https://github.com/pwr-Solaar/Solaar
[logitech]: https://www.logitech.com
[unifying]: https://en.wikipedia.org/wiki/Logitech_Unifying_receiver
[G700s]: https://gaming.logitech.com/en-us/product/g700s-rechargeable-wireless-gaming-mouse
[K360]: http://logitech.com/product/keyboard-k360
[K700]: http://logitech.com/product/wireless-desktop-mk710
[K750]: http://logitech.com/product/k750-keyboard
[K800]: http://logitech.com/product/wireless-illuminated-keyboard-k800
[K830]: http://logitech.com/product/living-room-keyboard-k830
[M510]: http://logitech.com/product/wireless-mouse-m510
[M705]: http://logitech.com/product/marathon-mouse-m705
[P_MX]: http://logitech.com/product/performance-mouse-mx
[A_MX]: http://logitech.com/product/anywhere-mouse-mx
[M325]: http://logitech.com/product/wireless-mouse-m325
[M330]: https://www.logitech.com/en-us/product/m330-silent-plus
