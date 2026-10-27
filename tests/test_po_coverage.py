"""Regression tests for the standalone gettext coverage report."""

import runpy
import tempfile
import unittest

from pathlib import Path

COVERAGE_SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "po-coverage.py"
UTILS = runpy.run_path(str(COVERAGE_SCRIPT))
parse_po = UTILS["parse_po"]
report = UTILS["report"]


class TranslationCoverageTests(unittest.TestCase):
    def test_parsing_plural_fuzzy_multiline_context_and_obsolete_entries(self):
        po_text = """
msgid ""
msgstr "Language: ru\\n"

msgid "Connected"
msgstr "Подключено"

#, fuzzy
msgid "Changed"
msgstr "Изменено"

msgctxt "mouse"
msgid "Left"
msgstr "Слева"

msgid "Single"
msgid_plural "Many"
msgstr[0] "Один"
msgstr[1] "Несколько"
msgstr[2] "Много"

msgid "Split text"
msgstr ""
"Разделённый "
"текст"

#~ msgid "Obsolete"
#~ msgstr "Устарело"
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ru.po"
            path.write_text(po_text, encoding="utf-8")
            entries = parse_po(path)
            self.assertEqual(len(entries), 5)
            self.assertTrue(entries[("", "Connected")]["translated"])
            self.assertFalse(entries[("", "Changed")]["translated"])
            self.assertTrue(entries[("mouse", "Left")]["translated"])
            self.assertTrue(entries[("", "Single")]["translated"])
            self.assertTrue(entries[("", "Split text")]["translated"])
            self.assertNotIn(("", "Obsolete"), entries)

    def test_report_counts_missing_and_stale_without_editing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            folder = base / "po"
            folder.mkdir()
            (folder / "solaar.pot").write_text(
                'msgid "New"\nmsgstr ""\n\nmsgid "Existing"\nmsgstr ""\n',
                encoding="utf-8",
            )
            locale = folder / "ru.po"
            locale.write_text(
                'msgid "Existing"\nmsgstr "Существующий"\n\n' 'msgid "Old"\nmsgstr "Старый"\n',
                encoding="utf-8",
            )
            result = report(folder / "solaar.pot", folder)
            self.assertEqual(len(result), 1)
            row = result[0]
            self.assertEqual(row["language"], "ru")
            self.assertEqual(row["translated"], 1)
            self.assertEqual(row["untranslated"], 1)
            self.assertEqual(row["coverage_percent"], 50.0)
            self.assertEqual(row["catalog_only"], 1)
            self.assertEqual(row["missing"], [{"context": "", "msgid": "New"}])
            self.assertIn('msgid "Old"', locale.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
