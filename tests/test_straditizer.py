# -*- coding: utf-8 -*-
"""
Test module for the :mod:`straditize.straditizer` module
"""
import six
import os.path as osp
import unittest
from itertools import chain
import numpy as np
from straditize.straditizer import Straditizer
import pandas as pd
import create_test_sample as ct
import matplotlib as mpl

mpl.use('module://psyplot_gui.backend')


test_dir = osp.dirname(__file__)


class StraditizerTest(unittest.TestCase):
    """Test methods for the straditizer"""

    def test_format_coord(self):
        """Test the formatting of a coordinate"""
        stradi = Straditizer(osp.join(test_dir, 'test_figures',
                                      'basic_diagram.png'))
        stradi.data_xlim = stradi.data_ylim = np.array([10, 30])
        stradi.init_reader()
        stradi.data_reader._get_column_starts()
        ax = stradi.ax
        x, y = 11.0, 11.0
        ref = (stradi._orig_format_coord(x, y) +
               "DataReader: x=%s y=%sColumn 0 x=%s" % (
                   ax.format_xdata(1.), ax.format_ydata(1.),
                   ax.format_xdata(1.)))
        self.assertEqual(ax.format_coord(x, y), ref)

    def test_guess_data_lims(self):
        stradi = Straditizer(osp.join(test_dir, 'test_figures',
                                      'basic_diagram.png'))
        xlim, ylim = stradi.guess_data_lims()
        self.assertEqual(list(xlim), [10, 27])
        self.assertEqual(list(ylim), [10, 30])


if __name__ == '__main__':
    unittest.main()
