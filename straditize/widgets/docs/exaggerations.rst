.. _exaggerations:

Interpreting exaggerations
==========================
Visualizing an exaggerated version of the data is a common methodology in
pollen diagrams, since even small pollen counts can say a lot about the
environment.

Therefore it is common to not only plot the data, but also to exaggerate it
by a certain factor, e.g. 10 or two like the red areas in the image below.

.. image:: basic_diagram_exaggerated.png
    :width: 50%

You have two choices: Either you remove these exaggerated areas
(see :ref:`remove-features`), or you merge them into your results to improve
the digitization result.

To include and interprete the exaggerations, straditize can create a new reader
dedicated for the exaggerations which you then have to select and specify when
they should be used. This is all done in the `Exaggerations` tab of your
digitization control.

1. Specify the `exaggeration factor`. This number is usually described in the
   caption of your diagram and must be greater than 1.
2. Select the data reader type for the exaggerations (see
   :ref:`select-reader`). Most common this is one of `area` or `line`.
3. Initialize the reader for the exaggerations by clicking :guilabel:`+`. You
   will now find a new reader dedicated to the exaggerations in the dropdown
   menu of the `Current reader` tab. But for now, we stick with the original
   one.
4. Now, you then have to select the exaggerations. Click the
   :guilabel:`Select exaggerations` button and use the tools in the
   :ref:`selection toolbar <selection-toolbar>` for selecting the features in
   the diagram that represent the exaggerations. When you're done with this,
   click the :guilabel:`Select` button. You can also repeat this step to select
   more and more features.
5. Specify when the exaggerations should be used. This can be either where the
   unexaggerated data is below a certain percentage of the image width and/or
   below a certain number of pixels.
6. When you now click the :guilabel:`Digitize exaggerations` button (but after
   you clicked the :guilabel:`Digitize` button for the original reader), the
   exaggerations will be digitized and merged into the digitization result of
   the non-exaggerated reader.
