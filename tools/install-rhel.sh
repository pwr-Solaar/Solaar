#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/solaar"
LOG_FILE="$LOG_DIR/rhel-install-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

say() {
    printf '\n[%s] %s\n' "$SCRIPT_NAME" "$*"
}

warn() {
    printf '\n[%s] WARNING: %s\n' "$SCRIPT_NAME" "$*"
}

fail() {
    printf '\n[%s] ERROR: %s\n' "$SCRIPT_NAME" "$*"
    exit 1
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local answer

    while true; do
        if [[ "$default" == "y" ]]; then
            read -r -p "$prompt [Y/n]: " answer || true
            answer="${answer:-y}"
        else
            read -r -p "$prompt [y/N]: " answer || true
            answer="${answer:-n}"
        fi

        case "${answer,,}" in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            *) echo "Please answer y or n." ;;
        esac
    done
}

ask_value() {
    local prompt="$1"
    local default="$2"
    local answer

    read -r -p "$prompt [$default]: " answer || true
    printf '%s\n' "${answer:-$default}"
}

run_cmd() {
    say "Running: $*"
    "$@"
}

run_sudo() {
    say "Running with sudo: $*"
    sudo "$@"
}

if [[ "${EUID}" -eq 0 ]]; then
    fail "Do not run as root. Run as your normal user; this script uses sudo when needed."
fi

say "Log file: $LOG_FILE"
say "This installer follows RHEL.md for RHEL 10-like systems."

if ask_yes_no "Update dnf metadata first?" y; then
    run_sudo dnf makecache
fi

if ask_yes_no "Check for Logitech USB receiver with lsusb now?" y; then
    if lsusb | grep -i logitech; then
        say "Logitech device detected."
    else
        warn "No Logitech USB receiver detected via lsusb right now. You can continue anyway."
        ask_yes_no "Continue without receiver detection?" y || fail "Aborted by user."
    fi
fi

BASE_PACKAGES=(python3 python3-pip git libinput evemu)
DEV_PACKAGES=(python3-devel gcc pkgconf-pkg-config gtk3 python3-gobject)

say "Base packages: ${BASE_PACKAGES[*]}"
say "Build/runtime packages: ${DEV_PACKAGES[*]}"

if ask_yes_no "Install required packages with dnf?" y; then
    run_sudo dnf install -y "${BASE_PACKAGES[@]}" "${DEV_PACKAGES[@]}"
fi

REPO_PARENT_DEFAULT="$HOME/dev-repos"
REPO_PARENT="$(ask_value "Repository parent directory" "$REPO_PARENT_DEFAULT")"
REPO_URL_DEFAULT="https://github.com/pwr-Solaar/Solaar.git"
REPO_URL="$(ask_value "Git URL for Solaar" "$REPO_URL_DEFAULT")"
REPO_DIR_DEFAULT="$REPO_PARENT/Solaar"
REPO_DIR="$(ask_value "Local checkout directory" "$REPO_DIR_DEFAULT")"

run_cmd mkdir -p "$REPO_PARENT"

if [[ -d "$REPO_DIR/.git" ]]; then
    say "Existing git checkout found at $REPO_DIR"
    if ask_yes_no "Pull latest changes in this repository?" y; then
        run_cmd git -C "$REPO_DIR" pull --ff-only
    fi
else
    run_cmd git clone "$REPO_URL" "$REPO_DIR"
fi

say "Installing Solaar into user site-packages"
if ask_yes_no "Use upgrade mode for pip install?" n; then
    run_cmd python3 -m pip install --user --upgrade "$REPO_DIR"
else
    run_cmd python3 -m pip install --user "$REPO_DIR"
fi

SOLAAR_BIN="$HOME/.local/bin/solaar"
if [[ ! -x "$SOLAAR_BIN" ]]; then
    fail "Expected executable not found: $SOLAAR_BIN"
fi

say "Installed binary: $SOLAAR_BIN"
run_cmd "$SOLAAR_BIN" --help >/dev/null

if ask_yes_no "Add alias 'solaar=$SOLAAR_BIN' to ~/.bashrc if missing?" y; then
    if grep -Fqx "alias solaar=\"$SOLAAR_BIN\"" "$HOME/.bashrc" 2>/dev/null; then
        say "Alias already exists in ~/.bashrc"
    else
        printf '\n# Solaar user-local install\nalias solaar="%s"\n' "$SOLAAR_BIN" >> "$HOME/.bashrc"
        say "Alias appended to ~/.bashrc"
    fi
fi

if ask_yes_no "Run 'solaar show' now for validation?" y; then
    run_cmd "$SOLAAR_BIN" show || warn "'solaar show' returned a non-zero status."
fi

if ask_yes_no "Run 'solaar config <device name>' now?" n; then
    DEVICE_NAME_DEFAULT="M720 Triathlon Multi-Device Mouse"
    DEVICE_NAME="$(ask_value "Device name" "$DEVICE_NAME_DEFAULT")"
    run_cmd "$SOLAAR_BIN" config "$DEVICE_NAME" || warn "'solaar config' returned a non-zero status."
fi

if ask_yes_no "Run libinput debug-events for a specific /dev/input/eventX device?" n; then
    EVENT_NODE="$(ask_value "Input event node" "/dev/input/eventX")"
    warn "This is a live monitor and may run until interrupted (Ctrl+C)."
    run_sudo libinput debug-events --device "$EVENT_NODE"
fi

if ask_yes_no "Run keyd monitor (/usr/local/bin/keyd) if present?" n; then
    if [[ -x /usr/local/bin/keyd ]]; then
        warn "This is a live monitor and may run until interrupted (Ctrl+C)."
        run_sudo /usr/local/bin/keyd monitor
    else
        warn "/usr/local/bin/keyd not found; skipping."
    fi
fi

say "Install workflow completed."
say "To use alias in current shell: source ~/.bashrc"
say "Evidence log saved at: $LOG_FILE"
