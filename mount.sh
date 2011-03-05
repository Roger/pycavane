#!/bin/sh
mkdir -p cuevana cache

# Check if python2 exists else fallback to python
PYTHON=$(which python2)
if [ $? -ne 0 ]; then
    PYTHON=python
fi

$PYTHON fucavane.py -oro,direct_io,max_readahead=6024 -f cuevana -c cache
