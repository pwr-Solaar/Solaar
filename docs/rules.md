---
title: Rule Processing of HID++ Notifications
layout: page
---

# Rule Processing of HID++ Notifications
Creating and editing most rules can be done in the Solaar GUI, by pressing the 'Rule Editor' button in the
Solaar main window.

Note that rule processing only fully works under X11.
When running under Wayland with X11 libraries loaded some features will not be available.
When running under Wayland without X11 libraries loaded even more features will not be available.
Rule features known not to work under Wayland include process and mouse process conditions,
although on GNOME desktop under Wayland, you can use those with the Solaar Gnome extension installed,
You can install it from `https://extensions.gnome.org/extension/6162/solaar-extension`.
Under Wayland using keyboard groups may result in incorrect symbols being input for simulated input.
Under Wayland simulating inputs when modifier keys are pressed may result in incorrect symbols being sent.
Simulated input uses Xtest if available under X11 or uinput if the user has write access to /dev/uinput.
The easiest way to maintain write access to /dev/uinput is to use Solaar's alternative udev rule by downloading
`https://raw.githubusercontent.com/pwr-Solaar/Solaar/master/rules.d-uinput/42-logitech-unify-permissions.rules`
and copying it as root into the `/etc/udev/rules.d` directory.
You may have to reboot your system for the write permission to be set up.
Another way to get write access to /dev/uinput is to run `sudo setfacl -m u:${USER}:rw /dev/uinput`
but this needs to be done every time the system is rebooted.

## HID++ notifications and diversion
Logitech devices that use HID++ version 2.0 or greater, produce feature-based
notifications that Solaar can process using a simple rule language. For
example, using rules Solaar can emulate an `XF86_MonBrightnessDown` key tap
in response to the pressing of the `Brightness Down` key on Craft keyboards,
which normally does not produce any input at all when the keyboard is in
Windows mode.

Solaar's rules only trigger on HID++ notifications so device actions that
normally produce HID output have to be first be set (diverted) to
produce HID++ notifications instead of their normal behavior.
Currently, Solaar can divert some mouse scroll wheels, some
mouse thumb wheels, the crown of Craft keyboards, and some keys and buttons.
If the scroll wheel, thumb wheel, crown, key, or button is
not diverted by setting the appropriate setting then no HID++ notification is
generated and rules will not be triggered by manipulating the wheel, crown, key, or button.
Look for `HID++` or `Diversion` settings to see what
diversion can be done with your devices.

### Show notifications
Running Solaar with the `-ddd`
option will show information about notifications, including their feature
name, report number, and data.

In response to a feature-based HID++ notification Solaar runs a sequence of
rules. A `Rule` is a sequence of components, which are either sub-rules,
conditions, or actions. Conditions and actions are dictionaries with one
entry whose key is the name of the condition or action and whose value is
the argument of the action.

If the last thing that a rule does is execute an action, no more rules are
processed for the notification.

Rules are evaluated by evaluating each of their components in order. The
evaluation of a rule is terminated early if a condition component evaluates
to false or the last evaluated subcomponent of a component is an action. A
rule is false if its last evaluated component evaluates to false.

## Conditions

### Not
`Not` conditions take a single component and are true if their component
evaluates to a false value.

### Or
`Or` conditions take a sequence of components and are evaluated by
evaluating each of their components in order.
An Or condition is terminated early if a component evaluates to true or the
last evaluated subcomponent of a component is an action.
A Or condition is true if its last evaluated component evaluates to a true
value. `And` conditions take a sequence of components which are evaluated the same
as rules.

### Feature
`Feature` conditions are true if the name of the feature of the current
notification is their string argument.
`Report` conditions are true if the report number in the current
notification is their integer argument.

### Key
`Key` conditions are true if the Logitech name of the current **diverted** key or button being pressed is their
string argument. Alternatively, if the argument is a list `[name, action]` where `action`
is either `'pressed'` or `'released'`, the key down or key up events of `name` argument are
matched, respectively. Logitech key and button names are shown in the `Key/Button Diversion`
setting. These names are also shown in the output of `solaar show` in the 'Reprogrammable keys'
section. Only keys or buttons that have 'Divertable' in their report can be diverted.
Some keyboards have 'Gn', 'Mn', or 'MR' keys, which are diverted using the 'Divert G Keys' setting.

