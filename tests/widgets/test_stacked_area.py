"""Test the straditize.widgets.stacked_area_reader module"""
import os.path as osp
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


if __name__ == '__main__':
    unittest.main()
