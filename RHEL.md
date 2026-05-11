# Solaar installation guide for RHEL, Rocky, AlmaLinux, and CentOS Stream

This guide covers manual installation and an automated install example for
RHEL-family systems using `dnf`.

## Supported distributions

- Red Hat Enterprise Linux (RHEL)
- Rocky Linux
- AlmaLinux
- Oracle Linux
- CentOS Stream

The commands assume a minimal CLI system with `sudo` access.

## 1) Install dependencies

```bash
sudo dnf makecache --refresh
sudo dnf install -y \
  git \
  gtk3 \
  python3 \
  python3-devel \
  python3-dbus \
  python3-gobject \
  python3-pip \
  python3-psutil \
  python3-pyudev \
  python3-setuptools \
  python3-xlib \
  python3-yaml
```

Optional troubleshooting helpers:

```bash
sudo dnf install -y \
  evemu \
  libinput \
  usbutils
```

## 2) Clone Solaar

```bash
git clone https://github.com/pwr-Solaar/Solaar.git
cd Solaar
```

## 3) Install Solaar

Install for the current user:

```bash
python3 -m pip install --user .
```

Or install system-wide:

```bash
sudo python3 -m pip install .
```

## 4) Install udev rules

Install the recommended `uinput` rule:

```bash
sudo make install_udev_uinput
```

Verify rule installation:

```bash
ls -l /etc/udev/rules.d/42-logitech-unify-permissions.rules
```

Rollback udev rule installation:

```bash
sudo make uninstall_udev
```

## 5) Run Solaar

```bash
solaar
```

or:

```bash
python3 -m solaar
```

## 6) Automated install options

Use the guided installer in this repository:

```bash
./tools/install-rhel.sh
```

Minimal non-interactive example script:

```bash
cat > install-rhel-solaar.sh <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo "Run as a regular user with sudo access, not as root."
  exit 1
fi

sudo dnf makecache --refresh
sudo dnf install -y \
  git \
  gtk3 \
  python3 \
  python3-devel \
  python3-dbus \
  python3-gobject \
  python3-pip \
  python3-psutil \
  python3-pyudev \
  python3-setuptools \
  python3-xlib \
  python3-yaml

if [[ ! -d Solaar/.git ]]; then
  git clone https://github.com/pwr-Solaar/Solaar.git
fi

cd Solaar
python3 -m pip install --user .
sudo make install_udev_uinput
~/.local/bin/solaar --version
SCRIPT

chmod +x install-rhel-solaar.sh
./install-rhel-solaar.sh
```

## 7) Verification

```bash
command -v solaar
solaar --version
python3 -m pip show solaar
```

If installed with `--user`, ensure `~/.local/bin` is on your `PATH`:

```bash
echo "$PATH" | tr ':' '\n' | grep -Fx "$HOME/.local/bin" >/dev/null || \
  echo 'Add ~/.local/bin to PATH'
```

## 8) Troubleshooting

Receiver not detected:

```bash
lsusb | grep -Ei 'logitech|046d'
sudo udevadm trigger
```

Check access to hidraw devices:

```bash
ls -l /dev/hidraw*
getfacl /dev/hidraw* 2>/dev/null | sed -n '1,80p'
```
