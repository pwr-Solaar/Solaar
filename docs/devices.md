# Supported devices

**Solaar** will detect all devices paired with your receiver, and at the very
least display some basic information about them.

At this moment, all [Unifying Receiver][unifying] are supported (devices with
USB ID `046d:c52b` or `046d:c532`), but only some newer [Nano Receiver][nano]s
(devices with USB ID `046d:c52f`). You can check your connected Logitech devices
by running `lsusb -d 046d:` in a console.

For some devices, extra settings (usually not available through the standard
Linux system configuration) are supported:

* The [K750 Solar Keyboard][K750] is also queried for its solar charge status.
  Pressing the `Light-Check` button on the keyboard will pop-up the application
  window and display the current lighting value (Lux) as reported by the
  keyboard, similar to Logitech's *Solar.app* for Windows.

* The state of the `FN` key can be toggled on some keyboards ([K360][K360],
  [MK700][K700], [K750][K750] and [K800][K800]). It changes the way the function
  keys (`F1`..`F12`) work, i.e. whether holding `FN` while pressing the function
  keys will generate the standard `Fx` keycodes or the special function (yellow
  icons) keycodes.

* The DPI can be changed on the [Performance MX Mouse][P_MX].

* Smooth scrolling (higher sensitivity on vertical scrolling with the wheel) can
  be toggled on the [M705 Marathon Mouse][M705] and [M510 Wireless Mouse][M510].


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


Keyboards:

| Device           | HID++ | Battery | Other supported features                |
|------------------|-------|---------|-----------------------------------------|
| K230             | 2.0   | yes     |                                         |
| K270             |       |         |                                         |
| K340             |       |         |                                         |
| K350             |       |         |                                         |
| K360             | 2.0   | yes     | FN swap, reprog keys                    |
| K400 Touch       | 2.0   | yes     |                                         |
| K750 Solar       | 2.0   | yes     | FN swap, Lux reading, light button      |
| K800 Illuminated | 1.0   | yes     | FN swap, reprog keys                    |
| MK700            | 1.0   | yes     | FN swap, reprog keys                    |


Mice:

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| M215             | 1.0   | yes     |       |                                 |
| M310             |       |         |       |                                 |
| M315             |       |         |       |                                 |
| M325             |       |         |       |                                 |
| M345             |       |         |       |                                 |
| M505             |       |         |       |                                 |
| M510             | 1.0   | yes     |       | smooth scrolling                |
| M515 Couch       | 2.0   | yes     | -     |                                 |
| M525             | 2.0   | yes     | -     |                                 |
| M705 Marathon    | 1.0   | yes     | -     | smooth scrolling                |
| T400 Zone Touch  |       |         |       |                                 |
| T620 Touch       |       |         |       |                                 |
| Performance MX   | 1.0   | yes     | R/W   |                                 |
| Anywhere MX      |       |         |       |                                 |
| Cube             |       |         |       |                                 |


Trackballs:

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| M570 Trackball   |       |         |       |                                 |


Touchpads:

| Device           | HID++ | Battery | DPI   | Other supported features        |
|------------------|-------|---------|-------|---------------------------------|
| T650 Touchpad    |       |         |       |                                 |


Mouse-Keyboard combos:

| Device           | HID++ | Battery | Other supported features                |
|------------------|-------|---------|-----------------------------------------|
| MK330            |       |         |                                         |
| MK520            |       |         |                                         |
| MK550            |       |         |                                         |
| MK710            | 1.0   | yes     | FN swap, reprog keys                    |


[unifying]: http://logitech.com/en-us/66/6079
[nano]: http://logitech.com/mice-pointers/articles/5926
[K360]: http://logitech.com/product/keyboard-k360
[K700]: http://logitech.com/product/wireless-desktop-mk710
[K750]: http://logitech.com/product/k750-keyboard
[K800]: http://logitech.com/product/wireless-illuminated-keyboard-k800
[M510]: http://logitech.com/product/wireless-mouse-m510
[M705]: http://logitech.com/product/marathon-mouse-m705
[P_MX]: http://logitech.com/product/performance-mouse-mx
[A_MX]: http://logitech.com/product/anywhere-mouse-mx
