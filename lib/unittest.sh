#!/bin/sh

cd -P `dirname "$0"`

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$PWD/native/`uname -m`

exec python -m unittest discover -v "$@"
