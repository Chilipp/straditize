"""Test the straditize.widgets.menu_actions module"""
import numpy as np
import pandas as pd
import os.path as osp
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt
from straditize.colnames import tesserocr


class MenuActionsTest(bt.StraditizeWidgetsTestCase):
    """A test case for testing the menu actions"""

    def test_open_img(self):
        self.open_img()

    def test_save_and_load_01_pickle(self):
        """Test the loading and saving of pickled projects"""
        self._test_save_and_load('.pkl')

    def test_save_and_load_02_netcdf(self):
        """Test the loading and saving of netCDF projects"""
        self._test_save_and_load('.nc')

    def test_save_and_load_03_pickle_bar(self):
        """Test the loading and saving of BarDataReader"""
        self.digitizer.cb_reader_type.setCurrentText('bars')
        old_stradi = self._test_save_and_load('.pkl', 'bar_diagram.png')
        old_reader = old_stradi.data_reader
        self.assertEqual(self.reader._all_indices, old_reader._all_indices)
        self.assertEqual(self.reader._splitted, old_reader._splitted)
        self.assertFrameEqual(self.reader._full_df_orig,
                              old_reader._full_df_orig)

    def test_save_and_load_04_netcdf_bar(self):
        """Test the loading and saving of BarDataReader"""
        self.digitizer.cb_reader_type.setCurrentText('bars')
        old_stradi = self._test_save_and_load('.nc', 'bar_diagram.png')
        old_reader = old_stradi.data_reader
        self.assertEqual(self.reader._all_indices, old_reader._all_indices)
        self.assertEqual(self.reader._splitted, old_reader._splitted)
        self.assertFrameEqual(self.reader._full_df_orig,
                              old_reader._full_df_orig)

    @unittest.skipIf(tesserocr is None, "requires tesserocr")
    def test_save_and_load_05_colnames(self):
        """Test the saving and loading of column names reader"""
        from PIL import Image
        from test_colnames import ColNamesTest
        self.init_reader('colnames_diagram.png', xlim=ColNamesTest.data_xlim,
                         ylim=ColNamesTest.data_ylim)
        self.reader.column_starts = ColNamesTest.column_starts
        self.straditizer.colnames_reader.highres_image = hr_image = Image.open(
            self.get_fig_path('colnames_diagram-colnames.png'))
        sw = self.straditizer_widgets
        sw.refresh()

        if not sw.colnames_manager.is_shown:
            QTest.mouseClick(sw.colnames_manager.btn_select_names,
                             Qt.LeftButton)

        sw.colnames_manager.find_colnames(
            warn=False, full_image=True, all_cols=True)
        colnames = self.straditizer.colnames_reader.column_names
        colpics = self.straditizer.colnames_reader.colpics
        self.assertEqual(colnames[0], 'Charcoal')
        self.assertEqual(colnames[1], 'Pinus')
        self.assertIsNotNone(colpics[0])
        self.assertIsNotNone(colpics[1])

        # save the straditizer
        for ending in ['.pkl', '.nc']:
            fname = self.get_random_filename(suffix=ending)
            sw.menu_actions.save_straditizer_as(fname)

            # load the straditizer
            sw.menu_actions.open_straditizer(fname)

            self.assertEqual(self.straditizer.colnames_reader.column_names,
                             colnames, msg='Ending: ' + ending)
            self.assertArrayEquals(self.straditizer.colnames_reader.colpics[0],
                                   colpics[0], msg='Ending: ' + ending)
            self.assertArrayEquals(self.straditizer.colnames_reader.colpics[1],
                                   colpics[1], msg='Ending: ' + ending)

            self.assertArrayEquals(
                self.straditizer.colnames_reader.image,
                self.straditizer.image, msg='Ending: ' + ending)
            self.assertArrayEquals(
                self.straditizer.colnames_reader.highres_image, hr_image,
                msg='Ending: ' + ending)

    def _test_save_and_load(self, ending, fname='basic_diagram.png'):
        # create a reader with samples
        self.init_reader(fname)
        self.reader.vline_locs = np.array([10])
        self.reader.hline_locs = np.array([10])
        self.reader.digitize()
        self.reader._get_sample_locs()
        self.straditizer_widgets.refresh()
        stradi = self.straditizer
        reader = stradi.data_reader

        # save the straditizer
        fname = self.get_random_filename(suffix=ending)
        self.straditizer_widgets.menu_actions.save_straditizer_as(fname)

        # load the straditizer
        self.straditizer_widgets.menu_actions.open_straditizer(fname)

        # check the loaded straditizer
        self.assertIsNot(self.straditizer, stradi)
        self.assertIsNot(self.reader, reader)
        self.assertFrameEqual(self.reader.sample_locs,
                              reader.sample_locs)
        self.assertEqual(self.reader.column_bounds.tolist(),
                         reader.column_bounds.tolist())
        self.assertFrameEqual(self.reader.full_df,
                              reader.full_df)
        self.assertEqual(list(self.reader.vline_locs),
                         list(reader.vline_locs))
        self.assertEqual(list(self.reader.hline_locs),
                         list(reader.hline_locs))
        return stradi

    def test_save_image(self):
        """Test the saving of the image"""
        self.open_img()
        fname = self.get_random_filename(suffix='.png')
        self.straditizer_widgets.menu_actions.save_full_image(fname)
        self.assertImageEquals(fname, self.straditizer.get_attr('image_file'))

    def test_save_binary_image(self):
        """Test the saving of the binary image"""
        self.init_reader()
        fname = self.get_random_filename(suffix='.png')
        self.straditizer_widgets.menu_actions.save_data_image(fname)
        self.assertImageEquals(
            fname, self.get_fig_path('basic_diagram_binary.png'))

    def test_export_final(self):
        """Test the exporting of the final DataFrame"""
        # create a reader with samples
        self.init_reader()
        self.reader.digitize()
        self.reader._get_sample_locs()
        fname = self.get_random_filename(suffix='.csv')
        self.straditizer_widgets.menu_actions.export_final(fname)
        self.assertTrue(osp.exists(fname), msg=fname + ' is missing!')
        exported = pd.read_csv(fname, index_col=0, comment='#')
        self.assertFrameEqual(exported, self.straditizer.final_df)

    def test_export_full_df(self):
        """Test the exporting of the final DataFrame"""
        # create a reader with samples
        self.init_reader()
        self.reader.digitize()
        fname = self.get_random_filename(suffix='.csv')
        self.straditizer_widgets.menu_actions.export_full(fname)
        self.assertTrue(osp.exists(fname), msg=fname + ' is missing!')
        exported = pd.read_csv(fname, index_col=0, comment='#')
        self.assertFrameEqual(exported, self.straditizer.full_df)


if __name__ == '__main__':
    unittest.main()
