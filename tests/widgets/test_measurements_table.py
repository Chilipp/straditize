"""Test the straditize.widgets.measurements_table module"""
import numpy as np
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt
from psyplot.utils import unique_everseen


class EditMeasurementsTest(bt.StraditizeWidgetsTestCase):
    """Test the editing of measurements"""

    def test_creation(self):
        """Test whether the marks and table is set up correctly"""
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        self.straditizer_widgets.refresh()
        self.assertTrue(self.digitizer.btn_find_measurements.isEnabled())
        self.assertTrue(self.digitizer.btn_edit_measurements.isEnabled())
        # first try with empty measurements
        QTest.mouseClick(self.digitizer.btn_edit_measurements, Qt.LeftButton)
        self.assertFalse(self.straditizer.marks)
        self.assertTrue(hasattr(self.digitizer, '_measurements_editor'))
        QTest.mouseClick(self.digitizer.apply_button, Qt.LeftButton)
        self.assertFalse(hasattr(self.digitizer, '_measurements_editor'))
        # Now try with the found measurements
        QTest.mouseClick(self.digitizer.btn_find_measurements, Qt.LeftButton)
        QTest.mouseClick(self.digitizer.btn_edit_measurements, Qt.LeftButton)
        self.assertTrue(self.straditizer.marks)
        self.assertTrue(hasattr(self.digitizer, '_measurements_editor'))
        model = self.digitizer._measurements_editor.table.model()
        df = self.reader.measurement_locs
        marks = iter(self.straditizer.marks)
        # check index
        for i, val in enumerate(df.index.values):
            self.assertEqual(
                    float(model._get_cell_data(i, 0)), val,
                    msg='Wrong index value at row %i' % i)
        # check cells
        for irow, (row, vals) in enumerate(df.iterrows()):
            for col, val in vals.items():
                self.assertEqual(
                    float(model._get_cell_data(irow, col + 1)), val,
                    msg='Wrong value at row %i (index %1.1f), column %i' % (
                        irow, row, col))
                if irow and col == 0:
                    next(marks)  # the next mark is for the numbers of extrema
                mark = next(marks)
                self.assertEqual(
                    tuple(mark.pos), (val, row),
                    msg='Wrong position of mark at index %1.1f, column %i' % (
                        row, col))

    def test_move_mark(self):
        """Test whether the table updates correctly when a mark is moved"""
        self.test_creation()
        model = self.digitizer._measurements_editor.table.model()
        df = self.reader.measurement_locs
        marks = self.straditizer.marks
        mark = marks[0]
        # move mark in x-direction
        self.move_mark(mark, [1, 0])
        self.assertEqual(float(model._get_cell_data(0, 1)), df.iloc[0, 0] + 1)
        # move mark in y-direction
        self.move_mark(mark, [0, 1])
        idx_val = df.index.values[0] + 1
        for i in range(len(df.columns)):
            self.assertEqual(marks[i].y, idx_val,
                             msg='Did not move mark of column %i' % (i + 1, ))
        self.assertEqual(float(model._get_cell_data(0, 0)), idx_val)

    def test_edit_table(self):
        """Test whether the table updates correctly when a mark is moved"""
        self.test_creation()
        model = self.digitizer._measurements_editor.table.model()
        df = self.reader.measurement_locs
        marks = self.straditizer.marks
        mark = marks[0]
        # edit the x-value
        new_xval = df.iloc[0, 0] + 1
        self.assertTrue(model._set_cell_data(0, 1, str(new_xval)))
        self.assertEqual(mark.x, new_xval)
        # edit the y-value
        idx_val = df.iloc[0, 0] + 1
        self.assertTrue(model._set_cell_data(0, 0, str(idx_val)))
        for i in range(len(df.columns)):
            self.assertEqual(marks[i].y, idx_val,
                             msg='Did not move mark of column %i' % (i + 1, ))

    def test_add_mark(self):
        """Test the adding of a new measurment"""
        self.test_creation()
        model = self.digitizer._measurements_editor.table.model()
        df = self.reader.measurement_locs
        new_y = np.mean(df.index[:2])
        # add new marks
        self.add_mark((2, new_y))
        # check index
        self.assertEqual(float(model._get_cell_data(1, 0)), new_y)
        # check data values
        for col, val in self.reader.full_df.loc[new_y, :].items():
            self.assertEqual(float(model._get_cell_data(1, col + 1)), val,
                             msg='Wrong value in column %i' % col)

    def test_remove_mark(self):
        """Test the adding of a new measurment"""
        self.test_creation()
        model = self.digitizer._measurements_editor.table.model()
        df = self.reader.measurement_locs
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
        table = self.digitizer._measurements_editor.table
        df = self.reader.measurement_locs
        model = table.model()
        table.selectRow(1)
        n = len(self.straditizer.marks)
        table.insert_row_above_selection()
        self.assertEqual(len(self.straditizer.marks), n + len(df.columns) + 1)
        for col in range(len(df.columns) + 1):
            self.assertEqual(
                model._get_cell_data(1, col), model._get_cell_data(2, col))

    def test_del_row_above(self):
        """Insert a new row"""
        self.test_creation()
        table = self.digitizer._measurements_editor.table
        df = self.reader.measurement_locs
        table.selectRow(1)
        table.delete_selected_rows()
        self.assertNotIn(df.index[1], (m.y for m in self.straditizer.marks))

    def test_fit2data(self):
        """Test fitting a cell to a data"""
        self.test_creation()
        table = self.digitizer._measurements_editor.table
        df = self.reader.measurement_locs
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
        editor = self.digitizer._measurements_editor
        table = editor.table
        df = self.reader.measurement_locs
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
        ax.set_ylim(len(full_df), 0)
        canvas = ax.figure.canvas
        xmean = np.mean(ax.get_xlim())
        x, y = ax.transData.transform([xmean, idx])
        canvas.button_press_event(x, y, 1)
        # validate the selection
        for col in range(len(df.columns)):
            self.assertEqual(
                float(model._get_cell_data(1, col + 1)), full_df.loc[idx, col])

        editor.cb_fit2selection.setChecked(False)

    def test_show_selected_marks(self):
        """Test showing only the selected marks"""
        self.test_creation()
        editor = self.digitizer._measurements_editor
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
        editor = self.digitizer._measurements_editor
        table = editor.table
        model = table.model()
        df = self.reader.measurement_locs
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
        editor = self.digitizer._measurements_editor
        table = editor.table
        df = self.reader.measurement_locs
        for ax in unique_everseen(mark.ax for mark in self.straditizer.marks):
            ax.set_ylim(-1, 0)
            ax.set_xlim(-1, 0)
        editor.cb_zoom_to_selection.setChecked(True)
        # select the last row
        table.selectRow(len(df) - 1)
        y = df.index[-1]
        for col, ax in enumerate(
                unique_everseen(mark.ax for mark in self.straditizer.marks)):
            if col == len(df.columns):
                continue
            val = df.iloc[-1, col]
            xmin, xmax = ax.get_xlim()
            ymax, ymin = ax.get_ylim()
            self.assertGreaterEqual(val, xmin)
            self.assertLessEqual(val, xmax)
            self.assertGreater(y, ymin)
            self.assertLess(y, ymax)
        editor.cb_zoom_to_selection.setChecked(False)


if __name__ == '__main__':
    unittest.main()