### Key is down
`KeyIsDown` conditions are true if the **diverted** key or button that is their string argument is currently down.
Note that this only works for **diverted** keys or buttons, including diverted Gn, Mn, and MR keys.

### Key and button diversion
Solaar can also create special notifications in response to mouse movements on some mice.
Setting `Key/Button Diversion` for a key or button to Mouse Gestures causes the key or button to create a `Mouse Gesture`
notification for the period that the key or button is depressed.
Moving the mouse creates a mouse movement event.
Stopping the mouse for a little while and moving it again creates another mouse movement event.
Pressing a diverted key creates a key event.
When the key is released the sequence of events is sent as a synthetic notification
that can be matched with `Mouse Gesture` conditions.

### Mouse gestures
`Mouse Gesture` conditions are true if the actions (mouse movements and diverted key presses) taken while a mouse gestures button is held down match the arguments of the condition.
Mouse gestures buttons can be set using the 'Key/Button Diversion' setting, by changing the value to `Mouse Gestures`.
The arguments of a Mouse Gesture condition can be a direction, i.e., `Mouse Up`, `Mouse Down`, `Mouse Left`, `Mouse Right`, `Mouse Up-Left`, `Mouse Up-Right`, `Mouse Down-Left`, or `Mouse Down-Right`, or the Logitech name of a key.
If the first argument is the Logitech name of a key then that argument is matched against the button that was held down to initiate mouse gesture processing.
For example, a Mouse Gesture condition of `Mouse Up` -> `Mouse Up` would match pressing any Mouse Gestures button, moving the mouse upwards, pausing momentarily, moving the mouse upwards again, and releasing the button.
The condition `Smart Shift` -> `Mouse Down` -> `Back Button` would match pressing the Smart Shift button (provided that it is a Mouse Gestures button!), moving the mouse downwards, clicking the Back button (provided that it is diverted!), and then releasing the Smart Shift button.
Directions and buttons can be mixed and chained together however you like.
It's possible to create a `No-op` gesture by clicking 'Delete' on the initial Action when you first create the rule. This gesture will trigger when you simply click a Mouse Gestures button.

### Key modifiers
`Modifiers` conditions take either a string or a sequence of strings, which
can only be `Shift`, `Control`, `Alt`, and `Super`.
Modifiers conditions are true if their argument is the current keyboard
modifiers.

### Process focused
`Process` conditions are true if the process for the focused input window
or the window's Window manager class or instance name starts with their string argument.

### Window under cursor
`MouseProcess` conditions are true if the process for the window under the mouse
or the window's Window manager class or instance name starts with their string argument.

### Device notification and device active
`Device` conditions are true if a particular device originated the notification.
`Active` conditions are true if a particular device is active.
`Device` and `Active` conditions take one argument, which is the serial number or unit ID of a device,
as shown in Solaar's detail pane.
Some older devices do not have a useful serial number or unit ID and so cannot be tested for by these conditions.

### Host
`Host` conditions are true if the computers hostname starts with the condition's argument.

### Solaar device setting
`Setting` conditions check the value of a Solaar setting on a device.
`Setting` conditions take three or four arguments, depending on the setting:
the Serial number or Unit ID of a device, as shown in Solaar's detail pane,
or null for the device that initiated rule processing;
the internal name of a setting (which can be found from solaar config \<device\>);
one or two arguments for the setting.
For settings that use keys or buttons as an argument the Logtech name can be used
as shown in the Solaar main window for these settings,
or the numeric value for the key or button.
For settings that use gestures as an argument the internal name of the gesture is used,
which can be found in the GESTURE2_GESTURES_LABELS structure in lib/logitech_receiver/settings_templates.
For settings that need one of a set of names as an argument the name can be used or its internal integer value,
as used in the Solaar config file.

`Setting` conditions check device settings of devices, provided the device is on-line.
The first arguments to the condition are the Serial number or Unit ID of a device, as shown in Solaar's detail pane,
or null for the device that initiated rule processing; and
the internal name of a setting (which can be found from solaar config \<device\>).
Most simple settings take one extra argument, the value to check the setting value against.
Range setting can also take two arguments, which form an inclusive range to check against.
Other settings take two arguments, a key indicating which sub-setting to check and the value to check it against.
For settings that use gestures as an argument the internal name of the gesture is used,
which can be found in the GESTURE2_GESTURES_LABELS structure in lib/logitech_receiver/settings_templates.
For boolean settings '~' can be used to toggle the setting.

