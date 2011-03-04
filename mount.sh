#!/bin/sh
mkdir -p cuevana cache
python fucavane.py -odirect_io,max_readahead=6024 -f cuevana -c cache
