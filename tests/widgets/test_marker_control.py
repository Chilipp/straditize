# -*- coding: utf-8 -*-
"""Test module for straditize.widgets.marker_control"""
import _base_testing as bt
from itertools import chain
from psyplot_gui.compat.qtcompat import QTest, Qt
import straditize.cross_mark as cm
import unittest
import pandas as pd


class MarkerControlTest(bt.StraditizeWidgetsTestCase):
    """Test class for :class:`straditize.widgets.marker_control.MarkerControl`
    """

    @property
    def marker_control(self):
        return self.straditizer_widgets.marker_control

    @property
    def marks(self):
        return self.straditizer.marks

    def setUp(self):
        super().setUp()
        self.init_reader()
        # create marks
        QTest.mouseClick(self.digitizer.btn_select_data, Qt.LeftButton)

    def test_change_select_colors(self):
        color = (0, 1.0, 0.0, 1.0)
        self.marker_control.lbl_color_select.set_color(color)
        for i, mark in enumerate(self.marks):
            self.assertEqual(
                list(mark._select_props['c']), list(color),
                msg='Wrong color for mark %i' % i)

    def test_change_unselect_colors(self):
        color = (0, 1.0, 0.0, 1.0)
        self.marker_control.lbl_color_unselect.set_color(color)
        for i, mark in enumerate(self.marks):
            self.assertEqual(
                list(mark._unselect_props['c']), list(color),
                msg='Wrong color for mark %i' % i)
            for j, l in enumerate(chain(mark.hlines, mark.vlines)):
                self.assertEqual(list(l.get_color()), list(color),
                                 msg='Wrong color for line %i in mark %i' % (
                                     j, i))

    def test_change_auto_hide(self):
        """Change the auto_hide modification"""
        self.marker_control.cb_auto_hide.setChecked(True)
        for i, mark in enumerate(self.marks):
            self.assertTrue(mark.auto_hide, msg='Wrong value for mark %i' % i)
            for j, l in enumerate(chain(mark.hlines, mark.vlines)):
                self.assertEqual(
                    l.get_linewidth(), 0,
                    msg='Wrong line width for line %i in mark %i' % (j, i))
        lw = float(self.marker_control.txt_line_width.text())
        self.assertGreater(lw, 0)

        self.marker_control.cb_auto_hide.setChecked(False)
        for i, mark in enumerate(self.marks):
            self.assertFalse(mark.auto_hide, msg='Wrong value for mark %i' % i)
            for j, l in enumerate(chain(mark.hlines, mark.vlines)):
                self.assertEqual(
                    l.get_linewidth(), lw,
                    msg='Wrong line width for line %i in mark %i' % (j, i))

    def test_change_line_style(self):
        """Change the line style"""
        ls = '--'
        mc = self.marker_control
        for i, t in enumerate(mc.line_styles):
            if ls in t:
                mc.combo_line_style.setCurrentIndex(i)
                break
        for i, mark in enumerate(self.marks):
            for j, l in enumerate(chain(mark.hlines, mark.vlines)):
                self.assertEqual(
                    l.get_ls(), ls,
                    msg='Wrong style for line %i in mark %i' % (j, i))

    def test_change_marker_style(self):
        """Change the line style"""
        ms = 'o'
        mc = self.marker_control
        for i, (name, t) in enumerate(mc.marker_styles):
            if ms in t:
                mc.combo_marker_style.setCurrentIndex(i)
                break
        for i, mark in enumerate(self.marks):
            for j, l in enumerate(chain(mark.hlines, mark.vlines)):
                self.assertEqual(
                    l.get_marker(), ms,
                    msg='Wrong style for line %i in mark %i' % (j, i))

    def test_change_marker_size(self):
        """Test changing the size of the marker"""
        self.marker_control.change_marker_size(100)
        for i, mark in enumerate(self.marks):
            for j, l in enumerate(chain(mark.hlines, mark.vlines)):
                self.assertEqual(
                    l.get_markersize(), 100,
                    msg='Wrong style for line %i in mark %i' % (j, i))

    def test_goto_right_mark_01_single(self):
        """Test the navigation button to the right mark for one edge per mark
        """
        ax = self.straditizer.ax
        minx, maxx = sorted(self.data_xlim)
        miny, maxy = sorted(self.data_ylim)
        ax.set_xlim(minx - 1, minx + 1)
        ax.set_ylim(miny - 1, miny + 1)
        self.marker_control.go_to_right_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(maxx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(maxy, yi)

    def test_goto_right_mark_02_multi(self):
        """Test the navigation button to the right mark for multiple edges
        per mark
        """
        self.straditizer.remove_marks()
        self.marker_control.refresh()
        ax = self.straditizer.ax
        minx, maxx = xlim = sorted(self.data_xlim)
        miny, maxy = sorted(self.data_ylim)
        self.straditizer.marks = [cm.CrossMarks((xlim, miny), ax=ax),
                                  cm.CrossMarks((xlim, maxy), ax=ax)]
        self.marker_control.refresh()
        ax.set_xlim(minx - 1, minx + 1)
        ax.set_ylim(miny + 1, miny - 1)
        self.marker_control.go_to_right_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(maxx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(miny, yi)

    def test_goto_left_mark_01_single(self):
        """Test the navigation button to the right mark for one edge per mark
        """
        ax = self.straditizer.ax
        minx, maxx = sorted(self.data_xlim)
        miny, maxy = sorted(self.data_ylim)
        ax.set_xlim(maxx - 1, maxx + 1)
        ax.set_ylim(maxy - 1, maxy + 1)
        self.marker_control.go_to_left_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(minx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(miny, yi)

    def test_goto_left_mark_02_multi(self):
        """Test the navigation button to the right mark for multiple edges
        per mark
        """
        self.straditizer.remove_marks()
        self.marker_control.refresh()
        ax = self.straditizer.ax
        minx, maxx = xlim = sorted(self.data_xlim)
        miny, maxy = sorted(self.data_ylim)
        self.straditizer.marks = [cm.CrossMarks((xlim, miny), ax=ax),
                                  cm.CrossMarks((xlim, maxy), ax=ax)]
        self.marker_control.refresh()
        ax.set_xlim(maxx - 1, maxx + 1)
        ax.set_ylim(miny + 1, miny - 1)
        self.marker_control.go_to_left_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(minx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(miny, yi)

    def test_goto_lower_mark_01_single(self):
        """Test the navigation button to the right mark for one edge per mark
        """
        ax = self.straditizer.ax
        minx, maxx = sorted(self.data_xlim)
        miny, maxy = sorted(self.data_ylim)
        ax.set_xlim(minx - 0.5, minx + 1)
        ax.set_ylim(miny - 0.5, miny + 1)
        self.marker_control.go_to_lower_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(maxx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(maxy, yi)

    def test_goto_lower_mark_02_multi(self):
        """Test the navigation button to the right mark for multiple edges
        per mark
        """
        self.straditizer.remove_marks()
        self.marker_control.refresh()
        ax = self.straditizer.ax
        minx, maxx = sorted(self.data_xlim)
        miny, maxy = ylim = sorted(self.data_ylim)
        self.straditizer.marks = [cm.CrossMarks((minx, ylim), ax=ax),
                                  cm.CrossMarks((maxx, ylim), ax=ax)]
        self.marker_control.refresh()
        ax.set_xlim(minx - 1, minx + 1)
        ax.set_ylim(miny + 1, miny - 1)
        self.marker_control.go_to_lower_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(minx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(maxy, yi)

    def test_goto_upper_mark_01_single(self):
        """Test the navigation button to the right mark for one edge per mark
        """
        ax = self.straditizer.ax
        minx, maxx = sorted(self.data_xlim)
        miny, maxy = sorted(self.data_ylim)
        ax.set_xlim(maxy - 1, maxy + 1)
        ax.set_ylim(maxy - 1, maxy + 1)
        self.marker_control.go_to_upper_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(minx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(miny, yi)

    def test_goto_upper_mark_02_multi(self):
        """Test the navigation button to the right mark for multiple edges
        per mark
        """
        self.straditizer.remove_marks()
        self.marker_control.refresh()
        ax = self.straditizer.ax
        minx, maxx = sorted(self.data_xlim)
        miny, maxy = ylim = sorted(self.data_ylim)
        self.straditizer.marks = [cm.CrossMarks((minx, ylim), ax=ax),
                                  cm.CrossMarks((maxx, ylim), ax=ax)]
        self.marker_control.refresh()
        ax.set_xlim(minx - 1, minx + 1)
        ax.set_ylim(maxy + 1, maxy - 1)
        self.marker_control.go_to_upper_mark()
        xi = pd.Interval(*ax.get_xlim(), closed='both')
        self.assertIn(minx, xi)
        yi = pd.Interval(*sorted(ax.get_ylim()), closed='both')
        self.assertIn(miny, yi)


if __name__ == '__main__':
    unittest.main()
