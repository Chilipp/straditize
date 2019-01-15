Remove artifacts
================
Stratigraphic diagrams, and especially pollen diagrams, often have a lot of
artifacts in it, that are informative for the reader.

In our case, the diagram is splitted into three temporal *zones* (HDC-2, HDC-3
and HDC-4, see the *Zone* column on the right part of the diagram) which are
visually separated with horizontal lines. Additionally, the diagram has
vertical, dashed lines at each column start (the y-axes for each column).

Before we digitize our diagram, those *informative features* have to be
removed. You can do this in an external image editing software (e.g.
Photoshop) but we also implemented several automated algorithms to detect
common features and remove them easily.

For our tutorial, we use the *Remove lines* feature to detect and remove the
vertical and horizontal lines.

Horizontal lines
----------------

1. Expand the *Remove features* tab in the *Digitization control*
2. Expand the item with the :guilabel:`vertical lines` and
   :guilabel:`horizontal lines` button by clicking on the small arrow on their
   left
3. Set the minimum line width to 1 pixel
4. Click the :guilabel:`horizontal lines` button. In the plot you will see,
   that the horizontal lines are red now (if necessary, go with the mouse over
   the plot and you will see it in the zoom window). You could edit the
   selection now using the selection toolbar (see :ref:`selection-toolbar`),
   but for our tutorial, this is not necessary.
5. Click the :guilabel:`Remove` button to remove the lines

Vertical lines (y-axes)
-----------------------

1. Enable the maximum line width and set it to 2 pixel
2. Set the minimum fraction to 30%
3. Click the :guilabel:`vertical lines` button and the vertical lines turn
   red and are marked to be removed.
4. Click the :guilabel:`Remove` button to remove the y-axes

Additional automated removal tools are available and fully described in the
documentation (see :ref:`remove-features`). But here, we can continue
with the digitization.
