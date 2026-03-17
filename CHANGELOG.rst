v0.2.1
======

This hotfix release keeps the refreshed ``0.2`` runtime stack but trims
release housekeeping that was no longer maintained.

Changed
-------
* README and docs installation guidance now describe the maintained
  source-install workflow more clearly and avoid contradictory legacy paths.
* Release-facing badges and references no longer point to retired Travis and
  AppVeyor infrastructure.

Removed
-------
* Obsolete Travis CI and AppVeyor configuration files from the active release
  branch.
* Local virtual-environment clutter is now explicitly ignored in development
  checkouts.

v0.2
====

This release refreshes straditize for modern Python and scientific Python
stacks while preserving the original stratigraphic digitization workflow.

Added
-----
* Result review plots can now overlay the digitized output directly on top of
  the original image for faster visual QA.
* The result review dialog now includes explicit ``Export data`` and
  ``Close`` actions.
* Stacked-area sample finding now defaults to consensus interpolation instead
  of exposing an unfinished GUI mode switch.

Changed
-------
* The tested runtime stack has been updated to Python 3.10-3.14 with modern
  pandas, matplotlib, scipy, xarray, psyplot and PyQt5 releases.
* Installation and testing docs now recommend isolated environments and
  ``pip install -e .`` / ``pytest`` workflows instead of deprecated
  ``setup.py install`` and ``setup.py test`` commands.
* Plot-results review now opens as a dedicated comparison window and applies
  configured axis scaling in the exported/reviewed data.

Fixed
-----
* Restored compatibility with pandas 2.3 and 3.0, including Excel export,
  project save/load, nearest-index lookups and modern DataFrame APIs.
* Fixed modern Matplotlib / psyplot-gui toolbar integration and Qt resize
  regressions.
* Reduced startup noise from deprecated docstring helpers and late OpenGL
  configuration warnings.
* Hardened headless Qt test paths, stacked-area label handling and several
  export/sample-editing edge cases uncovered during regression testing.

v0.1.3
======
Patch that forces the diagram limits to be integers.

v0.1.2
======
This release contains several small bug fixes, mainly for the bar data reader
and for duplicated samples and occurences.


v0.1.1
======
.. image:: http://joss.theoj.org/papers/10.21105/joss.01216/status.svg
    :alt: Journal of Open Source Software
    :target: https://doi.org/10.21105/joss.01216

.. image:: https://zenodo.org/badge/128653545.svg
   :alt: zenodo
   :target: https://zenodo.org/badge/latestdoi/128653545

This release has been approved by the Journal of Open Source Software
(JOSS) in https://github.com/openjournals/joss-reviews/issues/1216

Added
-----
* Changelog

Changed
-------
* Thanks to the feedbacks from `@ixjlyons <https://github.com/ixjlyons>`__ and
  `@sgrieve <https://github.com/sgrieve>`__ the installation instructions and
  some other documentation instructions have been improved (see the issues
  https://github.com/Chilipp/straditize/issues/1,
  https://github.com/Chilipp/straditize/issues/2,
  https://github.com/Chilipp/straditize/issues/3,
  https://github.com/Chilipp/straditize/issues/4 and
  https://github.com/Chilipp/straditize/issues/8)
