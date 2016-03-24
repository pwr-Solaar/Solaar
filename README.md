**Solaar** is a Linux device manager for Logitech's [Unifying Receiver][unifying]
peripherals. It is able to pair/unpair devices to the receiver, and for most
devices read battery status.

It comes in two flavors, command-line and GUI.  Both are able to list the
devices paired to a Unifying Receiver, show detailed info for each device, and
also pair/unpair supported devices with the receiver.

[unifying]: http://logitech.com/en-us/66/6079

## Supported Devices

**Solaar** will detect all devices paired with your Unifying Receiver, and at
the very least display some basic information about them.

For some devices, extra settings (usually not available through the standard
Linux system configuration) are supported. For a full list of supported devices
and their features, see [docs/devices.md](docs/devices.md).


## Pre-built packages

Pre-built packages are available for a few Linux distros.

* Debian 7 (Wheezy) or higher: packages in this [repository](docs/debian.md)
* Ubuntu/Kubuntu 12.04+: [ppa:daniel.pavel/solaar][ppa]

The `solaar` package uses a standard system tray implementation; to ensure
integration with *gnome-shell* or *Unity*, install `solaar-gnome3`.

* an [Arch package][arch], courtesy of Arnaud Taffanel
* a [Fedora package][fedora], courtesy of Eric Smith
* a [Gentoo package][gentoo], courtesy of Carlos Silva and Tim Harder
* a [Mageia package][mageia], courtesy of Damien Lallement
* an [OpenSUSE rpm][opensuse], courtesy of Mathias Homann

[ppa]: http://launchpad.net/~daniel.pavel/+archive/solaar
[arch]: http://aur.archlinux.org/packages/solaar
[fedora]: https://admin.fedoraproject.org/pkgdb/package/solaar/
[gentoo]: https://packages.gentoo.org/packages/app-misc/solaar
[mageia]: http://mageia.madb.org/package/show/release/cauldron/application/0/name/solaar
[opensuse]: http://software.opensuse.org/package/Solaar


## Manual installation

See [docs/installation.md](docs/installation.md) for the step-by-step
procedure for manual installation.


## Known Issues

- KDE/Kubuntu: if some icons appear broken in the application, make sure you've
  properly configured the Gtk theme and icon theme in KDE's control panel.

- Some devices using the [Nano Receiver][nano] (which is very similar to the
  Unifying Receiver) are supported, but not all. For details, see
  [docs/devices.md](docs/devices.md).

- Running the command-line application (`bin/solaar-cli`) while the GUI
  application is also running *may* occasionally cause either of them to become
  confused about the state of the devices. I haven't encountered this often
  enough to be able to be able to diagnose it properly yet.

[nano]: http://logitech.com/mice-pointers/articles/5926


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
