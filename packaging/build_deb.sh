#!/bin/sh

set -e

export DEBFULLNAME="Daniel Pavel"
export DEBMAIL=${DEBMAIL:-daniel.pavel+debian@gmail.com}
export DEBSIGN_KEYID=${DEBSIGN_KEYID:-0B34B1A7}

DISTRIBUTION=${DISTRIBUTION:-debian}
DIST_RELEASE=${DIST_RELEASE:-unstable}

cd "$(dirname "$0")/.."
UDEV_RULES="$PWD/rules.d"
DEBIAN_FILES="$PWD/packaging/debian"
DIST_TARGET="$PWD/dist/$DISTRIBUTION"

#
# build a python sdist package
#

export TMPDIR=${TMPDIR:-/tmp}/solaar-build-$USER
/bin/mkdir --parents --mode=0700 "$TMPDIR"
BUILD_DIR="$TMPDIR/build-$DISTRIBUTION"
/bin/rm --recursive --force "$BUILD_DIR"
/bin/mkdir --parents --mode=0700 "$BUILD_DIR"
python "setup.py" sdist --dist-dir="$BUILD_DIR" --formats=gztar

cd "$BUILD_DIR"

# guess the version of the built sdist
S=$(ls -1t solaar-*.tar.gz | tail -n 1)
test -r "$S"
VERSION=${S#solaar-}
VERSION=${VERSION%.tar.gz}

# check the last version built
LAST=$(head -n 1 "$DEBIAN_FILES/changelog" | grep -o ' ([0-9.-]*) ')
LAST=${LAST# (}
LAST=${LAST%) }
LAST_VERSION=$(echo "$LAST" | cut -d- -f 1)
LAST_BUILD=$(echo "$LAST" | cut -d- -f 2)

if test "$BUILD_EXTRA"; then
	# when building for a distro other than Debian, keep the same build number,
	# just append the BUILD_EXTRA to it
	BUILD_NUMBER=$LAST_BUILD
elif dpkg --compare-versions "$VERSION" gt "$LAST_VERSION"; then
	# the version increased, this is the first build for this version
	BUILD_NUMBER=1
else
	# increase the build number
	BUILD_NUMBER=$(($LAST_BUILD + 1))
fi

tar xfz "$S"
mv "$S" solaar_$VERSION.orig.tar.gz

#
# preparing to build the package
#

cd solaar-$VERSION
cp -a "$DEBIAN_FILES" .

# udev rules, if not already set
test -s debian/solaar.udev || cp -a "$UDEV_RULES"/??-*.rules debian/solaar.udev

# generate the changelog with the right version number and release
cat >debian/changelog <<_CHANGELOG
solaar ($VERSION-$BUILD_NUMBER$BUILD_EXTRA) $DIST_RELEASE; urgency=low

  * Debian packaging scripts, supports ubuntu ppa as well.

 -- $DEBFULLNAME <$DEBMAIL>  $(date -R)

_CHANGELOG

# if this is the main (Debian) build, update the changelog
test "$BUILD_EXTRA" || cp -a debian/changelog "$DEBIAN_FILES"/changelog

# other distros may have extra files to place in debian/
test "$DEBIAN_FILES_EXTRA" && cp -a $DEBIAN_FILES_EXTRA/* debian/

# set the right maintainer email address
sed -i -e "s/^Maintainer: .*$/Maintainer: $DEBFULLNAME <$DEBMAIL>/" debian/control

export DEBUILD_LINTIAN_OPTS="--profile $DISTRIBUTION"
export DEBUILD_DPKG_BUILDPACKAGE_OPTS="-sa"
export DEBUILD_PRESERVE_ENVVARS='GPG_AGENT_INFO,DISPLAY'
/usr/bin/debuild $@

#
# place the resulting files in dist/$DISTRIBUTION/
#

/bin/rm --force "$DIST_TARGET"/*
/bin/mkdir --parents "$DIST_TARGET"
cp -a -t "$DIST_TARGET" ../solaar_$VERSION*
cp -a -t "$DIST_TARGET" ../solaar-*_$VERSION* || true
