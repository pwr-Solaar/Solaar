"""Standard library only; no physical device required."""

import importlib.util
import unittest

from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit = load("audit", BASE / "tools/solaar-platform-audit.py")
plan = load("plan", BASE / "tools/solaar-config-plan.py")


class FedoraToolsTests(unittest.TestCase):
    def test_read_only_audit_report(self):
        r = audit.collect()
        self.assertEqual(r["actions_performed"], "read-only inspection")
        self.assertFalse(r["fips_compliance_verified"])
        self.assertIn(r["secure_boot_indicator"], ("enabled", "disabled", "unknown"))
        self.assertIn(r["kernel_fips_indicator"], ("enabled", "disabled", "unknown"))
        self.assertIsInstance(r["hidraw"]["count"], int)

    def test_plan_never_invokes_shell(self):
        self.assertEqual(
            plan.commands({"device": "Mouse", "settings": [{"setting": "dpi", "value": "1200"}]}),
            [["solaar", "config", "Mouse", "dpi", "1200"]],
        )

    def test_invalid_keys(self):
        with self.assertRaises(ValueError):
            plan.commands({"device": "Mouse", "settings": [], "surprise": "x"})

    def test_reject_leading_dash(self):
        with self.assertRaises(ValueError):
            plan.commands({"device": "Mouse", "settings": [{"setting": "dpi", "value": "--help"}]})

    def test_reject_control_characters(self):
        with self.assertRaises(ValueError):
            plan.commands({"device": "Mouse\nX", "settings": [{"setting": "dpi", "value": "1200"}]})

    def test_os_release_parser(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "os-release"
            f.write_text('ID="fedora"\nVERSION_ID="44"\nPRETTY_NAME="Test"\n')
            self.assertEqual(audit.os_release(f), {"id": "fedora", "version_id": "44"})


if __name__ == "__main__":
    unittest.main()
