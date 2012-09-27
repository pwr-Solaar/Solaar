#!/bin/sh

cd `dirname "$0"`
export LD_LIBRARY_PATH=$PWD

exec python -m unittest discover -v "$@"
