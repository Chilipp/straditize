"""Test module for straditize.widgets.colnames"""

import _base_testing as bt
import numpy as np
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt
from straditize.colnames import tesserocr
from PIL import Image


class ColNamesTest(bt.StraditizeWidgetsTestCase):
    """Test for managing column names"""

    data_xlim = np.array([73., 526.])

    data_ylim = np.array([48., 386.])

    column_starts = np.array([0,  50, 229, 333, 359, 383, 407])

    column_ends = np.array([50, 229, 333, 359, 383, 407, 455])

    @property
    def colnames_reader(self):
        return self.straditizer.colnames_reader

    @property
    def colnames_manager(self):
        return self.straditizer_widgets.colnames_manager

    def init_reader(self, fname='colnames_diagram.png', *args, **kwargs):
        return super().init_reader(fname, *args, **kwargs)

    def init_colnames_reader(self, *args, **kwargs):
        self.init_reader(*args, **kwargs)
        self.reader.column_starts = self.column_starts
        self.reader.column_ends = self.column_ends
        reader = self.straditizer.colnames_reader
        reader.highres_image = Image.open(
            self.get_fig_path('colnames_diagram-colnames.png'))
        return reader

    @unittest.skipIf(tesserocr is None, "requires tesserocr")
    def test_find_all_column_names(self):
        sw = self.straditizer_widgets
        reader = self.init_colnames_reader()
        sw.refresh()
        if not sw.colnames_manager.is_shown:
            QTest.mouseClick(sw.colnames_manager.btn_select_names,
                             Qt.LeftButton)

        self.assertTrue(sw.colnames_manager.is_shown)
        sw.colnames_manager.cb_find_all_cols.setChecked(True)

        self.assertIsNone(sw.colnames_manager.find_colnames(warn=False,
                                                            full_image=True))

        # test whether we found all column names (but Juniperus which has been
        # removed from the HR image), whether they are correct or
        # not...
        self.assertEqual(
            set(map(str.lower, reader.column_names)).intersection(
                map(str, range(len(reader.column_names)))), {'2'})

    @unittest.skipIf(tesserocr is None, "requires tesserocr")
    def test_find_one_column_name(self):
        sw = self.straditizer_widgets
        reader = self.init_colnames_reader()
        sw.refresh()
        if not sw.colnames_manager.is_shown:
            QTest.mouseClick(sw.colnames_manager.btn_select_names,
                             Qt.LeftButton)

        self.assertTrue(sw.colnames_manager.is_shown)
        sw.colnames_manager.colnames_table.item(1, 0).setSelected(True)
        self.assertTrue(sw.colnames_manager.btn_select_colpic.isEnabled())

        QTest.mouseClick(sw.colnames_manager.btn_select_colpic, Qt.LeftButton)
        self.assertIsNone(sw.colnames_manager.find_colnames(warn=False,
                                                            full_image=True))

        self.assertEqual(
            list(reader.column_names), ['0', 'Pinus'] + list('23456'))
        QTest.mouseClick(sw.colnames_manager.btn_cancel_colpic_selection,
                         Qt.LeftButton)

    @unittest.skipIf(tesserocr is None, "requires tesserocr")
    def test_recognize(self):
        sw = self.straditizer_widgets
        reader = self.init_colnames_reader()
        reader.colpics
        colpic = Image.open(self.get_fig_path('colnames_diagram-Pinus.png'))
        reader._colpics[1] = colpic

        sw.refresh()
        if not sw.colnames_manager.is_shown:
            QTest.mouseClick(sw.colnames_manager.btn_select_names,
                             Qt.LeftButton)

        self.assertTrue(sw.colnames_manager.is_shown)
        sw.colnames_manager.colnames_table.item(1, 0).setSelected(True)
        self.assertIs(sw.colnames_manager.colpic, colpic)

        name = sw.colnames_manager.read_colpic()
        self.assertEqual(name, 'Pinus')

        self.assertEqual(
            list(self.colnames_reader.column_names),
            ['0', 'Pinus'] + list('23456'))

    def test_flip(self):
        reader = self.init_colnames_reader()
        self.colnames_manager.rotate(0)
        self.colnames_manager.flip(Qt.Checked)
        self.assertTrue(reader.flip)
        self.assertArrayEquals(reader.rotated_image,
                               np.asarray(reader.image)[::-1])

    def test_mirror(self):
        reader = self.init_colnames_reader()
        self.colnames_manager.rotate(0)
        self.colnames_manager.mirror(Qt.Checked)
        self.assertTrue(reader.mirror)
        self.assertArrayEquals(reader.rotated_image,
                               np.asarray(reader.image)[:, ::-1])

    @unittest.skipIf(tesserocr is None, "requires tesserocr")
    def test_colpic_selector(self):
        self.init_colnames_reader()
        sw = self.straditizer_widgets
        sw.refresh()
        if not sw.colnames_manager.is_shown:
            QTest.mouseClick(sw.colnames_manager.btn_select_names,
                             Qt.LeftButton)

        self.assertTrue(sw.colnames_manager.is_shown)
        sw.colnames_manager.colnames_table.item(1, 0).setSelected(True)
        self.assertTrue(sw.colnames_manager.btn_select_colpic.isEnabled())

        QTest.mouseClick(sw.colnames_manager.btn_select_colpic, Qt.LeftButton)
        self.colnames_manager.selector.extents = (361, 378, 117, 123)
        self.colnames_manager.update_image()
        self.assertEqual(self.colnames_manager.colpic_im.get_size(), (72, 204))


if __name__ == '__main__':
    unittest.main()
