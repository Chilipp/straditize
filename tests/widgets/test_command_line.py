"""Test module for the command line implementation of straditize

This module test :mod:`straditize.__main__`"""
import _base_testing as bt
import unittest
import pandas as pd
from straditize.__main__ import start_app, get_parser


class CommandLineTest(bt.StraditizeWidgetsTestCase):
    """Test class for the command lines"""

    def test_open_image(self, *args, **kwargs):
        fname = self.get_fig_path('basic_diagram.png')
        old_window = self.window
        self.window = start_app(fname, exec_=False, new_instance=self.window,
                                **kwargs)
        self.assertIs(self.window, old_window)
        self.init_reader()
        self.assertIsNotNone(self.straditizer)
        self.assertEqual(self.straditizer.get_attr('image_file'), fname,
                         msg='Image not opened correctly!')

    def test_xlim_ylim(self, *args, **kwargs):
        return
        self.test_open_image(xlim=list(self.data_xlim),
                             ylim=list(self.data_ylim))
        self.assertIsNotNone(self.reader)

    def test_output(self):
        fname = self.get_fig_path('basic_diagram.png')
        temp_file = self.get_random_filename(suffix='.csv')
        parser = get_parser()
        cmd = fname + ' -ni -f -o ' + temp_file
        parser.parse_known2func(cmd.split())
        df = pd.read_csv(temp_file, index_col=0)
        self.assertTrue(len(df))


if __name__ == '__main__':
    unittest.main()
