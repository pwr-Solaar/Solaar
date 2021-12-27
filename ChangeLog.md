# 1.1.1

* Keep left pane in Solaar main window the same size
* Fix crash when checking a process condition when X11 not running
* Add version number to output of solaar show
* Fix crash when pinging a device with unknown protocol
* Display battery percentage estimates from battery voltage
* Add minimal support for Logitech PRO X Wireless Gaming Headset
* Push settings when device requests software reconfiguration
* Fix read for key/button diversion setting
* Add modalias information to Solaar metainfo
* Don't do on-screen notifications when devices are powered on
* Add setting to switch crown between smooth and ratchet scrolling
* Add write_prefix_bytes argument to Boolean validator
* Update Russian and Spanish translations
* New shell script tools to help determine capabilities of receivers
* Add special keys for MX Keys for Business and MX Keys Mini
* Improve tray menu ordering
* Add --tray-icon-size option to get around bugs in some tray implementations

# 1.1.0

* Fix bug when adding receiver to tray menu
* Add Catalan translation.
* Add toggle command to solaar config to toggle boolean settings
* Don't select windows with no PID when looking for focus window
* Catch errors when applying settings so that other settings are not affected
* Add support for Bolt receivers and devices, including pairing
* Revise method for creating system tray menu
* Remove obsolete code (mostly Python 2 compatibility code)
* Add support for PRO X Wireless Mouse, G914 TKL keyboard
* Ignore more notifications that come to a device listener
* Handle more device connection protocols
* Update usage and rules documentation
* Change emojis to text in documentation
* Pare down device documentation so as not to require frequent updates
* Add information about M500S mouse
* Reimplement MOUSE GESTURE and DPI SLIDING settings
* Add setting for DPI CHANGE button to switch sensitivity
* Use file name instead of icon name for tray to avoid XFCE bug
* Update documentation on implemented features and mouse gestures
* Update Polish, Japanese, and Spanish translations
* Make Quit and About strings more translatable

# 1.0.7

* Don't use time_ns so as not to require Python 3.7
* Correctly determine setting box in change_click method
* Handle fake Nano connection notifications
* Lock on actual handle, not just on handle number
* Mark Nano receiver C52F as not unpairing
* Upgrade pairing/unpairing documentation
* Don't signal status change when battery changes from None to None.
* Add Japanese translation
* Use first word of name for code name if no other code name available.
* Better determination of when to add SW ID.
* Check for more HID++ feature request failing.
* Fix bug with new_fn_inversion setting.
* Use correct device number for directly connected devices
* Add debug message when candidate device found
* Update Polish, Taiwanese, and Brazilian Portuguese translations
* Add MouseProcess a rule condition like Process but for the window under the mouse
* Add parameters for binary settings to support prefixes
* Add locks to serialize requests to devices
* Fix bug when reprog key requests returns None
* Fix bug for empty process name and class
* Rules can now trigger on both pressing and releasing a diverted key
* Upgrade mouse gestures to allow sequences of movements
* Fix gkeys diversion faked read
* Add support for Logitech g pro x superlight receiver
* Convert HID++ 2.0 device kinds to enhanced HID++ 1.0 device kinds
* Update about window, bug report templates, and supported kernels.

# 1.0.6

* Update sliding DPI to look for suitable keys
* Add mouse gestures that can trigger rules
* Complain if receivers do not support connection notification
* In polling rate setting, only modify onboard profiles when actually writing polling rate
* Add ability to ignore settings.
* Use symbols for receiver sub-registers
* Add support for wired G700
* Do not set attention icon
* Replace deprecated GTK stock menu icons
* Better handling of icons in tray and tray menus
* Receiver c52e does not unpair
* Match active WM_CLASS as well as active process name in rules
* Correctly set icon theme value when regular battery icons are not available
* Handle exception when device is not available when device is being added
* Perform initial activation of devices in listener threads
* Keep track of serial numbers in the configuration file
* Don't update settings for non-active devices
* Set the current host name if not stored on the device
* Add setting for SMART SHIFT ENHANCED feature
* Don't unnecessarily use long messages for HID++ 1.0 commands
* Correctly select choices in solaar config and use 1-origin addressing
* Add quirk for G915 TKL keyboard because its host mode interferes with its Fn keys
* Show command outputs both saved and on-device settings
* Update documentation
* Fix bug in hidconsole
* Update French translation

# 1.0.5

