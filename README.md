# <img src="https://pwr-solaar.github.io/Solaar/img/solaar.svg" width="60px"/> Solaar-Battery

**Solaar-Battery** is a customized, feature-rich fork of Solaar for managing Logitech wireless peripherals, specifically designed with advanced RGB battery monitoring and enhanced profile management. 

*(Like the original Solaar, it connects wirelessly to Unifying, Bolt, Lightspeed, or Nano receivers, as well as via USB cable or Bluetooth.)*

<a href="https://pwr-solaar.github.io/Solaar/index">Original Solaar Docs</a> -
<a href="https://pwr-solaar.github.io/Solaar/usage">Usage</a> -
<a href="https://pwr-solaar.github.io/Solaar/capabilities">Capabilities</a> -
<a href="https://pwr-solaar.github.io/Solaar/rules">Rules</a> 

[![codecov](https://codecov.io/gh/pwr-Solaar/Solaar/graph/badge.svg?token=D7YWFEWID6)](https://codecov.io/gh/pwr-Solaar/Solaar)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2+-blue.svg)](../LICENSE.txt)

---

## ✨ What's New in Solaar-Battery?

### 🔋 Dynamic Battery LED Configurator
Never guess your mouse's battery level again. Solaar-Battery intelligently hijacks the primary RGB lighting zone on compatible Logitech G-Series hardware (such as the G305, G Pro Wireless, G502 Lightspeed, etc.) to act as a real-time battery indicator.

* **Intelligent Color Mapping:** The mouse RGB dynamically shifts colors based on your current battery percentage:
  * 🟢 **100% - 70%:** Green
  * 🟡 **69% - 45%:** Yellow
  * 🟠 **44% - 20%:** Orange
  * 🔴 **19% - 6%:** Red
  * 🚨 **< 5%:** Blinking Red (Critical)
* **Hardware-Bypassing Brightness Control:** Includes a custom "Battery LED Brightness" slider directly in the GUI. Because Logitech's proprietary firmware aggressively caches static lighting commands, Solaar-Battery includes a custom "Apply" macro that programmatically restarts the LED state machine, allowing you to dim or brighten the battery indicator colors seamlessly.

### 💾 Enhanced Profile Management
Solaar-Battery features a completely overhauled profile saving and deletion system, fixing native bugs present in the original Solaar codebase.

* **Explicit Profile Saving:** Prevents the "save-on-keystroke" bug. Solaar-Battery strictly binds profile creation to an explicit "Save Profile" button (or by hitting the `Enter` key), keeping your configuration files clean and intentional.
* **1-Click Profile Deletion:** Adds a dedicated "Delete Profile" button to the main GUI. Solaar-Battery completely bypasses the GTK signal-looping bugs that normally prevent profiles from being cleanly removed from the `profiles.json` cache, allowing for instant, error-free profile management.

### 🎨 Custom Branding & Aesthetics
* Rebranded as **Solaar-Battery** with custom high-resolution icons integrated directly into the system tray, application launcher, and internal GUI windows.

### 🖱️ Hardware Compatibility
Solaar-Battery's dynamic RGB battery indicator is built to automatically deploy on any connected device that meets two criteria:
1. It is a wireless, battery-powered device.
2. It features a software-controllable RGB lighting zone (utilizing Logitech's `led_zone_1` HID++ protocol).

*(Note: Devices lacking programmable RGB chips, such as the MX Master series or the G Pro X Superlight, will still function normally but will not display the Battery LED Configurator.)*

---

## 📷 Screenshots

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

---

## 💻 Standard Solaar Features
In addition to the custom features above, Solaar-Battery retains all original Solaar functionality. Solaar supports:
- pairing/unpairing of devices with receivers
- configuring device settings
- custom button configuration
- running rules in response to special messages from devices

For more information see
    <a href="https://pwr-solaar.github.io/Solaar/index">the main Solaar documentation page.</a>


## 📦 Installation Packages

Up-to-date prebuilt packages are available for some Linux distros (e.g., Fedora) in their standard repositories. If a recent version of Solaar is not available from the standard repositories for your distribution, you can try one of these packages:

- Arch solaar package in the [extra repository][arch]
- Ubuntu/Kubuntu package in [Solaar stable ppa][ppa stable]
- NixOS Flake package in [Svenum/Solaar-Flake][nix flake]

Solaar is available from some other repositories but may be several versions behind the current version:

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
