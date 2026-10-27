# Solaar translation coverage

Solaar uses GNU gettext catalogues in `po/*.po` and the English template
`po/solaar.pot`. English is the source language; these catalogues cover the
locales that currently have translators. Having a PO file does **not** mean
that every string in that language has been translated.

## Audit all existing languages

From the repository root:

```sh
python3 tools/po-coverage.py
python3 tools/po-coverage.py --missing ru
python3 tools/po-coverage.py --json
```

The audit is read-only and uses only the Python standard library. It compares
active source-message IDs (including contexts) with every existing catalogue,
excluding fuzzy, empty, and obsolete translations from the completed count.
`Outdated` means messages in a catalogue not present in the current template;
this can happen when translations have not yet been merged with a new template.
It is **not** a measure of incorrect translations.

The script does not translate anything automatically and does not modify
`po/*.po`. Use its output as a review queue, not as a measure of translation
quality.

## Update a language

Follow the official [translation instructions](i18n.md):

1. Install GNU gettext and your locale's GTK language pack.
2. Run `./tools/po-update.sh <locale>`, e.g. `./tools/po-update.sh ru`.
3. Translate the remaining `msgstr` values in `po/<locale>.po`. Preserve
   Python format placeholders such as `%(name)s`, `%d`, and `{count}`,
   markup, newline escapes, and plural forms.
4. Validate with `msgfmt --check --check-format -o /dev/null po/<locale>.po`.
5. Run `./tools/po-compile.sh` and test `LANGUAGE=<locale> ./bin/solaar`.
6. Re-run `./tools/po-update.sh <locale>` before submitting a PR to minimize
   formatting drift.

The Russian changes contributed alongside this audit cover 90 source
messages absent from the prior `ru.po`. Their phrasing should be reviewed
by a fluent Russian-speaking contributor before merging.

## Extending Solaar to more languages

To add an entirely new locale, use `./tools/po-update.sh <locale>` and
contribute actual reviewed translations. Do not create empty catalogues or
populate missing entries with copied English; that makes a language appear
available without meaningful localized support.

Each language is independently reviewed and should be contributed in
separate changes where practicable. This audit supports **all existing
catalogues** without claiming every human language has been translated.
