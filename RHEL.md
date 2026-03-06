# Solaar on RHEL 10

## Purpose

This documents the steps required to get **Solaar** running on **RHEL 10** when the package is not available from the normal repositories.

## Environment

* OS: RHEL 10
* Desktop: KDE Plasma on Wayland
* Device class: Logitech Unifying Receiver
* Example mouse: Logitech M720 Triathlon

## Observed issue

The following packages were not available from the configured repositories:

```bash
sudo dnf install solaar xbindkeys xdotool evtest
```

DNF returned package-not-found errors for those package names.

## What worked

### 1. Confirm the Logitech receiver is detected

```bash
lsusb | grep -i logitech
```

Expected output looked similar to this:

```text
Bus 001 Device 00X: ID 046d:c52b Logitech, Inc. Unifying Receiver
```

### 2. Install required base packages from RHEL and EPEL where available

Install Python packaging support and device/input tooling first.

```bash
sudo dnf install python3 python3-pip git libinput evemu
```

Also install build and runtime pieces commonly needed for user-space input and HID tools.

```bash
sudo dnf install python3-devel gcc pkgconf-pkg-config gtk3 python3-gobject
```

Note: exact dependency resolution may vary depending on enabled repositories and what is already installed.

### 3. Clone the Solaar repository

```bash
mkdir -p ~/dev-repos
cd ~/dev-repos
git clone https://github.com/pwr-Solaar/Solaar.git
cd Solaar
```

### 4. Install Solaar to the user environment

Install it into the user site-packages instead of system-wide.

```bash
python3 -m pip install --user .
```

If upgrading later from the fork or local checkout:

```bash
python3 -m pip install --user --upgrade .
```

### 5. Run Solaar directly from the user-local install path

```bash
~/.local/bin/solaar
```

For CLI inspection:

```bash
~/.local/bin/solaar show
~/.local/bin/solaar config "M720 Triathlon Multi-Device Mouse"
```

### 6. Confirm the receiver and device are visible

A working example:

```bash
~/.local/bin/solaar show
```

This displayed the Unifying Receiver and the M720 Triathlon, including battery state and configurable features.

## Automated installer script

A guided installer script is included in this repository and automates the RHEL workflow in this document while prompting before each major action.

Run it from the Solaar checkout:

```bash
./tools/install-rhel.sh
```

The script can:

* check for Logitech receiver visibility with `lsusb`
* install required packages with `dnf`
* create the checkout directory and clone/update Solaar
* install Solaar with `python3 -m pip install --user`
* optionally add a Bash alias for `solaar`
* optionally run `solaar show`, `solaar config`, `libinput debug-events`, and `keyd monitor`
* write a timestamped evidence log in `~/.local/state/solaar/`

## Wayland note

On KDE Wayland, Solaar prints a warning similar to:

```text
rules cannot access modifier keys in Wayland, accessing process only works on GNOME with Solaar Gnome extension installed
```

This does **not** prevent basic Solaar usage. It only means some rule-processing features are limited under Wayland, especially outside GNOME.

## Device-specific issue seen with the M720

`solaar show` triggered a traceback when trying to read host-name metadata from the M720 Triathlon:

```text
UnicodeDecodeError: 'utf-8' codec can't decode bytes in position 12-13: unexpected end of data
```

This appears related to Solaar parsing stored host information from the mouse, not to receiver detection itself.

### Practical workaround

Use targeted commands that still work, such as:

```bash
~/.local/bin/solaar config "M720 Triathlon Multi-Device Mouse"
```

This successfully showed configurable settings like:

* scroll wheel direction
* scroll wheel resolution
* pointer speed
* reprogrammable keys
* persistent remappable keys
* diversion settings

## Verifying input behavior outside Solaar

To inspect raw input events from the mouse, identify the correct `/dev/input/eventX` node for the mouse on your system and then run:

```bash
sudo libinput debug-events --device /dev/input/eventX
```

This confirmed the mouse was producing:

* pointer motion
* left and middle button events
* scroll wheel events
* horizontal wheel events
* keyboard-style events for some remapped functions

## keyd note

A locally installed `keyd` binary may exist under `/usr/local/bin/keyd` if built from source or installed manually.

If it is not available in the shell `PATH`, direct invocation may be required for monitoring:

```bash
sudo /usr/local/bin/keyd monitor
```

This can help verify that virtual keyboard and pointer events are being created and that remapped device actions are flowing through the input stack.

## Recommended quality-of-life alias

Add a shell alias so Solaar can be launched normally:

```bash
vi ~/.bashrc
```

Append:

```bash
alias solaar="$HOME/.local/bin/solaar"
```

Reload shell config:

```bash
source ~/.bashrc
```

Then launch with:

```bash
solaar
```

## Summary

The working path on RHEL 10 was:

1. Confirm the Logitech Unifying Receiver is visible with `lsusb`.
2. Install Python and required development/runtime packages.
3. Clone the Solaar repository.
4. Install Solaar with `python3 -m pip install --user .`.
5. Run Solaar from `~/.local/bin/solaar`.
6. Use `solaar config "M720 Triathlon Multi-Device Mouse"` for stable device configuration.
7. Use `libinput debug-events` and optionally `keyd monitor` to validate the input stack.

## Commands used

```bash
lsusb | grep -i logitech
mkdir -p ~/dev-repos
cd ~/dev-repos
git clone https://github.com/pwr-Solaar/Solaar.git
cd Solaar
python3 -m pip install --user .
~/.local/bin/solaar
~/.local/bin/solaar show
~/.local/bin/solaar config "M720 Triathlon Multi-Device Mouse"
sudo libinput debug-events --device /dev/input/eventX
sudo /usr/local/bin/keyd monitor
```

## Caveats

* Package availability in RHEL 10 repositories may differ from Fedora or Debian-based systems.
* Wayland limits certain Solaar rule features.
* `solaar show` may crash on some host-info metadata due to an upstream parsing issue.
* Direct user-local execution from `~/.local/bin/solaar` may be required if no system package exists.
* Replace example paths and event device numbers with the values on your own system.
