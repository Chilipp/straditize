"""Test the straditize.widgets.stacked_area_reader module"""
import os.path as osp
import numpy as np
import pandas as pd
import _base_testing as bt
import unittest
from straditize.widgets.stacked_area_reader import StackedReader
from psyplot_gui.compat.qtcompat import QTest, Qt


class StackedAreaReaderTest(bt.StraditizeWidgetsTestCase):
    """A test case for the BarReader"""

    @property
    def toolbar(self):
        return self.straditizer_widgets.selection_toolbar

    def tearDown(self):
        if getattr(self.reader, 'btn_prev', None) is not None:
            self.reader._remove_digitze_child(self.digitizer)
            del self.reader.straditizer_widgets
        super().tearDown()

    def select_rectangle(self, x0, x1, y0, y1):
        tb = self.toolbar
        slx, sly = tb.get_xy_slice(x0, y0, x1, y1)
        tb.select_rect(slx, sly)

    def init_reader(self, fname='stacked_diagram.png', *args, **kwargs):
        """Reimplemented to make sure, we intiailize a bar diagram"""
        self.digitizer.cb_reader_type.setCurrentText('stacked area')
        super(StackedAreaReaderTest, self).init_reader(fname, *args, **kwargs)
        self.assertIsInstance(self.reader, StackedReader)

    def test_init_reader(self):
        self.init_reader()

    def test_digitize(self):
        self.init_reader()
        QTest.mouseClick(self.digitizer.btn_column_starts, Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)
        self.assertTrue(self.digitizer.btn_digitize.isCheckable())
        self.assertTrue(self.digitizer.btn_digitize.isChecked())
        self.assertEqual(list(self.reader._full_df.columns), [0])
        tb = self.toolbar

        # select the first column
        self.reader.select_and_add_current_column()
        tb.set_color_wand_mode()
        tb.wand_action.setChecked(True)
        tb.toggle_selection()
        self.select_rectangle(10.5, 10.5, 10.5, 10.5)
        QTest.mouseClick(self.digitizer.apply_button, Qt.LeftButton)
        self.assertEqual(list(self.reader._full_df.columns), [0, 1])

        # now select the second column
        self.reader.increase_current_col()
        self.reader.select_and_add_current_column()
        tb.set_color_wand_mode()
        tb.wand_action.setChecked(True)
        tb.toggle_selection()
        self.select_rectangle(13.5, 13.5, 10.5, 10.5)
        QTest.mouseClick(self.digitizer.apply_button, Qt.LeftButton)
        self.assertEqual(list(self.reader._full_df.columns), [0, 1, 2])

        # test the digitization result
        full_df = self.reader.full_df
        ref = pd.read_csv(self.get_fig_path(osp.join('data', 'full_data.csv')),
                          index_col=0, dtype=float)
        self.assertEqual(list(map(str, full_df.columns)),
                         list(map(str, ref.columns)))
        ref.columns = full_df.columns
        self.assertFrameEqual(full_df, ref, check_index_type=False)

        QTest.mouseClick(self.reader.btn_prev, Qt.LeftButton)

        # end digitizing
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)

    def test_find_samples_uses_consensus_by_default(self):
        self.test_digitize()
        calls = []
        samples = pd.DataFrame([[1.5, 2.5, 3.5]], index=[10.5],
                               columns=self.reader.full_df.columns)
        rough = pd.DataFrame(
            [[9, 11, 9, 11, 9, 11]],
            index=[10.5],
            columns=pd.MultiIndex.from_product(
                [self.reader.full_df.columns, ['vmin', 'vmax']]))

        def fail_standard(*args, **kwargs):
            raise AssertionError('standard finder should not be used')

        def fake_consensus(**kwargs):
            calls.append(kwargs)
            return samples.copy(), rough.copy()

        self.reader.find_samples = fail_standard
        self.reader.find_consensus_samples = fake_consensus

        QTest.mouseClick(self.digitizer.btn_find_samples, Qt.LeftButton)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['pixel_tol'], self.digitizer.sp_pixel_tol.value())
        self.assertFrameEqual(self.reader.sample_locs, samples)

    def test_edit_col(self):
        """Test the editing of a column"""
        self.test_digitize()
        ref = self.reader.full_df.copy(True)
        tb = self.toolbar
        # restart the digitization
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)
        self.reader.decrease_current_col()
        self.reader.select_current_column()

        # deselect one pixel
        tb.set_rect_select_mode()
        tb.select_action.setChecked(True)
        tb.remove_select_action.setChecked(True)
        tb.toggle_selection()
        self.select_rectangle(11.5, 11.5, 10.5, 10.5)

        QTest.mouseClick(self.digitizer.apply_button, Qt.LeftButton)

        # now the first cell should be lowered
        self.assertEqual(self.reader.full_df.iloc[0, 0], ref.iloc[0, 0] - 1)

        # end digitizing
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)

    def test_plot_full_df(self):
        """Test the visualization of the full df"""
        self.test_digitize()
        self.reader.plot_full_df()
        x0 = self.straditizer.data_xlim[0]
        self.assertEqual(list(self.reader.lines[0].get_xdata()),
                         list(x0 + self.reader.full_df.iloc[:, 0]))
        self.assertEqual(list(self.reader.lines[1].get_xdata()),
                         list(x0 + self.reader.full_df.iloc[:, :2].sum(axis=1))
                         )
        self.assertEqual(list(self.reader.lines[2].get_xdata()),
                         list(x0 + self.reader.full_df.sum(axis=1)))

    def test_plot_potential_samples(self):
        """Test the visualization of the full df"""
        self.test_digitize()
        self.reader.plot_potential_samples()
        x0 = self.straditizer.data_xlim[0]
        j = 0
        for col in range(3):
            for i, (s, e) in enumerate(
                    self.reader.find_potential_samples(col)[0]):
                self.assertEqual(
                    list(self.reader.sample_ranges[j].get_xdata()),
                    list(x0 +
                         self.reader.full_df.iloc[s:e, :col + 1].sum(axis=1)),
                    msg='Failed at sample %i in column %i' % (i, col))
                j += 1


