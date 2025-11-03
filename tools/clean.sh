#!/usr/bin/env sh

cd "$(dirname "$0")/.."

find . -type f -name '*.py[co]' -delete
find . -type d -name '__pycache__' -delete

rm --force po/*~
rm --force --recursive share/locale/
