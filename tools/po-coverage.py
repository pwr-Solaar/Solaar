#!/usr/bin/env python3
"""Report gettext translation coverage without changing any PO files.

Run from the repository root: python3 tools/po-coverage.py
Use --json for machine-readable output or --missing ru to review missing strings.
"""

import argparse
import ast
import json
import re

from pathlib import Path

FIELD_RE = re.compile(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")$')


def parse_po(path):
    """Return active gettext entries indexed by (context, source message)."""
    entries = {}
    text = Path(path).read_text(encoding="utf-8")
    for block in re.split(r"\n\s*\n", text):
        fields = {}
        flags = set()
        active = None
        obsolete = False
        for line in block.splitlines():
            if line.startswith("#~"):
                obsolete = True
                break
            if line.startswith("#,"):
                flags.update(flag.strip() for flag in line[2:].split(","))
                continue
            if line.startswith("#"):
                continue
            match = FIELD_RE.match(line)
            if match:
                active = match.group(1)
                fields[active] = ast.literal_eval(match.group(2))
            elif active is not None and line.lstrip().startswith('"'):
                fields[active] += ast.literal_eval(line.strip())
            else:
                active = None
        if obsolete or not fields.get("msgid"):
            continue
        key = (fields.get("msgctxt", ""), fields["msgid"])
        values = [value for name, value in fields.items() if name == "msgstr" or name.startswith("msgstr[")]
        entries[key] = {
            "translated": bool(values) and all(values) and "fuzzy" not in flags,
            "plural": "msgid_plural" in fields,
            "values": len(values),
        }
    return entries


def report(pot, po_dir):
    reference = parse_po(pot)
    result = []
    for path in sorted(po_dir.glob("*.po")):
        translated = parse_po(path)
        missing = [key for key, entry in reference.items() if key not in translated or not translated[key]["translated"]]
        result.append(
            {
                "language": path.stem,
                "total": len(reference),
                "translated": len(reference) - len(missing),
                "untranslated": len(missing),
                "coverage_percent": round(100 * (len(reference) - len(missing)) / len(reference), 1) if reference else 100.0,
                "catalog_only": sum(key not in reference for key in translated),
                "missing": [{"context": ctx, "msgid": msgid} for ctx, msgid in missing],
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pot", type=Path, default=Path("po/solaar.pot"))
    parser.add_argument("--po-dir", type=Path, default=Path("po"))
    parser.add_argument("--json", action="store_true", help="Print full JSON coverage including missing strings")
    parser.add_argument("--missing", metavar="LANG", help="List untranslated source strings for one language")
    args = parser.parse_args()

    if not args.pot.is_file() or not args.po_dir.is_dir():
        parser.error("translation template or PO directory does not exist")
    rows = report(args.pot, args.po_dir)
    if args.missing:
        row = next((r for r in rows if r["language"] == args.missing), None)
        if row is None:
            parser.error("unknown language: " + args.missing)
        print(f"{row['language']}: {row['untranslated']} untranslated messages")
        for item in row["missing"]:
            label = f"[{item['context']}] " if item["context"] else ""
            print(label + item["msgid"].replace("\n", "\\n"))
    elif args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(f"{'Language':<12} {'Translated':>10} {'Missing':>9} {'Coverage':>10} {'Outdated':>9}")
        for row in rows:
            print(
                f"{row['language']:<12} {row['translated']:>10} {row['untranslated']:>9} "
                f"{row['coverage_percent']:>9.1f}% {row['catalog_only']:>9}"
            )


if __name__ == "__main__":
    main()
