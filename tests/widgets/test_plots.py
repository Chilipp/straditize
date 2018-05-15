"""Test the straditize.widgets.plots module"""
import numpy as np
import pandas as pd
import os.path as osp
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt


class PlotControlTableTest(bt.StraditizeWidgetsTestCase):
    """A test case for testing the plotting functions"""

    @property
    def table(self):
        return self.straditizer_widgets.plot_control.table

    def _test_plot(self, key):
        def test_plot():
            QTest.mouseClick(btn, Qt.LeftButton)
            a = None
            for a in get_artists():
                self.assertTrue(a.get_visible())
            self.assertIsNotNone(a, msg='No artist plotted!')
            self._test_hiding(key)

        def test_remove():
            QTest.mouseClick(btn, Qt.LeftButton)
            self.assertIsNone(next(iter(get_artists()), None))

        get_artists = self.table.get_artists_funcs[key]
        is_plotted = next(iter(get_artists()), None)
        row = list(self.table.get_artists_funcs).index(key)
        btn = self.table.cellWidget(row, 1)
        if is_plotted:
            test_remove()
            test_plot()
        else:
            test_plot()
            test_remove()

    def _test_hiding(self, key):
        """Test a plotting function"""
        def test_if_visible():
            cb.setChecked(True)
            for a in get_artists():
                self.assertTrue(a.get_visible())

        def test_if_hidden():
            cb.setChecked(False)
            for a in get_artists():
                self.assertFalse(a.get_visible())

        get_artists = self.table.get_artists_funcs[key]
        row = list(self.table.get_artists_funcs).index(key)
        cb = self.table.cellWidget(row, 0)
        is_shown = cb.isChecked()
        if is_shown:
            test_if_hidden()
            test_if_visible()
        else:
            test_if_visible()
            test_if_hidden()

    def test_plot_full_image(self):
        """Test disabling and enabling the plot of the full image"""
        self._test_hiding('Full image')

    def test_plot_data_background(self):
        self.init_reader()
        self._test_hiding('Data background')

    def test_plot_binary_image(self):
        self.init_reader()
        self._test_hiding('Binary image')

    def test_plot_diagram_part(self):
        self.open_img()
        self.set_data_lims()
        self._test_plot('Diagram part')

    def test_plot_column_starts(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self._test_plot('Column starts')

    def test_plot_full_df(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        self.straditizer_widgets.refresh()
        self._test_plot('Full digitized data')

    def test_plot_potential_samples(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        self.straditizer_widgets.refresh()
        self._test_plot('Potential samples')

    def test_plot_samples(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        self.reader._get_sample_locs()
        self.straditizer_widgets.refresh()
        self._test_plot('Samples')

    def test_plot_reconstruction(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        self.reader._get_sample_locs()
        self.straditizer_widgets.refresh()
        self._test_plot('Reconstruction')


if __name__ == '__main__':
    unittest.main()
