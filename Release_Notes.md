# Notes on Major Changes in Releases

## Version 1.1.15

* Solaar supports configuration of Bluetooth devices on macOS.

## Version 1.1.13

* Solaar will drop support for Python 3.7 immediately after version 1.1.13.

* Version 1.1.12 does not push settings to many devices after a resume resulting in the device reverting to its default behaviour.  This is fixed in 1.1.13.

## Version 1.1.12

* Solaar now processes DBus disconnection and connection messages from Bluez and re-initializes devices when they reconnect, to handle to a change introduced in Bluez 5.73. The HID++ driver does not re-initialize devices, which causes problems with smooth scrolling. Until the issue is resolved having Scroll Wheel Resolution set to true (and not ignored) may be helpful.

* The credits for translations have not been kept up to date.  Translators who are not listed can update docs/i18n.ml and lib/solaar/ui/about.py.

* Solaar now has settings for features BRIGHTNESS_CONTROL, RGB_EFFECTS, and PER_KEY_LIGHTING features.  The names of keys in the Per-key Lighting setting are for the standard US keyboard.  Users who wish to modify these names should look at the section Keyboard Key Names and Locations in `https://pwr-solaar.github.io/Solaar/capabilities`

* A unit test test suite is being constructed using pytest.

* The Solaar code for communicating with receivers and devices has been significantly modified to improve testability and organization.  Errors may have been introduced for uncommon hardware.

* The Later rule action uses precision timing for delays of less than one second.

* Solaar now indentifies supported devices by whether they support the HID protocols that Solaar needs.  If a device does not show up at all when running Solaar, it almost certainly cannot be supported by Solaar.

## Version 1.1.11