### Test and TestBytes
`Test` and `TestBytes` conditions are true if their test evaluates to true on the feature,
report and data of the current notification.
`TestBytes` conditions can return a number instead of a boolean.

`TestBytes` conditions consist of a sequence of three or four integers and use the first
two to select bytes of the notification data.
Writing this kind of test condition is not trivial.
Three-element `TestBytes` conditions are true if the selected bytes bit-wise AND
with its third element is non-zero.
The value of these test conditions is the result of the AND.
Four-element `TestBytes` conditions are true if the selected bytes form a signed
integer between the third and fourth elements.
The value of these conditions is the signed value of the selected bytes
if that is non-zero otherwise True.

`Test` conditions are mnemonic shorthands for meaningful feature,
report, and data combinations in notifications.
A `crown_right` test is the rotation amount of a `CROWN` right rotation notification.
A `crown_left` test is the rotation amount of a `CROWN` left rotation notification.
A `crown_right_ratchet` test is the ratchet amount of a `CROWN` right ratchet rotation notification.
A `crown_left_ratchet` test is the ratchet amount of a `CROWN` left ratchet rotation notification.
A `crown_tap` test is true for a `CROWN` tap notification.
A `crown_start_press` test is true for the start of a `CROWN` press notification.
A `crown_stop_press` test is true for the end of a `CROWN` press notification.
A `crown_pressed` test is true for a `CROWN` notification with the Crown pressed.
A `thumb_wheel_up` test is the rotation amount of a `THUMB WHEEL` upward rotation notification.
A `thumb_wheel_down` test is the rotation amount of a `THUMB WHEEL` downward rotation notification.
`lowres_wheel_up`, `lowres_wheel_down`, `hires_wheel_up`, `hires_wheel_down` are the
same but for `LOWRES WHEEL` and `HIRES WHEEL`.
`True` and `False` tests return True and False, respectively.

Solaar keeps track of the total signed displacement of the current thumb wheel movement.
This displacement is reset when the thumb wheel is inactive.
`thumb_wheel_up` and `thumb_wheel_down` tests take an optional integer parameter.
With a parameter the test is only true if the current thumb wheel displacement is greater than the parameter.
The displacement is then lessened by the amount of the parameter.

## Actions

### Key press
A `KeyPress` action takes either the name of an X11 key symbol, such as "a",
a list of X11 key symbols, such as "a" or "CTRL + A",
or a two-element list with the first element as above
and the second element one of `'click'`, `'depress'`, or `'release'`
and executes key actions on a simulated keyboard to produce these symbols.
Use separate `KeyPress` actions for multiple characters,
i.e., don't use a single `KeyPress` like 'a+b'.
The `KeyPress` action normally both depresses and releases (clicks) the keys,
but can also just depress the keys or just release the keys.
Use the depress or release options with extreme care,
ensuring that the depressed keys are later released,
otherwise it may become difficult to use your system.
The keys are depressed in forward order and released in reverse order.

If a key symbol can only be produced by a shfited or level 3 keypress, e.g., "A",
then Solaar will add keypresses to produce that key symbol,
e.g., simulating a left shift keypress to get "A" instead of "a".
If a key symbol is not available in the current keymap or needs other shift-like keys,
then Solaar cannot simulate it.
Under X11 Solaar can determine the current key modifiers (shift, control, etc.).
Any key symbols that correspond to these modifier keys are not depressed and released when clicking.
So if the shift key is currently down on a keyboard Solaar will not bother to simulate a shift key.
Under Wayland this check cannot be done so the net result of a `KeyPress` action that is not a `depress` or a `release`
and that contains modifier keys might be to release the modifier keys.

Simulating input in Linux is complex.
Solaar has to try to determine which keyboard key corresponds to which input character as it cannot directly
simulate inputting a key symbol.
Unfortunately, this determination can go wrong in several ways and is more likely
to go wrong under Wayland than under X11.

