#!/bin/sh

cd `dirname "$0"`
export LD_LIBRARY_PATH=$PWD

exec python -Qnew -m unittest discover -v "$@"
