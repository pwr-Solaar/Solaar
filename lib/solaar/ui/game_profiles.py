import json
import subprocess
import sys
from pathlib import Path

import gi

from solaar.i18n import _

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

CONFIG_PATH = Path.home() / ".config" / "solaar" / "game_dpi_profiles.json"
SERVICE_PATH = Path.home() / ".config" / "systemd" / "user" / "solaar-game-profile-detector.service"
PROFILE_CHOICES = [f"Profile {i}" for i in range(1, 6)]
SERVICE_TEMPLATE = """[Unit]
Description=Solaar Game Profile Detector
After=graphical-session.target

[Service]
Type=simple
ExecStart=%h/.local/bin/solaar-game-profile-detector
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
"""


def _run_systemctl(*args):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)


def _load_config():
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception:
        return {}


def _save_config(data):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def _device_key(device):
    return getattr(device, "name", None) or getattr(device, "codename", None) or "Unknown Device"


def _service_status_text():
    active = _run_systemctl("is-active", "solaar-game-profile-detector.service")
    enabled = _run_systemctl("is-enabled", "solaar-game-profile-detector.service")
    return f"{_('Status')}: {active.stdout.strip() or active.stderr.strip() or 'unknown'} / {_('Autostart')}: {enabled.stdout.strip() or enabled.stderr.strip() or 'disabled'}"


def _service_enabled():
    result = _run_systemctl("is-enabled", "solaar-game-profile-detector.service")
    return result.returncode == 0 and result.stdout.strip() == "enabled"


