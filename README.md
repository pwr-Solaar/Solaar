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

Pre-built packages are available for a few Linux distros:

* Ubuntu 12.04+: [ppa:daniel.pavel/solaar][ppa]
* a Debian Wheezy package [.deb][debian], should work on testing and Sid as well
* a [Gentoo overlay][gentoo], courtesy of Carlos Silva
* an [OpenSUSE rpm][opensuse], courtesy of Mathias Homann
* an [Arch package][arch], courtesy of Arnaud Taffanel

[ppa]: http://launchpad.net/~daniel.pavel/+archive/solaar
[debian]: http://pwr.github.io/Solaar/packages/solaar_0.8.8.1-2_all.deb
[gentoo]: http://code.r3pek.org/gentoo-overlay/src
[opensuse]: http://software.opensuse.org/package/Solaar
[arch]: http://aur.archlinux.org/packages/solaar


## Manual installation

See [docs/installation.md](docs/installation.md) for the step-by-step
procedure for manual installation.


## Known Issues

- Ubuntu's Unity indicators are not supported at this time. However, if you
  whitelist 'Solaar' in the systray, you will get an icon (see
  [Enable more icons to be in the system tray?][ubuntu_systray] for details).

[ubuntu_systray]: http://askubuntu.com/questions/30742

- Devices connected throught a [Nano Receiver][nano] (which is very similar to
  the Unifying Receiver) are not supported at this time.

[nano]: http://logitech.com/mice-pointers/articles/5926

- Running the command-line application (`bin/solaar-cli`) while the GUI
  application is also running *may* occasionally cause either of them to become
  confused about the state of the devices. I haven't encountered this often
  enough to be able to be able to diagnose it properly yet.


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
