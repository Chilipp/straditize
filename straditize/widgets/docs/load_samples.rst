.. _load-samples:

Load samples locations from external file
=========================================
samples can be loaded from an external CSV (comma-separated) file. The
first column in this CSV file is expected to represent the y-locations of the
samples. If the y-axis scale has already been specified (see
:ref:`yaxis-translation`), this data should be on the same scale. Otherwise,
we assume that the data is in pixel coordinates.

.. warning::

    Make sure, that you first entered the correct
    :ref:`y-axis scale <yaxis-translation>`. Otherwise the samples might
    not be interpreted correctly.
