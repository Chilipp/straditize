=================================
Digitizing stratigraphic diagrams
=================================

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

**BETA-VERSION**: Straditize is currently in it's beta version. New
installation methods will be provided and the documentation will be
significantly improved.

EGU Presentation
-----------------
straditize will be presented at the  European Geosciences Union General
Assembly (EGU) 2018 as a `PICO presentation`_ in the session of
`Free and Open Source Software (FOSS) for Geoinformatics and Geosciences`_.

The PICO presentation files can be downloaded via http://dx.doi.org/10.13140/RG.2.2.34357.58083

.. _PICO presentation: https://meetingorganizer.copernicus.org/EGU2018/EGU2018-4433.pdf
.. _Free and Open Source Software (FOSS) for Geoinformatics and Geosciences: https://meetingorganizer.copernicus.org/EGU2018/session/26511

Installation
------------
At the moment, straditize has to be installed from the source files, i.e. the
github repository. We highly recommend to use anaconda_ and install the
dependencies via::

    conda config --add channels conda-forge
    conda install -c chilipp/label/dev psyplot-gui scikit-image
    git clone https://github.com/Chilipp/straditize.git
    cd straditize
    python setup.py install

It can then be started from the command line via::

    straditize
