#!/bin/sh

cd `dirname "$0"`
rm -f test.log
python -m unittest discover -v -p '*_test.py'
