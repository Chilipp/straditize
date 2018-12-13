.. _remove-lines:

Remove horizontal or vertical lines
===================================
The features described here automatically remove the y- and x-axes, or in
general vertical or horizontal lines that span a certain fraction of the
diagram part.

The methodology is simple: If a certain pixel column or
row in the binary data image is covered, it is considered
as a vertical or horizontal line, respectively.

+------------------+----------------+
| x-axes           | y-axes         |
+------------------+----------------+
| |xaxes|          | |yaxes|        |
+------------------+----------------+
| horizontal lines | vertical lines |
+------------------+----------------+
| |hlines|         | |vlines|       |
+------------------+----------------+

.. |xaxes| image:: basic_diagram_xaxes.png

.. |yaxes| image:: basic_diagram_yaxes.png

.. |hlines| image:: basic_diagram_hlines.png

.. |vlines| image:: basic_diagram_vlines.png

You can modify the recognition using three options

Minimum fraction:
    This is the minimum fraction of a pixel column (for
    or row that must be covered
Minimum line width:
    Lines are only selected, if their line width is greater than
    or equal to the given minimum axis width.
Maximum line width:
    Lines are only selected up to the given maximum axis width
