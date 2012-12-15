#!/bin/sh

cd `dirname "$0"`/..
exec python setup.py sdist_dsc -x packaging/debian/stdeb.cfg bdist_deb "$@"
