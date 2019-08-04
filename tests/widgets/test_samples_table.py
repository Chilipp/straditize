"""Test the straditize.widgets.samples_table module"""
import numpy as np
import _base_testing as bt
from itertools import chain
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt
from psyplot.utils import unique_everseen


class EditSamplesTest(bt.StraditizeWidgetsTestCase):
    """Test the editing of samples"""

    def test_creation(self):
        """Test whether the marks and table is set up correctly"""
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        self.straditizer_widgets.refresh()
        self.assertTrue(self.digitizer.btn_find_samples.isEnabled())
        self.assertTrue(self.digitizer.btn_edit_samples.isEnabled())
        # add an occurence to the reader
        df = self.reader.find_samples()[0]
        self.reader.occurences = {
            (df.index[2], self.reader.column_starts[1] + df.iloc[2, 1] + 1)}

        # first try with empty samples
        QTest.mouseClick(self.digitizer.btn_edit_samples, Qt.LeftButton)
        self.assertFalse(self.straditizer.marks)
        self.assertTrue(hasattr(self.digitizer, '_samples_editor'))
        QTest.mouseClick(self.digitizer.apply_button, Qt.LeftButton)
        self.assertFalse(hasattr(self.digitizer, '_samples_editor'))

        # Now try with the found samples
        QTest.mouseClick(self.digitizer.btn_find_samples, Qt.LeftButton)
        QTest.mouseClick(self.digitizer.btn_edit_samples, Qt.LeftButton)
        self.assertTrue(self.straditizer.marks)
        self.assertTrue(hasattr(self.digitizer, '_samples_editor'))
        model = self.digitizer._samples_editor.table.model()
        df = self.reader.sample_locs
        marks = iter(self.straditizer.marks)

        # check index
        for i, val in enumerate(df.index.values):
            self.assertEqual(
                    float(model._get_cell_data(i, 0)), val,
                    msg='Wrong index value at row %i' % i)
        # check cells
        for irow, (row, vals) in enumerate(df.iterrows()):
            for col, val in vals.items():
                if irow == 2 and col == 1:  # the occurence column
                    val = self.reader.occurences_value
                self.assertEqual(
                    float(model._get_cell_data(irow, col + 1)), val,
                    msg='Wrong value at row %i (index %1.1f), column %i' % (
                        irow, row, col))
                if irow and col == 0:
                    next(marks)  # the next mark is for the numbers of extrema
                if irow == 2 and col == 1:
                    val = np.diff(self.reader.all_column_bounds[1])[0] / 2.
                self._test_position(model.get_cell_mark(irow, col + 1).pos,
                                    val, row, col)

    def _test_position(self, pos, value, row, col):
        model = self.digitizer._samples_editor.table.model()
        val_mark, ymark = pos
        val_mark = val_mark - model._bounds[col, 0]
        ymark = ymark - model._y0
        self.assertEqual(
            (val_mark, ymark), (value, row),
            msg='Wrong position of mark at index %1.1f, column %i' % (
                row, col))

    def test_move_mark(self):
        """Test whether the table updates correctly when a mark is moved"""
        self.test_creation()
        model = self.digitizer._samples_editor.table.model()
        df = self.reader.sample_locs
        mark = model.get_cell_mark(0, 1)
        # move mark in x-direction
        current = float(model._get_cell_data(0, 1))
        self.move_mark(mark, [1, 0])
        self.assertEqual(float(model._get_cell_data(0, 1)), current + 1)
        # move mark in y-direction
        current = float(model._get_cell_data(0, 0))
        current_mark = mark.y
        self.move_mark(mark, [0, 1])
        for i in range(len(df.columns) + 1):
            self.assertEqual(model.get_cell_mark(0, i).y, current_mark + 1,
                             msg='Did not move mark of column %i' % (i + 1, ))
        self.assertEqual(float(model._get_cell_data(0, 0)), current + 1)

    def test_edit_table(self):
        """Test whether the table updates correctly when a mark is moved"""
        self.test_creation()
        model = self.digitizer._samples_editor.table.model()
        df = self.reader.sample_locs
        mark = model.get_cell_mark(0, 1)
        # edit the x-value
        current = mark.x
        self.assertTrue(model._set_cell_data(0, 1, str(df.iloc[0, 0] + 1)))
        self.assertEqual(mark.x, current + 1)
        # edit the y-value
        current = mark.y
        self.assertTrue(model._set_cell_data(0, 0, str(df.index[0] + 1)))
        for i in range(len(df.columns) + 1):
            self.assertEqual(model.get_cell_mark(0, i).y, current + 1,
                             msg='Did not move mark of column %i' % (i + 1, ))

    def test_add_mark(self):
        """Test the adding of a new measurment"""
        self.test_creation()
        model = self.digitizer._samples_editor.table.model()
        df = self.reader.sample_locs
        new_y = np.mean(df.index.values[:2])
        # add new marks
        self.add_mark((self.data_xlim[0] + 2, self.data_ylim[0] + new_y))
        # check index
        self.assertEqual(float(model._get_cell_data(1, 0)), new_y)
        # check data values
        for col, val in self.reader.full_df.loc[new_y, :].items():
            self.assertEqual(float(model._get_cell_data(1, col + 1)), val,
                             msg='Wrong value in column %i' % col)

    def test_remove_mark(self):
        """Test the adding of a new measurment"""
        self.test_creation()
        model = self.digitizer._samples_editor.table.model()
        df = self.reader.sample_locs
        mark = self.straditizer.marks[0]
        # add new marks
        self.remove_mark(mark)
        # check index
        self.assertEqual(float(model._get_cell_data(0, 0)), df.index[1])
        # check data values
        for col, val in df.iloc[1, :].items():
            self.assertEqual(float(model._get_cell_data(0, col + 1)), val,
                             msg='Wrong value in column %i' % col)

    def test_insert_row_above(self):
        """Insert a new row"""
        self.test_creation()
        table = self.digitizer._samples_editor.table
        df = self.reader.sample_locs
        model = table.model()
        table.selectRow(1)
        n = len(self.straditizer.marks)
        table.insert_row_above_selection()
        self.assertGreater(len(self.straditizer.marks), n)
        for col in range(len(df.columns)):
            self.assertEqual(
                model._get_cell_data(1, col), model._get_cell_data(2, col))

    def test_del_row_above(self):
        """Insert a new row"""
        self.test_creation()
        table = self.digitizer._samples_editor.table
        df = self.reader.sample_locs
        table.selectRow(1)
        table.delete_selected_rows()
        self.assertNotIn(df.index[1], (m.y for m in self.straditizer.marks))

    def test_fit2data(self):
        """Test fitting a cell to a data"""
        self.test_creation()
        table = self.digitizer._samples_editor.table
        df = self.reader.sample_locs
        model = table.model()
        orig_val = df.iloc[1, 1]
        model._set_cell_data(1, 2, orig_val + 1)
        self.assertEqual(float(model._get_cell_data(1, 2)),
                         orig_val + 1)
        table.selectRow(1)
        table.fit2data()
        self.assertEqual(float(model._get_cell_data(1, 2)),
                         orig_val)

    def test_fit2selection(self):
        """Test fitting the selected cells to the selected values"""
        self.test_creation()
        editor = self.digitizer._samples_editor
        table = editor.table
        df = self.reader.sample_locs
        full_df = self.reader.full_df
        model = table.model()
        editor.cb_fit2selection.setChecked(True)
        # find a different value than the current value
        orig_val = df.iloc[1, 0]
        idx = next(row for row, val in full_df.loc[:, 0].items()
                   if val != orig_val)
        # select this value
        table.selectRow(1)
        ax = self.straditizer.marks[0].ax
        y0 = getattr(model, '_y0', 0)
        ax.set_ylim(len(full_df) + y0 * 2, 0)
        canvas = ax.figure.canvas
        xmean = np.mean(ax.get_xlim())
        x, y = ax.transData.transform([xmean, y0 + idx])
        canvas.button_press_event(x, y, 1)
        canvas.button_release_event(x, y, 1)
        # validate the selection
        for col in range(len(df.columns)):
            self.assertEqual(
                float(model._get_cell_data(1, col + 1)), full_df.loc[idx, col])

        editor.cb_fit2selection.setChecked(False)

    def test_show_selected_marks(self):
        """Test showing only the selected marks"""
        self.test_creation()
        editor = self.digitizer._samples_editor
        table = editor.table
        model = table.model()
        # hide all marks
        editor.cb_selection_only.setChecked(True)
        for m in self.straditizer.marks:
            self.assertFalse(m.hline.get_visible())
        # select the first row
        table.selectRow(1)
        for col in range(1, model.columnCount()):
            self.assertTrue(model.get_cell_mark(1, col).hline.get_visible())
        for row in set(range(model.rowCount())) - {1}:
            for col in range(1, model.columnCount()):
                self.assertFalse(
                    model.get_cell_mark(row, col).hline.get_visible())
        # now show all marks again
        editor.cb_selection_only.setChecked(False)
        for m in self.straditizer.marks:
            self.assertTrue(m.hline.get_visible())

    def test_format(self):
        """Test the changing of the number format"""
        self.test_creation()
        editor = self.digitizer._samples_editor
        table = editor.table
        model = table.model()
        df = self.reader.sample_locs
        # change the format
        editor.format_editor.setText('%1.5f')
        editor.toggle_fmt_button(editor.format_editor.text())
        self.assertTrue(editor.btn_change_format.isEnabled())
        QTest.mouseClick(editor.btn_change_format, Qt.LeftButton)
        # validate index
        for i, val in enumerate(df.index.values):
            self.assertEqual(
                    model._get_cell_data(i, 0), '%1.5f' % val,
                    msg='Wrong index value at row %i' % i)
        # check cells
        for irow, (row, vals) in enumerate(df.iterrows()):
            for col, val in vals.items():
                self.assertEqual(
                    model._get_cell_data(irow, col + 1), '%1.5f' % val,
                    msg='Wrong value at row %i (index %1.1f), column %i' % (
                        irow, row, col))

    def test_zoom_to_selection(self):
        """Test the automatic zoom to the selection"""
        self.test_creation()
        editor = self.digitizer._samples_editor
        table = editor.table
        model = table.model()
        df = self.reader.sample_locs
        for ax in unique_everseen(mark.ax for mark in self.straditizer.marks):
            ax.set_ylim(-1, 0)
            ax.set_xlim(-1, 0)
        editor.cb_zoom_to_selection.setChecked(True)
        # select the last row
        table.selectRow(len(df) - 1)
        y = getattr(model, '_y0', 0) + df.index[-1]
        try:
            starts = model._bounds[:, 0]
        except AttributeError:
            starts = np.zeros(len(df.columns))
        for col, ax in enumerate(
                unique_everseen(mark.ax for mark in self.straditizer.marks)):
            if col == len(df.columns):
                continue
            val = starts[col] + df.iloc[-1, col]
            xmin, xmax = ax.get_xlim()
            ymax, ymin = ax.get_ylim()
            self.assertGreaterEqual(val, xmin)
            self.assertLessEqual(val, xmax)
            self.assertGreater(y, ymin)
            self.assertLess(y, ymax)
        editor.cb_zoom_to_selection.setChecked(False)


class EditSamplesSepTest(EditSamplesTest):
    """Test the editing of samples"""

    def setUp(self):
        super(EditSamplesSepTest, self).setUp()
        self.digitizer.cb_edit_separate.setChecked(True)

    def _test_position(self, pos, value, row, col):
        self.assertEqual(
            tuple(pos), (value, row),
            msg='Wrong position of mark at index %1.1f, column %i' % (
                row, col))

    def test_add_mark(self):
        """Test the adding of a new measurment"""
        self.test_creation()
        model = self.digitizer._samples_editor.table.model()
        df = self.reader.sample_locs
        new_y = np.mean(df.index[:2])
        # add new marks
        self.add_mark((2, new_y))
        # check index
        self.assertEqual(float(model._get_cell_data(1, 0)), new_y)
        # check data values
        for col, val in self.reader.full_df.loc[new_y, :].items():
            self.assertEqual(float(model._get_cell_data(1, col + 1)), val,
                             msg='Wrong value in column %i' % col)


if __name__ == '__main__':
    unittest.main()
