.. straditize documentation master file

.. _straditize:

Digitizing stratigraphic diagrams
=================================

.. image:: _static/straditize.png
    :width: 50%
    :alt: straditize logo
    :align: center

.. only:: html and not epub

    .. start-badges

    .. list-table::
        :stub-columns: 1
        :widths: 10 90

        * - docs
          - |docs|
        * - tests
          - |travis| |appveyor| |requires| |codecov|
        * - package
          - |version| |conda| |github|
        * - implementations
          - |supported-versions| |supported-implementations|

    .. |docs| image:: http://readthedocs.org/projects/straditize/badge/?version=latest
        :alt: Documentation Status
        :target: http://straditize.readthedocs.io/en/latest/?badge=latest

    .. |travis| image:: https://travis-ci.org/Chilipp/straditize.svg?branch=master
        :alt: Travis
        :target: https://travis-ci.org/Chilipp/straditize

    .. |appveyor| image:: https://ci.appveyor.com/api/projects/status/3jk6ea1n4a4dl6vk/branch/master?svg=true
        :alt: AppVeyor
        :target: https://ci.appveyor.com/project/Chilipp/straditize/branch/master

    .. |codecov| image:: https://codecov.io/gh/Chilipp/straditize/branch/master/graph/badge.svg
        :alt: Coverage
        :target: https://codecov.io/gh/Chilipp/straditize

    .. |requires| image:: https://requires.io/github/Chilipp/straditize/requirements.svg?branch=master
        :alt: Requirements Status
        :target: https://requires.io/github/Chilipp/straditize/requirements/?branch=master

    .. |version| image:: https://img.shields.io/pypi/v/straditize.svg?style=flat
        :alt: PyPI Package latest release
        :target: https://pypi.python.org/pypi/straditize

    .. |conda| image:: https://anaconda.org/chilipp/straditize/badges/version.svg
        :alt: conda
        :target: https://anaconda.org/chilipp/straditize

    .. |supported-versions| image:: https://img.shields.io/pypi/pyversions/straditize.svg?style=flat
        :alt: Supported versions
        :target: https://pypi.python.org/pypi/straditize

    .. |supported-implementations| image:: https://img.shields.io/pypi/implementation/straditize.svg?style=flat
        :alt: Supported implementations
        :target: https://pypi.python.org/pypi/straditize

    .. |joss| image:: http://joss.theoj.org/papers/3535c28017003f0b5fb63b1b64118b60/status.svg
        :alt: Journal of Open Source Software
        :target: http://joss.theoj.org/papers/3535c28017003f0b5fb63b1b64118b60

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

**BETA-VERSION**: Straditize is currently in it's beta version. New
installation methods will be provided and the documentation will be
significantly improved.

The package is very new and there are many features that will be included in
the future. So we are very pleased for feedback! Please simply raise an issue
on `GitHub <https://github.com/Chilipp/straditize>`__.


Documentation
-------------

.. toctree::
    :maxdepth: 1

    about
    installing
    command_line
    gui/straditize
    api/straditize
    todos


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
