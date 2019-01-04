Specifying the column names
===========================

.. note::

    Straditize also has a text recognition implemented if you install
    ``tesserocr`` (see the :ref:`user guide <colnames-ocr>`). If you would like
    to use it, install ``tesserocr`` and restart the tutorial.

Straditize can handle column names which will then be included in the final
export.

1. Expand the `Column names` item in the straditizer control and click the
   :guilabel:`Edit column names` button
2. In the appearing widget, the colnames editor

   .. image:: colnames-editor.png
       :alt: column names editor

   you find a table where you can edit the column names. The plot on it's left
   also shows a rotated version of the diagram, to help you identifying the
   column names. You can navigate in this plot using leftclick and zoom in and
   out using right-click (see
   `matplotlibs docs on interactive navigation with the Pan/Zoom-tool`_)
3. When you entered the correct names in the table, click the
   :guilabel:`Edit column names` button again to hide the dialog.

.. _matplotlibs docs on interactive navigation with the Pan/Zoom-tool: https://matplotlib.org/users/navigation_toolbar.html
