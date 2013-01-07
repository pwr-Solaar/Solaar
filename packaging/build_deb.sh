#!/bin/sh

set -e

cd `dirname "$0"`/..
DEBIAN_FILES="$PWD/packaging/debian"
DIST="$PWD/dist/${DISTRIBUTION:=debian}"

BUILD_DIR="${TMPDIR:-/tmp}/$DIST"
rm -rf "$BUILD_DIR"
mkdir -m 0700 -p "$BUILD_DIR"
python "setup.py" sdist --dist-dir="$BUILD_DIR" --formats=gztar

cd "$BUILD_DIR"
S=`ls -1 solaar-*.tar.gz`
VERSION=${S#solaar-}
VERSION=${VERSION%.tar.gz}
tar xfz "$S"
mv "$S" solaar_$VERSION.orig.tar.gz

cd solaar-$VERSION
cp -a "$DEBIAN_FILES" .

test -n "$DEBIAN_FILES_EXTRA" && cp -a $DEBIAN_FILES_EXTRA/* debian/
# test -d debian/patches && ls -1 debian/patches/*.diff | cut -d / -f 3 > debian/patches/series

debuild ${DEBUILD_ARGS:-$@}

rm -rf "$DIST"
mkdir -p "$DIST"
cp -a ../solaar_$VERSION* "$DIST"
cd "$DIST"
