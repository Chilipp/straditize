.. _install:

.. highlight:: bash

Installation
============

How to install
--------------
There basically four different methodologies for the installation. You should
choose the one, which is the most appropriate solution concerning your skills
and your usage:

The simple installation
    Use standalone installers which will install all the necessary packages and
    modules. See :ref:`install-standalone`
The intermediate installation
    For people coding in python, we recommend to install it through anaconda
    and the conda-forge channel (see :ref:`install-conda`) or, if you are
    not using anaconda, you can use pip (see :ref:`install-pip`)
The developer installation
    Install it from source (see :ref:`install-source`)


.. _install-standalone:

Installation via standalone installers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. todo::

    Will be provided in the future...

.. _install-conda:

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^
We highly recommend to use conda_ for installing straditize. Here you can
install it via manually via the `chilipp channel`_

After downloading the installer from anaconda_, you can install straditize simply
via::

    $ conda config --add channels conda-forge
    $ conda install -c chilipp/label/dev straditize

or install it into a new environment via::

    $ conda create -n straditize -c chilipp/label/dev straditize

and then activate the new environment via

    $ conda activate straditize

.. _install-pip:

Installation using pip
^^^^^^^^^^^^^^^^^^^^^^
If you do not want to use conda for managing your python packages, you can also
use the python package manager ``pip`` and install via::

    $ pip install straditize

However to be on the safe side, make sure you have the :ref:`dependencies`
installed.

.. _install-source:

Installation from source
^^^^^^^^^^^^^^^^^^^^^^^^
To install it from source, make sure you have the :ref:`dependencies`
installed, clone the github_ repository via::

    git clone https://github.com/Chilipp/straditize.git

and install it via::

    python setup.py install

.. _dependencies:

Dependencies
------------
Required dependencies
^^^^^^^^^^^^^^^^^^^^^
.. todo::

    Specify correct dependencies

straditize has been tested for python 3.6. Furthermore the
package is built upon multiple other packages, mainly

- xarray_>=0.8: Is used for the data management in the psyplot package
- matplotlib_>=1.4.3: **The** python visualiation
  package
- `PyYAML <http://pyyaml.org/>`__: Needed for the configuration of psyplot


.. _optional_deps:

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^
We furthermore recommend to use

- :ref:`psyplot-gui <psyplot_gui:install>`: A graphical user interface to psyplot
- :ref:`psy-simple <psy_simple:install>`: A psyplot plugin to make simple plots
- :ref:`psy-maps <psy_maps:install>`: A psyplot plugin for visualizing data on a
  map
- :ref:`psy-reg <psy_reg:install>`: A psyplot plugin for visualizing fits to
  your data
- cdo_: The python bindings for cdos (see also the
  :ref:`cdo example <gallery_examples_example_cdo.ipynb>`)

.. _netCDF4: https://github.com/Unidata/netcdf4-python
.. _gdal: http://www.gdal.org/
.. _conda: http://conda.io/
.. _anaconda: https://www.continuum.io/downloads
.. _chilipp channel: https://anaconda.org/chilipp
.. _matplotlib: http://matplotlib.org
.. _xarray installation notes: http://xarray.pydata.org/en/stable/installing.html
.. _xarray: http://xarray.pydata.org/
.. _cdo: https://code.zmaw.de/projects/cdo/wiki/Anaconda


Running the tests
-----------------
We us pytest_ to run our tests. So you can either run clone out the github_
repository and run::

    $ python setup.py test

or install pytest_ by yourself and run

    $ py.test


Building the docs
-----------------
To build the docs, check out the github_ repository and install the
requirements in ``'docs/environment.yml'``. The easiest way to do this is via
anaconda by typing::

    $ conda env create -f docs/environment.yml
    $ source activate straditize_docs

Then build the docs via::

    $ cd docs
    $ make html

.. _github: https://github.com/Chilipp/straditize
.. _pytest: https://pytest.org/latest/contents.html


.. _update:

Updating straditize
-------------------

.. _update-standalone:

Updating standalone app
^^^^^^^^^^^^^^^^^^^^^^^
.. todo::

    Need to document how to update the standalone app

.. _update-conda:

Updating via conda
^^^^^^^^^^^^^^^^^^
If you installed straditize via conda (see :ref:`install-conda`), you can
update it via::

    $ conda update -c chilipp/label/dev straditize

.. _update-pip:

Updating via pip
^^^^^^^^^^^^^^^^
If you installed it via ``pip`` (see :ref:`install-pip`), you can update it
via::

    $ pip install -U straditize


.. _uninstall:

Uninstallation
--------------
The uninstallation depends on the system you used to install straditize. Either
you did it via the :ref:`standalone installers <install-standalone>` (see
:ref:`uninstall-standalone`), via :ref:`conda <install-conda>` (see
:ref:`uninstall-conda`), via :ref:`pip <install-pip>` or from the
:ref:`source files <install-source>` (see :ref:`uninstall-pip`).

Anyway, if you may want to remove the psyplot configuration files. If you did
not specify anything else (see :func:`psyplot.config.rcsetup.psyplot_fname`),
the configuration files for psyplot are located in the user home directory.
Under linux and OSX, this is ``$HOME/.config/psyplot``. On other platforms it
is in the ``.psyplot`` directory in the user home.

.. _uninstall-standalone:

Uninstalling standalone app
^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. todo::

    will be provided in the future...

.. _uninstall-conda:

Uninstallation via conda
^^^^^^^^^^^^^^^^^^^^^^^^
If you installed straditize via :ref:`conda <install-conda>`, simply run::

    conda uninstall straditize

.. _uninstall-pip:

Uninstallation via pip
^^^^^^^^^^^^^^^^^^^^^^
Uninstalling via pip simply goes via::

    pip uninstall straditize

Note, however, that you should use :ref:`conda <uninstall-conda>` if you also
installed it via conda.
