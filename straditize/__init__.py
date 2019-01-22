# -*- coding: utf-8 -*-
"""Digitizing stratigraphic diagrams with straditize

The core of straditize is the :class:`~straditize.straditizer.Straditizer`
class and the reader for the diagram part, the
:class:`~straditize.binary.DataReader`. Both classes work completely
independent of the graphical user interace.

The graphical user interface is implemented as a plugin into the
:ref:`psyplot_gui:psyplot-gui` package and is implemented in the
:mod:`straditize.widgets` subpackage.

**Authors**

The code and GUI of straditize was developed by Philipp S. Sommer at the
Institute of Earth System Dynamics (IDYST) at the University of Lausanne as
part of the SNF funded HORNET Project (200021_169598).

The other contributors are Basil A. S. Davis, Manuel Chevalier and
Dilan Rech who made significant contributions to the layout, workflow, beta
tests and and reviewing of the software.

**Disclaimer**

Copyright (C) 2018-2019  Philipp S. Sommer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from straditize.version import __version__

__author__ = "Philipp S. Sommer (philipp.sommer@unil.ch)"
