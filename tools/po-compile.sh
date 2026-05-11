#!/usr/bin/env sh

set -e

cd "$(readlink -f "$(dirname "$0")/..")"

find "$PWD/po" -type f -name '*.po' | \
while read po_file; do
	language="$(basename "$po_file")"
	language="${language%.po}"
	target="$PWD/share/locale/$language/LC_MESSAGES/solaar.mo"
	mkdir --parents "$(dirname "$target")"
	msgfmt \
		--check \
		--output-file="$target" \
		"$po_file"
done