class StackedAreaConsensusTest(unittest.TestCase):
    """Unit tests for the stacked-area sample consensus prototype."""

    def setUp(self):
        image = np.ones((20, 20), dtype=np.int8)
        self.reader = StackedReader(image, plot=False)
        self.reader.columns = [0, 1, 2]
        self.reader.samples_at_boundaries = False
        fig_dir = osp.abspath(
            osp.join(osp.dirname(__file__), '..', 'test_figures', 'data'))
        self.reader._full_df = pd.read_csv(
            osp.join(fig_dir, 'full_data.csv'),
            index_col=0, dtype=float)
        self.reader._full_df.columns = [0, 1, 2]

    def test_interpolate_samples(self):
        """Sample values should be linearly interpolated at fractional rows."""
        samples = self.reader.interpolate_samples([8.5, 11.5])
        expected = pd.DataFrame(
            [[2.0, 2.5, 2.5],
             [2.0, 4.0, 1.0]],
            index=[8.5, 11.5], columns=[0, 1, 2])
        pd.testing.assert_frame_equal(samples, expected)

    def test_plot_results_overlay_uses_stacked_bands(self):
        """Stacked overlays should draw one fill and line per layer."""
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        self.reader.all_column_starts = np.zeros(3, dtype=int)

        fig = Figure()
        FigureCanvasAgg(fig)
        ax = fig.subplots()

        _, _, artists = self.reader.plot_results_overlay(
            self.reader._full_df.iloc[:4], ax=ax, samples=False)

        self.assertEqual(len(artists['fills']), 3)
        self.assertEqual(len(artists['lines']), 3)

    def test_find_consensus_samples(self):
        """Consensus rows should prefer the strongest overlap and interpolate."""
        self.reader.unique_bars = lambda *args, **kwargs: [
            {0: (0, 1), 1: (0, 1), 2: (0, 1)},
            {0: (7, 9), 1: (7, 10), 2: (8, 9)},
            {0: (10, 12), 1: (11, 12), 2: (11, 13)},
            {0: (18, 20), 1: (17, 20), 2: (19, 20)},
        ]

        samples, rough = self.reader.find_consensus_samples(pixel_tol=None)
        fig_dir = osp.abspath(
            osp.join(osp.dirname(__file__), '..', 'test_figures', 'data'))
        expected = pd.read_csv(
            osp.join(fig_dir, 'data.csv'),
            index_col=0, dtype=float)
        expected.columns = [0, 1, 2]
        expected.index = expected.index.astype(float)
        expected.index.name = None
        pd.testing.assert_frame_equal(samples, expected)
        self.assertEqual(list(rough.index), [0.0, 8.0, 11.0, 19.0])
        self.assertEqual(list(rough.loc[8.0, 2]), [8.0, 9.0])


if __name__ == '__main__':
    unittest.main()
