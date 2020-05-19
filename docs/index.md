---
title: Solaar
layout: default
---

**Solaar** is a Linux manager for Logitech's devices that connect via a USB 
[Unifying][unifying], Lightspeed, or Nano receiver.  
Solaar does not work with Logitech peripherals that
use Bluetooth or peripherals from other companies.

Solaar can be used as a GUI application or via its command-line interface.
Both interfaces are able to list the devices paired to a receiver and
show information about each device, including battery status for devices that support this feature.
Solaar's GUI normally uses an icon in the system tray and starts with its main window hidden.
If Solaar is invoked with the `--window=show` option (the default) Solaar starts with its main window visible.
If Solaar is invoked with the `--window=hide` option Solaar starts with its main window hidden.
If solaar is invoked with the `--window=only` option Solaar does not set up an icon in the
system tray and also starts with its main window showing.
For more information on Solaar's command-line interface use the help option,
as in `solaar --help`.

Solaar is able to pair and unpair devices with 
receivers as supported by the receiver.  Solaar can also control
some of the changeable features of devices, such as smooth scrolling or
function key behavior.  
For more information on how to use Solaar see
[docs/usage.md](https://pwr-solaar.github.io/Solaar/usage).
For more information on the capabilities of Solaar see
[docs/capabilities.md](https://pwr-solaar.github.io/Solaar/capabilities).

Solaar does not process normal input from the devices.  Solaar is thus unable
to fix problems that arise from incorrect handling of mouse movements or keycodes
by Linux drivers or other software.

Solaar has progressed past version 1.0.  Problems with earlier versions should
not be reported as bugs.  Instead upgrade to a recent version or manually install
the current version from [GitHub](https://github.com/pwr-Solaar/Solaar).
Some of the capabilities of Solaar have been developed by observing the behavior of
Logitech receivers and devices and generalizing from these observations.
If your Logitech receiver or device behaves in a strange way this may be caused by
an incorrect behavior generalization.
Please report such experiences by creating an issue in 
[the Solaar repository](https://github.com/pwr-Solaar/Solaar/issues).

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

Solaar has progressed beyond version 1.0 but some distros or repositories
version 0.9.2, which is very old. Installing the current version will
provide significant improvements.  If a recent version of Solaar is not
available from the standard repositories for your distribution you can try
one of these packages.

* Arch solaar package in the [community repository][arch]
* Debian 7 (Wheezy) or higher: packages in this [repository](https://pwr-solaar.github.io/Solaar/debian)
* Ubuntu/Kubuntu 16.04+: use the solaar package from [universe repository][universe repository]
* Ubuntu/Kubuntu stable packages: use the [Solaar stable ppa][ppa2], courtesy of [gogo][ppa4]
* Ubuntu/Kubuntu git build packages: use the [Solaar git ppa][ppa1], courtesy of [gogo][ppa4]
* a [Fedora package][fedora], courtesy of Eric Smith
* a [Gentoo package][gentoo], courtesy of Carlos Silva and Tim Harder
* a [Mageia package][mageia], courtesy of David Geiger
* an [OpenSUSE rpm][opensuse], courtesy of Mathias Homann

Solaar uses a standard system tray implementation; solaar-gnome3 is no longer required for gnome or unity integration.

[ppa4]: https://launchpad.net/~trebelnik-stefina
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
