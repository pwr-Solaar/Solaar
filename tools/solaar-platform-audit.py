#!/usr/bin/env python3
"""Read-only Fedora/RHEL Solaar HID access and FIPS-posture diagnostics.

Requires only Python's standard library. Does not enumerate device serials,
request elevated privileges, write HID messages, or modify host policy.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

from datetime import datetime
from datetime import timezone
from pathlib import Path


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def os_release(path="/etc/os-release"):
    fields = {}
    text = read_text(path) or ""
    for line in text.splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in ("ID", "VERSION_ID", "ID_LIKE"):
            fields[key.lower()] = value.strip().strip('"').strip("'")
    return fields


def safe_command(*argv):
    if not shutil.which(argv[0]):
        return None
    try:
        run = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=4,
            check=False,
        )
        return run.stdout.strip() if run.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def status_flag(path):
    value = read_text(path)
    return {"0": "disabled", "1": "enabled"}.get(value, "unknown")


def hidraw_access(dev_path="/dev"):
    root = Path(dev_path)
    try:
        paths = sorted(p for p in root.glob("hidraw*") if p.name[6:].isdigit())
    except OSError:
        return {"count": 0, "readable": 0, "writable": 0}
    return {
        "count": len(paths),
        "readable": sum(os.access(p, os.R_OK) for p in paths),
        "writable": sum(os.access(p, os.W_OK) for p in paths),
    }


def collect():
    fips = status_flag("/proc/sys/crypto/fips_enabled")
    selinux = status_flag("/sys/fs/selinux/enforce")
    policy = safe_command("update-crypto-policies", "--show")
    boot_text = safe_command("mokutil", "--sb-state")
    secure_boot = "unknown"
    if boot_text:
        lower = boot_text.lower()
        secure_boot = "disabled" if "disabled" in lower else "enabled" if "enabled" in lower else "unknown"
    mode = (os.environ.get("XDG_SESSION_TYPE") or "unknown").lower()
    rule_name = "42-logitech-unify-permissions.rules"
    rules = [
        p
        for p in (
            f"/etc/udev/rules.d/{rule_name}",
            f"/usr/lib/udev/rules.d/{rule_name}",
            f"/lib/udev/rules.d/{rule_name}",
        )
        if Path(p).is_file()
    ]
    uinput = Path("/dev/uinput")
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "distribution": os_release(),
        "kernel_release": os.uname().release,
        "session_type": mode,
        "selinux": selinux,
        "secure_boot_indicator": secure_boot,
        "kernel_fips_indicator": fips,
        "system_crypto_policy": policy if policy is not None else "unavailable",
        "fips_compliance_verified": False,
        "fips_note": "An enabled indicator or FIPS crypto policy does not demonstrate validated modules or system compliance.",
        "solaar_available": shutil.which("solaar") is not None,
        "solaar_udev_rule_present": bool(rules),
        "udev_rule_locations": rules,
        "hidraw": hidraw_access(),
        "uinput": {"present": uinput.exists(), "writable": uinput.exists() and os.access(uinput, os.W_OK)},
        "kernel_hid_modules": {
            "hid_logitech_dj": Path("/sys/module/hid_logitech_dj").exists(),
            "hid_logitech_hidpp": Path("/sys/module/hid_logitech_hidpp").exists(),
        },
        "actions_performed": "read-only inspection",
    }
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", action="store_true", help="machine-readable report")
    args = p.parse_args(argv)
    report = collect()
    if args.json:
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    print("Solaar Fedora/RHEL read-only platform audit")
    for field in (
        "timestamp_utc",
        "distribution",
        "kernel_release",
        "session_type",
        "selinux",
        "secure_boot_indicator",
        "kernel_fips_indicator",
        "system_crypto_policy",
        "solaar_available",
        "solaar_udev_rule_present",
        "hidraw",
        "uinput",
        "kernel_hid_modules",
    ):
        print(f"{field}: {report[field]}")
    print("FIPS compliance verified: NO (not assessed)")
    if report["kernel_fips_indicator"] != "enabled":
        print("Note: kernel FIPS indicator is not enabled or is unavailable.")
    if report["session_type"] == "wayland":
        print("Note: Solaar rules have known limitations under Wayland; use supported uinput rules.")
    if not report["solaar_udev_rule_present"]:
        print("Note: No known Solaar udev permissions rule found; inspect distro package solaar-udev.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
