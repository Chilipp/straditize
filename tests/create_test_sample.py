# -*- coding: utf-8 -*-
"""Create a test sample"""
import os.path as osp
import numpy as np
import pandas as pd


def get_numbers(n, summed=100):
    a = np.random.random(n)
    a *= summed / a.sum()
    ret = np.round(a).astype(int)
    dev = ret.sum() - summed
    if dev < 0:
        for i in range(-dev):
            ret[np.random.randint(0, n - 1)] += 1
    elif dev > 0:
        for i in range(dev):
            ret[np.random.randint(0, n - 1)] -= 1
    return ret


class TestSample(object):
    """A test sample

    See the :meth:`from_random` method for a random generation of a new
    :class:`TestSample`."""

    def __init__(self, df, full_df, col_starts=None, col_ends=None,
                 width=None):
        self.df = df
        self.full_df = full_df
        self.width = width
        if col_starts is None:
            self.estimate_col_starts()
        else:
            self.col_starts = col_starts
            self.col_ends = col_ends

    def get_binary(self, border=0, width=None):
        height = len(self.full_df)
        width = width or self.width
        values = self.full_df.values
        if not width:
            width = self.col_starts[-1] + values[:, -1].max() + 5
            self.width = width
        # init the binary image
        im_array = np.zeros((height + border * 2, width + border * 2),
                            dtype=int)
        if values.ndim == 1:
            values = np.reshape(values, (len(values), 1))
        col_starts = self.col_starts + border
        for row in range(height):
            for col, col_val in enumerate(values[row]):
                im_array[row + border,
                         col_starts[col]:col_starts[col] + col_val] = 1
        return im_array

    def estimate_col_starts(self):
        col_bounds = np.concatenate([[0], self.full_df.values.max(axis=0) + 5])
        col_bounds = col_bounds.cumsum()
        self.col_starts = col_bounds[:-1]
        self.col_ends = col_bounds[1:]

    def get_rgba(self, color=[0, 0, 0], *args, **kwargs):
        arr = np.tile(self.get_binary(*args, **kwargs)[..., np.newaxis],
                      (1, 1, 4)).astype(np.uint8)
        arr[..., -1] *= 255
        arr[..., :3] = np.asarray(color, np.uint8)[np.newaxis, np.newaxis]
        return arr

    def get_rgba_image(self, *args, **kwargs):
        from PIL import Image
        arr = self.get_rgba(*args, **kwargs)
        return Image.fromarray(arr, 'RGBA')

    @classmethod
    def from_random(cls, height, width, ncols, nsamples, mindiff=3):
        """Create a new :class:`TestSample` instance by randomly generating
        values"""
        vals = np.zeros((nsamples, ncols), dtype=int)
        maxvals = np.zeros(ncols, dtype=int)
        summed_cols = width - ncols * 2  # the widths of all columns summed up
        summed_row = np.int(width * 2 / 3.) - ncols * 2  # the sum for each row
        minval = 0.01 * summed_row  # at minimum we need 1 for each column
        while (maxvals < minval).any():
            maxvals[:] = get_numbers(ncols, summed_cols)
        for i in range(nsamples):
            # generate a series of random numbers that sum up to
            # width - ncols * 2 such that we can have two lines between each
            # column
            vals[i, :] = get_numbers(ncols, summed_row)
            while (vals[i, :] > maxvals).any():
                vals[i, :] = get_numbers(ncols, summed_row)
        samples = np.zeros(nsamples, dtype=int)
        while np.any(samples[1:] - samples[:-1] < mindiff):
            samples = np.sort(np.r_[
                [0],
                np.random.permutation(height)[:nsamples - 2],
                [height - 1]])
        df = pd.DataFrame(vals, index=pd.Index(samples, name='height'),
                          columns=np.arange(ncols))
        interpolated = np.zeros((height, ncols), dtype=int)
        for i in np.arange(ncols):
            interpolated[:, i] = np.round(np.interp(
                np.arange(height), df.index.values, df[i].values))
        full_df = pd.DataFrame(interpolated, index=pd.Index(np.arange(height)),
                               columns=np.arange(ncols))
        #: The starting points of the columns
        col_starts = np.concatenate([[0], maxvals[:-1] + 2])
        col_starts = col_starts.cumsum()
        col_ends = maxvals.cumsum()
        col_ends[1:] += np.cumsum(np.ones(ncols - 1, dtype=int) * 2)
        return cls(df, full_df, col_starts, col_ends, width)

    def export(self, dirname='.', base=''):
        """Export the dataframes and arrays associated with this sample

        This saves the attributes of this sample into different files, namely

        data.csv
            containing the :attr:`df` DataFrame
        full_data.csv
            containing the :attr:`full_df` DataFrame
        column_bounds.dat
            containing the :attr:`column_starts` and :attr:`column_ends` arrays


        Parameters
        ----------
        dirname: str
            The path of the output directory
        base: str
            The base string for the files. It will then be prepended to the
            filenames listed above

        Returns
        -------
        str
            The file name for the :attr:`df` attribute
            (``dirname + '/' + base + 'data.csv'``)
        str
            The file name for the :attr:`full_df` attribute
            (``dirname + '/' + base + 'full_data.csv'``)
        str
            The file name for the column bounds
            (``dirname + '/' + base + 'column_bounds.dat'``)

        See Also
        --------
        from_files: A constructor of the :class:`TestSample` from the files
        exported by this method"""
        df_file = osp.join(dirname, base + 'data.csv')
        full_df_file = osp.join(dirname, base + 'full_data.csv')
        bounds_file = osp.join(dirname, base + 'column_bounds.dat')
        self.df.to_csv(df_file)
        self.full_df.to_csv(full_df_file)
        np.savetxt(
            bounds_file,
            np.vstack([self.col_starts, self.col_ends]).T, fmt='%i')
        return df_file, full_df_file, bounds_file

    @classmethod
    def from_files(cls, df_file, full_df_file, bounds_file=None, *args,
                   **kwargs):
        df = pd.read_csv(df_file, index_col=0)
        full_df = pd.read_csv(full_df_file, index_col=0)
        if bounds_file is not None:
            bounds = np.loadtxt(bounds_file, dtype=int)
            col_starts = bounds[:, 0]
            col_ends = bounds[:, 1]
            args = (col_starts, col_ends) + args
        return cls(df, full_df, *args, **kwargs)
