			Notes on Major Changes in Releases

Version 1.1.0:

Solaar now supports Bolt receivers and devices that connect to them, including authentication of devices when pairing.

A setting has been added for the DPI CHANGE button to switch movement sensitivity.

Version 1.0.7:

Solaar rules can now trigger on both pressing and releasing a diverted key.

The new rule condition MouseProcess is like the Process condition except for the process of the window under the mouse.

Mouse gestures have been upgraded.  A mouse gesture is now a sequence of movements separated by no movement periods while the mouse gesture button is held down.  The MouseGesture rule condition matches mouse gesture sequences.  The old mouse-up, etc., tests are converted to MouseGesture conditions.


Version 1.0.6:

The sliding DPI setting now looks for suitable keys to use to trigger its effects.

If a mouse has a suitable button it can generate mouse gestures, which trigger rule processing.  Mouse gestures need to be turned on and the button diverted to produce mouse gestures.

Settings can now be ignored by clicking on the icon at the right-hand edge of a setting until the dialog error icon (usually a red icon) appears.   Solaar will not try to restore the value for an ignored setting.

Icon handling in the tray and the tray menu has been updated to work better with some system tray implementations.

The process rule condition also matches against the current X11 WM_CLASS.

The SMART SHIFT ENHANCED feature is supported.


Version 1.0.5:

Solaar has rules that can perform actions such as pressing keys or scrolling when certain HID++ feature notifications happen.  Users can change these rules either by editing ~/.config/solaar/rules.yaml or via a GUI.  Rules depend on X11 and so are only available under X11.  This is an experimental feature for Solaar and may undergo changes in the future.

Each setting has a clickable lock icon that determines whether the setting can be changed.


Version 1.0.4:

Devices that connect directly via Bluetooth or USB are now supported.  These devices show up in the GUI as separate lines, not under a receiver.  A device that is directly connected and also paired to a receiver will show up twice, but the entry under the receiver will not be active.  With this change identifying devices becomes more difficult so occasionally check your Solaar configuration file (at ~/.config/solaar/config.json) to see that there is only one entry for each of your devices.

There are new settings for gestures, thumb wheels,  adjusting the wheel ratchet behavior, and changing DPI using a DPI Switch button.

Solaar's Udev rule now adds seat permissions for all Logitech devices.  Users who install Solaar themselves will have to install the new Udev rule and activate the rule.  One way to do this is to restart the user's computer.


Version 1.0.3:

The separate deprecated solaar-cli command has been removed.

Devices can be switched between hosts using the Change Host setting.  The device will try to connect to the other host.  Some devices will detect that there is no active host on the other connections and reconnect back.


Version 1.0.2:

The separate unneeded solaar-gnome3 command has been removed.  The packaging directories have been removed.

Non-unifying receivers are modelled better.  Many of them cannot unpair but instead new pairings replace existing pairings.

Battery icon selection has been simplified.
