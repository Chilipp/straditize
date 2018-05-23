"""Test the straditize.widgets.axes_translations module"""
from __future__ import division
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt


class AxesTranslation(bt.StraditizeWidgetsTestCase):
    """A test case for testing the axes translations"""

    def test_xaxes_conversion(self):
        """Test the exporting of the final DataFrame"""
        # create a reader with samples
        btn = self.straditizer_widgets.axes_translations.btn_marks_for_x
        self.assertFalse(btn.isEnabled())
        self.init_reader()
        self.reader.digitize()
        self.reader._get_sample_locs()
        self.straditizer_widgets.refresh()
        self.assertTrue(btn.isEnabled())

        # create the marks
        self.straditizer_widgets.axes_translations.marks_for_x(False)
        QTest.mouseClick(btn, Qt.LeftButton)
        x0 = self.data_xlim[0] + self.reader.column_starts[1]
        x1 = x0 + self.reader.sample_locs.iloc[-1, 1]
        self.straditizer._new_mark(x0, self.data_ylim[1], value=0)
        self.straditizer._new_mark(x1, self.data_ylim[1], value=50)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)

        # check the x-values
        self.assertEqual(list(self.reader._xaxis_px_orig), [x0, x1])
        self.assertEqual(list(self.reader.xaxis_data), [0, 50])

        # recreate the marks
        QTest.mouseClick(btn, Qt.LeftButton)
        marks = self.straditizer.marks
        self.assertEqual(len(marks), 2)
        self.assertEqual(marks[0].x, x0)
        self.assertEqual(marks[0].value, 0)
        self.assertEqual(marks[1].x, x1)
        self.assertEqual(marks[1].value, 50)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)

        # check the x-values again
        self.assertEqual(list(self.reader._xaxis_px_orig), [x0, x1])
        self.assertEqual(list(self.reader.xaxis_data), [0, 50])

        # check translation in full_df
        orig_full_df = self.reader.full_df
        full_df = self.straditizer.full_df
        self.assertEqual(full_df.iloc[-1, 1], 50)
        ref0 = 50. * orig_full_df.iloc[-1, 0] / orig_full_df.iloc[-1, 1]
        self.assertEqual(full_df.iloc[-1, 0], ref0)

        # check the translation in final_df
        orig_final_df = self.reader.sample_locs
        final_df = self.straditizer.final_df
        self.assertEqual(final_df.iloc[-1, 1], 50)
        ref0 = 50. * orig_final_df.iloc[-1, 0] / orig_final_df.iloc[-1, 1]
        self.assertEqual(final_df.iloc[-1, 0], ref0)

        # test the setter
        xaxis_px = self.reader.xaxis_px.copy()
        self.reader.xaxis_px = self.reader.xaxis_px
        self.assertEqual(list(self.reader.xaxis_px), list(xaxis_px))

    def test_yaxes_conversion(self):
        """Test the exporting of the final DataFrame"""
        # create a reader with samples
        btn = self.straditizer_widgets.axes_translations.btn_marks_for_y
        self.assertFalse(btn.isEnabled())
        self.init_reader()
        self.reader.digitize()
        self.reader._get_sample_locs()
        self.straditizer_widgets.refresh()

        # create the marks
        QTest.mouseClick(btn, Qt.LeftButton)
        y0 = self.data_ylim[0]
        y1 = self.reader.sample_locs.index[-1] + self.data_ylim[0]
        self.straditizer._new_mark(self.data_xlim[0], y0, value=0)
        self.straditizer._new_mark(self.data_xlim[0], y1, value=50)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)

        # check the x-values
        self.assertEqual(list(self.straditizer._yaxis_px_orig), [y0, y1])
        self.assertEqual(list(self.straditizer.yaxis_data), [0, 50])

        # recreate the marks
        QTest.mouseClick(btn, Qt.LeftButton)
        marks = self.straditizer.marks
        self.assertEqual(len(marks), 2)
        self.assertEqual(marks[0].y, y0)
        self.assertEqual(marks[0].value, 0)
        self.assertEqual(marks[1].y, y1)
        self.assertEqual(marks[1].value, 50)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)

        # check the x-values again
        self.assertEqual(list(self.straditizer._yaxis_px_orig), [y0, y1])
        self.assertEqual(list(self.straditizer.yaxis_data), [0, 50])

        # check translation in full_df
        full_df = self.straditizer.full_df
        self.assertEqual(full_df.index[-1], 50)
        self.assertEqual(full_df.index[0], 0)
        self.assertAlmostEqual(full_df.index[len(full_df) // 2], 25, delta=3)

        # check the translation in final_df
        final_df = self.straditizer.final_df
        self.assertEqual(final_df.index[-1], 50)
        self.assertEqual(final_df.index[0], 0)

        # test the setter
        self.straditizer.yaxis_px = self.straditizer.yaxis_px
        self.assertEqual(list(self.straditizer._yaxis_px_orig), [y0, y1])


if __name__ == '__main__':
    unittest.main()
