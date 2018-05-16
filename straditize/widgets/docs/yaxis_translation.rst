.. _yaxis-translation:

Translating the shared vertical axis
====================================
For your final product, straditize needs to know about how the data in the
diagram is scaled, such that we can transform the final sample information from
the pixel coordinates into the units of the diagram (e.g. years or meters in
case of time or depth).

To translate the y-axis information,

1. Click the :guilabel:`Insert Y-axis values` button in the `Axes translations`
   section of the straditizer control (if not already done)
2. Shift-leftclick on the plot to enter the corresponding y-value.

   .. image:: select-y0_1.png

3. A small dialog will appear where you should enter the y-value to use (in
   this case, ``10000``)

   .. image:: select-y0_2.png

4. After hitting the :guilabel:`Ok` button, you will see a mark on the plot
   (blue line). You can select the mark via leftclick and drag it to a
   different location or you can delete it via rightclick.

   .. image:: select-y0_3.png

5. now repeat steps 2-4 on a second point on the y-axis

   - Select another point

     .. image:: select-y1_1.png

   - Enter the corresponding value (here ``15000``)

     .. image:: select-y1_2.png

   - A new mark is created that you can modify

     .. image:: select-y1_3.png

6. Click the :guilabel:`Apply` button at the bottom of the straditizer control
   when you are done.

.. note::

    If you drag a mark and hold the :kbd:`Shift` button while releasing the
    mouse button, the dialog in point 3 from above will not pop up.