* Solaar can dump device profiles in YAMLfor devices that support profiles and load profiles back from an edited file.  See [the capabilities page](https://pwr-solaar.github.io/Solaar/capabilities) for more information.

* Solaar has settings for each LED Zone that a device supports under feature Color LED Effects.

* Solaar has settings for extended report rate, backlight levels, durations, and profile selection.

* Solaar now partly works in MacOS.  Please open new issues for problems.  Solaar may work in Windows.   Please open new issues for problems.  See https://github.com/pwr-Solaar/Solaar/pull/1971 for more information.  Fixing problems in MacOS or Windows may take considerable time.

* Solaar works better when the Python package hid-parser is available.   Distriubtions should try have this package installed.

## Version 1.1.10

* The mouse click rule action can now just simulate depressing or releasing the button.

* There is a new rule condition to check the hostname.

## Version 1.1.9

* Solaar now exits with at 0 exit code when killed.

* Two Solaar settings can interfere with the implementation of smooth scrolling in modern Linux HID++ drivers.  These settings are initially set to ignore so that this interference does not happen.

* The Device rule condition checks for the device that produced a notification.

* The KeyIsDown rule condition checks whether a *diverted* rule key is down.

## Version 1.1.8

* The thumb wheel rule conditions take an optional parameter that checks for total signed thumb wheel movement.

## Version 1.1.7

* Solaar responds to scroll wheel ratchet notifications by changing its scroll wheel ratcheting.

* Solaar processing of report descriptors is optional, depending on whether the package hid-parser is available.

## Version 1.1.6

* Solaar requires Python version 3.7.

* Solaar uses report descriptors to recognize unknown devices that use HID++.

* The Later rule action takes an integer delay in seconds and one or more rule components.  The action immediately completes while also scheduling the rule components for later exection.

## Version 1.1.5

* The Active rule condition takes the serial number or unitID of a device and checks whether the device is active.  A device is active if it is connected (via a receiver, USB or Bluetooth), not turned off, and not in a power-saving state.  This condition can be used to check whether changing a setting on the device will have any effect, as devices respond to messages only when active.

* Solaar logs warnings and errors to a file in the user's temporary file directory.  This file is deleted when Solaar exists normally.  If Solaar is run with `-dd` or `-ddd` informational messages are also logged in the file.

* If the first element of a Mouse Gesture rule condition is a key or button name then that name must be the same as the name of the key or button that initiated the mouse gesture.

* The Sliding DPI and Mouse Gestures are now set up using the Key/Button Diversion setting.   Changing a key or button to Sliding DPI makes it initiate the sliding DPI changing.  Changing a key or button to Mouse Gestures makes it initiate a mouse gesture.  There can be multiple keys or buttons for sliding DPI and multiple keys or buttons for mouse gestures.

* Solaar waits a few seconds to save settings changes to its configuration file.  If you interrupt Solaar soon after changing a setting the change might not be saved.


## Version 1.1.4

* There are settings for sidetone and equalizer gains for headsets.

* The KeyPress action can now either deppress, release, or click (default) keys.

* The KeyPress action now inserts shift and level 3 keypresses if simulating a key symbol requires one or both of them.  So producing a "B" no longer requires adding a shift keysymbol.

## Version 1.1.3

* Solaar uses yaml for configuration files, converting the json configuration file to yaml if necessary.

* Solaar rules work better under Wayland but still cannot access the current process nor the current keyboard modifiers.

* Solaar uses uinput for simulating input in Wayland.  See https://pwr-solaar.github.io/Solaar/rules for instructions on setting up uinput correctly.

## Version 1.1.2

* Solaar now depends on Python evdev.  It can be installed if needed via `pip install --user evdev` or, in most distributions, by installing the python3-evdev package.

* Solaar rules partly work under Wayland.  There is no access to the current process in Wayland.  Simulated input uses uinput if XTest extension not available, requiring read and write permissions on /dev/uinput.

* There is a setting to divert gestures so that they can trigger rules.

* There is a setting to disable Onboard Profiles, which can interfere with the Polling Rate and M-Key LEDs settings.  The Polling Rate setting no longer disables onboard profiles.

* There is a setting for the Persistent Remappable Keys feature.

* There is a new rule condition that tests device settings.

* There are new settings to set M-Key LEDs and MR-Key LED.

* There is a new kind of Solaar rule action to change settings for devices.

## Version 1.1.1

* There is a new setting to switch keyboard crowns between smooth and ratchet scrolling.

## Version 1.1.0

* Solaar now supports Bolt receivers and devices that connect to them, including authentication of devices when pairing.

* A setting has been added for the DPI CHANGE button to switch movement sensitivity.

## Version 1.0.7

* Solaar rules can now trigger on both pressing and releasing a diverted key.

* The new rule condition MouseProcess is like the Process condition except for the process of the window under the mouse.

* Mouse gestures have been upgraded.  A mouse gesture is now a sequence of movements separated by no movement periods while the mouse gesture button is held down.  The MouseGesture rule condition matches mouse gesture sequences.  The old mouse-up, etc., tests are converted to MouseGesture conditions.

## Version 1.0.6

* The sliding DPI setting now looks for suitable keys to use to trigger its effects.

* If a mouse has a suitable button it can generate mouse gestures, which trigger rule processing.  Mouse gestures need to be turned on and the button diverted to produce mouse gestures.

* Settings can now be ignored by clicking on the icon at the right-hand edge of a setting until the dialog error icon (usually a red icon) appears.   Solaar will not try to restore the value for an ignored setting.

* Icon handling in the tray and the tray menu has been updated to work better with some system tray implementations.

* The process rule condition also matches against the current X11 WM_CLASS.

* The SMART SHIFT ENHANCED feature is supported.

## Version 1.0.5

* Solaar has rules that can perform actions such as pressing keys or scrolling when certain HID++ feature notifications happen.  Users can change these rules either by editing ~/.config/solaar/rules.yaml or via a GUI.  Rules depend on X11 and so are only available under X11.  This is an experimental feature for Solaar and may undergo changes in the future.

* Each setting has a clickable lock icon that determines whether the setting can be changed.

## Version 1.0.4

* Devices that connect directly via Bluetooth or USB are now supported.  These devices show up in the GUI as separate lines, not under a receiver.  A device that is directly connected and also paired to a receiver will show up twice, but the entry under the receiver will not be active.  With this change identifying devices becomes more difficult so occasionally check your Solaar configuration file (at ~/.config/solaar/config.json) to see that there is only one entry for each of your devices.

* There are new settings for gestures, thumb wheels,  adjusting the wheel ratchet behavior, and changing DPI using a DPI Switch button.

* Solaar's Udev rule now adds seat permissions for all Logitech devices.  Users who install Solaar themselves will have to install the new Udev rule and activate the rule.  One way to do this is to restart the user's computer.

## Version 1.0.3

* The separate deprecated solaar-cli command has been removed.

* Devices can be switched between hosts using the Change Host setting.  The device will try to connect to the other host.  Some devices will detect that there is no active host on the other connections and reconnect back.

## Version 1.0.2

* The separate unneeded solaar-gnome3 command has been removed.  The packaging directories have been removed.

* Non-unifying receivers are modelled better.  Many of them cannot unpair but instead new pairings replace existing pairings.

* Battery icon selection has been simplified.
