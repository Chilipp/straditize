.. _selection-toolbar:

The selection toolbar
*********************
The tools in this toolbar provides you the possibility to select
features in the diagram. By default, the selected features will
then be removed when you click the :guilabel:`Apply` or :
guilabel:`Remove` button at the bottom of the straditizer window.
The processing of the selection however varies depending on what
task you are doing at the moment (for exaggerations, the selected
features are for example marked as exaggerations).

The selection toolbar can
:ref:`select from different sources <selection-source>`,
provides :ref:`differenti mouse tools <mouse-selection-tools>`,
can be used in :ref:`different modes <selection-mode>` provides
:ref:`additional automatic tools for the selection <auto-tools>`

.. _selection-source:

Choosing the selection source
=============================
Using the combo box, you can also choose, where the features should
be selected.

Straditizer
    If you choose the `Straditizer`, features will only be selected
    in the full image and the diagram part is untouched.
Reader
    If you choose the `Reader`, features will only be selected in
    the diagram image and the original image will be kept untouched
Reader - Greyscale
    The same as `Reader`, but whether too parts are connected or not
    is based on their color, not only on the binary image (see the
    |wand| tool below).

.. _mouse-selection-tools:

Selection tools
===============

Too facilitate the selection for you, we implemented several tools
to select features in the image:

select a rectangle or point |rect|
    With this tool you can select everything within a rectangle or
    a single point
select a polygon |poly|
    This tool can be accessed through the context menu of the |rect|
    tool (click and hold this button to open the menu). If activated and you
    click on the image, hold the mouse button and drag it around the features
    you want to select. Everything that is in the shape you draw while pressing
    the mouse button will be selected.
select based on connectivity or functionality |wand|
    This tool selects entire features in the image. The exact
    behaviour depends on what you are doing at the moment. If you
    hold and drag the mouse, you can select all features within a
    rectangle

    In most cases, the tool just selects a feature based on the connectivity.
    If the selection source is the `Straditizer` or
    `Reader - Greyscale`, this connectivity is based on the greyscale
    image. For the `Reader` selection source, this is based on the
    binary image.
select based on color |color-wand|
    This tool can be accessed through the context menu of the |wand|
    tool (click and hold this button to open the menu). If activated and you
    click on the image, all connected cells that have the same color are
    selected. You can also relax this a bit, such that all colors that are
    close to the selected color will be selected. Furthermore, you can choose
    the select the colors in the `whole plot`, i.e. all pixels that have the
    same (or similar) color as the selected cell will be selected.
select the entire pixel row |row-wand|
    This tool also can be accessed through the context menu of the |wand|
    tool (click and hold this button to open the menu). If you click on the
    image, all selectable features on this horizontal level (i.e. on this
    pixel row in the image) are selected.
select the entire pixel column |col-wand|
    The same as the |row-wand| tool but for the vertical columns.

.. |rect| image:: select.png
    :width: 1.3em

.. |poly| image:: poly_select.png
    :width: 1.3em

.. |wand| image:: wand_select.png
    :width: 1.3em

.. |color-wand| image:: color_select.png
    :width: 1.3em

.. |row-wand| image:: row_select.png
    :width: 1.3em

.. |col-wand| image:: col_select.png
    :width: 1.3em

.. _selection-mode:

Selection mode
==============
What exatly happens when you use the
:ref:`selection tools desribed above <mouse-selection-tools>` depends
on the selection mode that you are in. This can be one of

new selection |new-select|
    When you select something, it will create a new selection
add to selection |add-select|
    Any new selection will be added the current selection
remove from selection |remove-select|
    Any new selection will be removed from the current selection

.. |new-select| image:: new_selection.png
    :width: 1.3em

.. |add-select| image:: add_select.png
    :width: 1.3em

.. |remove-select| image:: remove_select.png
    :width: 1.3em

.. _auto-tools:

Automatic tools
===============
The selection toolbar also provides you some automatic tools to
facilitate the selection for you

select all |select-all|
    Everything that can be selected will be selected
expand selection |expand-select|
    Every selected pixel will be expanded based on
    it's connectivity (see the |wand| tool above)
invert selection |invert-select|
    Everything that is selected will be unselected and
    everything that was not previously selected will be selected
clear selection |clear-select|
    Everything will be unselected
select everything to the right |select-right|
    For each selected pixel in a column of the diagram part, we
    also select everything that is to the right of this pixel
select based on a template |select-pattern|
    This method uses the :func:`skimage.feature.match_template`
    function to find a template within the current selection.
    This will then be selected or removed from the current
    selection based on the :ref:`current mode <selection-mode>`.

.. |select-all| image:: select_all.png
    :width: 1.3em

.. |expand-select| image:: expand_select.png
    :width: 1.3em

.. |invert-select| image:: invert_select.png
    :width: 1.3em

.. |clear-select| image:: clear_select.png
    :width: 1.3em

.. |select-right| image:: select_right.png
    :width: 1.3em

.. |select-pattern| image:: pattern.png
    :width: 1.3em
