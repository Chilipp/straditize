.. _find-samples:

Automatic samples identification
================================
straditize has reader specific sample identification algorithms
implemented. The overall algorithm is based on two steps:

1. For each column: Identify the intervals that contain exactly one
   samples (the rough locations)
2. Align the overlapping intervals between the columns to estimate the exact
   location

Where step 2 is the same for all diagram types, step one is diagram specific.
For bar diagrams, we use the bars that have been identified during
the digitization (see :ref:`digitizing-bars`).

For area and line diagrams on the other hand, we identify the local extrema
(minima and maxima) for each column. This strategy works well for pollen
diagrams since they are supposed to sum up to 100%. However, this does not
generally work for all stratigraphic diagrams.
