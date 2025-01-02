---
title: Manual Installation
layout: page
---

# Installing from PyPI

An easy way to install the most recent release version of Solaar is from the PyPI repository.
First install pip, and then run
`pip install --user solaar` or `pipx install --system-site-packages solaar` or
If you are using pipx add the `` flag.

This will not install the Solaar udev rule, which you will need to install manually by copying
`~/.local/lib/udev/rules.d/42-logitech-unify-permissions.rules`
to `/etc/udev/rules.d` as root.
If you want Solaar rules to simulate input you will have to instead install Solaar's uinput udev rule
from the GitHub repository.

## Installing in macOS

Solaar has limited support for macOS. You can use it to pair devices and configure settings
but the rule system and diversion will not work.

After installing Solaar via pip use homebrew to install the needed libraries:
```
brew update
brew install hidapi gtk+3 pygobject3
```

# Installating from GitHub

## Downloading

Clone Solaar from GitHub by `git clone https://github.com/pwr-Solaar/Solaar.git`.

## Installing using the Makefile

Solaar has a makefile that can be used to easily install Solaar after cloning the repository.

First, install the needed system packages by `make install_apt`
or `make install_dnf` or `make install_brew`.
These might not install all needed packages in older versions of your distribution.
Next, install the Solaar rule via `make install_udev`.
If you are using Wayland instead of X11 you may want to instead `make install_udev_uinput`
Finally, install Solaar via `make install_pip` or `make install_pipx`.
so that Solaar rules can simulate input in Wayland.

Parts of the installation process require sudo privileges so you may be asked for your password.

## Running from the download directory

To run Solaar from the download directory, just cd to there and run `bin/solaar` for the GUI
or `bin/solaar <command> <arguments>` for the CLI.

## Requirements for Solaar

This is only relevant if you have problems with the easier methods above.

Solaar needs a reasonably new kernel with kernel modules `hid-logitech-dj` and `hid-logitech-hidpp` loaded.
The kernel option CONFIG_HIDRAW also needs to be enabled.
Most of Solaar should work fine with any kernel more recent than 5.2,
but newer kernels might be needed for some devices to be correctly recognized and handled.
The `udev` package must be installed and its daemon running.

Solaar requires Python 3.7+ and requires several packages to be installed.
If you are running the system version of Python you should have the
`python3-pyudev`, `python3-psutil`, `python3-xlib`, `python3-evdev`, `python3-typing-extensions`, `dbus-python`
or `python3-dbus`, and `python3-yaml` or `python3-pyyaml` packages installed.

To run the GUI Solaar also requires Gtk3 and its GObject introspection bindings.
If you are running the system version of Python in Debian/Ubuntu you should have the
`python3-gi` and `gir1.2-gtk-3.0` packages installed.
In Fedora you need `gtk3` and `python3-gobject`.
You may have to install `gcc` and the Python development package (`python3-dev` or `python3-devel`,
depending on your distribution).
Other system packages may be required depending on your distribution, such as `python-gobject-common-devel` and `python-typing-extensions'.
Although the Solaar CLI does not require Gtk3,
`solaar config` does use Gtk3 capabilities to determine whether the Solaar GUI is running
and thus should tell the Solaar GUI to update its information about settings
so it is a good idea to have Gtk3 available even for the Solaar CLI.

Solaar needs a library to interact with the system tray.
The library that provides this interaction depends on the distribution and window system.
If ayatana appindicator is available then it is best to have this library installed,
e.g., by installing `libayatana-appindicator` or `gir1.2-ayatanaappindicator3-0.1` or similar,
depending on distribution.
Otherwise appindicator can sometimes be used,
e.g., by installing `libappindicator-gtk3` or `gir1.2-appindicator3-0.1` or similar,
depending on distribution.

If desktop notifications bindings are also installed
(`gir1.2-notify-0.7` for Debian/Ubuntu),
you will also see desktop notifications when devices come online and go offline.

If the `hid_parser` Python package is available, Solaar parses HID report descriptors
and can control more HID++ devices that do not use a receiver.
This package may not be available in some distributions but can be installed using pip
via `pip install --user hid-parser`.

If the `gitinfo` Python package is available, Solaar shows better information
about which version of Solaar is running.
This package may not be available in some distributions but can be installed using pip
via `pip install --user python-git-info`.

If you are running a version of Python different from the system version,
you may need to use pip to install projects that provide the above Python packages.

Solaar runs best under X11 with the Xtest extension enabled so that Solaar rules can fake keyboard input using Xtest.
Solaar also uses the X11 library to access the XKB extension,
which requires installation of the X11 development package.
(In Fedora this is `libX11-devel`.  In other distributions it may be `libX11-dev`.)
Solaar will run under Wayland but some parts of Solaar rules will not work.
For more information see [the rules page](https://pwr-solaar.github.io/Solaar/rules).

## Installing Solaar's udev rule manually

You can install Solaar's udev rule manually by copying the file
`rules.d/42-logitech-unify-permissions.rules`
as root from the Solaar repository to `/etc/udev/rules.d`.
In Wayland you may want to instead copy
`rules.d-uinput/42-logitech-unify-permissions.rules`.
Let udev reload its rules by running `sudo udevadm control --reload-rules`.

# Solaar in other languages

If you want to have Solaar's user messages in some other language you need to run
`tools/po-compile.sh` to create the translation files before running or installing Solaar
and set the LANGUAGE environment variable appropriately when running Solaar.

# Running Solaar at Startup

Distributions can cause Solaar can be run automatically at user login by installing a desktop file at
`/etc/xdg/autostart/solaar.desktop`. An example of this file content can be seen in the repository at
[`share/autostart/solaar.desktop`](/share/autostart/solaar.desktop).

If you install Solaar yourself you may need to create or modify this file or install a startup file under your home directory.
