**Solaar** will detect all devices paired with your Unifying Receiver, and at
the very least display some basic information about them.

For some devices, extra settings (usually not available through the standard
Linux system configuration) are supported:

* The [K750 Solar Keyboard][K750] is also queried for its solar charge status.
  Pressing the `Solar` key on the keyboard will pop-up the application window
  and display the current lighting value (Lux) as reported by the keyboard,
  similar to Logitech's *Solar.app* for Windows.

* The state of the `FN` key can be toggled on some keyboards ([K750][K750],
  [K800][K800] and [K360][K360]). It changes the way the function keys
  (`F1`..`F12`) work, i.e. whether holding `FN` while pressing the function keys
  will generate the standard `Fx` keycodes or the special function (yellow
  icons) keycodes.

* The DPI can be changed on the [Performance MX Mouse][P_MX].

* Smooth scrolling (higher sensitivity on vertical scrolling with the wheel) can
  be toggled on the [M705 Marathon Mouse][M705] and [Anywhere MX Mouse][A_MX].


# Supported devices

Ver as noted in the below tables refers to the reported HID++ protocol version.
1.0 is the initial protocol that retrieves information by reading/writing
registers. HID++ 2.0 is a newer protocol that uses standardised *features* to
read or change details.

Keyboards:

| Device           | Battery | Other features                            | Ver |
|------------------|---------|-------------------------------------------|-----|
| K230             |         |                                           |     |
| K270             |         |                                           |     |
| K350             |         |                                           |     |
| K360             |         |                                           |     |
| K400 Touch       |         |                                           |     |
| K750 Solar       | yes     | FN swap, Lux reading, solar button        |     |
| K800 Illuminated | yes     | FN swap, rechargable over USB             | 1.0 |


Mice:

| Device           | Battery | DPI   | Other features                    | Ver |
|------------------|---------|-------|-----------------------------------|-----|
| M315             |         |       |                                   |     |
| M325             |         |       |                                   |     |
| M345             |         |       |                                   |     |
| M505             |         |       |                                   |     |
| M510             |         |       |                                   | 1.0 |
| M515 Couch       | yes     | -     |                                   |     |
| M525             | yes     | -     |                                   | 2.0 |
| M705 Marathon    | yes     | -     | smooth scrolling                  | 1.0 |
| T400 Zone Touch  |         |       |                                   |     |
| T620 Touch       |         |       |                                   |     |
| Performance MX   | yes     | yes   |                                   | 1.0 |
| Anywhere MX      | yes     | -     | smooth scrolling                  |     |
| Cube             |         |       |                                   |     |


Trackballs:

| Device           | Battery | DPI   | Other features                    | Ver |
|------------------|---------|-------|-----------------------------------|-----|
| M570 Trackball   |         |       |                                   |     |


Touchpads:

| Device           | Battery | DPI   | Other features                    | Ver |
|------------------|---------|-------|-----------------------------------|-----|
| T650 Touchpad    |         |       |                                   |     |


Mouse-Keyboard combos:

| Device           | Battery | Other features                            | Ver |
|------------------|---------|-------------------------------------------|-----|
| MK330            |         |                                           |     |
| MK710            |         | FN swap                                   |     |


--

[K750]: http://logitech.com/product/k750-keyboard
[K800]: http://logitech.com/product/wireless-illuminated-keyboard-k800
[K360]: http://logitech.com/product/keyboard-k360
[M705]: http://logitech.com/product/marathon-mouse-m705
[P_MX]: http://logitech.com/product/performance-mouse-mx
[A_MX]: http://logitech.com/product/anywhere-mouse-mx
