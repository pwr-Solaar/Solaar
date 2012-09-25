#!/bin/sh

cd `dirname "$0"`

export LD_LIBRARY_PATH=$PWD/lib
export PYTHONPATH=$PWD/lib
export PYTHONDONTWRITEBYTECODE=true
export PYTHONWARNINGS=all

python -m unittest discover -v "$@"
