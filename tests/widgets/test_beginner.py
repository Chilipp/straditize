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
        from straditize.widgets.tutorial import Tutorial
        super().setUpClass()
        cls.straditizer_widgets.start_tutorial(True, Tutorial)

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
        self.skip_until(2)
        self._test_hint('beginner-tutorial.png')
        self.page.skip()
        self._test_finish()

    def test_02_select_data(self):
        self.skip_until(4)
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
        mark = sw.straditizer._new_mark(*self.page.ref_lims[:, 1] + 100)[0]
        self._test_hint('drag it')
        # now we select the wrong corners by purpose
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_hint('did not select the correct')
        # and start again
        self.digitizer.btn_select_data.click()
        sw.straditizer.marks[1].set_pos(self.page.ref_lims[:, 1])
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        # now test for the diagram part
        self._test_hint('Plot control')
        sw.tree.expandItem(sw.plot_control_item)
        self._test_hint('remove the red rectangle')
        self.straditizer.remove_data_box()
        sw.refresh()
        self._test_finish()

    def test_03_init_reader(self):
        self.skip_until(5)
        self._test_hint(self.digitizer.btn_init_reader.text())
        self.digitizer.btn_init_reader.click()
        self._test_finish()

    def test_04_column_starts(self):
        self.skip_until(6)
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

    def test_05_clean_image(self):
        self.skip_until(7)
        sw = self.straditizer_widgets
        stradi = sw.straditizer
        digitizer = self.digitizer
        # first expand the necessary items
        self._test_hint(digitizer.remove_child.text(0))
        digitizer.tree.expandItem(digitizer.remove_child)

        # now remove y-axes lines
        self._test_hint(digitizer.btn_remove_yaxes.text())
        digitizer.btn_remove_yaxes.click()
        self._test_hint(sw.apply_button.text())
        sw.apply_button.click()

        # now remove x-axes lines
        self._test_hint(digitizer.btn_remove_xaxes.text())
        digitizer.btn_remove_xaxes.click()
        self._test_hint(sw.apply_button.text())
        sw.apply_button.click()

        # and the last vertical line
        # -- ask for column selection tool
        self._test_hint('column selection')
        sw.selection_toolbar.set_col_wand_mode()
        # -- ask for change the selection mode
        self._test_hint('selection mode')
        sw.selection_toolbar.new_select_action.trigger()
        # -- ask for drawing a rectangle on the plot
        self._test_hint('rectangle')
        sw.selection_toolbar.start_selection(stradi.data_reader.labels)
        sw.selection_toolbar.select_rect(
            slice(1799 - stradi.data_xlim[0], None), slice(None))
        self._test_hint(sw.apply_button.text())
        sw.apply_button.click()
        self._test_finish()

    def test_06_digitize(self):
        self.skip_until(8)
        self._test_hint(self.digitizer.btn_digitize.text())
        self.digitizer.digitize()
        self._test_finish()

    def test_07_samples(self):
        self.skip_until(9)
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
        self.skip_until(10)
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        sw.tree.collapseItem(sw.axes_translations_item)
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
        self.straditizer._new_mark(250, 519, value=200)
        self._test_hint('another')
        self.straditizer._new_mark(250, 1450, value=400)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_09_translate_x(self):
        self.skip_until(11)
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        sw.tree.collapseItem(sw.axes_translations_item)
        self._test_hint(sw.axes_translations_item.text(0))
        digitizer.tree.expandItem(sw.axes_translations_item)
        self._test_hint(sw.axes_translations.btn_marks_for_x.text())

        # Test the 'wrong button' message'
        self.digitizer.btn_select_data.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        sw.axes_translations.marks_for_x(False)
        self.page.clicked_correct_button()
        self._test_hint('horizontal axis')
        self.straditizer._new_mark(258, 1665, value=0)
        self._test_hint('another')
        self.straditizer._new_mark(828, 1665, value=90)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        self._test_finish()

    def test_10_colnames(self):
        self.skip_until(12)
        sw = self.straditizer_widgets

        self._test_hint(sw.col_names_item.text(0))
        sw.tree.expandItem(sw.col_names_item)

        self._test_hint(sw.colnames_manager.btn_select_names.text())
        sw.colnames_manager.btn_select_names.click()

        self._test_hint('Edit the column names')
        self.straditizer.colnames_reader.column_names = [
            'Pinus', 'Juniperus', 'Quercus ilex-type', 'Chenopodiaceae']
        sw.refresh()

        self._test_hint(sw.colnames_manager.btn_select_names.text())
        sw.colnames_manager.btn_select_names.click()
        self._test_finish()

    def test_11_finish(self):
        self.skip_until(13)
        self.assertTrue(self.navigation.btn_prev.isEnabled())
        self.assertFalse(self.navigation.btn_hint.isEnabled())
        self.assertFalse(self.navigation.btn_next.isEnabled())
        self.assertFalse(self.navigation.btn_skip.isEnabled())


if __name__ == '__main__':
    unittest.main()
