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

    def setUp(self):
        super().setUp()
        self.straditizer_widgets.start_tutorial(True)
        for i in range(self.page_number):
            self.navigation.skip()
        self.assertEqual(self.navigation.current_step, self.page_number)
        self.assertIs(self.tutorial.current_page, self.page)

    def _test_hint(self, regex):
        """Test whether the current hint matches the given regular expression
        """
        QTest.mouseClick(self.navigation.btn_hint, Qt.LeftButton)
        self.assertRegex(self.page._last_tooltip_shown, regex)

    def test_page(self):
        """Test the tutorial page"""
        self.assertTrue(self.page.is_finished)
        self._test_hint(self.navigation.btn_next.text())

    def tearDown(self):
        super().tearDown()
        self.straditizer_widgets.start_tutorial(False)


class StraditizerInitTest(TutorialTest):
    """Test case for the first tutorial page to initialize the straditizer"""

    page_number = 1

    def test_page(self):
        self._test_hint('straditize-tutorial.png')
        self.page.skip()
        super().test_page()


class SelectDataPartTest(TutorialTest):
    """Test case for the first tutorial page to initialize the straditizer"""

    page_number = 2

    def test_page(self):
        sw = self.straditizer_widgets
        self._test_hint(self.digitizer.btn_select_data.text())
        # Test the 'wrong button' message'
        sw.image_rotator.btn_rotate_horizontal.click()
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        self._test_hint(self.digitizer.btn_select_data.text())
        QTest.mouseClick(self.digitizer.btn_select_data, Qt.LeftButton)
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
        QTest.mouseClick(self.digitizer.btn_select_data, Qt.LeftButton)
        sw.straditizer.marks[1].set_pos(self.page.ref_lims[:, 1])
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        super().test_page()


class InitReaderTest(TutorialTest):

    page_number = 3

    def test_page(self):
        self._test_hint(self.digitizer.btn_init_reader.text())
        QTest.mouseClick(self.digitizer.btn_init_reader, Qt.LeftButton)
        super().test_page()


class ColumnStartTest(TutorialTest):

    page_number = 4

    def test_page(self):
        sw = self.straditizer_widgets
        self._test_hint(self.digitizer.btn_column_starts.text())
        # Test the 'wrong button' message'
        QTest.mouseClick(self.digitizer.btn_select_data, Qt.LeftButton)
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        self._test_hint(self.digitizer.btn_column_starts.text())
        QTest.mouseClick(self.digitizer.btn_column_starts, Qt.LeftButton)
        # remove a mark and apply
        self.straditizer.marks.pop(1).remove()
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        # There should be now not enough columns, so we reset
        self._test_hint(sw.digitizer.btn_reset_columns.text())
        QTest.mouseClick(sw.digitizer.btn_reset_columns, Qt.LeftButton)

        # Now click the correct button again
        self._test_hint(self.digitizer.btn_column_starts.text())
        QTest.mouseClick(self.digitizer.btn_column_starts, Qt.LeftButton)
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)
        super().test_page()


class RemoveLinesTest(TutorialTest):

    page_number = 6

    def test_page(self):
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        # first expand the necessary items
        self._test_hint(digitizer.remove_child.text(0))
        digitizer.tree.expandItem(digitizer.remove_child)
        self._test_hint('remove lines')
        digitizer.tree.expandItem(digitizer.remove_line_child)

        # now remove horizontal lines
        self._test_hint('minimum line')
        digitizer.sp_min_lw.setValue(1)
        self._test_hint(digitizer.btn_remove_hlines.text())
        QTest.mouseClick(digitizer.btn_remove_hlines, Qt.LeftButton)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)

        # and vertical lines
        self._test_hint('Enable')
        digitizer.cb_max_lw.setChecked(True)
        self._test_hint('maximum line')
        digitizer.sp_max_lw.setValue(2)
        self._test_hint('minimum line fraction')
        digitizer.txt_line_fraction.setText('30')
        self._test_hint(digitizer.btn_remove_vlines.text())
        QTest.mouseClick(digitizer.btn_remove_vlines, Qt.LeftButton)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)

        super().test_page()


class DigitizeTest(TutorialTest):

    page_number = 7

    def test_page(self):
        self._test_hint(self.digitizer.btn_digitize.text())
        self.digitizer.digitize()
        super().test_page()


class SamplesTest(TutorialTest):

    page_number = 8

    def test_page(self):
        digitizer = self.digitizer
        sw = self.straditizer_widgets
        self._test_hint(digitizer.edit_samples_child.text(0))
        digitizer.tree.expandItem(digitizer.edit_samples_child)
        self._test_hint(digitizer.btn_find_samples.text())
        QTest.mouseClick(digitizer.btn_find_samples, Qt.LeftButton)
        self._test_hint(digitizer.btn_edit_samples.text())
        QTest.mouseClick(digitizer.btn_edit_samples, Qt.LeftButton)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)

        super().test_page()


class TranslateYAxisTest(TutorialTest):

    page_number = 9

    def test_page(self):
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        self._test_hint(sw.axes_translations_item.text(0))
        digitizer.tree.expandItem(sw.axes_translations_item)
        self._test_hint(sw.axes_translations.btn_marks_for_y.text())

        # Test the 'wrong button' message'
        QTest.mouseClick(self.digitizer.btn_select_data, Qt.LeftButton)
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)
        # Now click the correct button
        QTest.mouseClick(sw.axes_translations.btn_marks_for_y, Qt.LeftButton)
        self._test_hint('vertical axis')
        self.straditizer._new_mark(318, 641, value=200)
        self._test_hint('another')
        self.straditizer._new_mark(308, 777, value=250)
        self._test_hint(sw.apply_button.text())
        QTest.mouseClick(sw.apply_button, Qt.LeftButton)

        super().test_page()


class TranslateXAxisTest(TutorialTest):

    page_number = 10

    def test_page(self):
        sw = self.straditizer_widgets
        digitizer = self.digitizer
        self._test_hint(digitizer.current_reader_item.text(0))
        digitizer.tree.expandItem(digitizer.current_reader_item)
        self._test_hint('new reader')

        # Test the 'wrong button' message'
        QTest.mouseClick(self.digitizer.btn_select_data, Qt.LeftButton)
        self._test_hint('(?i)wrong')
        QTest.mouseClick(sw.cancel_button, Qt.LeftButton)

        # now click the correct button and start with the first column
        QTest.mouseClick(self.digitizer.btn_new_child_reader, Qt.LeftButton)
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

        QTest.mouseClick(sw.axes_translations.btn_marks_for_y, Qt.LeftButton)
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
        QTest.mouseClick(self.digitizer.btn_new_child_reader, Qt.LeftButton)
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

        super().test_page()


class AttributesTest(TutorialTest):

    page_number = 11

    def test_page(self):
        sw = self.straditizer_widgets
        self._test_hint(sw.attrs_button.text())
        QTest.mouseClick(sw.attrs_button, Qt.LeftButton)
        self._test_hint('Add some meta')

        sw.straditizer.attrs.iloc[0, 0] = 'me'

        super().test_page()


class FinishTest(TutorialTest):

    page_number = 12

    def test_page(self):
        self.assertTrue(self.navigation.btn_prev.isEnabled())
        self.assertFalse(self.navigation.btn_hint.isEnabled())
        self.assertFalse(self.navigation.btn_next.isEnabled())
        self.assertFalse(self.navigation.btn_skip.isEnabled())


if __name__ == '__main__':
    unittest.main()
