# <img src="https://pwr-solaar.github.io/Solaar/img/solaar.svg" width="60px"/> Solaar

Solaar is a Linux manager for many Logitech keyboards, mice, and other devices
that connect wirelessly to a Unifying, Bolt, Lightspeed or Nano receiver
as well as many Logitech devices that connect via a USB cable or Bluetooth.
Solaar is not a device driver and responds only to special messages from devices
that are otherwise ignored by the Linux input system.

## 🔧 Fork Notice: G515 TKL RGB Workaround

**This is a fork of the official Solaar project with a specific workaround for Logitech G515 TKL keyboards.**

### Background

The Logitech G515 TKL keyboard has a firmware behavior where it resets RGB LED settings to the default blue breathing pattern after approximately 58 seconds of keyboard inactivity. This happens because the keyboard enters a power-saving mode that overwrites Solaar's RGB configuration.

### Understanding the Maintainer's Position

The official Solaar maintainers declined to implement this workaround in the main project, and their reasoning is completely understandable:

- **Device-specific fixes**: Adding workarounds for individual device quirks can lead to code bloat and maintenance burden
- **Proper firmware fix**: The ideal solution would be a firmware update from Logitech to fix the underlying power management issue
- **Limited scope**: The workaround only benefits users of a specific keyboard model
- **Maintainability**: Device-specific workarounds can be fragile and difficult to maintain long-term

The github issue is here: https://github.com/pwr-Solaar/Solaar/issues/2791

### How the Workaround Works

This fork implements a targeted solution that:

1. **Monitors keyboard activity**: Tracks the timestamp of the last keyboard event using Solaar's notification system
2. **Detects the critical window**: When a key is pressed after 55+ seconds of inactivity (just before the 58-second firmware timeout)
3. **Preemptively refreshes settings**: Immediately reapplies all RGB settings before the key event is processed
4. **Maintains user experience**: The RGB configuration is restored seamlessly without user intervention

The implementation:
- Uses Solaar's existing notification handler system for efficiency
- Only activates on keyboards with the RGB_EFFECTS feature
- Includes proper cleanup and error handling
- Adds minimal overhead to normal keyboard operation

### Technical Details

- **Activation**: Automatically detects G515 TKL keyboards (USB ID: 0xC358) and enables the workaround
- **Compatibility**: Works with any keyboard that has RGB_EFFECTS feature and exhibits similar behavior
- **Performance**: Uses event-driven architecture with minimal impact on system resources
- **Reliability**: Includes comprehensive error handling and logging

### Installation

Use this fork exactly like the official Solaar - all standard installation methods work the same way.

#### For G515 TKL RGB Workaround:

1. **Add yourself to the input group** (required for keyboard event monitoring):
   ```bash
   sudo usermod -a -G input $USER
   ```
   Then log out and log back in (you may need to terminate your X session).

2. **Run Solaar with input group permissions**:
   ```bash
   # Normal mode (clean output)
   sg input -c "bin/solaar --window=none"
   
   # Debug mode (detailed RGB refresh logging)
   sg input -c "bin/solaar --window=none -ddd"
   ```

   **Note**: The `--window=none` option (added in this fork) disables both the main window and system tray icon, running Solaar in pure background mode. This is ideal for the RGB refresh workaround as it only needs to run in the background to monitor keyboard activity.

3. **Verify it's working**: With debug mode (`-ddd`), you should see:
   - `RGB refresh workaround enabled with evdev monitoring`
   - `evdev monitoring started for X devices`
   - Key events: `Key event detected: KEY_X = 1, time since last: X.Xs`
   - RGB refresh: `55+ seconds passed (X.Xs), refreshing RGB settings!`

### Status

✅ **Complete**: The RGB refresh workaround is fully implemented and tested
✅ **Production Ready**: Includes proper error handling and Solaar logging integration
✅ **Performance Optimized**: Uses efficient evdev monitoring with minimal system impact

### Technical Implementation

The workaround uses:
- **evdev monitoring** for real-time keyboard event detection
- **55-second threshold** to refresh RGB settings just before firmware timeout
- **Comprehensive RGB refresh** including rgb_control, rgb_zone_1, brightness_control, and per-key-lighting
- **Proper Solaar logging** with debug levels (-d, -dd, -ddd)
- **Automatic fallback** to timer-based approach if evdev is unavailable

### Additional Fork Features

#### Enhanced Window Control Options

This fork adds an additional `--window=none` option to the existing window control:

- `--window=show` (default): Start with main window visible
- `--window=hide`: Start with main window hidden but system tray icon visible
- `--window=only`: Show main window without system tray icon
- `--window=none` (**new**): Disable both main window and system tray icon (pure background mode)

---

<a href="https://pwr-solaar.github.io/Solaar/index">More Information</a> -
<a href="https://pwr-solaar.github.io/Solaar/usage">Usage</a> -
<a href="https://pwr-solaar.github.io/Solaar/capabilities">Capabilities</a> -
<a href="https://pwr-solaar.github.io/Solaar/rules">Rules</a> -
<a href="https://pwr-solaar.github.io/Solaar/installation">Manual Installation</a>


[![codecov](https://codecov.io/gh/pwr-Solaar/Solaar/graph/badge.svg?token=D7YWFEWID6)](https://codecov.io/gh/pwr-Solaar/Solaar)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2+-blue.svg)](../LICENSE.txt)

<p align="center">
<img src="https://pwr-solaar.github.io/Solaar/screenshots/Solaar-main-window-multiple.png" width="54%"/>
  &#160;
<img src="https://pwr-solaar.github.io/Solaar/screenshots/Solaar-main-window-receiver.png" width="43%"/>
</p>

<p align="center">
<img src="https://pwr-solaar.github.io/Solaar/screenshots/Solaar-main-window-back-divert.png" width="49%"/>
  &#160;
<img src="https://pwr-solaar.github.io/Solaar/screenshots/Solaar-rule-editor.png" width="48%"/>
</p>

Solaar supports:
- pairing/unpairing of devices with receivers
- configuring device settings
- custom button configuration
- running rules in response to special messages from devices

For more information see
    <a href="https://pwr-solaar.github.io/Solaar/index">the main Solaar documentation page.</a> -


## Installation Packages

Up-to-date prebuilt packages are available for some Linux distros
(e.g., Fedora) in their standard repositories.
If a recent version of Solaar is not
available from the standard repositories for your distribution, you can try
one of these packages:

- Arch solaar package in the [extra repository][arch]
- Ubuntu/Kubuntu package in [Solaar stable ppa][ppa stable]
- NixOS Flake package in [Svenum/Solaar-Flake][nix flake]

Solaar is available from some other repositories
but may be several versions behind the current version:

- a [Debian package][debian], courtesy of Stephen Kitt
- a Ubuntu package is available from [universe repository][ubuntu universe repository]
- a [Gentoo package][gentoo], courtesy of Carlos Silva and Tim Harder
- a [Mageia package][mageia], courtesy of David Geiger

[ppa stable]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/stable
[arch]: https://www.archlinux.org/packages/extra/any/solaar/
[gentoo]: https://packages.gentoo.org/packages/app-misc/solaar
[mageia]: http://mageia.madb.org/package/show/release/cauldron/application/0/name/solaar
[ubuntu universe repository]: http://packages.ubuntu.com/search?keywords=solaar&searchon=names&suite=all&section=all
[nix flake]: https://github.com/Svenum/Solaar-Flake
[debian]: https://packages.debian.org/search?keywords=solaar&searchon=names&suite=all&section=all
