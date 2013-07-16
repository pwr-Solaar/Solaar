#!/bin/sh

set -e

BUILD="$(/bin/mktemp --directory --tmpdir solaar-gh-pages-XXXXXX)"
cd "$(/usr/bin/dirname "$0")/.."
SELF="$PWD"
SITE="$(/bin/readlink --canonicalize "$SELF/../gh-pages")"

#
#
#

add_md() {
	local SOURCE="$SELF/$1"
	local TARGET="$BUILD/${2:-$(/usr/bin/basename "$1")}"

	LAYOUT=default
	TITLE=$(/bin/grep --max-count=1 '^# ' "$SOURCE" | /usr/bin/cut --characters=3-)
	if test -n "$TITLE"; then
		local TITLE="Solaar - $TITLE"
		LAYOUT=page
	else
		local TITLE=Solaar
	fi

	/bin/mkdir --parents "$(dirname "$TARGET")"
	/bin/cat >"$TARGET" <<-FRONTMATTER
		---
		layout: $LAYOUT
		title: $TITLE
		---

	FRONTMATTER

	/bin/cat "$SOURCE" >>"$TARGET"
}

fix_times() {
	local SOURCE="$SELF/$1"
	local TARGET="$SITE/$2"
	local f

	if test -d "$SOURCE"; then
		for f in "$SOURCE"/*; do
			f=$(/usr/bin/basename "$f")
			fix_times "$1/$f" "$2/$f"
		done
	fi
	/usr/bin/touch --reference="$SOURCE" "$TARGET"
}

#
#
#

/bin/cp --archive --update "$SELF/jekyll"/* "$BUILD/"
# convert the svg logo to png for the web site favicon
/usr/bin/convert.im6 "$SELF/share/solaar/icons/solaar.svg" -transparent white \
	-resize 32x32 "$BUILD/images/favicon.png"

# optimize the converted pngs
command -V optipng && optipng -preserve -quiet -o 7 "$BUILD/images"/*.png
#command -V pngcrush && pngcrush -d "$BUILD/images" -oldtimestamp -q "$BUILD/images"/*.png

add_md docs/devices.md
add_md docs/installation.md

add_md README.md index.md
# fix local links to the proper .html files
/bin/sed --in-place --expression='s#\[docs/\([a-z]*\)\.md\]#[\1]#g' "$BUILD/index.md"
/bin/sed --in-place --expression='s#(docs/\([a-z]*\)\.md)#(\1.html)#g' "$BUILD/index.md"
/bin/sed --in-place --expression='s#(COPYING)#({{ site.repository }}/blob/master/COPYING)#g' "$BUILD/index.md"

# remove empty lines, to minimze html sizes
for l in "$BUILD/_layouts"/*.html; do
	/bin/sed --expression='/^$/d' "$l" | /usr/bin/tr --delete '\t' >"$l="
	/bin/mv "$l=" "$l"
done

# create packages/ sub-directory
/bin/mkdir --parents "$SITE/../packages" "$SITE/packages/"
/bin/cp --archive --update --target-directory="$SITE/../packages/" "$SELF/dist/debian"/solaar_* || true
/bin/cp --archive --update --target-directory="$SITE/../packages/" "$SELF/dist/debian"/solaar-gnome3_* || true
if test -x /usr/bin/dpkg-scanpackages; then
	cd "$SITE/../packages/"
	/bin/rm --force *.build
	/usr/bin/dpkg-scanpackages --multiversion . > Packages
	/usr/bin/dpkg-scansources . > Sources
	add_md docs/debian.md
	cd -
fi

# check for the latest released version, and update the jekyll configuration
if test -x /usr/bin/uscan; then
	TAG=$(/usr/bin/uscan --no-conf --report-status --check-dirname-regex packaging ./packaging/ \
				| /bin/grep 'Newest version' \
				| /bin/grep --only-matching --word-regexp '[0-9.]*' | /usr/bin/head --lines=1)
	if test -n "$TAG"; then
		/bin/sed --in-place --expression='s#^version: .*$#'"version: $TAG#" "$SELF/jekyll/_config.yml"
		/bin/sed --in-place --expression='s#/archive/[0-9.]*\.tar\.gz$#'"/archive/$TAG.tar.gz#" "$SELF/jekyll/_config.yml"
	fi
fi

# Jekyll nukes the .git folder in the target
# so move it out of the way while building.
GIT_BACKUP="$(/bin/mktemp --dry-run --directory --tmpdir="$SITE/.." git-backup-XXXXXX)"
/bin/mv --no-target-directory "$SITE/.git" "$GIT_BACKUP"
jekyll --kramdown "$BUILD" "$SITE"
/bin/mv --no-target-directory "$GIT_BACKUP" "$SITE/.git"

/bin/cp --archive --link "$SITE/../packages/" "$SITE/"

# fix some html formatting
for p in "$SITE"/*.html; do
	/bin/sed --in-place --expression='s#^[ ]*##g' "$p"
	/bin/sed --in-place --file=- "$p" <<-SED
		bstart
		:eop /<\/p>/ brepl
		{ N; beop; }
		:repl { s#<li>\n<p>\(.*\)</p>#<li>\1#g; t; }
		:start /<li>/ N
		/<li>\n<p>/ {N;beop;}
		:end
		SED
done

# set timestmap of the created files to match the sources
fix_times README.md index.html
fix_times docs/devices.md devices.html
fix_times docs/installation.md installation.html
fix_times docs/debian.md debian.html
fix_times jekyll/images images
fix_times share/solaar/icons/solaar.svg images/favicon.png
fix_times jekyll/style style
