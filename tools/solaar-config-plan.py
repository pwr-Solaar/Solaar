#!/usr/bin/env python3
"""Validate and preview device-specific Solaar settings; optional explicit apply.

No shell invocation, no root escalation, and no device modification by default.
"""

import argparse
import json
import shlex
import subprocess
import sys

from pathlib import Path


def require_string(value, what):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise ValueError(f"{what} must be a nonempty string <= 128 characters")
    if any(ord(c) < 32 or ord(c) == 127 for c in value) or value.startswith("-"):
        raise ValueError(f"{what} contains control characters or begins with a dash")
    return value


def commands(profile):
    if not isinstance(profile, dict) or set(profile) != {"device", "settings"}:
        raise ValueError("profile needs exactly 'device' and 'settings'")
    device = require_string(profile["device"], "device")
    entries = profile["settings"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
        raise ValueError("settings must be a list of 1..20 entries")
    result = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"setting", "value"}:
            raise ValueError(f"settings[{i}] needs exactly 'setting' and 'value'")
        setting = require_string(entry["setting"], f"settings[{i}].setting")
        val = require_string(entry["value"], f"settings[{i}].value")
        result.append(["solaar", "config", device, setting, val])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path, help="JSON profile containing device and settings")
    parser.add_argument("--apply", action="store_true", help="write device settings (opt-in)")
    parser.add_argument("--confirm-device", help="must equal JSON device name when applying")
    args = parser.parse_args(argv)
    try:
        obj = json.loads(args.profile.read_text(encoding="utf-8"))
        ops = commands(obj)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.apply and args.confirm_device != obj["device"]:
        parser.error("--apply requires --confirm-device matching the JSON device value exactly")
    for cmd in ops:
        print(shlex.join(cmd), flush=True)
        if args.apply:
            try:
                subprocess.run(cmd, check=True, timeout=20)
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                parser.exit(1, f"Stopped after command error: {exc}\n")
    if not args.apply:
        print("DRY RUN: no Logitech device was modified.")
    else:
        print("Device commands completed. Inspect actual device state with 'solaar config DEVICE'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
