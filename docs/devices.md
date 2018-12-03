# Supported devices

**Solaar** will detect all devices paired with your receiver, and at the very
least display some basic information about them.

At this moment, all [Unifying][unifying] Receiver are supported (devices with
USB ID `046d:c52b` or `046d:c532`), but only some newer Nano Receiver (devices
with USB ID `046d:c52f` and `046d:c52b`). You can check your connected Logitech
devices by running `lsusb -d 046d:` in a console.

For some devices, extra settings (usually not available through the standard
Linux system configuration) are supported:

* The [K750 Solar Keyboard][K750] is also queried for its solar charge status.
  Pressing the `Light-Check` button on the keyboard will pop-up the application
  window and display the current lighting value (Lux) as reported by the
  keyboard, similar to Logitech's *Solar.app* for Windows.

* The state of the `FN` key can be toggled on some keyboards ([K360][K360],
  [MK700][K700], [K750][K750], [K800][K800] and [K830][K830]). It changes the
  way the function keys (`F1`..`F12`) work, i.e. whether holding `FN` while
  pressing the function keys will generate the standard `Fx` keycodes or the
  special function (yellow icons) keycodes.

* The DPI can be changed on the [Performance MX Mouse][P_MX].

* Smooth scrolling (higher sensitivity on vertical scrolling with the wheel) can
  be toggled on the [M705 Marathon Mouse][M705], [M510 Wireless Mouse][M510],
  [M325][M325] and [G700s][G700s].


# Supported features

These tables list all known Logitech [Unifying][unifying] devices, and to what
degree their features are supported by Solaar. If your device is not listed here
at all, it is very unlikely Solaar would be able to support it.

The information in these tables is incomplete, based on what devices myself and
other users have been able to test Solaar with. If your device works with
Solaar, but its supported features are not specified here, I would love to hear
about it.


The HID++ column specifies the device's HID++ version.

The Battery column specifies if Solaar is able to read the device's battery
level.

For mice, the DPI column specifies if the mouse's sensitivity is fixed (`-`),
can only be read (`R`), or can be read and changed by Solaar (`R/W`).

The reprog(rammable) keys feature is currently not fully supported by Solaar.
You are able to read this feature using solaar-cli, but it is not possible to
assign different keys.


Keyboards (Unifying):

| Device           | HID++ | Battery | Other supported features                |
|------------------|-------|---------|-----------------------------------------|
| K230             | 2.0   | yes     |                                         |
| K270             | 1.0   | yes     |                                         |
| K270             | 2.0   | yes     | reprog keys                             |
| K340             | 1.0   | yes     |                                         |
| K350             | 1.0   | yes     |                                         |
| K360             | 2.0   | yes     | FN swap, reprog keys                    |
| K400 Touch       | 2.0   | yes     | FN swap                                 |
| K400 Plus        | 2.0   |         | FN swap                                 |
| K750 Solar       | 2.0   | yes     | FN swap, Lux reading, light button      |
| K780             | 4.5   | yes     | FN swap                                 |
| K800 Illuminated | 1.0   | yes     | FN swap, reprog keys                    |
| K830 Illuminated | 2.0   | yes     | FN swap                                 |
| TK820            | 2.0   | yes     | FN swap                                 |
| MK700            | 1.0   | yes     | FN swap, reprog keys                    |


Mice (Unifying):

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| M317             |       |         |       |                                 |
| M325             | 2.0   | yes     | 1000  | smooth scrolling                |
| M345             | 2.0   | yes     | -     | smooth scrolling                |
| M350             | 1.0   | yes     |       |                                 |
| M505             | 1.0   | yes     |       | smooth scrolling                |
| M510             | 1.0   | yes     |       | smooth scrolling                |
| M515 Couch       | 2.0   | yes     | -     | smooth scrolling                |
| M525             | 2.0   | yes     | -     | smooth scrolling                |
| M560             | 2.0   | yes     | -     | smooth scrolling                |
| M600 Touch       | 2.0   | yes     |       |                                 |
| M705 Marathon    | 1.0   | yes     | -     | smooth scrolling                |
| M720 Triathlon   | 4.5   | yes     | -     | smooth scrolling                |
| T400 Zone Touch  | 2.0   | yes     |       | smooth scrolling                |
| T620 Touch       | 2.0   | yes     |       |                                 |
| Performance MX   | 1.0   | yes     | R/W   | smooth scrolling                |
| Anywhere MX      | 1.0   | yes     | R/W   | smooth scrolling                |
| Anywhere MX 2    | 4.5   | yes     |       | smooth scrolling                |
| MX Master        | 4.5   | yes     | R/W   | smart shift                     |
| Cube             | 2.0   | yes     |       |                                 |


Mice (Nano):

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| G700s            | 1.0   | yes     | -     | smooth scrolling                |
| G700             | 1.0   | yes     | -     | smooth scrolling                |
| V450 Nano        | 1.0   | yes     | -     | smooth scrolling                |
| V550 Nano        | 1.0   | yes     | -     | smooth scrolling                |
| VX Nano          | 1.0   | yes     | -     | smooth scrolling                |
| M175             |       | yes     |       |                                 |
| M185 [old]       | 4.5   | yes     | R/W   | smooth scrolling[note]          |
| M185 [new]       | 4.5   | no      | R/W   | smooth scrolling[note]          |
| M187             | 2.0   | yes     |       |                                 |
| M215             | 1.0   | yes     |       |                                 |
| M235             | 4.5   | yes     |       |                                 |
| M305             | 1.0   | yes     |       |                                 |
| M310             | 1.0   | yes     |       |                                 |
| M315             |       | yes     |       |                                 |
| MX 1100          | 1.0   | yes     | -     | smooth scrolling, side scrolling|

[old]: M185 with P/N: 810-003496

[new]: M185 with P/N: 810-005238

[note]: Currently, smooth scrolling events does not processed in xfce and this
setting useful only for disable smooth scrolling


Mice (Mini):

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| MX610            | 1.0   | yes     |       |                                 |
| MX610 lefthanded | 1.0   | yes     |       |                                 |
| V400             | 1.0   | yes     |       |                                 |
| V450             | 1.0   | yes     |       |                                 |
| VX Revolution    | 1.0   | yes     |       |                                 |
| MX Air           | 1.0   | yes     |       |                                 |
| MX Revolution    | 1.0   | yes     |       |                                 |


Trackballs (Unifying):

| Device            | HID++ | Battery | DPI   | Other supported features        |
|-------------------|-------|---------|-------|---------------------------------|
| M570 Trackball    | 1.0   | yes     | -     |                                 |
| MX Ergo Trackball | 4.5   | yes     | -     |                                 |

Touchpads (Unifying):

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| Wireless Touch   | 2.0   | yes     |       |                                 |
| T650 Touchpad    | 2.0   | yes     |       | smooth scrolling                |


Mouse-Keyboard combos:

| Device           | HID++ | Battery | Other supported features                |
|------------------|-------|---------|-----------------------------------------|
| MK220            | 2.0   | yes     |                                         |
| MK330            |       |         |                                         |
| MK520            | M2/K1 | yes     | FN swap, reprog keys                    |
| MK550            |       |         |                                         |
| MK710            | 1.0   | yes     | FN swap, reprog keys                    |


[unifying]: http://logitech.com/promotions/6072
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
