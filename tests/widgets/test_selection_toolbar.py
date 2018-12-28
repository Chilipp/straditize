"""Test the straditize.widgets.selection_toolbar module"""
import numpy as np
import pandas as pd
import os.path as osp
from itertools import chain
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt


class StraditizerSelectionToolsTest(bt.StraditizeWidgetsTestCase):
    """A test case for testing the plotting functions"""

    what = 'Straditizer'

    reference = 'basic_diagram_select_removed.png'

    def tearDown(self):
        super(StraditizerSelectionToolsTest, self).tearDown()
        try:
            del self.reference
        except AttributeError:
            pass

    @property
    def toolbar(self):
        return self.straditizer_widgets.selection_toolbar

    def select_rectangle(self, x0, x1, y0, y1):
        slx, sly = self.toolbar.get_xy_slice(x0, y0, x1, y1)
        self.toolbar.select_rect(slx, sly)

    def check_image(self):
        fname = self.get_random_filename(suffix='.png')
        self.straditizer_widgets.menu_actions.save_full_image(fname)
        self.assertImageEquals(fname, self.get_fig_path(self.reference))

    def test_rectangle(self):
        """Test the rectangle select tool"""
        self.init_reader('basic_diagram_select.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_rect_select_mode()
        self.toolbar.select_action.setChecked(True)
        self.toolbar.toggle_selection()
        self.select_rectangle(19.5, 21.5, 14.5, 17.5)
        self.assertTrue(self.straditizer_widgets.apply_button.isEnabled())
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_wand(self):
        """Test the wand tool"""
        self.init_reader('basic_diagram_select.png')
        self.toolbar.set_label_wand_mode()
        self.toolbar.data_obj = self.what
        self.toolbar.wand_action.setChecked(True)
        self.toolbar.toggle_selection()
        self.select_rectangle(20.5, 20.5, 15.5, 15.5)
        self.assertTrue(self.straditizer_widgets.apply_button.isEnabled())
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_color_wand(self):
        """Test the color wand"""
        self.init_reader('basic_diagram_select.png')
        self.toolbar.set_color_wand_mode()
        self.toolbar.data_obj = self.what
        self.toolbar.wand_action.setChecked(True)
        self.toolbar.toggle_selection()
        self.select_rectangle(20.5, 20.5, 15.5, 15.5)
        self.assertTrue(self.straditizer_widgets.apply_button.isEnabled())
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_poly_select(self):
        """Test the polygon selection"""
        self.init_reader('basic_diagram_select.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_poly_select_mode()
        self.toolbar.select_action.setChecked(True)
        self.toolbar.toggle_selection()
        self.toolbar.select_poly([[20., 14.8], [19.6, 17.], [21.5, 17.3],
                                  [21.8, 14.8]])
        self.assertTrue(self.straditizer_widgets.apply_button.isEnabled())
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_invert_selection(self, reference=None):
        """Test the inversion of the selection"""
        self.reference = reference or 'basic_diagram.png'
        self.init_reader('basic_diagram_select.png')
        tb = self.toolbar
        tb.data_obj = self.what
        tb.start_selection(tb.labels)
        tb.data_obj.select_labels(np.array([1, 2, 3]))
        tb.invert_selection()
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_select_all(self):
        """Test selecting all labels"""
        self.init_reader('basic_diagram_select.png')
        tb = self.toolbar
        tb.data_obj = self.what
        tb.select_all()
        self.assertEqual(
            list(tb.data_obj.selected_labels),
            list(range(1, tb.data_obj._select_nlabels + 1)))

    def test_clear_selection(self):
        """Test clearing the selection"""
        self.test_select_all()
        tb = self.toolbar
        tb.clear_selection()
        self.assertFalse(tb.data_obj.selected_part.any())

    def test_expand_selection(self):
        """Test expanding the selection"""
        self.init_reader('basic_diagram_select.png')
        self.toolbar.data_obj = self.what
        self.toolbar.select_action.setChecked(True)
        self.toolbar.toggle_selection()
        self.select_rectangle(20.5, 20.5, 15.5, 15.5)
        self.toolbar.expand_selection()
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_binary_pattern(self, reference=None):
        """Test the pattern selection for full binary patterns"""
        if reference is None:
            reference = 'basic_diagram_select_pattern_removed.png'
        self.reference = reference
        self.init_reader('basic_diagram_select_pattern.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_binary_pattern_mode()
        self._test_pattern_selection()

    def test_grey_pattern(self, reference=None):
        """Test the pattern selection for full binary patterns"""
        if reference is None:
            reference = 'basic_diagram_select_pattern_removed.png'
        self.reference = reference
        self.init_reader('basic_diagram_select_pattern.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_grey_pattern_mode()
        self._test_pattern_selection()

    def test_partial_binary_pattern(self, reference=None):
        """Test the pattern selection for full binary patterns"""
        if reference is None:
            reference = 'basic_diagram.png'
        self.reference = reference
        self.init_reader('basic_diagram_select_pattern.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_binary_pattern_mode()
        self._test_pattern_selection(partial=True)

    def test_partial_grey_pattern(self, reference=None):
        """Test the pattern selection for full binary patterns"""
        if reference is None:
            reference = 'basic_diagram.png'
        self.reference = reference
        self.init_reader('basic_diagram_select_pattern.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_grey_pattern_mode()
        self._test_pattern_selection(partial=True)

    def _test_pattern_selection(self, partial=False, cancel=False):
        # start pattern selmection
        self.toolbar.select_pattern_action.setChecked(True)
        self.toolbar.start_pattern_selection()
        # select the template
        pw = self.toolbar._pattern_selection
        pw.btn_select_template.click()
        pw.selector.extents = np.array([20., 23., 14., 18.])
        pw.update_image()
        pw.btn_select_template.click()
        # use partial pattern
        if partial:
            pw.fraction_box.setChecked(True)
            pw.sl_increments.setValue(1)
        # correlate
        pw.btn_correlate.click()
        # plot the correlation
        pw.btn_plot_corr.click()
        self.assertIsNotNone(pw._corr_plot)
        pw.btn_plot_corr.click()
        # start the correlation
        pw.btn_select.click()
        pw.sl_thresh.setValue(90)
        # close the plot
        if cancel:
            pw.btn_cancel.click()
        else:
            pw.btn_close.click()
            QTest.mouseClick(self.straditizer_widgets.apply_button,
                             Qt.LeftButton)
            self.check_image()

    def test_cancel_pattern_selection(self):
        self.init_reader('basic_diagram_select_pattern.png')
        self.toolbar.data_obj = self.what
        self.toolbar.set_grey_pattern_mode()
        self._test_pattern_selection(cancel=True)
        self.assertEqual(
            self.toolbar.data_obj.selected_part.sum(),
            self.toolbar.data_obj._selection_arr.astype(bool).sum())


class ReaderSelectionToolsTest(StraditizerSelectionToolsTest):
    """A test case for selections based on the reader"""

    what = 'Reader'

    reference = 'basic_diagram_select_removed_binary.png'

    def check_image(self):
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path(self.reference))

    def test_wand(self):
        """Test the wand tool"""
        # entire object should be removed
        self.reference = 'basic_diagram_binary.png'
        StraditizerSelectionToolsTest.test_wand(self)

    def test_expand_selection(self):
        """Test expanding the selection"""
        # entire object should be removed
        self.reference = 'basic_diagram_binary.png'
        StraditizerSelectionToolsTest.test_expand_selection(self)

    def test_invert_selection(self):
        StraditizerSelectionToolsTest.test_invert_selection(
            self, 'basic_diagram_binary.png')

    def test_select_everything_to_the_right(self, reference=None):
        self.reference = 'basic_diagram_binary.png'
        self.init_reader('basic_diagram_select.png')
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self.toolbar.data_obj = self.what
        self.toolbar.select_action.setChecked(True)
        self.toolbar.toggle_selection()
        self.select_rectangle(20.5, 20.5, 15.5, 16.5)
        self.toolbar.select_everything_to_the_right()
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.check_image()

    def test_binary_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_binary_pattern(
            self, 'basic_diagram_select_pattern_removed_20px.png')

    def test_grey_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_grey_pattern(
            self, 'basic_diagram_select_pattern_removed_20px.png')

    def test_partial_binary_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_partial_binary_pattern(
            self, 'basic_diagram_binary.png')

    def test_partial_grey_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_partial_grey_pattern(
            self, 'basic_diagram_binary.png')


class ReaderGreyScaleToolsTest(StraditizerSelectionToolsTest):
    """A test case for selections based on the reader"""

    what = 'Reader - Greyscale'

    reference = 'basic_diagram_select_removed_binary.png'

    def check_image(self):
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path(self.reference))

    def test_invert_selection(self):
        StraditizerSelectionToolsTest.test_invert_selection(
            self, 'basic_diagram_binary.png')

    def test_binary_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_binary_pattern(
            self, 'basic_diagram_select_pattern_removed_20px.png')

    def test_grey_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_grey_pattern(
            self, 'basic_diagram_select_pattern_removed_20px.png')

    def test_partial_binary_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_partial_binary_pattern(
            self, 'basic_diagram_binary.png')

    def test_partial_grey_pattern(self):
        """Test the pattern selection for full binary patterns"""
        StraditizerSelectionToolsTest.test_partial_grey_pattern(
            self, 'basic_diagram_binary.png')


if __name__ == '__main__':
    unittest.main()
