import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

CONFIG_PATH = Path.home() / ".config" / "solaar" / "game_dpi_profiles.json"
POLL_SECONDS = 1.0
DEBOUNCE_REQUIRED = 2
COOLDOWN_SECONDS = 5.0
PROFILE_CHOICES = {f"profile {i}": f"Profile {i}" for i in range(1, 6)}

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("solaar-game-profile-detector")


def _load_config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def _alive_pids(pids):
    alive = set()
    for pid in pids:
        if psutil.pid_exists(pid):
            alive.add(pid)
    return alive


def _iter_processes():
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            info = proc.info
            name = (info.get("name") or "").lower()
            cmdline = [part.lower() for part in (info.get("cmdline") or [])]
            yield info.get("pid"), name, cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def _match_alias(alias, proc_name, cmdline):
    alias = alias.lower()
    joined = " ".join(cmdline)
    if alias == "minecraft":
        return proc_name == "java" and "mojang" in joined
    if alias == proc_name:
        return True
    if alias in proc_name:
        return True
    return alias in joined


def _find_target(config):
    for device_name, device_cfg in config.items():
        profiles = device_cfg.get("profiles", [])
        for profile in profiles:
            if profile.get("is_default"):
                continue
            aliases = profile.get("aliases", [])
            if not aliases:
                continue
            matched_pids = set()
            for pid, proc_name, cmdline in _iter_processes():
                if any(_match_alias(alias, proc_name, cmdline) for alias in aliases):
                    matched_pids.add(pid)
            if matched_pids:
                return {
                    "device_name": device_name,
                    "profile_name": profile.get("name") or profile.get("onboard_profile"),
                    "onboard_profile": PROFILE_CHOICES.get(profile.get("onboard_profile", "").lower(), profile.get("onboard_profile", "Profile 1")),
                    "matched_pids": matched_pids,
                }
    return None


def _default_for_device(config, device_name):
    profiles = config.get(device_name, {}).get("profiles", [])
    for profile in profiles:
        if profile.get("is_default"):
            return {
                "device_name": device_name,
                "profile_name": profile.get("name") or profile.get("onboard_profile"),
                "onboard_profile": PROFILE_CHOICES.get(profile.get("onboard_profile", "").lower(), profile.get("onboard_profile", "Profile 1")),
            }
    return None


def _solaar_cmd():
    return shutil.which("solaar") or str(Path.home() / ".local" / "bin" / "solaar")


def _apply_profile(binding):
    cmd = [_solaar_cmd(), "config", binding["device_name"], "onboard_profiles", binding["onboard_profile"]]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    last_applied = None
    active_game = None
    last_switch = 0.0
    pending_key = None
    pending_hits = 0

    while True:
        config = _load_config()
        now = time.monotonic()

        if active_game is not None:
            alive = _alive_pids(active_game.get("matched_pids", set()))
            if alive:
                active_game["matched_pids"] = alive
                time.sleep(POLL_SECONDS)
                continue
            default_binding = _default_for_device(config, active_game["device_name"])
            if default_binding and default_binding != last_applied and now - last_switch >= COOLDOWN_SECONDS:
                _apply_profile(default_binding)
                logger.info(f"reverted {default_binding['device_name']} to {default_binding['onboard_profile']}")
                last_applied = default_binding
                last_switch = now
            active_game = None
            pending_key = None
            pending_hits = 0
            time.sleep(POLL_SECONDS)
            continue

        target = _find_target(config)
        if target is None:
            pending_key = None
            pending_hits = 0
            time.sleep(POLL_SECONDS)
            continue

        key = (target["device_name"], target["onboard_profile"])
        if key == pending_key:
            pending_hits += 1
        else:
            pending_key = key
            pending_hits = 1

        if pending_hits >= DEBOUNCE_REQUIRED and target != last_applied and now - last_switch >= COOLDOWN_SECONDS:
            _apply_profile(target)
            logger.info(f"activated {target['device_name']} -> {target['onboard_profile']} for {target['profile_name']}")
            active_game = target
            last_applied = {
                "device_name": target["device_name"],
                "profile_name": target["profile_name"],
                "onboard_profile": target["onboard_profile"],
            }
            last_switch = now
            pending_key = None
            pending_hits = 0

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