* Update documentation on devices forgetting settings.
* Improve help messages
* Fix bug in finding receiver to pair
* Solaar config command can set keyed settings.
* Add setting for polling rate
* Use long HID++ messages for all 2.0 requests
* Update German, Italian, and Polish translations
* Solaar config command no longer selects paired but unconnected devices
* Show HID++ 1.0 remaining pairings value in solaar show for devices that support it
* Add option to not use battery icons in system tray.
* Update Polish and Dutch translation.
* Add Czech translation.
* Remove information on SUSE package as it is very old.
* Turn GKEY notifications into Gn key keypresses that can trigger rules.
* Push device settings to devices after suspend when device is immediately active.
* Reduce unnecessary saving of configuration file.
* Better handling of disconnected devices.
* Implement GUI to edit rules.
* Implement rule-base processing of HID++ feature notifications (depends on X11).
* Add settings for diversion of crown and remappable keys.
* Access widgets by name instead of by index.
* Implement UNIFIED_BATTERY feature and use in battery reports.
* Add a clickable lock icon that determines where each setting can be changed.

# 1.0.4

* Update pt_BR translation
* Support USB and BT connected devices that are not in descriptors.py
* Use FRIENDLY NAME for codename if needed and available.
* Extract manufacturer and product ID from Udev HID information.
* Add Bluetooth and USB product IDs to device descriptors records.
* Support Bluetooth-connected devices.
* Add model ID and unit ID to device identification.
* Support changing DPI by pressing DPI Switch button and sliding horizontally
* Add device-specific notification handlers.
* Add MX Vertical USB information.
* Udev rule adds seat permissions for all Logitech devices.
* Support USB-connected devices in GUI.
* Make probe and config work for USB-connected devices.
* Improve strings and display for settings.
* Correctly handle non-unifying connection notifications.
* Update GUI strings for several settings.
* Better support for EX100 and devices that connect to it.
* Partial support for feature GESTURE_2.
* Simplify interface for settings.
* Use DJ connection notifications to set device active status
* Udev rule sets seat write permissions for hidraw nodes for device as well as receivers.
* Handle USB devices that use HID++ protocol in CLI.
* Use device hidraw nodes where possible.
* Handle receivers with serial numbers that don't provide number of pairings.
* Ignore exceptions when setting locale.
* Correctly discover settings that share a name.
* Don't show pop-up notifications at startup.
* Keep battery voltage updated in GUI.
* Add Portuguese translation.
* Update several translations.
* Add Lightspeed receivers c545 and c541.
* Reimplement REPROG_CONTROLS data structure.

# 1.0.3

* Clean up documentation files.
* Update documentation on installation.
* Update Swedish and French translations.
* Add Norwegian Nynorsk and Danish translations.
* Fix bug handling DJ pairing notifications.
* Add Norwegian Bokmål translation.
* Remove deprecated solaar-cli application.
* Don't install udev or autostart files from python (or pip).
* Solaar needs Python 3.6+ and probably needs kernel 5.2+
* Handle exceptions on dynamic settings when device is not connected.
* Fix infinite loop on some low-level write errors
* Add support for EX100 keyboard/mouse and receiver (046d:c517)
* Add two settings for THUMB_WHEEL feature - inversion and reporting via HID++
* Update German translation
* Use REPORT RATE feature when available to determine polling rate.
* Improve config command speed when not printing all settings
* Improve config command handling and checking of arguments
* Add setting for CHANGE_HOST feature
* Add argument to settings for values that are not to persist
* Add argument to settings to not wait for reply when writing a value to device
* Add argument to not wait for reply from request to device
* Add settings for MULTIPLATFORM and DUALPLATFORM features
* Remove Logitech documents from documentation directory
* Change config command to not read all settings when only printing or showing one
* Display hosts info in 'solaar show' if device supports it
* Remove non-working smooth-scroll from M510 v1
* Add yapf and flake8 code style checks
* Fix feature k375s Fn inversion
* Update controls (keys and buttons) and tasks (actions)
* Improved way to specify feature settings.
* Don't abort on device notifications with unexpected device numbers, just warn.
* Keep track of non-features so as not to ask device multiple times.
* Implement KEYBOARD DISABLE KEYS feature.
* Don't create notifications for DJ device activity reports.
* Update a few special keys and actions.
* Add keyed choice settings in configuration panel.
* Support remappable keys from reprogrammable keys v4 feature.
* Add setting class for keyed choice.
* Only check for features once per device.
* Use settings interface to show feature values in `solaar show` if no special code for feature.
* Remove maximum window size.
* Process battery voltage notifications.
* Display battery voltage information in main window if regular battery information not available.
* Show next battery level where available.
* Update list of implemented features and provide information on how to implement features.
* Add c53d as a Lightspeed receiver.

# 1.0.2

