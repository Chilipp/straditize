# -*- coding: utf-8 -*-
"""
Test module for the :mod:`straditize.straditizer` module
"""
import six
import os.path as osp
import unittest
import warnings
from itertools import chain
import numpy as np
from straditize.straditizer import Straditizer, _new_mark_factory
from straditize.magnifier import Magnifier
import pandas as pd
import create_test_sample as ct
import matplotlib as mpl
import matplotlib.pyplot as plt

mpl.use('module://psyplot_gui.backend')


test_dir = osp.dirname(__file__)


class _DummySignal(object):

    def __init__(self):
        self.emitted = []

    def emit(self, value):
        self.emitted.append(value)


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

    def test_magnifier_init_without_window_title_deprecation(self):
        fig, ax = plt.subplots()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always',
                                      mpl.MatplotlibDeprecationWarning)
                magnifier = Magnifier(ax, image=np.zeros((2, 2)))
            self.assertIsNotNone(magnifier.ax)
            self.assertFalse(
                any(issubclass(w.category, mpl.MatplotlibDeprecationWarning)
                    for w in caught),
                msg=[str(w.message) for w in caught])
        finally:
            plt.close('all')

    def test_new_mark_factory_ignores_extra_mark_valueerror(self):
        fig, ax = plt.subplots()
        try:
            signal = _DummySignal()
            ret, _ = _new_mark_factory(
                [], signal,
                lambda pos: (_ for _ in ()).throw(
                    ValueError('Cannot use more than 2 marks!')),
                fig, axes=[ax])

            event = type('Event', (), {
                'key': 'shift', 'button': 1, 'inaxes': ax,
                'xdata': 1.0, 'ydata': 1.0})()
            ret(event)
            self.assertEqual(signal.emitted, [])
        finally:
            plt.close('all')


if __name__ == '__main__':
    unittest.main()
