Cleaning the image
==================
The next step is to clean the data image to make sure that everything that is
not representing real data is removed. In our case, these are y-axes, x-axes
and the outer frame. You can also use an external image editing software such
as Adobe Photoshop, but we will do this now inside straditize and use some of
the automatic recognition functionalities.

1. Expand the `Remove features` tab
2. Click the y-axes button, the y-axes in the plot will be highlighted

   .. image:: yaxes.png
3. Click `Remove` to remove them
4. 2. Click the x-axes button, the x-axes in the plot will be highlighted

   .. image:: xaxes.png
5. Click `Remove` to remove them
6. Finally there is the right part of the diagram frame left

   .. image:: right-line.png

   For this, we use the selection toolbar:

   i. from the |wand| menu, select the `column selection` tool (click and hold
      the button to the right of the |rect_select| button in the selection
      toolbar to open the menu)

      .. image:: column-selection-tool.png

   ii. Draw a rectangle around the right line

       .. image:: select-right.png

       and make sure you have the |new-select| mode activated

   iii. Click the `Remove` button when you are done


.. |wand| image:: wand_select.png
    :width: 1.3em

.. |rect_select| image:: select.png
    :width: 1.3em

.. |new-select| image:: new_selection.png
    :width: 1.3em
