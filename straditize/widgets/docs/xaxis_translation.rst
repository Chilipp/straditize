.. _xaxis-translation:

Translating the horizontal axes
===============================
For your final product, straditize needs to know about how the data in the
diagram is scaled, such that we can transform the final sample information from
the pixel coordinates into the units of the diagram (e.g. percent for pollen
data or Kelvin for temperature, etc.).

To translate the x-axis information,

1. Expand the `Axes translations` tab in the digitization control
2. Click the :guilabel:`Insert X-axis values` button in the `Axes translations`
   section of the straditizer control (if not already done)
3. Shift-leftclick on the plot in one of the columns to enter the corresponding
   x-value.

   .. image:: select-x0_1.png

4. A small dialog will appear where you should enter the x-value to use (in
   this case, ``10``)

   .. image:: select-x0_2.png

5. After hitting the :guilabel:`Ok` button, you will see a mark on the plot
   (blue line). You can select the mark via leftclick and drag it to a
   different location or you can delete it via rightclick.

   .. image:: select-x0_3.png

6. now repeat steps 3-5 on a second point in the same column

   - Select another point

     .. image:: select-x1_1.png

   - Enter the corresponding value (here ``30``)

     .. image:: select-x1_2.png

   - A new mark is created that you can modify

     .. image:: select-x1_3.png

7. Click the :guilabel:`Apply` button at the bottom of the straditizer control
when you are done.

.. note::

    If you have different units or different scalings in the diagram, create
    :ref:`column specific readers <child-readers>` and translate the x-axis
    separately for each reader/column.

.. note::

    If you drag a mark and hold the :kbd:`Shift` button while releasing the
    mouse button, the dialog in point 3 from above will not pop up.
