# -*- coding: utf-8 -*-
"""
Test module for the :mod:`straditize.binary` module
"""
import six
import unittest
from itertools import chain, starmap
import numpy as np
from straditize import binary
import pandas as pd
import create_test_sample as ct
import matplotlib as mpl

mpl.use('module://psyplot_gui.backend')


class AlmostArrayEqualMixin(object):

    def assertAlmostArrayEqual(self, actual, desired, rtol=1e-07, atol=0,
                               msg=None, **kwargs):
        """Asserts that the two given arrays are almost the same

        This method uses the :func:`numpy.testing.assert_allclose` function
        to compare the two given arrays.

        Parameters
        ----------
        actual : array_like
            Array obtained.
        desired : array_like
            Array desired.
        rtol : float, optional
            Relative tolerance.
        atol : float, optional
            Absolute tolerance.
        equal_nan : bool, optional.
            If True, NaNs will compare equal.
        err_msg : str, optional
            The error message to be printed in case of failure.
        verbose : bool, optional
            If True, the conflicting values are appended to the error message.
        """
        try:
            np.testing.assert_allclose(actual, desired, rtol=rtol, atol=atol,
                                       err_msg=msg or '', **kwargs)
        except (Exception, AssertionError) as e:
            self.fail(e if six.PY3 else e.message)


