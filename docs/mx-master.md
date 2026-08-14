---
title: Configuring an MX Master
layout: page
---

# Configuring an MX Master 3 / 3S

People often arrive at Solaar from Logitech Options+ or LogiOps expecting to find
the same gestures and button remappings, and get stuck because Solaar does not
present them as a single list of behaviours. The work is split across two layers,
and a setup only works when both are right — which is the usual reason a rule
"does nothing".

This page walks through a complete MX Master 3 / 3S configuration. Everything on
it was checked against an MX Master 3S on a Logi Bolt receiver; other MX mice
work the same way, though the exact set of buttons differs.

## The two layers

**Settings** live on the device and are applied by Solaar whenever the device
connects. Scroll behaviour, DPI and SmartShift are settings, and nothing else is
needed to use them.

**Rules** live in `~/.config/solaar/rules.yaml` and react to notifications sent by
the device. A button only sends notifications once its `Key/Button Diversion` is
changed from `Regular`, so a rule that matches a button you have not diverted can
never fire.

| What you want | Diversion needed | Rule needed |
| --- | --- | --- |
| DPI, SmartShift, scroll direction | no | no |
| A button that types a key combination | `Diverted` | yes |
| Mouse gestures (hold a button, move) | `Mouse Gestures` | yes |
| Thumb wheel doing something other than horizontal scroll | `Thumb Wheel Diversion` on | yes |

## What your mouse reports

Start from what the device actually says rather than from a list of button names
copied from somewhere else:

```
solaar show
```

The `Reprogrammable keys` section lists every button with the exact name to use in
rules. Only buttons whose report includes `divertable` can be diverted. On an
MX Master 3S:

```
    0: Left Button               , default: Left Click
    1: Right Button              , default: Right Click
    2: Middle Button             , default: Mouse Middle Button
    3: Back Button               , default: Mouse Back Button
    4: Forward Button            , default: Mouse Forward Button
    5: Mouse Gesture Button      , default: Gesture Button Navigation
    6: Smart Shift               , default: Smart Shift
    7: Virtual Gesture Button    , default: Virtual Gesture Button
```

`Mouse Gesture Button` is the large thumb button, and `Smart Shift` is the button
behind the scroll wheel.

## Settings that need no rules

These are set in the main window and are all Solaar needs to know about:

| Setting | Notes |
| --- | --- |
| `Sensitivity (DPI)` | Pointer speed, in steps the device reports. |
| `Scroll Wheel Ratcheted` | `Ratcheted` for a clicky wheel, `Free Spinning` for a free wheel. |
| `Scroll Wheel Ratchet Speed` | How fast the wheel must spin before it disengages the ratchet — the equivalent of a SmartShift threshold. |
| `Scroll Wheel Direction`, `Thumb Wheel Direction` | Invert a wheel. |
| `Scroll Wheel Resolution` | High-resolution scrolling. |

## Remapping a button

Two steps, both required.

**1. Divert the button.** In the main window, set `Key/Button Diversion` for the
button to `Diverted`. From the command line:

```
solaar config "MX Master 3S" divert-keys "Mouse Gesture Button" Diverted
```

**2. Add a rule** that matches the button and does something. Rules can be written
in the rule editor (main window, `Rule Editor`) or directly in
`~/.config/solaar/rules.yaml`.

### Thumb button opens the GNOME overview

```yaml
---
- Key: [Mouse Gesture Button, pressed]
- KeyPress: [Super_L]
...
```

### Back and Forward navigate in the browser

The two side buttons already send back/forward events by default. Divert them only
if you want something else — here, the keyboard shortcuts that also work in
applications that ignore the dedicated buttons:

```yaml
---
- Key: [Back Button, pressed]
- KeyPress: [Alt_L, Left]
...
---
- Key: [Forward Button, pressed]
- KeyPress: [Alt_L, Right]
...
```

`KeyPress` takes X11 key symbol names, not evdev key codes: `Super_L`, not
`KEY_LEFTMETA`.

## Mouse gestures