* Add usage document
* Don't produce error dialog for inaccessible receivers with access control lists.
* Add option --battery-icons=symbolic to use symbolic icons if available.
* Update French translation
* Update installation documentation
* Remove packaging directory tree as it is not maintained
* Pip installs udev rule and solaar autostart when doing install without --user flag
* Use Solaar icon instead of a missing battery icon
* Use only standard icons for battery levels.  Symbolic icons do not change to white in dark themes because of problems external to Solaar.
* Better reporting of battery levels when charging for some devices.
* Add information on K600 TV, M350 WIPD 4080, and MX Keys
* Remove assertion requiring receivers to still be in window when they are updated.
* Augment long description of Solaar showing up in repositories.
* Update installation directions.
* Install udev rule as well as autostart file when doing system install.
* Add support for Ayatana AppIndicator.
* Use setuptools icon directory on system installs when not using pip.
* Add receiver C517 and several older devices.
* Improved translations for polish.
* Bypass bug in appindicator when solaar is file in current directory.
* Don't check that device kind matches feature kind.
* Better determination of icons for battery levels.
* Use Ayatana AppIndicator if available.
* Improve error reporting when required system packages are not install.
* Better tooltip description
* Add release script to help when creating releases
* Look up tray icon filenames to get around a bug in libappindicator.
* Make the default behavior be to show the main window at startup.
* Support c537 nano receiver
* Add logind signals for suspend/resume.
* Remove solaar-gnome3 package
* Ignore features for devices that don't follow feature specification
* Add probe command to command-line interface to dump receiver registers
* Don't terminate on malformed or unknown messages
* Create fewer internal notifications for messages from devices
* Add a button to the main window to terminate (quit) Solaar
* Set up nano receivers as receivers with no unpairing and with re-pairing
* Set up c534 as receiver with max 2 pairings, no unpairing, re-pairing
* Better support receivers that do not unpair or when pairing replace existing pairings
* Add information about receiver pairing to receiver data structure
* Better support devices that only allow a limited number of total re-pairings
* Add --window option to control main window visibility and tray usage
* Ignore receiver if USB id is not retrieved
* Fix bug with double deleting when devices are disconnected
* Determine some receiver information from data structure for USB ids
* Treat battery level of 0 as unknown
* Fix bug on devices with no serial number
* Drop support for python2, and use python3 throughout
* Fix bug in remembering features discovered from device reports
* Show icons in main window device list
* Count offline devices when determining whether pairing is possible
* Update French, Dutch, German, and Croatian translations
* Better icons for battery levels
* Support DPI, Backlight 2, Battery Voltage features
* Support M585, M590, M330, MX Master 2s and 3, new M310, new K800, craft keyboard
* Documentation improvements
* Clean up directory structure and remove unused files

# 1.0.1

* Updated the repo url.
* Fixed typo which was crashing the application.
* Improved the HID write routine which was causing issues on some devices.
* Fix non-unifying receivers in Linux 5.2.
* Add new Lightspeed receiver (used in the G305)

# 1.0.0

* Too many to track...

# 0.9.3

* Merged solaar-cli functionality into main solaar.
* Scrolling over the systray icon switches between multiple peripherals.
* Swedish translation courtesy of Daniel Zippert and Emelie Snecker
* French translation courtesy of Papoteur, David Geiger and Damien Lallement.
* Fixed some untranslated strings.

# 0.9.2

* Added support for hand detection on the K800.
* Added support for V550 and V450 Nano.
* Fixed side-scrolling with the M705 Marathon.
* Fixed identification of the T650 Touchpad.
* Added internationalization support and romanian translation.
* Polish translation courtesy of Adrian Piotrowicz.

# 0.9.1

* When devices report a battery alert, only show the alert once.
* Make sure devices in the window tree are sorted by registration index.
* Added an autostart .desktop file.
* Replaced single-instance code with GtkApplication.
* Fixed identification of the M505 mouse.
* Fixed an occasional windowing layout bug with the C52F Nano Receiver.

# 0.9.0

* New single-window UI.
* Performance MX leds show the current battery charge.
* Support the VX Nano mouse.
* Faster and more accurate detection of devices.
* If upower is accessible through DBus, handle suspend/resume.
* Replaced Solaar icons with SVGs.
* Running solaar-cli in parallel with solaar is now less likely to cause issues.
* Bugfixes to saving and applying device settings.
* Properly handle ^C when running in console.

# 0.8.9

* Improved support for gnome-shell/Unity.
* Persist devices settings between runs.
* Fixed reading of MK700 keyboard battery status.
* Use battery icons from the current theme instead of custom ones.
* Debian/Ubuntu packages now depend on an icon theme, to make sure
  no missing icons appear in the application window.
* Fixed missing icons under Kubuntu.
* Many more bug-fixes and reliability improvements.

# 0.8.8

* Partial support for some Nano receivers.
* Improved support for some devices: M510, K800, Performance MX.
* Improved battery support for some HID++ 1.0 devices.
* Properly handle device loss on computer sleep/wake.
* Better handling of receiver adding and removal at runtime.
* Removed a few more unhelpful notifications.
* Incipient support for multiple connected receivers.
* More Python 3 fixes.

# 0.8.7

* Don't show the "device disconnected" notification, it can be annoying and
  not very useful.
* More robust detection of systray icon visibility.

# 0.8.6

* Ensure the Gtk application is single-instance.
* Fix identifying available dpi values.
* Fixed locating application icons when installed in a custom prefix.
* Fixed some icon names for the oxygen theme.
* Python 3 fixes.
