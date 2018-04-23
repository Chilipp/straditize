.. _cross-column:

Remove cross-column features
============================
This function removes features that have a certain amount of pixels in 
multiple columns. Only those features are selected for removement, that
have at least the given *Number of pixels* in more than one column of
the stratigraphic diagram.

.. image:: basic_diagram_cross_col.png

.. note:: 

    This feature should be called before intializing column specific
    readers.
