#!/bin/sh

set -e

if test ! -r "$HOME/.devscripts"; then
	echo "$HOME/.descripts must exist"
	exit 1
fi

cd "$(dirname "$0")/.."
DEBIAN_FILES="$PWD/packaging/debian"
DIST="$PWD/dist/${DISTRIBUTION:=debian}"

BUILD_DIR="${TMPDIR:-/tmp}/$DIST"
rm -rf "$BUILD_DIR"
mkdir -m 0700 -p "$BUILD_DIR"
python "setup.py" sdist --dist-dir="$BUILD_DIR" --formats=gztar

cd "$BUILD_DIR"
S=$(ls -1 solaar-*.tar.gz | head -n 1)
test -r "$S"
VERSION=${S#solaar-}
VERSION=${VERSION%.tar.gz}
tar xfz "$S"
mv "$S" solaar_$VERSION.orig.tar.gz

cd solaar-$VERSION
cp -a "$DEBIAN_FILES" .

test -n "$DEBIAN_FILES_EXTRA" && cp -a $DEBIAN_FILES_EXTRA/* debian/

debuild ${DEBUILD_ARGS:-$@}

rm -rf "$DIST"
mkdir -p "$DIST"
cp -a ../solaar_$VERSION* "$DIST"
cd "$DIST"
