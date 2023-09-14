---
title: Solaar
layout: default
---

**Solaar** is a Linux manager for many Logitech keyboards, mice, and trackpads
that connect wirelessly to a USB [Unifying][unifying], Bolt, Lightspeed, or Nano receiver;
connect directly via a USB cable; or connect via Bluetooth.
Solaar does not work with peripherals from other companies.

Documentation here is for the current version of Solaar.
Some Linux distributions distribute old versions of Solaar.
If you are using an old version and something described here does not work you should upgrade
using one of the methods described below.

Solaar runs as a regular user process, albeit with direct access to the Linux interface
that lets it directly communicate with the Logitech devices it manages using special
Logitech-proprietary (HID++) commands.
Each Logitech device implements a different subset of these commands.
Solaar is thus only able to make the changes to devices that devices implement.

Solaar is not a device driver and does not process normal input from devices.
It is thus unable to fix problems that arise from incorrect handling of
mouse movements or keycodes by Linux drivers or other software.

Solaar can be used as a GUI application, the usual case, or via its command-line interface.
The Solaar GUI is meant to run continuously in the background,
monitoring devices, making changes to them, and responding to some messages they emit.
To this end, it is useful to have Solaar start at user login so that
changes made to devices by Solaar are applied at login and throughout the user's session.

