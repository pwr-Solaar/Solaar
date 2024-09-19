# <img src="https://pwr-solaar.github.io/Solaar/img/solaar.svg" width="60px"/> Solaar

Solaar is a Linux manager for many Logitech keyboards, mice, and other devices
that connect wirelessly to a Unifying, Bolt, Lightspeed or Nano receiver
as well as many Logitech devices that connect via a USB cable or Bluetooth.
Solaar is not a device driver and responds only to special messages from devices
that are otherwise ignored by the Linux input system.

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
