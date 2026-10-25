# Fedora / RHEL diagnostics and Logitech configuration (contribution)

This is an optional, non-invasive developer toolset. It does not change Solaar's
runtime, pairing behavior, device firmware, SELinux policy, kernel security state,
or system cryptographic configuration. Run as a normal desktop user.

## Fedora KDE/Wayland

Install the maintained Fedora packages where available:

```bash
sudo dnf install solaar solaar-udev
rpm -q solaar solaar-udev
```

`solaar-udev` provides permissions rules. Do not replace this with world-writable
`/dev/hidraw*` or `/dev/uinput` permissions. Inspect existing rules and device
ACLs first. Solaar's upstream rule uses seat-aware `TAG+="uaccess"`.

Run a source checkout without installing it system-wide:

```bash
cd /path/to/Solaar
python3 tools/solaar-platform-audit.py
python3 tools/solaar-platform-audit.py --json
python3 -m unittest discover -s tests -p 'test_fedora_tools.py' -v
./bin/solaar show
./bin/solaar config 'DEVICE_NAME'
```

Do not indiscriminately run `sudo python3 -m pip install .` on RPM-managed
Python. If building from source, use a purpose-built isolated development
environment with distro-provided GTK, GI and dbus bindings, and verify imports
first. RPM-packaged Solaar is the preferred baseline on Fedora.

Solaar's rules have known limitations on Wayland. Rule-triggered input simulation
may require `/dev/uinput` access. `uinput` writes are powerful synthetic
input capabilities and should not be granted to every local user. KDE Wayland
is not the same as X11; process-specific rules should be tested separately.

## Read-only preflight and FIPS posture

```bash
python3 tools/solaar-platform-audit.py --json
cat /proc/sys/crypto/fips_enabled 2>/dev/null || true
command -v update-crypto-policies >/dev/null && update-crypto-policies --show
getenforce 2>/dev/null || true
ls -l /dev/uinput /dev/hidraw* 2>/dev/null || true
```

FIPS mode, a cryptographic policy, approved algorithms, FIPS-validated
cryptographic modules and system-level compliance are separate statements.
The diagnostic **never** claims compliance. A device's proprietary Logitech
HID++/Bolt transport is not made FIPS-validated by running Solaar on a system
with FIPS indicators enabled. Auditing cryptography requires vendor/module
validation evidence and the actual algorithm paths used, including firmware.

**RHEL 10 difference:** Red Hat documents that FIPS mode must be configured
during installation; changing to FIPS mode after installation is unsupported.
`fips-mode-setup` was removed from RHEL 10. Setting the system-wide `FIPS`
crypto policy alone does not turn a RHEL 10 system into a compliant one.
For Fedora or older RHEL versions, follow the distribution/version-specific
vendor documentation rather than transplanting RHEL 10 commands.

The audit intentionally does not list serial numbers, receiver IDs or Bluetooth
addresses. JSON reports can still include system information; review before
sharing. No network requests or writes are performed by the audit tool.

## Device settings: dry run first

Inspect available options for the exact connected device:

```bash
./bin/solaar show
./bin/solaar config 'DEVICE_NAME'
```

Copy `examples/logitech-settings.template.json` to a **new file** in your
workspace (never overwrite an existing profile), then fill in the device's
reported name, setting names and valid values. The CLI accepts only simple
setting/value pairs. Complex settings, rules and onboard-profile YAML formats
should be managed through Solaar's existing GUI/CLI until they have dedicated
validation and tests. Different receiver and device models support different
subsets of HID++ features.

```bash
python3 tools/solaar-config-plan.py ./examples/logitech-settings.template.json
```

This only prints proposed commands. It does not contact hardware.
To apply an individually reviewed profile, use the exact device name as a
second confirmation:

```bash
python3 tools/solaar-config-plan.py ./my-device-profile.json \
  --apply --confirm-device 'EXACT_DEVICE_NAME'
```

Executing commands may change persistent device settings. Verify device
identity and current configuration, and save a backup using the device's
supported configuration export mechanism before changing any device. Do not
use this for pairing, firmware modification or receiver identity changes.
If any command fails, the tool stops without rolling back previous writes.

## Hardware and security verification

- Check package ownership and effective udev rules before troubleshooting ACLs.
- Review `solaar config DEVICE` to confirm the actual supported settings.
- Test Wayland synthetic-input mappings in a non-critical user session.
- Check SELinux AVC denials (`ausearch -m AVC -ts recent`) before proposing
  targeted policy changes; do not disable SELinux.
- Keep `Secure Boot`, audit, firewall and crypto policies unchanged.
- Confirm system crypto module validation separately from peripheral support.

## Sources

- Upstream Solaar: https://github.com/pwr-Solaar/Solaar
- Upstream rules: https://pwr-solaar.github.io/Solaar/rules/
- Fedora packages: https://packages.fedoraproject.org/pkgs/solaar/solaar/
- Fedora udev package: https://packages.fedoraproject.org/pkgs/solaar/solaar-udev/
- Red Hat RHEL 10 FIPS guidance: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/switching-rhel-to-fips-mode
