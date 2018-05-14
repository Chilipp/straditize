"""Test module for the command line implementation of straditize

This module test :mod:`straditize.__main__`"""
import _base_testing as bt
import unittest
import pandas as pd
from straditize.__main__ import start_app, get_parser
from straditize.widgets import get_straditizer_widgets


class CommandLineTest(bt.StraditizeWidgetsTestCase):
    """Test class for the command lines"""

    def setUp(self):
        """Do nothing"""
        self.created_files = set()

    def test_open_image(self, *args, **kwargs):
        fname = self.get_fig_path('basic_diagram.png')
        self.window = start_app(fname, exec_=False, **kwargs)
        self.straditizer_widgets = get_straditizer_widgets(self.window)
        self.assertIsNotNone(self.straditizer)
        self.assertEqual(self.straditizer.image.filename, fname,
                         msg='Image not opened correctly!')

    def test_xlim_ylim(self, *args, **kwargs):
        self.test_open_image(xlim=list(self.data_xlim),
                             ylim=list(self.data_ylim))
        self.assertIsNotNone(self.reader)

    def test_output(self):
        fname = self.get_fig_path('basic_diagram.png')
        temp_file = self.get_random_filename(suffix='.csv')
        parser = get_parser()
        cmd = fname + ' -f -o ' + temp_file
        parser.parse_known2func(cmd.split())
        df = pd.read_csv(temp_file, index_col=0)
        self.assertTrue(len(df))


if __name__ == '__main__':
    unittest.main()
