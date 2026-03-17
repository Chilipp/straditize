.. _install:

.. highlight:: bash

Installation
============

How to install
--------------
For the refreshed ``0.2`` line, the maintained path is to install straditize
from a source checkout inside an isolated environment. The recommended options
below differ only in how the environment itself is created.

.. _install-conda:

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^
We recommend an isolated conda_ or mamba_ environment and a source install for
the refreshed ``0.2`` release, because that keeps the Qt and scientific Python
stack explicit.

After having installed conda_ or mamba_, open a terminal (or the
*Anaconda Prompt* on Windows) and create a dedicated environment via::

    $ mamba create -n straditize python=3.12 "numpy>=1.26" "pandas>=2.3" "matplotlib>=3.8" "scipy>=1.13" "xarray>=2024.7" "psyplot=1.5.1" "psyplot-gui=1.5.0" "pyqt=5.15" pyqtwebengine netcdf4 openpyxl scikit-image pillow pip
    $ conda activate straditize

Then install straditize from a checkout via::

    $ git clone https://github.com/Chilipp/straditize.git
    $ cd straditize
    $ pip install -e .

In the same terminal, now type ``straditize`` to start the software.

.. _install-pip:

Installation using ``venv`` + pip
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you already manage isolated environments with ``venv`` or another Python
tool, first install the validated dependency stack and then install straditize
from source::

    $ python -m venv .venv
    $ .venv\\Scripts\\activate  # on Linux/macOS: source .venv/bin/activate
    $ pip install "numpy>=1.26" "pandas>=2.3" "matplotlib>=3.8" "scipy>=1.13" "xarray>=2024.7" "psyplot==1.5.1" "psyplot-gui==1.5.0" "PyQt5!=5.12" PyQtWebEngine netCDF4 openpyxl scikit-image pillow
    $ git clone https://github.com/Chilipp/straditize.git
    $ cd straditize
    $ pip install -e .

To open the software, type ``straditize`` in the same terminal.

.. _dependencies:

Dependencies
------------
Required dependencies
^^^^^^^^^^^^^^^^^^^^^
straditize ``0.2`` has been validated with python>=3.10. Furthermore the
package is built upon multiple other packages, mainly

- :ref:`psyplot-gui <psyplot_gui:psyplot-gui>`>=1.5.0: The graphical user
  interface for psyplot
- PyQt5_: Pythons Qt bindings that are required by psyplot-gui (note that
  PyQt4 is **not** supported!)
- `numpy, scipy`_ and pandas_: for the data management and computations
- matplotlib_>=3.8: **The** python visualization package
- xarray_>=2024.7: dataset handling used by psyplot
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
.. _anaconda: https://conda.io/en/latest/miniconda.html
.. _chilipp channel: https://anaconda.org/chilipp
.. _conda-forge channel: https://conda-forge.org/
.. _mamba: https://mamba.readthedocs.io/
.. _matplotlib: http://matplotlib.org
.. _PyQt5: https://www.riverbankcomputing.com/software/pyqt/intro
.. _numpy, scipy: https://docs.scipy.org/doc/
.. _pandas: http://pandas.pydata.org/
.. _xarray: https://docs.xarray.dev/
.. _scikit-image: https://scikit-image.org/
.. _pillow: https://pillow.readthedocs.io/en/stable/
.. _openpyxl: https://openpyxl.readthedocs.io/en/stable/
.. _tesserocr: https://pypi.org/project/tesserocr/
.. _tesseract: https://github.com/tesseract-ocr/tesseract


Running the tests
-----------------
We use pytest_ to run our tests. Clone the github_ repository and run::

    $ python -m pytest -q

Alternatively you can build the recipe in the `conda-recipe` directory via

    $ conda build conda-recipe

which will also run the test suite. The recipe is kept for release and
compatibility work, but it is not the primary end-user installation path for
``0.2``.

.. warning::

    Running the entire test suite in one single process might be quite memory
    consumptive because it involves the creation and closing of many PyQt
    widgets and unfortunately some memory is leaked from one test to another.
    Therefore we recommend to split the tests into multiple processes, e.g.::

        # run the test suite but ignore some modules
        python -m pytest -q --ignore=tests/widgets/test_selection_toolbar.py --ignore=tests/widgets/test_samples_table.py --ignore=tests/widgets/test_beginner.py --ignore=tests/widgets/test_hoya_del_castillo.py
        # run the tests for the previously ignored modules
        python -m pytest -q tests/widgets/test_selection_toolbar.py tests/widgets/test_samples_table.py
        python -m pytest -q tests/widgets/test_beginner.py
        python -m pytest -q tests/widgets/test_hoya_del_castillo.py

    or equivalently with `pytest` instead of `python -m pytest -q`. Note that
    `conda build conda-recipe` already splits the session into multiple
    processes.

    Nevertheless, you should expect about ~180 tests to be ran and a total memory usage of about 3 to 4GB RAM.


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

Updating from a source checkout
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Pull the latest version from github_ in your checkout and run
``pip install -e .`` again inside the same environment.


.. _uninstall:

Uninstallation
--------------
The uninstallation depends on the environment you used for the source install.
In practice this means either removing the whole dedicated environment or
uninstalling the editable package from it.

Anyway, if you may want to remove the psyplot configuration files. If you did
not specify anything else (see :func:`psyplot.config.rcsetup.psyplot_fname`),
the configuration files for psyplot are located in the user home directory.
Under linux and OSX, this is ``$HOME/.config/psyplot``. On other platforms it
is in the ``.psyplot`` directory in the user home.

.. _uninstall-pip:

Uninstallation from the active environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Uninstalling the editable package goes via::

    pip uninstall straditize