Set `Key/Button Diversion` for the thumb button to `Mouse Gestures` rather than
`Diverted`. Holding that button, moving the mouse, and releasing it then produces a
single notification describing the movement, which `MouseGesture` conditions match.

Switching workspaces by holding the thumb button and flicking left or right:

```yaml
---
- MouseGesture: [Mouse Left]
- KeyPress: [Super_L, Page_Up]
...
---
- MouseGesture: [Mouse Right]
- KeyPress: [Super_L, Page_Down]
...
```

A gesture can chain several movements, so `[Mouse Up, Mouse Up]` is a different
gesture from `[Mouse Up]`. Pressing and releasing the button without moving
produces a `No-op` gesture, which can be given its own rule — useful for keeping an
action on a button that is otherwise used for gestures.

## Thumb wheel

Turn on `Thumb Wheel Diversion`, then match the wheel with `thumb_wheel_up` and
`thumb_wheel_down`. Switching browser tabs:

```yaml
---
- Feature: THUMB WHEEL
- Rule: [Test: [thumb_wheel_up, 5], KeyPress: [Control_L, Shift_L, Tab]]
- Rule: [Test: [thumb_wheel_down, 5], KeyPress: [Control_L, Tab]]
...
```

The integer argument matters. The thumb wheel reports many small increments, so a
bare `thumb_wheel_up` test fires far too often for a discrete action like changing
tabs. With a parameter the test is only true once the accumulated displacement
passes that value, and the displacement is then reduced by it — raise the number
for slower switching, lower it for faster.

## A complete example

```yaml
%YAML 1.3
---
- Key: [Mouse Gesture Button, pressed]
- KeyPress: [Super_L]
...
---
- Key: [Back Button, pressed]
- KeyPress: [Alt_L, Left]
...
---
- Key: [Forward Button, pressed]
- KeyPress: [Alt_L, Right]
...
---
- Feature: THUMB WHEEL
- Rule: [Test: [thumb_wheel_up, 5], KeyPress: [Control_L, Shift_L, Tab]]
- Rule: [Test: [thumb_wheel_down, 5], KeyPress: [Control_L, Tab]]
...
```

with `Key/Button Diversion` set to `Diverted` for `Mouse Gesture Button`,
`Back Button` and `Forward Button`, and `Thumb Wheel Diversion` turned on.

## Coming from LogiOps

| `logid.cfg` | Solaar |
| --- | --- |
| `dpi: 1500` | `Sensitivity (DPI)` setting |
| `smartshift: { on: true; threshold: 15 }` | `Scroll Wheel Ratcheted` and `Scroll Wheel Ratchet Speed` |
| `hiresscroll: { hires: ... }` | `Scroll Wheel Resolution` setting |
| `buttons: ({ cid: 0xc3; action = Keypress ... })` | divert `Mouse Gesture Button`, then a `Key` rule with `KeyPress` |
| `cid: 0x53` / `cid: 0x56` | `Back Button` / `Forward Button` |
| `gestures` on a button | `Key/Button Diversion` set to `Mouse Gestures`, then `MouseGesture` rules |
| evdev names (`KEY_LEFTMETA`) | X11 key symbols (`Super_L`) |

Control IDs do not appear in Solaar's interface; use the button names from
`solaar show` instead.

Do not run LogiOps and Solaar against the same device at the same time. Both
reprogram the same controls, and whichever writes last wins, which looks like
settings randomly reverting.

## Session notes

`KeyPress`, `MouseScroll` and `MouseClick` actions are performed through a uinput
virtual device, so they work under both X11 and Wayland. This needs Solaar's udev
rule to be installed; see [the installation page](https://pwr-solaar.github.io/Solaar/installation).

Two kinds of condition are more limited under Wayland, because no Wayland protocol
exposes what they need:

- `Modifiers` conditions cannot read the keyboard modifier state.
- `Process` and `MouseProcess` conditions need the Solaar GNOME extension, and
  work only under GNOME.

Solaar reports both limitations at startup when it detects a Wayland session.

For the full set of conditions and actions see [the rules page](https://pwr-solaar.github.io/Solaar/rules).
