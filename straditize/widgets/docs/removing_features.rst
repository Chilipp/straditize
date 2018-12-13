.. _remove-features:

Removing features
=================
The diagram part is converted to a binary image where everything black
(i.e. 1) represents data (see :ref:`select-reader`). So before the data is
digitized, features that do not represent data have to be removed.

Here, you can either use the
:ref:`features of the selection toolbar <selection-toolbar>`,
or you use one of the automatic removal tools we provide here. Note that you
can edit every selection using the
:ref:`mouse selection tools <mouse-selection-tools>` or the
:ref:`automatic tools <auto-tools>` from the selection toolbar.

After you selected the features to remove, click the :guilabel:`Remove` button
at the bottom of the straditizer control panel.


+------------------------------------------------------------+-----------------------------------------------------+
| :ref:`x-axes <remove-lines>`                               | :ref:`y-axes <remove-lines>`                        |
+------------------------------------------------------------+-----------------------------------------------------+
|                   |xaxes|                                  |                    |yaxes|                          |
+------------------------------------------------------------+-----------------------------------------------------+
| :ref:`horizontal lines <remove-lines>`                     | :ref:`vertical lines <remove-lines>`                |
+------------------------------------------------------------+-----------------------------------------------------+
|                   |hlines|                                 |                    |vlines|                         |
+------------------------------------------------------------+-----------------------------------------------------+
| :ref:`features at column ends <features-at-column-ends>`   | :ref:`disconnected features <remove-disconnected>`  |
+------------------------------------------------------------+-----------------------------------------------------+
|                    |col-ends|                              |                    |disco|                          |
+------------------------------------------------------------+-----------------------------------------------------+
| :ref:`cross column features <cross-column>`                | :ref:`small artifacts <remove-small>`               |
+------------------------------------------------------------+-----------------------------------------------------+
|                   |cross-col|                              |                     |small|                         |
+------------------------------------------------------------+-----------------------------------------------------+


.. |xaxes| image:: basic_diagram_xaxes.png
    :target: remove_lines.html

.. |yaxes| image:: basic_diagram_yaxes.png
    :target: remove_lines.html

.. |hlines| image:: basic_diagram_hlines.png
    :target: remove_lines.html

.. |vlines| image:: basic_diagram_vlines.png
    :target: remove_lines.html

.. |col-ends| image:: basic_diagram_features_at_col_ends.png
    :target: remove_col_ends.html

.. |disco| image:: basic_diagram_disconnected.png
    :target: remove_disconnected_parts.html

.. |cross-col| image:: basic_diagram_cross_col.png
    :target: remove_cross_column.html

.. |small| image:: basic_diagram_small_features.png
    :target: remove_small_parts.html


.. toctree::
    :hidden:

    remove_col_ends
    remove_cross_column
    remove_disconnected_parts
    remove_lines
    remove_small_parts
