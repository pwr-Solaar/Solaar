#!/bin/sh

set -e

if test ! -r "$HOME/.devscripts"; then
	echo "$HOME/.descripts must exist"
	exit 1
fi
. "$HOME/.devscripts"

cd "$(dirname "$0")/.."
DEBIAN_FILES="$PWD/packaging/debian"
DIST="$PWD/dist/${DISTRIBUTION:=debian}"
DIST_RELEASE=${DIST_RELEASE:-UNRELEASED}

BUILD_DIR="${TMPDIR:-/tmp}/$DIST"
rm -rf "$BUILD_DIR"
mkdir -m 0700 -p "$BUILD_DIR"
python "setup.py" sdist --dist-dir="$BUILD_DIR" --formats=gztar

cd "$BUILD_DIR"
S=$(ls -1t solaar-*.tar.gz | tail -n 1)
test -r "$S"
VERSION=${S#solaar-}
VERSION=${VERSION%.tar.gz}

LAST=$(head -n 1 "$DEBIAN_FILES/changelog" | grep -o ' ([0-9.-]*) ')
LAST=${LAST# (}
LAST=${LAST%) }
LAST_VERSION=$(echo "$LAST" | cut -d- -f 1)
LAST_BUILD=$(echo "$LAST" | cut -d- -f 2)

if test -n "$BUILD_EXTRA"; then
	BUILD_NUMBER=$LAST_BUILD
elif dpkg --compare-versions "$VERSION" gt "$LAST_VERSION"; then
	BUILD_NUMBER=1
else
	BUILD_NUMBER=$(($LAST_BUILD + 1))
fi

tar xfz "$S"
mv "$S" solaar_$VERSION.orig.tar.gz

cd solaar-$VERSION
cp -a "$DEBIAN_FILES" .
cat >debian/changelog <<_CHANGELOG
solaar ($VERSION-$BUILD_NUMBER$BUILD_EXTRA) $DIST_RELEASE; urgency=low

  * Debian packaging scripts, supports ubuntu ppa as well.

 -- $DEBFULLNAME <$DEBMAIL>  $(date -R)

_CHANGELOG
test -z "$BUILD_EXTRA" && cp debian/changelog "$DEBIAN_FILES"/changelog

test -n "$DEBIAN_FILES_EXTRA" && cp -a $DEBIAN_FILES_EXTRA/* debian/

debuild ${DEBUILD_ARGS:-$@}

rm -rf "$DIST"
mkdir -p "$DIST"
cp -a -t "$DIST" ../solaar_$VERSION*
cp -a -t "$DIST" ../solaar-*_$VERSION* || true
cd "$DIST"
#cp -av -t ../../../packages/ * || true
