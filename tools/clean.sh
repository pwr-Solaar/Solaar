#!/bin/sh

cd "$(dirname "$0")/.."

find . -type f -name '*.py[co]' -delete
find . -type d -name '__pycache__' -delete

/bin/rm --force po/*~
/bin/rm --force --recursive share/locale/
/bin/rm --force share/*/solaar.desktop
