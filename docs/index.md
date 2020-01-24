---
title: Solaar
layout: default
---

**Solaar** is a Linux manager for Logitech's peripherals that connect via a USB [Unifying][unifying], Lightspeed, or Nano receiver . It is able to pair/unpair devices with 
receivers and for most devices show battery status.  Solaar can also control
some of the changeable features of the devices, such as smooth scrolling or
function key behavior.  Solaar does not work with Logitech peripherals that
use Bluetooth or peripherals from other companies.

Solaar can be used as a GUI application or via its command-line interface.
Both are able to list the devices paired to a receiver,
show detailed info for each device, and
pair/unpair supported devices with the receiver.
For more information on the capabilities of Solaar see
[docs/capabilities.md](https://pwr-solaar.github.io/Solaar/capabilities).

Solaar does not handle normal input from the peripherals.  It is thus unable
to fix problems that arise from incorrect handling of mouse movements or keycodes
by Linux drivers or other software.

Solaar has progressed past version 1.0.  Problems with earlier versions should
not be reported as bugs.  Instead upgrade to a recent version or manually install
the current version from [github](https://github.com/pwr-Solaar/Solaar).

[unifying]: https://en.wikipedia.org/wiki/Logitech_Unifying_receiver

## Supported Devices

**Solaar** will detect all devices paired with your Unifying, Lightspeed, or Nano
receiver, and at the very least display some basic information about them.
Solaar can pair and unpair a Logitech device showing the Unifying logo (Solaar's version of the [logo][logo])
with any Unifying receiver and can pair and unpair devices with Lightspeed receivers.
Solaar can pair some Logitech
devices with Logitech Nano receivers but not all Logitech devices can be
paired with Nano receivers.  Logitech devices without a Unifying logo
generally cannot be paired with Unifying receivers.

For some devices, extra settings (usually not available through the standard
Linux system configuration) are supported. For a list of supported devices
and their features, see [docs/devices.md](https://pwr-solaar.github.io/Solaar/devices).

[logo]: https://pwr-solaar.github.io/Solaar/assets/solaar.svg

## Pre-built packages

Pre-built packages are available for a few Linux distros.

* Arch `solaar` package in the [community repository][arch]
* Debian 7 (Wheezy) or higher: packages in this [repository](https://pwr-solaar.github.io/Solaar/debian)
* Ubuntu/Kubuntu 16.04+: use the `solaar-gnome3` and/or `solaar` package from [universe repository][universe repository]
* Ubuntu/Kubuntu stable packages: use `solaar-gnome3` and/or `solaar`  package from [Solaar stable ppa][ppa2]
* Ubuntu/Kubuntu git build packages: use `solaar-gnome3` and/or `solaar`  package from [Solaar git ppa][ppa1]
* a [Fedora package][fedora], courtesy of Eric Smith
* a [Gentoo package][gentoo], courtesy of Carlos Silva and Tim Harder
* a [Mageia package][mageia], courtesy of David Geiger
* an [OpenSUSE rpm][opensuse], courtesy of Mathias Homann
* an [Ubuntu/Kubuntu git and stable ppa][ppa3], courtesy of [gogo][ppa4]

The `solaar` package uses a standard system tray implementation; to ensure
integration with *gnome-shell* or *Unity*, install `solaar-gnome3`.

[ppa4]: https://launchpad.net/~trebelnik-stefina
[ppa3]: https://launchpad.net/~solaar-unifying
[ppa2]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/stable
[ppa1]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/ppa
[ppa]: http://launchpad.net/~daniel.pavel/+archive/solaar
[arch]: https://www.archlinux.org/packages/community/any/solaar/
[fedora]: https://apps.fedoraproject.org/packages/solaar
[gentoo]: https://packages.gentoo.org/packages/app-misc/solaar
[mageia]: http://mageia.madb.org/package/show/release/cauldron/application/0/name/solaar
[opensuse]: http://software.opensuse.org/package/Solaar
[universe repository]: http://packages.ubuntu.com/search?keywords=solaar&searchon=names&suite=all&section=all


## Manual installation

See [docs/installation.md](https://pwr-solaar.github.io/Solaar/installation) for the step-by-step procedure for manual installation.


## Known Issues

- KDE/Kubuntu: if some icons appear broken in the application, make sure you've
  properly configured the Gtk theme and icon theme in KDE's control panel.

- Running the command-line application while the GUI
  application is also running *may* occasionally cause either of them to become
  confused about the state of the devices.


## License

This software is distributed under the terms of the
[GNU Public License, v2](COPYING).


## Thanks

This project began as a third-hand clone of [Noah K. Tilton](https://github.com/noah)'s
logitech-solar-k750 project on GitHub (no longer available). It was developed
further thanks to the diggings in Logitech's HID++ protocol done by many other
people:

- [Julien Danjou](http://julien.danjou.info/blog/2012/logitech-k750-linux-support),
who also provided some internal
[Logitech documentation](http://julien.danjou.info/blog/2012/logitech-unifying-upower)
- [Lars-Dominik Braun](http://6xq.net/git/lars/lshidpp.git)
- [Alexander Hofbauer](http://derhofbauer.at/blog/blog/2012/08/28/logitech-performance-mx)
- [Clach04](http://bitbucket.org/clach04/logitech-unifying-receiver-tools)
- [Peter Wu](https://lekensteyn.nl/logitech-unifying.html)
- [Nestor Lopez Casado](http://drive.google.com/folderview?id=0BxbRzx7vEV7eWmgwazJ3NUFfQ28)
provided some more Logitech specifications for the HID++ protocol

Also thanks to Douglas Wagner, Julien Gascard and Peter Wu for helping with
application testing and supporting new devices.
