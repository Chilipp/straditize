#!/bin/bash
# script to automatically generate the straditize api documentation using
# sphinx-apidoc and sed
sphinx-apidoc -P -f -M -e  -T -o api ../straditize/ ../straditize/ocr.py
# replace chapter title in sphinx_nbexamples.rst
sed -i -e 1,1s/.*/'API Reference'/ api/straditize.rst
sed -i -e 2,2s/.*/'============='/ api/straditize.rst