class DataReaderTest(unittest.TestCase, AlmostArrayEqualMixin):

    def setUp(self, seed=1234, plot=True):
        if seed is not None:
            np.random.seed(seed)
        self.sample = ct.TestSample.from_random(400, 400, 10, 20)
        self.reader = binary.DataReader(self.sample.get_binary(), plot=plot)

    def tearDown(self):
        import matplotlib.pyplot as plt
        plt.close('all')
        del self.sample, self.reader

    nsamples = 2

    def test_column_bounds(self):
        """Test whether the column bounds are identified correctly
        """
        reader = self.reader
        reader._get_column_starts()
        col_starts = self.sample.col_starts
        self.assertEqual(len(reader.column_bounds[:, 0]), len(col_starts),
                         msg='bounds: %s\nref: %s' % (reader.column_starts,
                                                      col_starts))
        self.assertTrue(
            np.all(reader.column_starts <= col_starts),
            msg=("Reader:  %s\n"
                 "Data:    %s\n"
                 "Smaller: %s\n") % (
                    reader.column_starts, col_starts,
                    reader.column_starts <= col_starts))

    def test_find_potential_samples(self):
        """Test whether the extrema are found correctly"""
        reader = self.reader
        df = self.sample.df
        col = df[1]
        minima_mask = np.r_[[False], (col.values[1:-1] < col.values[2:]) & (
            col.values[1:-1] < col.values[:-2]), [False]]
        maxima_mask = np.r_[[False], (col.values[1:-1] > col.values[2:]) & (
            col.values[1:-1] > col.values[:-2]), [False]]
        extrema = sorted(col.index.values[minima_mask | maxima_mask])
        reader.digitize()
        reader_extrema = list(starmap(
            np.arange, reader.find_potential_samples(1)[0]))
        flattened = sorted(chain.from_iterable(reader_extrema))
        self.assertEqual(len(reader_extrema), len(extrema),
                         msg='\nEstimated: %s\nReference: %s' % (
                            reader_extrema, extrema))
        for i, (ext, possibilities) in enumerate(zip(extrema, reader_extrema)):
            self.assertIn(ext, possibilities)
        self.assertLessEqual(
            set(extrema), set(flattened),
            msg=('\nReader:  %s\n'
                 'Data:    %s\n'
                 'missing: %s') % (
                    reader_extrema, extrema,
                    sorted(set(extrema) - set(flattened))))

    def test_obstacle_01_alternation_min(self):
        """Test whether the alternation is identified correctly in a minimum"""
        # a looks like
        #     /            _   /
        #    / \         _/ \ /
        #   /  \  _ _   /   \/
        # _/   \__ _ __/
        #
        a = np.array([
            1, 1, 2, 3, 4, 5,     # 0-6: increase
            3, 2,                 # 6-8: decrease
            1, 1, 2, 1, 2, 1, 1,  # 8-15: alternation
            2, 3, 3, 4, 4,        # 15-20: increase
            3, 2,                 # 20-22: decrease
            3, 4, 5               # 22-25: increase
            ])
        self.reader.columns = [0]
        self.reader._full_df = pd.DataFrame(a[:, np.newaxis])
        extrema, excluded = self.reader.find_potential_samples(0)
        # this should now give the following extrema
        reference = [
            [5, 6],       # maximum at 5
            [8, 15],      # minimum at 1
            [18, 20],     # maximum at 4
            [21, 22]      # minimum at 2
            ]
        self.assertEqual(extrema, reference)
        # excluded should be between the obstacles
        # the middle will be included because of a slope change
        ref_excluded = [[8, 10], [13, 15]]
        self.assertEqual(excluded, ref_excluded)

    def test_obstacle_02_alternation_max(self):
        """Test whether the alternation is identified correctly in a maximum"""
        # a looks like
        #         _  __
        # \      _ __  __
        #  \    /        \
        #   \  /          \   /\
        #    \/            \_/  \
        #
        a = np.array([
            5, 4, 3, 2, 1,           # 0-5: decrease
            2, 3, 4,                 # 5-8: increase
            4, 5, 4, 4, 5, 5, 4, 4,  # 8-16: alternation
            3, 2, 1, 1,              # 16-20: decrease
            2, 3,                    # 20-22: increase
            2, 1                     # 22-24: decrease
            ])
        self.reader.columns = [0]
        self.reader._full_df = pd.DataFrame(a[:, np.newaxis])
        extrema, excluded = self.reader.find_potential_samples(0)
        reference = [
            [4, 5],      # minimum at 1
            [7, 16],     # maximum at 4
            [18, 20],    # minimum at
            [21, 22]     # maximum at 3
            ]
        self.assertEqual(extrema, reference)
        # excluded should be the maxima of the obstacles
        # the middle will be included because of a slope change
        ref_excluded = [[9, 10], [12, 14]]
        self.assertEqual(excluded, ref_excluded)

    def test_obstacle_03_wrong_slope_up(self):
        """Test whether obstacles in an upward slope can be identified"""
        # a looks like
        #         /\
        #        /  \    /
        #       /|   \  /
        #      /      \/
        #     /|_
        # \__/
        a = np.array([
            2, 1, 1,     # 0-3: decrease
            1, 2, 3,     # 3-6: increase
            2, 2,        # 6-8: obstacle
            3, 4, 5,     # 8-11: increase
            4,           # 11-12: obstacle
            6, 7,        # 12-14: maximum
            6, 5, 4, 3,  # 14-18: decrease
            4, 5, 6      # 18-21: increase
            ])
        self.reader.columns = [0]
        self.reader._full_df = pd.DataFrame(a[:, np.newaxis])
        extrema, excluded = self.reader.find_potential_samples(0)
        reference = [
            [1, 4],
            [13, 14],   # maximum at 7
            [17, 18],   # minimum at 3
            ]
        self.assertEqual(extrema, reference)
        # excluded should be the top of the obstacles and their surroundings
        # the middle will be included because of a slope change
        ref_excluded = [[5, 6], [6, 8], [10, 11], [11, 12]]
        self.assertEqual(excluded, ref_excluded)

    def test_obstacle_04_wrong_slope_down(self):
        """Test whether obstacles in an downward slope can be identified"""
        # a looks like
        #   _
        #  / \
        # /   \
        #      |
        #      |_\     /\
        #         \   /  \
        #          \_/
        a = np.array([
            5, 6, 7, 7,     # 0-4: increase
            6, 5,           # 4-6: decrease
            3,              # 6-7: obstacle
            4, 3, 2, 1, 1,  # 7-12: decrease
            2, 3, 4,        # 12-15: increase
            3, 2            # 15-17: decrease
            ])
        self.reader.columns = [0]
        self.reader._full_df = pd.DataFrame(a[:, np.newaxis])
        extrema, excluded = self.reader.find_potential_samples(0)
        reference = [
            [2, 4],    # maximum at 7
            [10, 12],  # minimum at 1
            [14, 15]   # maximum at 4
            ]
        self.assertEqual(extrema, reference)
        # excluded should be the bottom of the obstacles and their surrounding
        # the middle will be included because of a slope change
        ref_excluded = [[6, 7], [7, 8]]
        self.assertEqual(excluded, ref_excluded)

    def test_find_samples(self, fail_fast=False):
        """Test the finding and alignment of samples

        This computationally rather intense test method tests, whether we are
        able to find samples. We do not expect our software to exactly
        reproduce the samples because there are several challenges to it:

        1. potential samples (i.e. extrema) might be spread out over quite
           a long distance
        2. the exact location of the sample might vary by some pixels
        3. when encountering a 0, it is sometimes difficult to merge it exactly
           with the other columns.

        Parameters
        ----------
        fail_fast: bool
            If True, fail immediately after the first, otherwise fail after
            more than two wrong sample reconstructions
        """
        def test():
            self.reader.digitize()
            ref = self.sample.df.index
            samples = self.reader.find_samples(max_len=6, pixel_tol=2)[0].index
            self.assertAlmostArrayEqual(
                ref.shape, samples.shape, atol=2,
                msg='Failed at iteration %i' % i)
            missing = []
            for m in ref:
                if np.abs(samples-m).min() > 4:
                    missing.append(m)
            if len(missing) > 1:
                msg = 'Failed at iteration %i. %s not found in %s' % (
                    i, missing, samples)
                if fail_fast:
                    self.fail(msg)
                else:
                    failed.append(msg)
                if len(failed) > 2:
                    self.fail('Failed in too many iterations!\n' +
                              '\n'.join(failed))
        i = 0
        test()
        failed = []
        for i in range(1, self.nsamples):
            self.tearDown()
            self.setUp(seed=None, plot=False)
            test()


if __name__ == '__main__':
    unittest.main()
