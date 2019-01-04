Specifying the column names
===========================
Straditize can handle column names which will then be included in the final
export. It interfaces with the tesserocr_ package and we will use this to
minimize our typing amount. However, we have a complex diagram so manual
corrections are unavoidable.

1. Expand the `Column names` item in the straditizer control and click the
   :guilabel:`Edit column names` button.

   In the appearing widget, the colnames editor

   .. image:: colnames-editor.png
       :alt: column names editor

   you find a table where you can edit the column names. The plot on it's left
   also shows a rotated version of the diagram, to help you identifying the
   column names. You can navigate in this plot using leftclick and zoom in and
   out using right-click (see
   `matplotlibs docs on interactive navigation with the Pan/Zoom-tool`_)
2. To improve the text recognition, it is highly recommended to have a clean
   image with only the column names on it and a sufficient resolution. We have
   something prepared for you:

   .. image:: hoya-del-castillo-colnames.png
        :alt: HR column names image

   Click the :guilabel:`Load HR image` button and select the
   `hoya-del-castillo-colnames.png` image file.
3. We will now use the automatic finding of column names. For this,
   click the :guilabel:`Find column names` button. This will search for the
   column names in the plot to the left of the table
4. There will probably be some errors in the column names. Therefore, go
   through each row in the table and check the name. You can use the
   :guilabel:`Hint` button to help you and/or zoom to the column name to see
   the name in the original

   .. image:: colnames-editor-zoomed.png
       :alt: Zoomed in column names editor

5. When you entered the correct names in the table, click the
   :guilabel:`Edit column names` button again to hide the button.

.. _tesserocr: https://pypi.org/project/tesserocr/
.. _matplotlibs docs on interactive navigation with the Pan/Zoom-tool: https://matplotlib.org/users/navigation_toolbar.html))