Both Solaar interfaces are able to list the connected devices and
show information about each device, often including battery status.
Solaar is able to pair and unpair devices with
receivers as supported by the device and receiver.
Solaar can also control some changeable settings of devices,
such as scroll wheel direction and function key behavior.
Solaar keeps track of most of these settings on a per-computer basis,
because devices forget most settings when powered down,
and the GUI application restores them whenever a device connects.
For more information on how to use Solaar see
[the usage page](https://pwr-solaar.github.io/Solaar/usage),
and for more information on its capabilities see
[the capabilities page](https://pwr-solaar.github.io/Solaar/capabilities).


Solaar's GUI normally uses an icon in the system tray and starts with its main window visible.
This aspect of Solaar depends on having an active system tray, which is not the default
situation for recent versions of Gnome.  For information on to set up a system tray under Gnome see
[the capabilities page](https://pwr-solaar.github.io/Solaar/capabilities).

Solaar's GUI can be started in several ways

- `--window=show` (the default) starts with its main window visible,
- `--window=hide` starts with its main window hidden,
- `--window=only` does not use the system tray, and starts with main window visible.

For more information on Solaar's command-line interface use the help option,
as in `solaar --help`.

Solaar has progressed past version 1.1. Problems with earlier versions should
not be reported as bugs. Instead, upgrade to a recent version or manually install
the current version from [GitHub](https://github.com/pwr-Solaar/Solaar).
Some capabilities of Solaar have been developed by observing the behavior of
Logitech receivers and devices and generalizing from these observations.
If your Logitech receiver or device behaves strangely this may be caused by
an incorrect behavior generalization.
Please report such experiences by creating an issue in
[the Solaar repository](https://github.com/pwr-Solaar/Solaar/issues).

[unifying]: https://en.wikipedia.org/wiki/Logitech_Unifying_receiver


## Supported Devices

Solaar will detect all devices paired with supported Unifying, Bolt, Lightspeed, or Nano
receivers, and at the very least display some basic information about them.
Solaar will detect some Logitech devices that connect via a USB cable or Bluetooth.

Solaar can pair and unpair a Logitech device showing the Unifying logo
(Solaar's version of the [logo][logo])
with any Unifying receiver,
and pair and unpair a Logitech device showing the Bolt logo
with any Bolt receiver,
and
can pair and unpair Lightspeed devices with Lightspeed receivers for the same model.
Solaar can pair some Logitech devices with Logitech Nano receivers but not all Logitech
devices can be paired with Nano receivers.
Logitech devices without a Unifying or Bolt logo
generally cannot be paired with Unifying or Bolt receivers.

Solaar does not handle connecting or disconnecting via Bluetooth,
which is done using the usual Bluetooth mechanisms.

For a partial list of supported devices
and their features, see [the devices page](https://pwr-solaar.github.io/Solaar/devices).

[logo]: https://pwr-solaar.github.io/Solaar/assets/solaar.svg

## Prebuilt packages

Up-to-date prebuilt packages are available for some Linux distros
(e.g., Fedora 33+) in their standard repositories.
If a recent version of Solaar is not
available from the standard repositories for your distribution you can try
one of these packages.

- Arch solaar package in the [extra repository][arch]
- Ubuntu/Kubuntu stable packages: use the [Solaar stable ppa][ppa2], courtesy of [gogo][ppa4]
- Ubuntu/Kubuntu git build packages: use the [Solaar git ppa][ppa1], courtesy of [gogo][ppa4]

Solaar is available from some other repositories
but they are several versions behind the current version.

- for Ubuntu/Kubuntu 16.04+: the solaar package from [universe repository][universe repository]
- a [Gentoo package][gentoo], courtesy of Carlos Silva and Tim Harder
- a [Mageia package][mageia], courtesy of David Geiger

Solaar uses a standard system tray implementation; solaar-gnome3 is no longer required for Gnome or Unity integration.

[ppa4]: https://launchpad.net/~trebelnik-stefina
[ppa2]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/stable
[ppa1]: https://launchpad.net/~solaar-unifying/+archive/ubuntu/ppa
[ppa]: http://launchpad.net/~daniel.pavel/+archive/solaar
[arch]: https://www.archlinux.org/packages/extra/any/solaar/
[gentoo]: https://packages.gentoo.org/packages/app-misc/solaar
[mageia]: http://mageia.madb.org/package/show/release/cauldron/application/0/name/solaar
[universe repository]: http://packages.ubuntu.com/search?keywords=solaar&searchon=names&suite=all&section=all

## Manual installation

See [the installation page](https://pwr-solaar.github.io/Solaar/installation)
for the step-by-step procedure for manual installation.

## Known Issues

- Solaar expects that it has exclusive control over settings that are not ignored.
  Running other programs that modify these settings, such as logiops,
  will likely result in unexpected device behavior.

- The Linux HID++ driver modifies the Scroll Wheel Resolution setting to
  implement smooth scrolling.  If Solaar later changes this setting scrolling
  can be either very fast or very slow.  To fix this problem
  click on the icon at the right edge of the setting to set it to
  "Ignore this setting", which is the default for new devices.
  The mouse has to be reset (e.g., by turning it off and on again) before this fix will take effect.

- The driver also sets the scrolling direction to its normal setting when implementing smooth scrolling.
  This can interfere with the Scroll Wheel Direction setting, requiring flipping this setting back and forth
  to restore reversed scrolling.

- The driver sends messages to devices that do not conform with the Logitech HID++ specification
  resulting in reponses being sent back that look like other messages.  For some devices this causes
  Solaar to report incorrect battery levels.

- If the Python hid-parser package is not available Solaar will not recognize some devices.
  Use pip to install hid-parser.

- Solaar normally uses icon names for its icons, which in some system tray implementatations
  results in missing or wrong-sized icons.
  The `--tray-icon-size` option forces Solaar to use icon files of appropriate size
  for tray icons instead, which produces better results in some system tray implementatations.
  To use icon files close to 32 pixels in size use `--tray-icon-size=32`.

- The icon in the system tray can show up as 'black on black' in dark
  themes or as non-symbolic when the theme uses symbolic icons.  This is due to problems
  in some system tray implementations. Changing to a different theme may help.
  The `--battery-icons=symbolic` option can be used to force symbolic icons.

- Many gaming mice and keyboards have the ONBOARD PROFILES feature.
  This feature can override other features, including polling rate and key lighting.
  To make the Polling Rate and M-Key LEDs settings effective the Onboard Profiles setting has to be disabled.
  This may have other effects, such as turning off backlighting.

- Solaar will try to use uinput to simulate input from rules under Wayland or if Xtest is not available
  but this needs write permission on /dev/uinput.
  For more information see [the rules page](https://pwr-solaar.github.io/Solaar/rules).

- Diverted keys remain diverted and so do not have their normal behaviour when Solaar terminates
  or a device disconnects from a host that is running Solaar.  If necessary, their normal behaviour
  can be reestablished by turning the device off and on again.  This is most important to restore
  the host switching behaviour of a host switch key that was diverted, for example to switch away
  from a host that crashed or was turned off.

- When a receiver-connected device changes hosts Solaar remembers which diverted keys were down on it.
  When the device changes back the first time any of these diverted keys is depressed Solaar will not
  realize that the key was newly depressed.  For this reason Solaar rules that can change hosts should
  trigger on key releasing.

## Contributing to Solaar

Conributions to Solaaar are very welcome.

Solaar has complete or partial translations of its GUI strings in several languages.
If you want to update a translation or add a new one see [the translation page](https://pwr-solaar.github.io/Solaar/i18n) for more information.

If you find a bug, please check first if it has already been reported. If yes, please add additional information you may have to the existing issue. If not, please open a new bug report issue. If you can provide a fix for it, please also open a GitHub pull request. Label your commits using the naming conventions in recent commits to Solaar.

If you want to add a new feature to Solaar, feel free to open a feature request issue to discuss your proposal.
There are also usually several open issues for enhancements that have already been requested.


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

Also, thanks to Douglas Wagner, Julien Gascard, and Peter Wu for helping with
application testing and supporting new devices.
