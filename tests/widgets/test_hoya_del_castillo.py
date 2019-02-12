# -*- coding: utf-8 -*-
"""Test module for the tutorial"""
import _base_testing as bt
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt
import unittest


class TutorialTest(bt.StraditizeWidgetsTestCase):
    """A base class for testing tutorial pages"""

    page_number = 0

    @property
    def tutorial(self):
        return self.straditizer_widgets.tutorial

    @property
    def navigation(self):
        return self.tutorial.navigation

    @property
    def page(self):
        return self.tutorial.pages[self.page_number]

    @classmethod
    def setUpClass(cls):
        from straditize.widgets.tutorial import HoyaDelCastilloTutorial
        super().setUpClass()
        cls.straditizer_widgets.start_tutorial(True, HoyaDelCastilloTutorial)

    @classmethod
    def tearDownClass(cls):
        cls.straditizer_widgets.start_tutorial(False)
        super().tearDownClass()

    def skip_until(self, page_number):
        for i in range(self.navigation.current_step, page_number):
            self.navigation.skip()
        self.page_number = page_number
        self.assertEqual(self.navigation.current_step, page_number)
        self.assertIs(self.tutorial.current_page, self.page)

    def _test_hint(self, regex):
        """Test whether the current hint matches the given regular expression
        """
        QTest.mouseClick(self.navigation.btn_hint, Qt.LeftButton)
        self.assertRegex(self.page._last_tooltip_shown, regex)

    def _test_finish(self):
        self.assertTrue(self.page.is_finished)
        self._test_hint(self.navigation.btn_next.text())

    def test_01_init_stradi(self):
        self.skip_until(1)
        self._test_hint('hoya-del-castillo.png')
        self.page.skip()
        self._test_finish()

    def test_02_select_data(self):
        self.skip_until(2)
        sw = self.straditizer_widgets
        self._test_hint(self.digitizer.btn_select_data.text())
        # Test the 'wrong button' message'
        sw.image_rotator.btn_rotate_horizontal.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        self._test_hint(self.digitizer.btn_select_data.text())
        self.page.clicked_correct_button()
        self.digitizer.select_data_part(guess_lims=False)
        self.straditizer.marks.clear()
        self.straditizer.magni_marks.clear()
        # this should display a hint to shift+leftclick one of the corners
        self._test_hint('(?i)Shift\+leftclick')
        mark = sw.straditizer._new_mark(*self.page.ref_lims[:, 0] + 20)[0]
        self._test_hint('drag it')
        mark.set_pos(self.page.ref_lims[:, 0])

        # now select the opposite corner
        self._test_hint('(?i)Shift\+leftclick')
        mark = sw.straditizer._new_mark(*self.page.ref_lims[:, 1] + 20)[0]
        self._test_hint('drag it')
        # now we select the wrong corners by purpose
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_hint('did not select the correct')
        # and start again
        self.digitizer.btn_select_data.click()
        sw.straditizer.marks[1].set_pos(self.page.ref_lims[:, 1])
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_03_init_reader(self):
        self.skip_until(3)
        self._test_hint(self.digitizer.btn_init_reader.text())
        self.digitizer.btn_init_reader.click()
        self._test_finish()

    def test_04_column_starts(self):
        self.skip_until(4)
        sw = self.straditizer_widgets
        self._test_hint(self.digitizer.btn_column_starts.text())
        # Test the 'wrong button' message'
        self.digitizer.btn_select_data.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        self._test_hint(self.digitizer.btn_column_starts.text())
        self.digitizer.btn_column_starts.click()
        # remove a mark and apply
        self.straditizer.marks.pop(1).remove()
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        # There should be now not enough columns, so we reset
        self._test_hint(sw.digitizer.btn_reset_columns.text())
        sw.digitizer.btn_reset_columns.click()

        # Now click the correct button again
        self._test_hint(self.digitizer.btn_column_starts.text())
        self.digitizer.btn_column_starts.click()
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_05_remove_lines(self):
        self.skip_until(6)
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        # first expand the necessary items
        self._test_hint(digitizer.remove_child.text(0))
        digitizer.tree.expandItem(digitizer.remove_child)
        self._test_hint('remove lines')
        digitizer.tree.expandItem(digitizer.remove_line_child)

        # now remove horizontal lines
        self._test_hint(digitizer.btn_remove_hlines.text())
        digitizer.btn_remove_hlines.click()
        self._test_hint(sw.apply_button.text())
        sw.apply_button.click()

        # and vertical lines
        self._test_hint('Enable')
        digitizer.cb_max_lw.setChecked(True)
        self._test_hint('maximum line')
        digitizer.sp_max_lw.setValue(2)
        self._test_hint(digitizer.btn_remove_vlines.text())
        digitizer.btn_remove_vlines.click()
        self._test_hint(sw.apply_button.text())
        sw.apply_button.click()
        self._test_finish()

    def test_06_digitize(self):
        self.skip_until(7)
        self._test_hint(self.digitizer.btn_digitize.text())
        self.digitizer.digitize()
        self._test_finish()

    def test_07_samples(self):
        self.skip_until(8)
        digitizer = self.digitizer
        sw = self.straditizer_widgets
        self._test_hint(digitizer.edit_samples_child.text(0))
        digitizer.tree.expandItem(digitizer.edit_samples_child)
        self._test_hint(digitizer.btn_find_samples.text())
        digitizer.btn_find_samples.click()
        self._test_hint(digitizer.btn_edit_samples.text())
        digitizer.btn_edit_samples.click()
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_08_translate_y(self):
        self.skip_until(9)
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        self._test_hint(sw.axes_translations_item.text(0))
        digitizer.tree.expandItem(sw.axes_translations_item)
        self._test_hint(sw.axes_translations.btn_marks_for_y.text())

        # Test the 'wrong button' message'
        self.digitizer.btn_select_data.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        sw.axes_translations.btn_marks_for_y.click()
        self._test_hint('vertical axis')
        self.straditizer._new_mark(318, 641, value=200)
        self._test_hint('another')
        self.straditizer._new_mark(308, 777, value=250)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_09_translate_x(self):
        self.skip_until(10)
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        self._test_hint(digitizer.current_reader_item.text(0))
        digitizer.tree.expandItem(digitizer.current_reader_item)
        self._test_hint('new reader')

        # Test the 'wrong button' message'
        self.digitizer.btn_select_data.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)

        # now click the correct button and start with the first column
        self.digitizer.btn_new_child_reader.click()
        self._test_hint('column 0')

        # select the first column
        self.reader._select_column(col=0)
        self._test_hint(sw.apply_button.text())
        digitizer.new_reader_for_selection(self.reader.__class__)
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)

        # now enter the translation
        self._test_hint('column 0')
        digitizer.change_reader('Columns 0')

        sw.tree.collapseItem(sw.axes_translations_item)
        self._test_hint(sw.axes_translations_item.text(0))
        digitizer.tree.expandItem(sw.axes_translations_item)
        self._test_hint(sw.axes_translations.btn_marks_for_x.text())

        sw.axes_translations.btn_marks_for_y.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)

        # Start the translation
        self._test_hint(sw.axes_translations.btn_marks_for_x.text())
        sw.axes_translations.marks_for_x(False)
        self.page.clicked_translations_button()
        self._test_hint('enter the corresponding x-value')
        self.straditizer._new_mark(321, 777, value=0)
        self._test_hint('enter another x-value')
        self.straditizer._new_mark(374, 777, value=50)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)

        # continue with the last column
        self._test_hint('reader for column 27')
        digitizer.change_reader('Columns 1-27')
        self._test_hint('new reader')

        # select the last column
        self.digitizer.btn_new_child_reader.click()
        self._test_hint('column 27')
        self.reader._select_column(col=-1)
        self._test_hint(sw.apply_button.text())
        digitizer.new_reader_for_selection(self.reader.__class__)
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)

        # now enter the translation
        self._test_hint('column 27')
        digitizer.change_reader('Columns 27')

        # Start the translation
        self._test_hint(sw.axes_translations.btn_marks_for_x.text())
        sw.axes_translations.marks_for_x(False)
        self.page.clicked_translations_button()
        self._test_hint('enter the corresponding x-value')
        self.straditizer._new_mark(1776, 777, value=0)
        self._test_hint('enter another x-value')
        self.straditizer._new_mark(1855, 777, value=30000)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)

        # continue with the columns in between
        self._test_hint('reader for column 1')
        digitizer.change_reader('Columns 1-26')

        # Start the translation
        self._test_hint(sw.axes_translations.btn_marks_for_x.text())
        sw.axes_translations.marks_for_x(False)
        self.page.clicked_translations_button()
        self._test_hint('enter the corresponding x-value')
        self.straditizer._new_mark(499, 777, value=0)
        self._test_hint('enter another x-value')
        self.straditizer._new_mark(583, 777, value=40)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_10_attributes(self):
        self.skip_until(11)
        sw = self.straditizer_widgets
        self._test_hint(sw.attrs_button.text())
        QTest.mouseClick(sw.attrs_button, Qt.LeftButton)
        self._test_hint('Add some meta')

        sw.straditizer.attrs.iloc[0, 0] = 'me'

        self._test_finish()

    def test_11_finish(self):
        self.skip_until(12)
        self.assertTrue(self.navigation.btn_prev.isEnabled())
        self.assertFalse(self.navigation.btn_hint.isEnabled())
        self.assertFalse(self.navigation.btn_next.isEnabled())
        self.assertFalse(self.navigation.btn_skip.isEnabled())


if __name__ == '__main__':
    unittest.main()