### Mouse scroll
A `MouseScroll` action takes a sequence of two numbers and simulates a horizontal and vertical mouse scroll of these amounts.
If the previous condition in the parent rule returns a number the scroll amounts are multiplied by this number.

### Mouse click
A `MouseClick` action takes a mouse button name (`left`, `middle` or `right`) and a positive number or 'click', 'depress', or 'release'.
The action simulates that number of clicks of the specified button or just one click, depress, or release of the button.
A `MouseClick` action takes a mouse button name (`left`, `middle` or `right`) and a positive number, and simulates that number of clicks of the specified button.
An `Execute` action takes a program and arguments and executes it asynchronously.

### Set setting
A `Set` action changes a Solaar setting for a device, provided that the device is on-line.
`Set` actions take three or four arguments, depending on the setting.
The first two are the Serial number or Unit ID of a device, as shown in Solaar's detail pane,
or null for the device that initiated rule processing; and
the internal name of a setting (which can be found from `solaar config <device>`).
Simple settings take one extra argument, the value to set the setting to.
For boolean settings `~` can be used to toggle the setting.
Other simple settings take two extra arguments, a key indicating which sub-setting to set and the value to set it to.
For settings that use gestures as an argument the internal name of the gesture is used,
which can be found in the GESTURE2_GESTURES_LABELS structure in `lib/logitech_receiver/settings_templates`.
All settings are supported.

### Later
A `Later` action executes rule components later.
`Later` actions take an integer delay in seconds between 1 and 100 followed by zero or more rule components that will be executed later.
Processing of the rest of the rule continues immediately.

## Built-in Rules

Solaar has a built-in rule, which is run after user-created rules and so can be overridden by user-created rules.
This rule turns
`Brightness Down` key press notifications into `XF86_MonBrightnessDown` key taps
and `Brightness Up` key press notifications into `XF86_MonBrightnessUp` key taps.

## Example Solaar Rule File

Solaar reads rules from a YAML configuration file (normally `~/.config/solaar/rules.yaml`).
This file contains zero or more documents, each a rule.

Here is a file with six rules:

```
%YAML 1.3
---
- Key: [M2, pressed]
- Set: [198E3EB8, dpi, 3000]
- Execute: [notify-send, Increased mouse speed]
...
---
- Key: [Host Switch Channel 2, pressed]
- Set: [43DAF041, change-host, 1]
- Set: [198E3EB8, change-host, 1]
- Execute: [notify-send, Switched to host 2]
...
---
- MouseGesture: [Mouse Up, Mouse Down]
- Execute: [notify-send, Locking]
- Execute: xflock4
...
- Feature: CROWN
- Process: quodlibet
- Rule: [ Test: crown_start_press, KeyPress: XF86_AudioMute ]
- Rule: [ Test: crown_pressed, Test: crown_right_ratchet, KeyPress: XF86_AudioNext ]
- Rule: [ Test: crown_pressed, Test: crown_left_ratchet, KeyPress: XF86_AudioPrev ]
- Rule: [ Test: crown_right_ratchet, KeyPress: XF86_AudioRaiseVolume ]
- Rule: [ Test: crown_left_ratchet, KeyPress: XF86_AudioLowerVolume ]
...
---
- Feature: THUMB WHEEL
- Rule: [ Modifiers: Control, Test: thumb_wheel_up, MouseScroll: [-2, 0] ]
- Rule:
  - Modifiers: Control
  - Test: thumb_wheel_down
  - MouseScroll: [-2, 0]
- Rule: [ Or: [ Test: thumb_wheel_up, Test: thumb_wheel_down ], MouseScroll: [-1, 0] ]
...
---
- Feature: LOWRES WHEEL
- Rule: [ Or: [ Test: lowres_wheel_up, Test: lowres_wheel_down ], MouseScroll: [0, 2] ]
...
```

## Button diversion example
Here is an example showing how to divert the Back Button on an MX Master 3 so that pressing
the button will initiate rule processing and a rule that triggers on this notification and
switches the mouse to host 3 after popping up a simple notification.

![Solaar-divert-back](screenshots/Solaar-main-window-back-divert.png)

![Solaar-rule-back-host](screenshots/Solaar-rule-editor.png)
