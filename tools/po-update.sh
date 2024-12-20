#!/bin/sh

set -e

if test "$1" = "-h" -o "$1" = "--help"; then
	echo "Use: $0 [<language>]"
	echo "Run without arguments to update all translation files."
	exit 0
fi

cd "$(readlink -f "$(dirname "$0")/..")"

VERSION=$(python setup.py --version)
DOMAIN=$(python setup.py --name)

SOURCE_FILES=$(/bin/mktemp --tmpdir $DOMAIN-po-update-XXXXXX)

find "lib" -name '*.py' >"$SOURCE_FILES"
find "share" -name "*.template.desktop" >>"$SOURCE_FILES"

POT_DIR="$PWD/po"
test -d "$POT_DIR"

POT_FILE="$POT_DIR/$DOMAIN.pot"

/usr/bin/xgettext \
	--package-name "$DOMAIN" \
	--package-version "$VERSION" \
	--default-domain="$L_NAME" \
	--from-code=UTF-8 --files-from="$SOURCE_FILES" \
	--no-escape --indent --add-location --sort-by-file \
	--add-comments=I18N \
	--output="$POT_FILE"

/bin/sed --in-place --expression="s/charset=CHARSET/charset=UTF-8/" "$POT_FILE"


unfmt() {
	local SOURCE="/usr/share/locale/$LL_CC/LC_MESSAGES/$1.mo"
	if test ! -f "$SOURCE"; then
		SOURCE="/usr/share/locale-langpack/$LL_CC/LC_MESSAGES/$1.mo"
	fi
	local TARGET="$(mktemp --tmpdir $1-$LL_CC-XXXXXX.po)"
	/usr/bin/msgunfmt \
		--no-escape --indent \
		--output-file="$TARGET" \
		"$SOURCE"
	echo "$TARGET"
}

update_po() {
	local LL_CC="$1"
	local PO_FILE="$POT_DIR/$LL_CC.po"

	test -r "$PO_FILE" || /usr/bin/msginit \
			--no-translator --locale="$LL_CC" \
			--input="$POT_FILE" \
			--output-file="$PO_FILE"

	/usr/bin/msgmerge \
		--update --no-fuzzy-matching \
		--no-escape --indent --add-location --sort-by-file \
		--lang="$LL_CC" \
		--compendium="$(unfmt gtk30)" \
		--compendium="$(unfmt gtk30-properties)" \
		"$PO_FILE" "$POT_FILE"

	# /bin/sed --in-place --expression="s/Language: \\\\n/Language: $L_NAME\\\\n/" "$PO_FILE"
	echo "Updated $PO_FILE"
}

if test "$1"; then
	update_po "$1"
else
	for l in $(ls -1 "$POT_DIR"/??.po); do
		l="$(basename "$l")"
		update_po "${l%.po}"
	done
fi
