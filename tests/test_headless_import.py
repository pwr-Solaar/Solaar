"""The device core and listener must import without any GUI toolkit (needed by the headless plasmaard service)."""

import subprocess
import sys
import textwrap

import pytest

HEADLESS_MODULES = [
    "logitech_receiver.device",
    "logitech_receiver.receiver",
    "logitech_receiver.settings_templates",
    "logitech_receiver.notifications",
    "logitech_receiver.diversion",
    "solaar.configuration",
    "solaar.listener",
]

_BLOCKER = textwrap.dedent(
    """
    import importlib, importlib.abc, sys

    class Blocker(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name == "Xlib" or name.startswith("Xlib."):
                raise ImportError("blocked " + name)

    sys.meta_path.insert(0, Blocker())

    import gi
    _require_version = gi.require_version

    def require_version(namespace, version):
        if namespace in ("Gtk", "Gdk", "Notify"):
            raise ValueError("blocked gi " + namespace)
        return _require_version(namespace, version)

    gi.require_version = require_version
    importlib.import_module(sys.argv[1])
    """
)


@pytest.mark.parametrize("module", HEADLESS_MODULES)
def test_imports_without_gui_toolkit(module):
    result = subprocess.run([sys.executable, "-c", _BLOCKER, module], capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, result.stderr
