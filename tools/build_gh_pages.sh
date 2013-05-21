#!/bin/sh

set -e

BUILD="$(mktemp -dt solaar-gh-pages-XXXXXX)"
cd "$(dirname "$0")"/..
SELF="$PWD"
SITE="$(readlink -f "$SELF/../gh-pages")"

#
#
#

add_md() {
	local SOURCE="$SELF/$1"
	local TARGET="$BUILD/$(basename "$1")"

	LAYOUT=default
	TITLE=$(grep '^# ' "$SOURCE" -m 1 | cut -c 3-)
	if test -n "$TITLE"; then
		local TITLE="Solaar - $TITLE"
		LAYOUT=page
	else
		local TITLE=Solaar
	fi

	cat >"$TARGET" <<-FRONTMATTER
		---
		layout: $LAYOUT
		title: $TITLE
		---

	FRONTMATTER

	cat "$SOURCE" >>"$TARGET"
}

fix_times() {
	local SOURCE="$SELF/$1"
	local TARGET="$SITE/$2"
	local f

	if test -d "$SOURCE"; then
		for f in "$SOURCE"/*; do
			f=$(basename "$f")
			fix_times "$1/$f" "$2/$f"
		done
	fi
	touch -r "$SOURCE" "$TARGET"
}

#
#
#

cp -upr "$SELF/jekyll"/* "$BUILD/"
cp -up "$SELF/share/solaar/icons/solaar-logo.png" "$BUILD/images/"
cp -up "$SELF/share/solaar/icons/solaar.png" "$BUILD/images/favicon.png"

add_md docs/devices.md
add_md docs/installation.md

add_md README.md
sed -i -e 's#\[docs/\([a-z]*\)\.md\]#[\1]#g' "$BUILD/README.md"
sed -i -e 's#(docs/\([a-z]*\)\.md)#(\1.html)#g' "$BUILD/README.md"
sed -i -e 's#(COPYING)#({{ site.repository }}/blob/master/COPYING)#g' "$BUILD/README.md"

for l in "$BUILD/_layouts"/*.html; do
	sed -e '/^$/d' "$l" | tr -d '\t' >"$l="
	mv "$l=" "$l"
done

mkdir -p "$SITE/../packages"
cp -up "$SELF/dist/debian"/*.deb "$SITE/../packages/"

GIT_BACKUP="$(mktemp -ud --tmpdir="$SITE/.." git-backup-XXXXXX)"
mv "$SITE/.git" "$GIT_BACKUP"
jekyll --kramdown "$BUILD" "$SITE"
mv "$GIT_BACKUP" "$SITE/.git"

cp -al "$SITE/../packages/" "$SITE/"

for p in "$SITE"/*.html; do
	sed -i -e 's#^[ ]*##g' "$p"
	sed -i -f- "$p" <<-SED
		bstart
		:eop /<\/p>/ brepl
		{ N; beop; }
		:repl { s#<li>\n<p>\(.*\)</p>#<li>\1#g; t; }
		:start /<li>/ N
		/<li>\n<p>/ {N;beop;}
		:end
		SED
done
mv "$SITE/README.html" "$SITE/index.html"

fix_times README.md index.html
fix_times docs/devices.md devices.html
fix_times docs/installation.md installation.html
fix_times jekyll/images images
fix_times share/solaar/icons/solaar-logo.png images/solaar-logo.png
fix_times jekyll/style style
