---
title: Known Issues
layout: page
---

# Known Issues

- Some internal structures in Solaar have been updated to use more standard Python language features.
  This has caused some problems and introduced bugs are still being found.

- Onboard Profiles, when active, can prevent changes to other settings, such as Polling Rate, DPI, and various LED settings. Which settings are affected depends on the device.  To make changes to affected settings, disable Onboard Profiles.  If Onboard Profiles are later enabled the affected settings may change to the value in the profile.

- Bluez 5.73 does not remove Bluetooth devices when they disconnect.
  Solaar 1.1.12 processes the DBus disconnection and connection messages from Bluez and does re-initialize devices when they reconnect.
  The HID++ driver does not re-initialize devices, which causes problems with smooth scrolling.
  Until the problem is resolved having Scroll Wheel Resolution set to true (and not ignored) may be helpful.

- The Linux HID++ driver modifies the Scroll Wheel Resolution setting to
  implement smooth scrolling.  If Solaar changes this setting, scrolling
  can be either very fast or very slow.  To fix this problem
  click on the icon at the right edge of the setting to set it to
  "Ignore this setting", which is the default for new devices.
  The mouse has to be reset (e.g., by turning it off and on again) before this fix will take effect.

- Solaar expects that it has exclusive control over settings that are not ignored.
  Running other programs that modify these settings, such as logiops,
  will likely result in unexpected device behavior.

- The driver also sets the scrolling direction to its normal setting when implementing smooth scrolling.
  This can interfere with the Scroll Wheel Direction setting, requiring flipping this setting back and forth
  to restore reversed scrolling.

- The driver sends messages to devices that do not conform with the Logitech HID++ specification
  resulting in responses being sent back that look like other messages.  For some devices this causes
  Solaar to report incorrect battery levels.

- Solaar normally uses icon names for its icons, which in some system tray implementations
  results in missing or wrong-sized icons.
  The `--tray-icon-size` option forces Solaar to use icon files of appropriate size
  for tray icons instead, which produces better results in some system tray implementations.
  To use icon files close to 32 pixels in size use `--tray-icon-size=32`.

- The icon in the system tray can show up as 'black on black' in dark
  themes or as non-symbolic when the theme uses symbolic icons.  This is due to problems
  in some system tray implementations. Changing to a different theme may help.
  The `--battery-icons=symbolic` option can be used to force symbolic icons.

- Solaar will try to use uinput to simulate input from rules under Wayland or if Xtest is not available
  but this needs write permission on /dev/uinput.
  For more information see [the rules page](https://pwr-solaar.github.io/Solaar/rules).

- Diverted keys remain diverted and so do not have their normal behavior when Solaar terminates
  or a device disconnects from a host that is running Solaar.  If necessary, their normal behavior
  can be reestablished by turning the device off and on again.  This is most important to restore
  the host switching behavior of a host switch key that was diverted, for example to switch away
  from a host that crashed or was turned off.

- When a receiver-connected device changes hosts Solaar remembers which diverted keys were down on it.
  When the device changes back the first time any of these diverted keys is depressed Solaar will not
  realize that the key was newly depressed.  For this reason Solaar rules that can change hosts should
  trigger on key releasing.
