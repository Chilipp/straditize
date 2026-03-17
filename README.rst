=================================
Digitizing stratigraphic diagrams
=================================

.. start-badges

.. list-table::
    :stub-columns: 1
    :widths: 10 90

    * - docs
      - |docs|
    * - package
      - |version| |joss| |github|
    * - implementations
      - |supported-versions| |supported-implementations|

.. |docs| image:: http://readthedocs.org/projects/straditize/badge/?version=latest
    :alt: Documentation Status
    :target: http://straditize.readthedocs.io/en/latest/?badge=latest

.. |version| image:: https://img.shields.io/pypi/v/straditize.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/straditize

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

This refreshed ``0.2`` release focuses on reliable digitization on modern
Python, pandas and matplotlib stacks while preserving the original
stratigraphic workflow.

STRADITIZE (Stratigraphic Diagram Digitizer) is an open-source program that
allows stratigraphic figures to be digitized in a single semi-automated
operation. It is designed to detect multiple plots of variables analyzed along
the same vertical axis, whether this is a sediment core or any similar
depth/time series.

Usually, in an age of digital data analysis, gaining access to data from the
pre-digital era, or any data that is only available as a figure on a page,
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

Highlights in 0.2
-----------------

* Modernized runtime compatibility for Python 3.10-3.14, pandas 2.3-3.0 and
  current matplotlib / psyplot-gui stacks.
* Improved result review by overlaying digitized output on the source image
  with exportable comparison data.
* Better stacked-area sample inference via consensus interpolation.
* Restored modern Excel / NetCDF export paths and several headless Qt fixes.

Installation
------------

We recommend installing straditize into its own isolated environment from a
source checkout so the tested dependency stack is explicit.

Recommended source install with ``pixi``::

    git clone https://github.com/Chilipp/straditize.git
    cd straditize
    pixi init
    pixi add python=3.12 "numpy>=1.26" "pandas>=2.3" "matplotlib>=3.8" "scipy>=1.13" "xarray>=2024.7" "psyplot=1.5.1" "psyplot-gui=1.5.0" "pyqt=5.15" pyqtwebengine netcdf4 openpyxl scikit-image pillow
    pixi run pip install -e .
    pixi run straditize

Alternative source install with ``mamba``/``conda``::

    git clone https://github.com/Chilipp/straditize.git
    cd straditize
    mamba create -n straditize python=3.12 "numpy>=1.26" "pandas>=2.3" "matplotlib>=3.8" "scipy>=1.13" "xarray>=2024.7" "psyplot=1.5.1" "psyplot-gui=1.5.0" "pyqt=5.15" pyqtwebengine netcdf4 openpyxl scikit-image pillow pip
    mamba activate straditize
    pip install -e .

It can then be started from the command line via::

    straditize

Validated dependency stack
--------------------------

The ``0.2`` update has been verified with:

* Python 3.10 to 3.14
* NumPy >= 1.26
* pandas 2.3 to 3.0
* matplotlib 3.8 to 3.10
* SciPy >= 1.13
* xarray >= 2024.7
* psyplot 1.5.1
* psyplot-gui 1.5.0
* PyQt5 5.15

Older environments may still work, but the configurations above are the ones
that were exercised during this release refresh.

A more detailed description is provided in the docs_.

.. _docs: https://straditize.readthedocs.io/en/latest/installing.html

License
-------
straditize is published under the
`GNU General Public License v3.0 <https://www.gnu.org/licenses/>`__
under the copyright of Philipp S. Sommer, 2018-2019
