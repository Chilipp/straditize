.. _install:

.. highlight:: bash

Installation
============

How to install
--------------
You can either install straditize through a package manager such as
:ref:`conda <install-conda>` or :ref:`pip <install-pip>` or install it
:ref:`from source <install-source>`.

.. _install-conda:

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^
We highly recommend to use conda_ for installing straditize. Here you can
install it via manually via the `chilipp channel`_

After having downloaded and installed  anaconda_, open a terminal (or the
*Anaconda Prompt* on windows) and add the `conda-forge channel`_ to your
default conda-channels via::

    $ conda config --add channels conda-forge

Then you can choose. Either you install straditize into your base environment
via::

    $ conda install -c chilipp straditize

or you create a new virtual environment via::

    $ conda create -n straditize -c chilipp straditize

and then activate it via::

    $ conda activate straditize

In the same terminal, now type ``straditize`` to start the software.

.. note::

    The latest master branch on github is always available under the ``master``
    label on the `chilipp channel`_. Just type::

        $ conda install -c chilipp/label/master straditize

    to install the latest version from the master branch.

.. _install-pip:

Installation using pip
^^^^^^^^^^^^^^^^^^^^^^
If you do not want to use conda for managing your python packages and already
have python3 installed on your computer, you can also
use the python package manager ``pip``. To be on the safe side, make sure you
have the :ref:`dependencies` installed. If so, open a terminal and install it
via::

    $ pip install straditize

To open the software, type ``straditize`` in the same terminal.

.. _install-source:

Installation from source
^^^^^^^^^^^^^^^^^^^^^^^^
To install it from source, make sure you have the :ref:`dependencies`
installed. Download (or clone) the github_ repository, e.g. via::

    git clone https://github.com/Chilipp/straditize.git

and install it via::

    python setup.py install

from your terminal. To open the software, type ``straditize`` in the same
terminal.

.. _dependencies:

Dependencies
------------
Required dependencies
^^^^^^^^^^^^^^^^^^^^^
straditize has been tested for python>=3.6. Furthermore the
package is built upon multiple other packages, mainly

- :ref:`psyplot-gui <psyplot_gui:psyplot-gui>`>1.2.0: The graphical user
  interface for psyplot
- `numpy, scipy`_ and pandas_: for the data management and compuations
- matplotlib_>=2.0: **The** python visualiation package
- pillow_: for reading and writing images
- scikit-image_: For image recognition features
- openpyxl_: For exports to Excel files
- netCDF4_: A library for saving and storing netCDF files.


.. _optional_deps:

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^
We furthermore recommend to use

- tesserocr_: for column names recognition. It depends on the tesseract_ OCR
  and you can install both (on Linux and MacOS) via::

      $ conda install -c chilipp tesserocr

  (see :ref:`colnames-ocr` for more information)


.. _netCDF4: https://github.com/Unidata/netcdf4-python
.. _conda: http://conda.io/
.. _anaconda: https://www.continuum.io/downloads
.. _chilipp channel: https://anaconda.org/chilipp
.. _conda-forge channel: https://conda-forge.org/
.. _matplotlib: http://matplotlib.org
.. _numpy, scipy: https://docs.scipy.org/doc/
.. _pandas: http://pandas.pydata.org/
.. _scikit-image: https://scikit-image.org/
.. _pillow: https://pillow.readthedocs.io/en/stable/
.. _openpyxl: https://openpyxl.readthedocs.io/en/stable/
.. _tesserocr: https://pypi.org/project/tesserocr/
.. _tesseract: https://github.com/tesseract-ocr/tesseract


Running the tests
-----------------
We us pytest_ to run our tests. So you can either run clone out the github_
repository and run::

    $ python setup.py test

or install pytest_ by yourself and run

    $ py.test

Alternatively you can build the recipe in the `conda-recipe` directory via

    $ conda build conda-recipe

which will also run the test suite.


Building the docs
-----------------
The online documentation is accessible as PDF, HTML and Epub under
https://straditize.readthedocs.io or https://straditize.rtfd.io. Thanks to the
free services by `readthedocs.org <https://readthedocs.org/>`__, the online
documentation is build automatically after each commit to the github_
repository.

To build the docs locally on your machine, check out the github_ repository and
install the requirements in ``'docs/environment.yml'`` and the
sphinx_rtd_theme_ package. The easiest way to do this is via anaconda by
typing::

    $ conda env create -f docs/environment.yml
    $ conda activate straditize_docs
    $ conda install sphinx_rtd_theme

Then build the docs via::

    $ cd docs
    $ make html  # or `make pdf` for a PDF version compiled with Latex

.. _github: https://github.com/Chilipp/straditize
.. _pytest: https://pytest.org/latest/contents.html
.. _sphinx_rtd_theme: https://sphinx-rtd-theme.readthedocs.io/en/latest/?badge=latest


.. _update:

Updating straditize
-------------------

Updating the software depends on how you installed it on your system.

.. _update-conda:

Updating via conda
^^^^^^^^^^^^^^^^^^
If you installed straditize via conda (see :ref:`install-conda`), you can
update it via::

    $ conda update -c chilipp straditize

.. _update-pip:

Updating via pip
^^^^^^^^^^^^^^^^
If you installed it via ``pip`` (see :ref:`install-pip`), you can update it
via::

    $ pip install -U straditize

.. _update-source:

Updating from source files
^^^^^^^^^^^^^^^^^^^^^^^^^^
If you installed it via ``python setup.py install`` from the source repository
(see :ref:`install-source`), just run that command again after having checked
out the latest version from github.


.. _uninstall:

Uninstallation
--------------
The uninstallation depends on the system you used to install straditize. Either
you did it via :ref:`conda <install-conda>` (see :ref:`uninstall-conda`), via
:ref:`pip <install-pip>` or from the
:ref:`source files <install-source>` (see :ref:`uninstall-pip`).

Anyway, if you may want to remove the psyplot configuration files. If you did
not specify anything else (see :func:`psyplot.config.rcsetup.psyplot_fname`),
the configuration files for psyplot are located in the user home directory.
Under linux and OSX, this is ``$HOME/.config/psyplot``. On other platforms it
is in the ``.psyplot`` directory in the user home.

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
