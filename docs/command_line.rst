.. highlight:: bash

.. _command-line:

Command line usage
==================
The :mod:`straditize.__main__` module defines a simple parser to parse commands
from the command line to load a diagram or a straditize project.

It can be run from the command line via::

    python -m straditize [options] [arguments]

or simply::

    straditize [options] [arguments]

.. argparse::
   :module: straditize.__main__
   :func: get_parser
   :prog: straditize