class _GameProfilesDialog(Gtk.Dialog):
    def __init__(self, parent, device):
        super().__init__(title=_("Game DPI Profiles"), transient_for=parent, flags=0)
        self.device = device
        self.set_modal(True)
        self.set_default_size(760, 420)
        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(_("Save"), Gtk.ResponseType.OK)

        area = self.get_content_area()
        area.set_spacing(10)
        area.set_margin_top(10)
        area.set_margin_bottom(10)
        area.set_margin_start(10)
        area.set_margin_end(10)

        intro = Gtk.Label(label=_("Bind running games to onboard mouse profiles. Default profile is restored when the matched game exits."))
        intro.set_xalign(0)
        intro.set_line_wrap(True)
        area.pack_start(intro, False, False, 0)

        service_frame = Gtk.Frame(label=_("Background detector"))
        service_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 8)
        service_box.set_border_width(8)
        self.status_label = Gtk.Label(label=_service_status_text())
        self.status_label.set_xalign(0)
        service_box.pack_start(self.status_label, False, False, 0)

        self.autostart = Gtk.CheckButton(label=_("Start detector on login"))
        self.autostart.set_active(_service_enabled())
        service_box.pack_start(self.autostart, False, False, 0)

        btn_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        for label, callback in [
            (_("Install/repair service"), self._install_service),
            (_("Start detector"), self._start_service),
            (_("Stop detector"), self._stop_service),
            (_("Refresh status"), self._refresh_status),
        ]:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", callback)
            btn_box.pack_start(btn, False, False, 0)
        service_box.pack_start(btn_box, False, False, 0)
        service_frame.add(service_box)
        area.pack_start(service_frame, False, False, 0)

        self.store = Gtk.ListStore(str, str, str, bool)
        self._load_rows()

        tree = Gtk.TreeView(model=self.store)
        tree.set_hexpand(True)
        tree.set_vexpand(True)
        self.tree = tree

        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("editable", True)
        name_renderer.connect("edited", self._on_name_edited)
        tree.append_column(Gtk.TreeViewColumn(_("Name"), name_renderer, text=0))

        profile_renderer = Gtk.CellRendererCombo()
        profile_renderer.set_property("editable", True)
        profile_renderer.set_property("has-entry", False)
        combo_model = Gtk.ListStore(str)
        for choice in PROFILE_CHOICES:
            combo_model.append([choice])
        profile_renderer.set_property("model", combo_model)
        profile_renderer.set_property("text-column", 0)
        profile_renderer.connect("edited", self._on_profile_edited)
        tree.append_column(Gtk.TreeViewColumn(_("Onboard profile"), profile_renderer, text=1))

        aliases_renderer = Gtk.CellRendererText()
        aliases_renderer.set_property("editable", True)
        aliases_renderer.connect("edited", self._on_aliases_edited)
        tree.append_column(Gtk.TreeViewColumn(_("Game aliases"), aliases_renderer, text=2))

        default_renderer = Gtk.CellRendererToggle()
        default_renderer.connect("toggled", self._on_default_toggled)
        tree.append_column(Gtk.TreeViewColumn(_("Desktop default"), default_renderer, active=3))

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(tree)
        area.pack_start(scroller, True, True, 0)

        row_buttons = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 6)
        add_btn = Gtk.Button(label=_("Add binding"))
        add_btn.connect("clicked", self._add_row)
        remove_btn = Gtk.Button(label=_("Remove selected"))
        remove_btn.connect("clicked", self._remove_selected)
        row_buttons.pack_start(add_btn, False, False, 0)
        row_buttons.pack_start(remove_btn, False, False, 0)
        area.pack_start(row_buttons, False, False, 0)

        self.show_all()

    def _device_config(self):
        data = _load_config()
        key = _device_key(self.device)
        return data, key, data.get(key, {})

    def _load_rows(self):
        self.store.clear()
        _data, _key, device_cfg = self._device_config()
        profiles = device_cfg.get("profiles", [])
        if not profiles:
            self.store.append([_("Desktop"), "Profile 1", "", True])
            self.store.append([_("Minecraft"), "Profile 2", "minecraft", False])
            return
        for profile in profiles:
            self.store.append([
                profile.get("name", ""),
                profile.get("onboard_profile", "Profile 1"),
                ",".join(profile.get("aliases", [])),
                bool(profile.get("is_default", False)),
            ])

    def _refresh_status(self, *_args):
        self.status_label.set_text(_service_status_text())
        self.autostart.set_active(_service_enabled())

    def _install_service(self, *_args):
        SERVICE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SERVICE_PATH.write_text(SERVICE_TEMPLATE)
        _run_systemctl("daemon-reload")
        self._refresh_status()

    def _start_service(self, *_args):
        self._apply_autostart_choice()
        _run_systemctl("start", "solaar-game-profile-detector.service")
        self._refresh_status()

    def _stop_service(self, *_args):
        _run_systemctl("stop", "solaar-game-profile-detector.service")
        self._refresh_status()

    def _apply_autostart_choice(self):
        if self.autostart.get_active():
            _run_systemctl("enable", "solaar-game-profile-detector.service")
        else:
            _run_systemctl("disable", "solaar-game-profile-detector.service")

    def _add_row(self, *_args):
        self.store.append([_("New profile"), "Profile 1", "", False])

    def _remove_selected(self, *_args):
        selection = self.tree.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            model.remove(treeiter)

    def _on_name_edited(self, _renderer, path, text):
        self.store[path][0] = text

    def _on_profile_edited(self, _renderer, path, text):
        self.store[path][1] = text

    def _on_aliases_edited(self, _renderer, path, text):
        self.store[path][2] = text

    def _on_default_toggled(self, _renderer, path):
        for idx, row in enumerate(self.store):
            row[3] = str(idx) == path

    def save(self):
        self._apply_autostart_choice()
        data, key, _device_cfg = self._device_config()
        profiles = []
        has_default = False
        for row in self.store:
            name = row[0].strip()
            onboard_profile = row[1].strip() or "Profile 1"
            aliases = [a.strip().lower() for a in row[2].split(",") if a.strip()]
            is_default = bool(row[3])
            has_default = has_default or is_default
            profiles.append({
                "name": name or onboard_profile,
                "onboard_profile": onboard_profile,
                "aliases": aliases,
                "is_default": is_default,
            })
        if profiles and not has_default:
            profiles[0]["is_default"] = True
        data[key] = {"profiles": profiles}
        _save_config(data)


def show(parent, device):
    if device is None:
        return
    dialog = _GameProfilesDialog(parent, device)
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        dialog.save()
    dialog.destroy()
