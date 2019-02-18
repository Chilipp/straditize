=================================
Digitizing stratigraphic diagrams
=================================

.. start-badges

.. list-table::
    :stub-columns: 1
    :widths: 10 90

    * - docs
      - |docs|
    * - tests
      - |travis| |appveyor| |codecov|
    * - package
      - |version| |conda| |joss| |github|
    * - implementations
      - |supported-versions| |supported-implementations|

.. |docs| image:: http://readthedocs.org/projects/straditize/badge/?version=latest
    :alt: Documentation Status
    :target: http://straditize.readthedocs.io/en/latest/?badge=latest

.. |travis| image:: https://travis-ci.org/Chilipp/straditize.svg?branch=master
    :alt: Travis
    :target: https://travis-ci.org/Chilipp/straditize

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/c1c8pqvh8h8rolxw?svg=true
    :alt: AppVeyor
    :target: https://ci.appveyor.com/project/Chilipp/straditize/branch/master

.. |codecov| image:: https://codecov.io/gh/Chilipp/straditize/branch/master/graph/badge.svg
    :alt: Coverage
    :target: https://codecov.io/gh/Chilipp/straditize

.. |version| image:: https://img.shields.io/pypi/v/straditize.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/straditize

.. |conda| image:: https://anaconda.org/conda-forge/straditize/badges/version.svg
    :alt: conda
    :target: https://anaconda.org/conda-forge/straditize

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/straditize.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/straditize

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/straditize.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/straditize

.. |joss| image:: http://joss.theoj.org/papers/10.21105/joss.01216/status.svg
    :alt: Journal of Open Source Software
    :target: https://doi.org/10.21105/joss.01216

.. |github| image:: https://img.shields.io/github/release/Chilipp/straditize.svg
    :target: https://github.com/Chilipp/straditize/releases/latest
    :alt: Latest github release

.. end-badges

STRADITIZE (Stratigraphic Diagram Digitizer) is an open-source program that
allows stratigraphic figures to be digitized in a single semi-automated
operation. It is designed to detect multiple plots of variables analyzed along
the same vertical axis, whether this is a sediment core or any similar
depth/time series.

Usually, in an age of digital data analysis, gaining access to data from the
pre-digital era – or any data that is only available as a figure on a page –
remains a problem and an under-utilized scientific resource.

This program tackles this problem by providing a python package to digitize
especially pollen diagrams, but also any other type of stratigraphic diagram.

Straditize is written in python and supports mixtures of many different diagram
types, such as bar plots, line plots, as well as shaded, stacked, and filled
area plots. The package provides an extensively documented graphical user
interface for a point-and-click handling of the semi-automatic process, but can
also be scripted or used from the command line. Other features of STRADITIZE
include text recognition to interpret the names of the different plotted
variables, the automatic and semi-automatic recognition of picture artifacts,
as well an automatic measurement finder to exactly reproduce the data that has
been used to create the diagram.

Installation
------------
We highly recommend to use anaconda_ and install straditize into its own
environment::

    conda create -n straditize -c conda-forge straditize
    conda activate straditize

or install it from the source files via::

    git clone https://github.com/Chilipp/straditize.git
    cd straditize
    pip install .  # or python setup.py install, but pip is recommended

It can then be started from the command line via::

    straditize

A more detailed description is provided in the docs_.

.. _anaconda: https://conda.io/en/latest/miniconda.html
.. _docs: https://straditize.readthedocs.io/en/latest/installing.html

License
-------
straditize is published under the
`GNU General Public License v3.0 <https://www.gnu.org/licenses/>`__
under the copyright of Philipp S. Sommer, 2018-2019
