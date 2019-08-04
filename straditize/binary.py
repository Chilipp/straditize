# -*- coding: utf-8 -*-
"""A module to read in and digitize the pollen diagram

**Disclaimer**

Copyright (C) 2018-2019  Philipp S. Sommer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import skimage.morphology as skim
from warnings import warn
import numpy as np
import six
import pandas as pd
from functools import wraps
from itertools import chain, starmap, repeat, takewhile
from collections import defaultdict
import matplotlib.colors as mcol
from straditize.common import docstrings
from straditize.label_selection import LabelSelection
import xarray as xr
from psyplot.data import safe_list

if six.PY2:
    from itertools import izip_longest as zip_longest
else:
    from itertools import zip_longest


def only_parent(func):
    """Call the given `func` only from the parent reader"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.parent is not self:
            return getattr(self.parent, func.__name__)(*args, **kwargs)
        return func(self, *args, **kwargs)
    return wrapper


def groupby_arr(arr):
    """Groupby a boolean array

    Parameters
    ----------
    arr: np.ndarray of ndim 1 of dtype bool
        An array that can be converted to a numeric array

    Returns
    -------
    keys: np.ndarrayrdi
        The keys in the array
    starts: np.ndarray
        The index of the first element that correspond to the key in `keys`"""
    diff = np.ones_like(arr)
    diff[1:] = np.diff(arr)
    idx = np.where(diff.astype(bool))
    keys = arr[idx]
    bounds = np.r_[[0], np.diff(idx).cumsum(), [len(arr)]]
    return keys, bounds


class DataReader(LabelSelection):
    """A class to read in and digitize the data files of the pollen diagram

    The source image is stored in the :attr:`image` attribute, the binary
    array of it is stored in the :attr:`binary` attribute. A labeled version
    created by the :func:`skimage.morphology.label` function, is stored in the
    :attr:`labels` attribute and can regenerated using the :meth:`reset_labels`
    method.

    Subclasses of this class should reimplement the :meth:`digitize` method
    that digitizes the diagram, and the :meth:`find_potential_samples` method.

    There is always one parent reader stored in the :attr:`parent` attribute.
    This is then the reader that is accessible through the
    :attr:`straditize.straditizer.Straditizer.data_reader` attribute and holds
    the references to other readers in it's :attr:`children` attribute"""

    #: PIL.Image.Image of the diagram part with mode RGBA
    image = None

    #: A 2D numpy array representing the binary version of the :attr:`image`
    binary = None

    #: A connectivity-based labeled version of the :attr:`binary` data
    labels = None

    #: The full dataframe of the digitized image
    _full_df = None

    #: the matplotlib image artist
    plot_im = None

    #: magnified :attr:`plot_im`
    magni_plot_im = None

    magni_color_plot_im = None

    #: the :class:`straditize.magnifier.Magnifier` for the :attr:`ax`
    magni = None

    _sample_locs = None

    _occurences = set()

    @property
    def occurences(self):
        """A set of tuples marking the position of an occurence

        An occurence, motivated by pollen diagrams, just highlights the
        existence at a certain point without giving the exact value. In pollen
        diagrams, these are usually taxa that were found but have a percentage
        of less than 0.5 %.

        This set of tuples (x, y) contains the coordinates of the occurences.
        The first value in each tuple is the y-value, the second the x-value.

        See Also
        --------
        occurences_dict: A mapping from column number to occurences"""
        return self.parent._occurences

    @occurences.setter
    def occurences(self, value):
        self.parent._occurences = value

    #: The value that is given to the occurences in the measurements
    occurences_value = -9999

    @property
    def occurences_dict(self):
        """A mapping from column number to an numpy array with the indices of
        an occurence"""
        def get_col(x):
            return next(i for i, (s, e) in enumerate(bounds)
                        if s <= x and e > x)
        ret = defaultdict(list)
        bounds = self.all_column_bounds
        for x, y in self.occurences:
            ret[get_col(x)].append(y)
        return {col: np.unique(indices) for col, indices in ret.items()}

    @property
    def sample_locs(self):
        """
        The :class:`pandas.DataFrame` with locations and values of the
        samples"""
        if self.parent._sample_locs is not None:
            return self.parent._sample_locs
        elif self.parent._full_df is not None:
            self.parent._sample_locs = pd.DataFrame(
                [], columns=list(self.parent._full_df.columns))
            return self.parent._sample_locs

    @sample_locs.setter
    def sample_locs(self, value):
        """
        The :class:`pandas.DataFrame` with locations and values of the
        samples"""
        self.parent._sample_locs = value

    _rough_locs = None

    @property
    def rough_locs(self):
        """
        The :class:`pandas.DataFrame` with rough locations for the samples.
        It has one row per sample in the :attr:`sample_locs` dataframe and
        ``ncols * 2`` columns, where ``ncols`` is the number of columns
        in the :attr:`sample_locs`.

        If the potential sample :attr:`sample_locs`\ ``.iloc[i, col]`` ranges
        ``j`` to ``k`` (see the :meth:`find_potential_samples` method), the
        cell at ``rough_locs.iloc[i, col * 2]`` specifies the first y-pixel
        (``j``) and ``rough_locs.iloc[i, col * 2 + 1]`` the last y-pixel (+1),
        i.e. ``k`` where this sample might be located"""
        if self.parent._rough_locs is not None:
            return self.parent._rough_locs
        elif self.sample_locs is not None:
            self.parent._update_rough_locs()
            return self.parent._rough_locs

    @rough_locs.setter
    def rough_locs(self, value):
        """
        The :class:`pandas.DataFrame` with rough locations for the samples.
        It has one row per sample in the :attr:`sample_locs` dataframe and
        ``ncols * 2`` columns, where ``ncols`` is the number of columns
        in the :attr:`sample_locs`.

        If the potential sample :attr:`sample_locs`\ ``.iloc[i, col]`` ranges
        ``j`` to ``k`` (see the :meth:`find_potential_samples` method), the
        cell at ``rough_locs.iloc[i, col * 2]`` specifies the first y-pixel
        (``j``) and ``rough_locs.iloc[i, col * 2 + 1]`` the last y-pixel (+1),
        i.e. ``k`` where this sample might be located"""
        self._rough_locs = value

    #: the starts for each column
    _column_starts = None

    @property
    def column_starts(self):
        """1D numpy array with the starts for each column of this reader

        See Also
        --------
        column_ends: The ends for each column
        column_bounds: The (start, end)-tuple for each of the columns
        all_column_starts: The starts for all columns, including child
        reader"""
        starts = self.parent._column_starts
        if starts is None or self.columns is None:
            return starts
        else:
            return starts[self.columns]

    @column_starts.setter
    def column_starts(self, value):
        """1D numpy array with the starts for each column of this reader

        See Also
        --------
        all_column_starts: The starts for all columns, including child
        reader"""
        if self.parent._column_starts is None or self.columns is None:
            self.parent._column_starts = value
        else:
            self.parent._column_starts[self.columns] = value

    #: the starts for each column
    _column_ends = None

    @property
    def column_ends(self):
        """1D numpy array with the ends for each column of this reader

        See Also
        --------
        column_starts: The starts for each column
        column_bounds: The (start, end)-tuple for each of the columns
        all_column_ends: The ends for all columns, including child
        reader"""
        ends = self.parent._column_ends
        if ends is None and self.parent._column_starts is not None:
            ends = np.r_[self.parent._column_starts[1:],
                         [self.binary.shape[1]]]
        if ends is None or self.columns is None:
            return ends
        else:
            return ends[self.columns]

    @column_ends.setter
    def column_ends(self, value):
        """1D numpy array with the ends for each column of this reader

        See Also
        --------
        column_starts: The starts for each column
        column_bounds: The (start, end)-tuple for each of the columns
        all_column_ends: The ends for all columns, including child
        reader"""
        parent = self.parent
        all_columns = np.unique(np.concatenate(
            [child.columns for child in self.iter_all_readers]))
        if len(value) == len(all_columns):
            parent._column_ends = value
        elif parent.columns is None:
            parent._column_ends = value
        elif self.columns is None:
            raise ValueError(
                "The columns for this reader have not yet been defined!")
        elif len(value) == len(self.columns):
            parent._column_ends[self.columns] = value
        else:
            raise ValueError(
                "Length of the columns (%i) do not match the number of "
                "columns of the reader (%i) nor the total number of columns "
                "(%i)!" % (len(value), len(all_columns), len(self.columns)))

    @property
    def all_column_ends(self):
        """1D numpy array with the ends for all column (including child reader)

        See Also
        --------
        all_column_starts: The starts for all column
        all_column_bounds: The (start, end)-tuple for all of the columns
        column_ends: The ends for this specific reader
        reader"""
        ends = self.parent._column_ends
        if ends is None and self.parent._column_starts is not None:
            ends = np.r_[self.parent._column_starts[1:],
                         [self.binary.shape[1]]]
        return ends

    @all_column_ends.setter
    def all_column_ends(self, value):
        """1D numpy array with the ends for all column (including child reader)

        See Also
        --------
        all_column_starts: The starts for all column
        all_column_bounds: The (start, end)-tuple for all of the columns
        column_ends: The ends for this specific reader
        reader"""
        self.parent._column_ends = value

    @property
    def all_column_starts(self):
        """1D numpy array with the ends for all column (including child reader)

        See Also
        --------
        all_column_ends: The ends for all column
        all_column_bounds: The (start, end)-tuple for all of the columns
        column_starts: The starts for this specific reader
        reader"""
        return self.parent._column_starts

    @all_column_starts.setter
    def all_column_starts(self, value):
        """1D numpy array with the ends for all column (including child reader)

        See Also
        --------
        all_column_ends: The ends for all column
        all_column_bounds: The (start, end)-tuple for all of the columns
        column_starts: The starts for this specific reader
        reader"""
        self.parent._column_starts = value

    #: :class:`list` or floats. The indexes of horizontal lines
    hline_locs = None

    #: :class:`list` or floats. The indexes of vertical lines
    vline_locs = None

    #: The matplotlib axes where the :attr:`plot_im` is plotted on
    ax = None

    #: The number of pixels the columns have been shifted
    shifted = None

    #: The minimum fraction of overlap for two bars to be considered as the
    #: same sample (see :meth:`unique_bars`)
    min_fract = 0.9

    #: a boolean flag that shall indicate if we assume that the first and last
    #: rows shall be a sample if they contain non-zero values
    samples_at_boundaries = True

    #: Child readers for specific columns. Is not empty if and only if the
    #: :attr:`parent` attribute is this instance
    children = []

    #: Parent reader for this instance. Might be the instance itself
    parent = None

    #: The columns that are handled by this reader
    _columns = []

    #: White rectangle that represents the background of the binary image.
    #: This is only plotted by the parent reader
    background = None

    #: White rectangle that represents the background of the binary image in
    #: the magnifier. This is only plotted by the parent reader
    magni_background = None

    #: Exaggeration factor that is not 0 if this reader represents exaggeration
    #: plots
    is_exaggerated = 0

    #: An alternative function to the class constructor to load the data reader
    _loader = None

    @property
    def full_df(self):
        """The full :class:`pandas.DataFrame` of the digitized image"""
        if self.parent._full_df is None:
            return None
        return self.parent._full_df.loc[:, self.columns]

    @full_df.setter
    def full_df(self, value):
        """The full :class:`pandas.DataFrame` of the digitized image"""
        parent = self.parent
        if parent._full_df is None:
            all_columns = np.unique(
                np.concatenate(
                    [child.columns for child in [parent] + parent.children]))
            index = np.arange(self.binary.shape[0])
            vals = np.zeros((len(index), len(all_columns)))
            parent._full_df = pd.DataFrame(vals, columns=all_columns,
                                           index=index)
        parent._full_df.loc[:, self.columns] = np.asarray(value)

    @property
    def columns(self):
        """The indices of the columns that are handled by this reader"""
        if not self._columns:
            if self._column_starts is not None:
                ret = list(range(len(self._column_starts)))
                self._columns = ret
            else:
                ret = None
            return ret
        else:
            return self._columns

    @columns.setter
    def columns(self, value):
        """The indices of the columns that are handled by this reader"""
        self._columns = value

    @property
    def extent(self):
        """The extent of the :attr:`plot_im`"""
        if self._extent is not None:
            return self._extent
        return [0] + list(self.binary.shape)[::-1] + [0]

    @extent.setter
    def extent(self, value):
        """The extent of the :attr:`plot_im`"""
        self._extent = value

    @property
    def fig(self):
        """The matplotlib figure of the :attr:`ax`"""
        return getattr(self.ax, 'figure')

    @property
    def num_labels(self):
        """The maximum label in the :attr:`labels` array"""
        return self.labels.max()

    label_arrs = ['binary', 'labels', 'image_array']

    @docstrings.get_sectionsf('DataReader')
    def __init__(self, image, ax=None, extent=None,
                 plot=True, children=[], parent=None, magni=None,
                 plot_background=False, binary=None):
        """
        Parameters
        ----------
        image: PIL.Image.Image
            The image of the diagram
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on
        extent: list
            List of four number specifying the extent of the image in it's
            source. This extent will be used for the call of
            :func:`matplotlib.pyplot.imshow`
        children: list of :class:`DataReader`
            Child readers for other columns in case the newly created instance
            is the parent reader
        parent: :class:`DataReader`
            The parent reader.
        magni: straditize.magnifier.Magnifier
            The magnifier for the given `ax`
        plot_background: bool
            If True (and `plot` is True), a white, opaque are is plotted below
            the :attr:`plot_im`
        binary: None
            The binary version of the given `image`. If not provided, the
            :meth:`to_binary_pil` method is used with the given `image`
        """
        from PIL import Image
        if binary is not None:
            self.binary = binary
        if np.ndim(image) == 2:
            if binary is None:
                self.binary = np.asarray(image, dtype=np.int8)
            image = np.tile(
                image[..., np.newaxis].astype(np.int8), (1, 1, 4)) * 255
            image[..., -1] = 255
        elif binary is None:
                self.binary = self.to_binary_pil(image)

        try:
            mode = image.mode
        except AttributeError:
            image = Image.fromarray(image, mode='RGBA')
        else:
            if mode != 'RGBA':
                image = image.convert('RGBA')
        self.image = image
        self._occurences = set()
        self.reset_labels()
        self.lines = []
        self.sample_ranges = []
        self.ax = ax
        self._extent = extent
        self.hline_locs = np.empty(0, int)
        self.vline_locs = np.empty(0, int)
        self.magni = magni
        if plot_background:
            self.plot_background()
        if plot:
            self.plot_image()

        self.remove_callbacks = {'labels': [self.update_image]}
        if np.ndim(image) == 3:
            self.remove_callbacks['image_array'] = [self.update_rgba_image]
        self.children = list(children)
        for child in children:
            child.parent = self
        self.parent = parent or self

    def reset_image(self, image, binary=False):
        """Reset the image for this straditizer

        Parameters
        ----------
        image: PIL.Image.Image
            The new image
        binary: bool
            If True, then the `image` is considered as the binary image and
            the :attr:`image` attribute is not touched"""
        from PIL import Image
        if np.ndim(image) == 2:
            self.binary = np.array(image, dtype=np.int8)
        else:
            try:
                mode = image.mode
            except AttributeError:
                image = Image.fromarray(image, mode='RGBA')
            else:
                if mode != 'RGBA':
                    image = image.convert('RGBA')

            if not binary:
                self.image = image
            self.binary = self.to_binary_pil(image)
            self.reset_labels()
            if self.plot_im is not None:
                self.update_image(None, None)
                self.draw_figure()

    def reset_labels(self):
        """Reset the :attr:`labels` array"""
        self.labels = self.get_labeled_array()

    def _get_column_starts(self, threshold=None):
        """Return the column starts and estimate them if necessary"""
        starts = self.column_starts
        if starts is None:
            starts = self.estimated_column_starts(threshold)
            for child in chain([self], self.children):
                child._column_starts = starts
            return self.column_starts
        return starts

    @property
    def iter_all_readers(self):
        """Iter through the :attr:`parent` reader and it's :attr:`children`"""
        return chain([self.parent], self.parent.children)

    def get_labeled_array(self):
        """Create a connectivity-based labeled array of the :attr:`binary` data
        """
        return skim.label(self.binary, 8, return_num=False)

    def update_image(self, arr, amask):
        """Update the image after having removed binary data

        This method is in the :attr:`remove_callbacks` mapping and is
        called after a pixel has been removed from the :attr:`binary` data.
        It mainly just calls the :meth:`reset_labels` method and updates the
        plot
        """
        self.reset_labels()
        arr = self.labels
        self.plot_im.set_array(arr)
        if self.magni_plot_im is not None:
            self.magni_plot_im.set_array(arr)

    def update_rgba_image(self, arr, mask):
        """Update the RGBA image from the given 3D-array

        This method is in the :attr:`remove_callbacks` mapping and is
        called after a pixel has been removed from the :attr:`binary` data.
        It updates the :attr:`image` attribute

        Parameters
        ----------
        arr: 3D np.ndarray of dtype float
            The image array
        mask: boolean mask of the same shape as `arr`
            The mask of features that shall be set to 0 in `arr`
        """
        from PIL import Image
        arr = arr.copy()
        arr[mask] = 0
        self.image = Image.fromarray(arr, self.image.mode)

    def remove_in_children(self, arr, amask):
        """Update the child reader images after having removed binary data

        Calls the :meth:`update_image` and :meth:`update_rgba_image` methods
        for all :attr:`children`"""
        for child in self.children:
            child.binary[amask] = 0
            child.update_image(arr, amask)
            child.update_rgba_image(arr, amask)

    def disable_label_selection(self, *args, **kwargs):
        super(DataReader, self).disable_label_selection(*args, **kwargs)
        try:
            self.remove_callbacks['labels'].remove(self.remove_in_children)
        except ValueError:
            pass

    def reset_column_starts(self):
        """Reset the column starts, :attr:`full_df`, :attr:`shifted`
        and :attr:`occurences`"""
        for child in self.iter_all_readers:
            child._column_starts = child.shifted = child._column_ends = None
            child._full_df = child._sample_locs = child._rough_locs = None
            child._occurences = set()
        self._columns = []

    def reset_samples(self):
        """Reset the samples"""
        for child in self.iter_all_readers:
            child._sample_locs = child._rough_locs = None

    def plot_image(self, ax=None, **kwargs):
        """Plot the :attr:`binary` data image on a matplotlib axes

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on. If not given, the :attr:`ax`
            attribute is used and (if this is None, too) a new figure is
            created
        ``**kwargs``
            Any other keyword that is given to the
            :func:`matplotlib.pyplot.imshow` function"""
        ax = ax or self.ax
        # plot the binary image
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.subplots()[1]
        self.ax = ax
        ncolors = self.num_labels
        colors = np.zeros((2, 4))
        colors[:, -1] = 1
        cmap = mcol.LinearSegmentedColormap.from_list('black', colors, 2)
        cmap.set_under('none')
        extent = self.extent
        kwargs.setdefault('extent', extent)
        kwargs.setdefault('cmap', cmap)
        norm = mcol.BoundaryNorm([0.1, 0.5, ncolors + 0.5], 2)
        kwargs.setdefault('norm', norm)
        self.plot_im = ax.imshow(self.labels, **kwargs)
        if self.magni is not None:
            self.magni_plot_im = self.magni.ax.imshow(self.labels, **kwargs)
        ax.grid(False)

    def plot_color_image(self, ax=None, **kwargs):
        """Plot the colored :attr:`image` on a matplotlib axes

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on. If not given, the :attr:`ax`
            attribute is used
        ``**kwargs``
            Any other keyword that is given to the
            :func:`matplotlib.pyplot.imshow` function"""
        ax = ax or self.ax
        extent = self.extent
        kwargs.setdefault('extent', extent)
        self.color_plot_im = ax.imshow(self.image, **kwargs)
        if self.magni is not None:
            self.magni_color_plot_im = self.magni.ax.imshow(
                self.image, **kwargs)

    def plot_background(self, ax=None, **kwargs):
        """Plot a white layer below the :attr:`plot_im`

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on. If not given, the :attr:`ax`
            attribute is used
        ``**kwargs``
            Any other keyword that is given to the
            :func:`matplotlib.pyplot.imshow` function"""
        ax = ax or self.ax
        # plot the binary image
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.subplots()[1]
        self.ax = ax
        extent = self.extent
        kwargs.setdefault('extent', extent)
        self.background = ax.imshow(np.zeros_like(self.binary),
                                    cmap='binary', **kwargs)
        if self.magni is not None:
            self.magni_background = self.magni.ax.imshow(
                np.zeros_like(self.binary), cmap='binary', **kwargs)

    def __reduce__(self):
        is_parent = self.parent is self
        return (
            self._loader or self.__class__,   # the constructor
            # init args
            (self.binary,     # image
             None,            # ax
             self._extent,    # extent
             False,           # plot
             self.children if is_parent else [],   # children
             None,            # parent
             None,            # magni
             False,           # plot_background
             ),
            # __setstate__
            {
             'labels': self.labels,
             'image': self.image,
             '_sample_locs': (self._sample_locs if is_parent else None),
             '_rough_locs': self._rough_locs if is_parent else None,
             'hline_locs': self.hline_locs, 'vline_locs': self.vline_locs,
             '_column_starts': self.parent._column_starts,
             '_full_df': self._full_df if is_parent else None,
             'shifted': self.shifted if is_parent else None,
             '_columns': self._columns,
             'is_exaggerated': self.is_exaggerated,
             '_xaxis_px_orig': self._xaxis_px_orig,
             'xaxis_data': self.xaxis_data,
             '_occurences': self._occurences if is_parent else set(),
             }
            )

    #: A mapping from variable name to meta information
    nc_meta = {
        'reader_image': {
            'dims': ('reader', 'ydata', 'xdata', 'rgba'),
            'long_name': 'RGBA images for data readers',
            'units': 'color'},
        'occurences': {
            'dims': ('occurence', 'xy'),
            'long_name': 'taxa occurences',
            'comments': ('The locations where the only an occurence of a '
                         'taxa is highlighted without value')},
        'reader': {
            'dims': 'reader',
            'long_name': 'index of the reader'},
        'reader_cls': {
            'dims': 'reader',
            'long_name': 'The name of the class constructor'},
        'reader_mod': {
            'dims': 'reader',
            'long_name': 'The module of the reader class'},
        'binary': {
            'dims': ('reader', 'ydata', 'xdata'),
            'long_name': 'Binary images for data readers'},
        'xaxis_translation': {
            'dims': ('reader', 'px_data', 'limit'),
            'long_name': 'Pixel to data mapping for x-axis'},
        'is_exaggerated': {
            'dims': 'reader',
            'long_name': 'Exaggeration factor'},
        'col_map': {
            'dims': 'column',
            'long_name': 'Mapping from column to reader',
            'units': 'reader_index'},
        'exag_col_map': {
            'dims': 'column',
            'long_name': 'Mapping from column to exaggerated reader',
            'units': 'reader_index'},
        'column_starts': {
            'dims': 'column',
            'long_name': 'Start of the columns',
            'units': 'px'},
        'column_ends': {
            'dims': 'column',
            'long_name': 'Ends of the columns',
            'units': 'px'},
        'full_data': {
            'dims': ('ydata', 'column'),
            'long_name': 'Full digitized data',
            'units': 'px'},
        'hline': {
            'long_name': 'Horizontal line location', 'units': 'px'},
        'vline': {
            'long_name': 'Vertical line location', 'units': 'px'},
        'shifted': {
            'dims': 'column',
            'long_name': 'Vertical shift per column', 'units': 'px'},
        'sample': {'long_name': 'Sample location', 'units': 'px'},
        'samples': {
            'dims': ('sample', 'column'),
            'long_name': 'Sample data', 'units': 'px'},
        'rough_locs': {
            'dims': ('sample', 'column', 'limit'),
            'long_name': 'Rough locations for samples'},
        }

    def create_variable(self, ds, vname, data, **kwargs):
        """Insert the data into a variable in an :class:`xr.Dataset`

        Parameters
        ----------
        ds: xarray.Dataset
            The destination dataset
        vname: str
            The name of the variable in the :attr:`nc_meta` mapping. This name
            might include ``{reader}`` which will then be replaced by the
            number of the reader in the :attr:`iter_all_readers` attribute
        data: np.ndarray
            The numpy array to store in the variable specified by `vname`
        ``**kwargs``
            A mapping from dimension to slicer that should be used to slice
            the dataset

        Returns
        -------
        str
            The resolved `vname` that has been used in the dataset"""
        ireader = list(self.iter_all_readers).index(self)
        final_vname = vname.format(reader=ireader)
        attrs = self.nc_meta[vname].copy()
        dims = safe_list(attrs.pop('dims', final_vname))
        for i, d in enumerate(dims):
            dims[i] = d.format(reader=ireader)
        if 'reader' in dims and final_vname != 'reader':
            kwargs['reader'] = ireader
        if final_vname in ds:
            ds.variables[final_vname][kwargs] = data
        else:
            if 'reader' in dims and final_vname != 'reader':
                nreaders = len(list(self.iter_all_readers))
                shape = list(np.shape(data))
                shape.insert(dims.index('reader'), nreaders)
                if final_vname in ['reader_mod', 'reader_cls']:
                    dtype = object
                else:
                    dtype = np.asarray(data).dtype
                v = xr.Variable(
                    dims, np.zeros(shape, dtype=dtype),
                    attrs=attrs)
                v[kwargs] = data
            else:
                for key, val in attrs.items():
                    attrs[key] = val.format(reader=ireader)
                v = xr.Variable(
                    dims, np.asarray(data), attrs=attrs)
            ds[final_vname] = v
        return final_vname

    def to_dataset(self, ds=None):
        """All the necessary data as a :class:`xarray.Dataset`

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset in which to insert the data. If None, a new one will be
            created

        Returns
        -------
        xarray.Dataset
            Either the given `ds` or a new :class:`xarray.Dataset` instance"""
        if ds is None:
            ds = xr.Dataset()

        if 'reader' not in ds:
            self.create_variable(ds, 'reader',
                                 np.arange(len(list(self.iter_all_readers))))
        self.create_variable(ds, 'reader_image', self.image)
        self.create_variable(ds, 'binary', self.binary)
        self.create_variable(ds, 'is_exaggerated', self.is_exaggerated)
        self.create_variable(ds, 'reader_cls', self.__class__.__name__)
        self.create_variable(ds, 'reader_mod', self.__class__.__module__)
        ireader = list(self.iter_all_readers).index(self)

        if self._xaxis_px_orig is not None:
            self.create_variable(
                ds, 'xaxis_translation',
                np.vstack([self._xaxis_px_orig, self.xaxis_data]))

        is_parent = self.parent is self

        if self.parent._columns is not None and len(self.parent._columns):
            all_columns = sorted(set(chain.from_iterable(
                    r.columns for r in self.iter_all_readers)))
            if self.is_exaggerated:
                if 'exag_col_map' not in ds:
                    self.create_variable(ds, 'exag_col_map',
                                         np.zeros_like(all_columns))
                self.create_variable(ds, 'exag_col_map', ireader,
                                     column=self.columns)
            else:
                if 'col_map' not in ds:
                    self.create_variable(ds, 'col_map',
                                         np.zeros_like(all_columns))
                self.create_variable(ds, 'col_map', ireader,
                                     column=self.columns)
            if is_parent:
                self.create_variable(ds, 'column_starts', self._column_starts)
                if self._column_ends is not None:
                    self.create_variable(ds, 'column_ends', self._column_ends)
                if self._full_df is not None:
                    self.create_variable(ds, 'full_data', self._full_df.values)
                if self.hline_locs is not None:
                    self.create_variable(ds, 'hline', self.hline_locs)
                if self.vline_locs is not None:
                    self.create_variable(ds, 'vline', self.vline_locs)
                if self.shifted is not None:
                    self.create_variable(ds, 'shifted', self.shifted)
                if self._sample_locs is not None and len(self._sample_locs):
                    samples = self.sample_locs[
                        ~self.sample_locs.index.duplicated()]
                    self.create_variable(
                        ds, 'sample', samples.index)
                    self.create_variable(
                        ds, 'samples', samples.values)
                    rough = self.rough_locs
                    self.create_variable(
                        ds, 'rough_locs',
                        rough[~rough.index.duplicated()].values.reshape(
                            samples.shape + (2, )))
                if self.occurences:
                    self.create_variable(ds, 'occurences',
                                         np.asarray(list(self.occurences)))

                for child in self.children:
                    ds = child.to_dataset(ds)

        return ds

    @classmethod
    def from_dataset(cls, ds, *args, **kwargs):
        """Create a new :class:`DataReader` from a :class:`xarray.Dataset`

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset that has been stored with the :meth:`to_dataset` method
        ``*args,**kwargs``
            Any other arguments passed to the :class:`DataReader`
            constructor

        Returns
        -------
        DataReader
            The reader recreated from `ds`"""
        if ds['reader_image'].ndim == 4:
            ds = ds.isel(reader=0)

        # initialize the reader
        reader = cls(ds['reader_image'].values, *args,
                     binary=ds['binary'].values, **kwargs)
        reader.is_exaggerated = ds['is_exaggerated'].values

        is_parent = reader.parent is reader

        # xaxis_translation
        if 'xaxis_translation' in ds and (ds['xaxis_translation'] > 0).any():
            reader._xaxis_px_orig = ds['xaxis_translation'].sel(
                px_data='pixel').values
            reader.xaxis_data = ds['xaxis_translation'].sel(
                px_data='data').values

        if reader.is_exaggerated and 'exag_col_map' in ds:
            reader.columns = list(np.where(
                ds['exag_col_map'].values == ds.reader.values)[0])
        elif 'col_map' in ds:
            reader.columns = list(np.where(
                ds['col_map'].values == ds.reader.values)[0])

        if is_parent:
            if 'column_starts' in ds:
                reader._column_starts = ds['column_starts'].values
            if 'column_ends' in ds:
                reader._column_ends = ds['column_ends'].values
            if 'full_data' in ds:
                reader._full_df = pd.DataFrame(ds['full_data'].values)
            if 'hline' in ds:
                reader.hline_locs = ds['hline'].values
            if 'vline' in ds:
                reader.vline_locs = ds['vline'].values
            if 'shifted' in ds:
                reader.shifted = ds['shifted'].values
            if 'samples' in ds:
                index = ds['sample'].values
                reader.sample_locs = pd.DataFrame(
                    ds['samples'].values, index=index)
                reader.rough_locs = pd.DataFrame(
                    ds['rough_locs'].values.reshape((len(index), -1)),
                    index=index, columns=pd.MultiIndex.from_product(
                        [reader.sample_locs.columns, ['vmin', 'vmax']]))
            if 'occurences' in ds:
                reader._occurences = set(map(tuple, ds.occurences.values))
        return reader

    def set_as_parent(self):
        """Set this instance as the parent reader"""
        old = self.parent
        if old is self:
            return
        self._column_ends = old._column_ends
        self._column_starts = old._column_starts
        self._sample_locs = old._sample_locs
        self._full_df = old._full_df
        self.rough_locs = old.rough_locs
        self._occurences = old._occurences
        self.occurences_value = old.occurences_value
        self.children = [old] + [c for c in old.children if c is not self]
        for c in [self] + self.children:
            c.parent = self
        old.children.clear()

    @only_parent
    def new_child_for_cols(self, columns, cls, plot=True):
        """Create a new child reader for specific columns

        Parameters
        ----------
        columns: list of int
            The columns for the new reader
        cls: type
            The :class:`DataReader` subclass
        plot: bool
            Plot the binary image

        Returns
        -------
        instance of `cls`
            The new reader for the specified `columns`"""
        from PIL import Image
        missing = set(columns).difference(self.columns)
        if missing:
            raise ValueError(
                "Columns %r have already been assigned!" % sorted(missing))
        image = self.image.copy()
        self_alpha = np.array(image)[..., -1]
        self_binary = self.binary
        new_binary = self.binary.copy()
        new_alpha = self_alpha.copy()
        new_columns = np.asarray(columns)
        self_columns = np.array(sorted(set(self.columns) - set(new_columns)))
        i_new_columns = list(map(self.columns.index, new_columns))
        i_self_columns = list(map(self.columns.index, self_columns))
        bounds = self.column_bounds.astype(int)
        self_bounds = bounds[i_self_columns]
        new_bounds = bounds[i_new_columns]
        for start, end in self_bounds:
            new_alpha[:, start:end] = 0
            new_binary[:, start:end] = 0
        for start, end in new_bounds:
            # check, whether the end is within one column here
            for s, e in self_bounds:
                if end > s and end <= e:
                    end = s
            self_alpha[:, start:end] = 0
            self_binary[:, start:end] = 0
        try:
            self.image.putalpha(Image.fromarray(self_alpha, "L"))
            image.putalpha(Image.fromarray(new_alpha, "L"))
        except AttributeError:  # np.ndarray
            self.image[..., -1] = self_alpha
            image[..., -1] = new_alpha
        ret = cls(new_binary, ax=self.ax, extent=self.extent, plot=plot,
                  parent=self, magni=self.magni, plot_background=False)
        self.children.append(ret)
        ret.columns = list(columns)
        self.columns = list(self_columns)
        ret.image = image
        # update plot and binary image
        self.binary = self_binary
        self.update_image(self.labels, new_alpha)
        ret.hline_locs = self.hline_locs
        ret.vline_locs = self.vline_locs
        return ret

    @property
    def exaggerated_reader(self):
        """The reader that represents the exaggerations"""
        cols = set(self.columns or [])
        return next(
            (child for child in chain([self.parent], self.parent.children)
             if child.is_exaggerated and cols <= set(child.columns or [])),
            None)

    @property
    def non_exaggerated_reader(self):
        """The reader that represents the exaggerations"""
        cols = set(self.columns)
        return next(
            (child for child in self.iter_all_readers
             if not child.is_exaggerated and
             set(child.columns or [None]) <= cols),
            None)

    def create_exaggerations_reader(self, factor, cls=None):
        """Create a new exaggerations reader for this reader

        Parameters
        ----------
        factor: float
            The exaggeration factor
        cls: type
            The :class:`DataReader` subclass

        Returns
        -------
        instance of `cls`
            The new exaggerated reader"""
        from PIL import Image
        if cls is None:
            cls = self.__class__
        new_binary = np.zeros_like(self.binary)
        ret = cls(new_binary, ax=self.ax, extent=self.extent, plot=True,
                  parent=self)
        ret.is_exaggerated = factor
        self.children.append(ret)
        ret.columns = self.columns
        # create a new empty image
        try:
            mode = self.image.mode
        except AttributeError:  # np.ndarray
            ret.image = np.zeros_like(self.image)
        else:
            ret.image = Image.fromarray(np.zeros_like(self.image), mode)
        # update plot and binary image
        ret.hline_locs = self.hline_locs
        ret.vline_locs = self.vline_locs
        return ret

    def mark_as_exaggerations(self, mask):
        """Mask the given array as exaggerated

        Parameters
        ----------
        mask: 2D np.ndarray of dtype bool
            A mask with the same shape as the :attr:`binary` array that is True
            if a cell should be interpreted as the visualization of an
            exaggeration"""
        from PIL import Image

        if not self.is_exaggerated:
            exaggerated = self.exaggerated_reader
            if exaggerated is None:
                raise ValueError(
                    "No exaggeration reader found for columns %r" % (
                        self.columns, ))
            return exaggerated.mark_as_exaggerations(mask)
        non_exaggerated = self.non_exaggerated_reader
        self.binary[mask] = non_exaggerated.binary[mask]
        non_exaggerated.binary[mask] = 0
        # update the plots
        non_exaggerated.update_image(non_exaggerated.labels, mask)
        self.update_image(self.labels, ~mask)
        # update the colored images
        non_exag_image = np.asarray(non_exaggerated.image)
        exag_image = np.asarray(self.image)
        mask3d = np.tile(mask[..., np.newaxis], (1, 1, 4))
        non_exag_alpha = non_exag_image[..., -1].copy()
        non_exag_alpha[mask] = 0
        try:
            non_exaggerated.image.putalpha(
                Image.fromarray(non_exag_alpha, "L"))
        except AttributeError:  # np.ndarray
            non_exag_image.image[..., -1] = non_exag_alpha
            self.image[mask3d] = non_exag_image[mask3d]
        else:
            self.image = Image.fromarray(
                np.where(mask3d, non_exag_image, exag_image), self.image.mode)

    def close(self):
        if self.image is not None:
            self.image.close()
        self.remove_callbacks.clear()
        self._full_df = None
        for attr in ['plot_im', 'magni_plot_im', 'magni_color_plot_im',
                     'color_plot_im', 'background', 'magni_background',
                     'magni', '_full_df', '_sample_locs', '_rough_locs',
                     'image', 'binary', 'labels', '_column_starts',
                     '_column_ends']:
            try:
                getattr(self, attr).remove()
            except (AttributeError, ValueError):
                pass
            setattr(self, attr, None)
        self._occurences = set()
        for child in self.children:
            child.close()
        self.children.clear()
        self.parent = self
        self.ax = None

    def _select_column(self, event=None, x=None, y=None, col=None):
        import matplotlib.patches as mpatch
        if event is None and x is None and y is None and col is None:
            raise ValueError("Either event, x and y, or col must be given!")
        if event is not None and event.inaxes is not self.ax:
            return
        elif event is not None:
            x, y = event.xdata, event.ydata
        if self.extent is None:
            xlim = [0, self.binary.shape[1]]
            ylim = [0, self.binary.shape[0]]
        else:
            xlim = sorted(self.extent[:2])
            ylim = sorted(self.extent[2:])
        if self._use_all_cols:
            bounds = self.all_column_bounds
        else:
            bounds = self.column_bounds
        if x is not None:
            if x <= xlim[0] or x >= xlim[1] or y <= ylim[0] or y >= ylim[1]:
                return
            x -= xlim[0]
            col, (xmin, xmax) = next(
                (col, l) for col, l in enumerate(bounds)
                if x >= l[0] and x <= l[1])
        else:
            xmin, xmax = bounds[col]
        if not self._use_all_cols:
            col = self.columns[col]
        if col in self._selected_cols:
            # if it is already selected, deselect it
            self._selected_cols.pop(col).remove()
        else:
            # otherwise, select it
            w = xmax - xmin
            h = np.diff(ylim)[0]
            rect = mpatch.Rectangle((xlim[0] + xmin, ylim[0]), w, h,
                                    facecolor='red', edgecolor='black',
                                    alpha=0.2, fill=True)
            self.ax.add_patch(rect)
            self._selected_cols[col] = rect
        self.draw_figure()

    def start_column_selection(self, use_all=False):
        """Enable the user to select columns

        Parameters
        ----------
        use_all: bool
            If True, all columns can be selected. Otherwise only the columns
            in the :attr:`columns` attribute can be selected"""
        fig = self.fig
        self._selected_cols = {}
        self._use_all_cols = use_all
        self._select_cols_cid = fig.canvas.mpl_connect('button_press_event',
                                                       self._select_column)

    def end_column_selection(self):
        """End the column selection and rmove the artists"""
        fig = self.fig
        fig.canvas.mpl_disconnect(self._select_cols_cid)
        for p in self._selected_cols.values():
            p.remove()
        del self._selected_cols

    @staticmethod
    def to_grey_pil(image, threshold=230 * 3):
        """Convert an image to a greyscale image

        Parameters
        ----------
        image: PIL.Image.Image
            The RGBA image file
        threshold: float
            If the multiplied RGB values in a cell are above the threshold,
            the cell is regarded as background and will be set to 0

        Returns
        -------
        np.ndarray of ndim 2
            The greyscale image of integer type"""
        arr = np.asarray(image, dtype=int)
        alpha = arr[..., -1]
        alpha[(alpha == 0) | (arr[..., :-1].sum(axis=-1) > threshold)] = 0
        ret = np.array(image.convert('L'), dtype=int) + 1
        ret[(alpha == 0) | (ret > 255)] = 0
        return ret

    @staticmethod
    def to_binary_pil(image, threshold=230 * 3):
        """Convert an image to a binary

        Parameters
        ----------
        image: PIL.Image.Image
            The RGBA image file
        threshold: float
            If the multiplied RGB values in a cell are above the threshold,
            the cell is regarded as background and will be set to 0

        Returns
        -------
        np.ndarray of ndim 2
            The binary image of integer type"""
        grey = DataReader.to_grey_pil(image, threshold)
        grey[grey > 0] = 1
        return grey

    def estimated_column_starts(self, threshold=None):
        """
        The estimated column starts as :class:`numpy.ndarray`.

        We assume a new column a pixel column $i$ if

        1. the previous pixel column $i-1$ did not contain any data
           ($D(i-1) = 0$)
        2. THE amount of data points doubled compared to $i-1$
           ($D(i) \\geq 2\\cdot D(i-1)$)
        3. the amount of data points steadily increases within the next few
           columns to a value twice as large as the previous column
           ($D(i+n) \\geq 2\\cdot D(i-1)$ with $n>0$ and
           $D(i+j) \\geq D(i)$ for all $0 < j \\geq n$)

        Each potential column starts must also be covered by a given
        `threshold`.

        Parameters
        ----------
        threshold: float between 0 and 1
            The fraction that has to be covered to assume a valid column start.
            By default, 0.1 (i.e. 10 percent)

        Returns
        -------
        np.ndarray
            The starts for each column
        """
        if threshold is None:
            threshold = 0.1
        binary = self.binary
        col_mask = binary.any(axis=0)  # True if the column contains a value
        summed = binary.sum(axis=0)   # The total number of data points per col
        nulls = np.where(col_mask)[0]  # columns with values
        diff = nulls[1:] - nulls[:-1]  # difference to the last col with values
        #: The valid columns that cover more than the threshold
        valid = (summed / binary.shape[0]) >= threshold
        if not len(nulls):
            starts = np.array([])
        else:
            #: columns where we had nothing before and is then covered by data
            starts = np.r_[[nulls[0]] if diff[0] == 1 else [],
                           nulls[1:][diff > 1]].astype(int)
            starts = starts[valid[starts]]
        #: Were we have a doubling of the data in the previous column and at
        #: least 10 percent of the column is covered by data
        doubled = np.where((summed[1:] > summed[:-1] * 2) & valid[1:])[0] + 1
        #: Were we have a slow increase in data points over x-range and at
        #: the end we have a doubled amount of valid pixels
        increasing, bounds = groupby_arr(summed[1:] > summed[:-1])
        from0 = int(not increasing[0])  # start from 0 if the first key is True
        starts_ends = zip(bounds[from0::2], bounds[1 + from0::2])
        increased = [s + 1 for s, e in starts_ends
                     if (summed[e] > summed[s] * 2 and valid[e])]
        ret = np.unique(np.r_[starts, doubled, increased])
        # now we check that we have at least one percent of the image width
        # between two columns
        min_diff = 0.01 * binary.shape[1]
        mask = (np.r_[ret[1:], binary.shape[1]] - ret) > min_diff
        return ret[mask]

    @docstrings.get_sectionsf('DataReader._filter_lines')
    def _filter_lines(self, locs, min_lw=1, max_lw=None):
        """Filter consecutive locations based on their length

        This method is used by :meth:`recognize_hlines` and
        :meth:`recognize_vlines` to filter those horizontal/vertical lines
        that have a certain line width

        Parameters
        ----------
        locs: 1D np.ndarray of int
            The locations of the horizontal or vertical lines
        min_lw: int
            The minimum line width for a line
        max_lw: int
            The maximum line width for a line or None if it should be ignored
        """
        if not len(locs) or min_lw < 2 and max_lw is None:
            return locs
        sl = slice(0, max_lw)
        try:
            selection = np.concatenate([
                indices[sl] for indices in np.split(
                    locs, np.where(np.diff(locs) != 1)[0]+1)
                if len(indices) >= min_lw])
        except ValueError:  # probably none of the lines is thick enough
            if all(len(indices) < min_lw for indices in np.split(
                    locs, np.where(np.diff(locs) != 1)[0]+1)):
                selection = np.array([], dtype=int)
            else:
                raise
        return np.asarray(selection, dtype=int)

    def recognize_xaxes(self, fraction=0.3, min_lw=1, max_lw=None,
                        remove=False, **kwargs):
        """Recognize (and potentially remove) x-axes at bottom and top

        Parameters
        ----------
        fraction: float
            The fraction (between 0 and 1) that has to be covered to recognize
            an x-axis
        min_lw: int
            The minimum line width of an axis
        max_lw: int
            Tha maximum line width of an axis. If not specified, it will be
            ignored
        remove: bool
            If True, they will be removed immediately, otherwise they are
            displayed using the :meth:`enable_label_selection` method and can
            be removed through the :meth:`remove_selected_labels` method"""
        binary = self.merged_binaries()
        ys, xs = binary.shape
        ys_5p = max(2, int(np.ceil(ys * 0.05)))

        full_mask = np.zeros_like(binary, dtype=bool)

        # upper 5 percent of the data image
        arr = binary[:ys_5p+1]
        row_sums = np.nansum(arr, axis=1)
        mask = (row_sums / float(xs) > fraction)
        if mask.any():
            # filter with min_lw and max_lw
            rows = np.where(mask)[0]
            for i, row in enumerate(rows[1:], 1):
                if np.abs(row_sums[row] / row_sums[rows[i-1]] - 1) > 0.05:
                    rows = rows[:i]
                    break
            mask = np.zeros_like(mask)
            selection = self._filter_lines(rows, min_lw, max_lw)
            mask[selection] = True
        if mask.any():
            labeled = skim.label(arr, 8)
            labels = np.unique(labeled[mask])
            labels = labels[labels > 0]
            labeled[mask] = 0
            n = int(mask.sum() * 2 * np.ceil(xs * 0.01))
            # look for connected small parts (such as axis ticks)
            labeled[arr.astype(bool) & np.isin(labeled, labels) &
                    (~skim.remove_small_objects(labeled.astype(bool), n))] = 0
            full_mask[:ys_5p+1] = np.where(
                arr.astype(bool) & ~labeled.astype(bool), True,
                np.zeros_like(arr, dtype=bool))

        # lower 5 percent of the data image
        arr = self.binary[-ys_5p:]
        row_sums = np.nansum(arr, axis=1)
        mask = (row_sums / float(xs) > fraction)
        if mask.any():
            # filter with min_lw and max_lw
            rows = np.where(mask)[0][::-1]
            for i, row in enumerate(rows[1:], 1):
                if np.abs(row_sums[row] / row_sums[rows[i-1]] - 1) > 0.05:
                    rows = rows[:i]
                    break
            rows.sort()
            mask = np.zeros_like(mask)
            selection = self._filter_lines(rows, min_lw, max_lw)
            mask[selection] = True
        if mask.any():
            labeled = skim.label(arr, 8)
            labels = np.unique(labeled[mask])
            labels = labels[labels > 0]
            labeled[mask] = 0
            n = int(mask.sum() * 2 * np.ceil(xs * 0.01))
            # look for connected small parts (such as axis ticks)
            labeled[arr.astype(bool) & np.isin(labeled, labels) &
                    (~skim.remove_small_objects(labeled.astype(bool), n))] = 0
            full_mask[-ys_5p:] = np.where(
                arr.astype(bool) & ~labeled.astype(bool), True,
                np.zeros_like(arr, dtype=bool))

        if remove:
            self.set_hline_locs_from_selection(full_mask)

        self._show_parts2remove(self.binary, remove, select_all=False,
                                selection=full_mask, **kwargs)

    docstrings.delete_params('DataReader._filter_lines.parameters', 'locs')

    @docstrings.with_indent(8)
    def recognize_hlines(self, fraction=0.3, min_lw=1, max_lw=None,
                         remove=False, **kwargs):
        """Recognize horizontal lines in the plot and subtract them

        This method removes horizontal lines in the data diagram, i.e. rows
        whose non-background cells cover at least the specified `fraction` of
        the row.

        Parameters
        ----------
        fraction: float
            The fraction (between 0 and 1) that has to be covered to recognize
            a horizontal line
        %(DataReader._filter_lines.parameters.no_locs)s
        remove: bool
            If True, they will be removed immediately, otherwise they are
            displayed using the :meth:`enable_label_selection` method and can
            be removed through the :meth:`remove_selected_labels` method

        Other Parameters
        ----------------
        ``**kwargs``
            Additional keywords are parsed to the
            :meth:`enable_label_selection` method in case `remove` is ``False``

        Notes
        -----
        This method has to be called before the :meth:`digitize` method!
        """
        arr = np.zeros_like(self.labels)
        mask = (np.nansum(self.binary, axis=1) / float(self.binary.shape[1]) >
                fraction)
        all_rows = np.where(mask)[0]
        selection = self._filter_lines(all_rows, min_lw, max_lw)
        for i, row in enumerate(selection if remove else all_rows, 1):
            arr[row, :] = i
        if remove:
            self.hline_locs = np.unique(np.r_[self.hline_locs, selection])
            self.binary[arr.astype(bool)] = 0
            self.reset_labels()
            self.plot_im.set_array(self.labels)
            if self.magni_plot_im is not None:
                self.magni_plot_im.set_array(self.labels)
        else:
            kwargs['extent'] = self.extent
            kwargs.setdefault('zorder', self.plot_im.zorder + 0.1)
            mask = np.zeros_like(self.binary, dtype=bool)
            mask[selection, :] = self.binary[selection, :].astype(bool)
            self._show_parts2remove(self.labels, False, select_all=False,
                                    selection=mask, **kwargs)

    def set_hline_locs_from_selection(self, selection=None):
        """Save the locations of horizontal lines

        This methods takes every pixel row in the :attr:`hline_locs`
        attribute where at least 30% is selected. The digitize method will
        interpolate at these indices."""
        selection = self.selected_part if selection is None else selection
        rows = np.where(
            selection.sum(axis=1) / self.binary.sum(axis=1) > 0.3)[0]
        self.hline_locs = np.unique(np.r_[self.hline_locs, rows])

    def recognize_yaxes(self, fraction=0.3, min_lw=0, max_lw=None,
                        remove=False):
        """Find (and potentially remove) y-axes in the image

        Parameters
        ----------
        fraction: float
            The fraction (between 0 and 1) that has to be covered to recognize
            a y-axis
        min_lw: int
            The minimum line width of an axis
        max_lw: int
            Tha maximum line width of an axis. If not specified, the median
            if the axes widths is taken
        remove: bool
            If True, they will be removed immediately, otherwise they are
            displayed using the :meth:`enable_label_selection` method and can
            be removed through the :meth:`remove_selected_labels` method"""

        grey = self.to_grey_pil(self.image)
        binary = self.binary

        ys, xs = binary.shape

        mask = (np.nansum(self.binary, axis=0) / ys > fraction)
        bounds = self.column_bounds
        min_col = bounds.min()
        yaxes = {}
        col = -1
        nvals = 0
        for i in np.where(mask)[0]:
            if i < min_col:
                continue
            icol = next(icol for icol, (s, e) in enumerate(bounds)
                        if i >= s and i < e)
            if i > max(2, bounds[icol, 0] + binary.shape[1] * 0.05):
                continue
            dominant_color = np.bincount(grey[:, i]).argmax()
            if icol != col:
                col = icol
                yaxes[icol] = [[i]]
                nvals = np.nansum(binary[:, i])
                line_color = dominant_color
                found_data = False
            # append when we have about the same number of vertical lines
            elif i - yaxes[icol][-1][-1] == 1:
                # if we do neither see a change in dominant color nor in the
                # number of data points in the row, we extend the line
                if ((abs(dominant_color - line_color) < 10 or
                     line_color > 150 or dominant_color > 150) and
                        np.abs(np.nansum(binary[:, i]) / nvals - 1) < 0.05):
                    line_color = dominant_color
                    yaxes[icol][-1].append(i)
            elif not found_data:
                # check whether more than 10% of the previous region has been
                # covered with data
                sub = binary[:, yaxes[icol][-1][-1]+1:i]
                ndata = np.nansum(sub)
                npotential = sub.size
                if ndata < 0.1 * npotential:
                    yaxes[icol].append([i])
                else:
                    found_data = True

        max_lw = int(max_lw or
                     (np.ceil(np.median(list(map(
                         len, chain.from_iterable(yaxes.values())))))))

        for col_lines in yaxes.values():
            removed = 0
            for i, lines in enumerate(col_lines[:]):
                if len(lines) < min_lw:
                    del col_lines[i - removed]
                    removed += 1
                else:
                    del lines[max_lw:]

        mask = np.zeros_like(binary, dtype=bool)
        mask[:, list(chain.from_iterable(
                chain.from_iterable(yaxes.values())))] = True

        # add small labels to account for ticks
        labeled = self.labels.copy()
        labeled_save = labeled.copy()
        labels = np.unique(labeled[mask])
        labels = labels[labels > 0]
        labeled[mask] = 0
        n = int(max_lw * 2 * np.ceil(len(binary) * 0.01))
        small = labeled.astype(bool) & (~skim.remove_small_objects(
            labeled.astype(bool), n))
        thresh = np.ceil(0.02 * len(binary))
        labeled_small = skim.label(small)
        for label in np.unique(labeled_small[labeled_small > 0]):
            lmask = labeled_small == label
            if np.any(np.sum(lmask, axis=0) > thresh):
                # do not remove small objects that span more than 2 percent of
                # the column to not remove anything of the data
                small[lmask] = False
            else:
                # additionally look for the dominant color, if it differs a lot
                # from the line color, do not remove
                try:
                    line_color = np.bincount(
                        grey[mask & lmask]).argmax()
                    small[lmask & ~((np.abs(grey[lmask] - line_color) < 10) |
                                    grey[lmask] > 150)] = False
                except ValueError:
                    pass

        mask[binary.astype(bool) & np.isin(labeled, labels) & small] = True

        # Now remove light colors that are attached to the lines and whose
        # neighbour belongs to a line, too
        labeled = self.labels.copy()
        labels = np.unique(labeled[mask])
        labels = labels[labels > 0]
        found = True
        nulls = np.zeros(mask.shape[0], dtype=bool)
        while found:
            rgrey = np.where(np.c_[nulls, mask[:, :-1]], grey, 0)
            lgrey = np.where(np.c_[mask[:, 1:], nulls], grey, 0)
            light_colors = ~mask & ((rgrey > 150) | (lgrey > 150))
            found = light_colors.any()
            if found:
                mask[light_colors] = True

        # now select up to the maximum for each line
        # if 10% of the column is selected, select all
        thresh = 0.1 * len(binary)
        for col, indices in yaxes.items():
            for l in indices:
                lmax = np.max(l[0] + 1 + np.where(
                    mask[:, l[0]:l[0] + max_lw + 1].sum(axis=0) > thresh)[0])
                mask[:, l[0]:lmax] = True

        if remove:
            self.set_vline_locs_from_selection(mask)

        self._show_parts2remove(binary, remove, select_all=False,
                                selection=mask)
        return mask

    @docstrings.with_indent(8)
    def recognize_vlines(self, fraction=0.3, min_lw=1, max_lw=None,
                         remove=False, **kwargs):
        """Recognize horizontal lines in the plot and subtract them

        This method removes horizontal lines in the data diagram, i.e. rows
        whose non-background cells cover at least the specified `fraction` of
        the row.

        Parameters
        ----------
        fraction: float
            The fraction (between 0 and 1) that has to be covered to recognize
            a horizontal line
        %(DataReader._filter_lines.parameters.no_locs)s
        remove: bool
            If True, they will be removed immediately, otherwise they are
            displayed using the :meth:`enable_label_selection` method and can
            be removed through the :meth:`remove_selected_labels` method

        Other Parameters
        ----------------
        ``**kwargs``
            Additional keywords are parsed to the
            :meth:`enable_label_selection` method in case `remove` is ``False``

        Notes
        -----
        This method should be called before the column starts are set
        """
        arr = np.zeros_like(self.labels)
        mask = (np.nansum(self.binary, axis=0) / float(self.binary.shape[0]) >
                fraction)
        all_cols = np.where(mask)[0]
        selection = self._filter_lines(all_cols, min_lw, max_lw)
        for i, col in enumerate(selection if remove else all_cols, 1):
            arr[:, col] = i
        if remove:
            self.vline_locs = np.unique(np.r_[self.vline_locs, selection])
            self._shift_column_starts(selection)
            self.binary[arr.astype(bool)] = 0
            self.reset_labels()
            self.plot_im.set_array(self.labels)
            if self.magni_plot_im is not None:
                self.magni_plot_im.set_array(self.labels)
        else:
            kwargs['extent'] = self.extent
            kwargs.setdefault('zorder', self.plot_im.zorder + 0.1)
            mask = np.zeros_like(self.binary, dtype=bool)
            mask[:, selection] = self.binary[:, selection].astype(bool)
            self._show_parts2remove(self.labels, False, select_all=False,
                                    selection=mask, **kwargs)

    def set_vline_locs_from_selection(self, selection=None):
        """Save the locations of vertical lines

        This methods takes every pixel column in the :attr:`vline_locs`
        attribute where at least 30% is selected."""
        selection = self.selected_part if selection is None else selection
        cols = np.where(
            selection.sum(axis=0) / self.binary.sum(axis=0) > 0.3)[0]
        self.vline_locs = np.unique(np.r_[self.vline_locs, cols])
        self._shift_column_starts(cols)
        self._shift_occurences(cols)

    def _shift_column_starts(self, locs):
        """Shift the column starts after the removement of vertical lines"""
        starts = self._column_starts
        if starts is None:
            return
        starts0 = starts.copy()
        if starts is not None:
            locs = np.asarray(locs)
            mask = np.isin(starts, locs)
            while mask.any():
                starts[mask] += 1
                mask = np.isin(starts, locs)
        # choose the mean of the starts because this is where we expect the 0
        self._column_starts = np.round(
            np.vstack([starts, starts0]).mean(axis=0)).astype(int)

    def _shift_occurences(self, locs):
        """Shift the occurences after the removement of vertical lines"""
        occurences = self.occurences
        if occurences:
            occurences = np.array(list(occurences))
            locs = np.asarray(locs)
            mask = np.isin(occurences[:, 0], locs)
            while mask.any():
                occurences[np.c_[mask, np.zeros_like(mask)]] += 1
                mask = np.isin(occurences[:, 0], locs)
            self.occurences = set(map(tuple, occurences))

    def color_labels(self, categorize=1):
        """The labels of the colored array"""
        arr = self.image_array()
        converted = np.asarray(self.image.convert('L'))
        binary = np.where(
            (arr[..., -1] == 0) | (converted == 255) | (self.labels == 0), 0,
            converted + 1)
        if categorize > 1:
            import pandas as pd
            shape = binary.shape
            bins = np.r_[0, np.arange(1, 260 + categorize, categorize)]
            binary = pd.cut(binary.ravel(), bins, labels=False).reshape(shape)
        return skim.label(binary, 8, return_num=False)

    def image_array(self):
        """The RGBA values of the colored image"""
        return np.asarray(self.image)

    def get_binary_for_col(self, col):
        """Get the binary array for a specific column"""
        s, e = self.column_bounds[self.columns.index(col)]
        return self.binary[:, s:e]

    def shift_vertical(self, pixels, draw=True):
        """Shift the columns vertically.

        Parameters
        ----------
        pixels: list of floats
            The y-value for each column for which to shift the values. Note
            that theses values have to be greater than or equal to 0
        draw: bool
            If True, the :attr:`ax` is drawn at the end"""
        arr = self.binary
        df = self._full_df
        bounds = self.column_bounds
        pixels = np.asarray(pixels)
        npx = len(pixels)
        for col, ((start, end), pixel) in enumerate(zip_longest(
                bounds, pixels[[col for col in self.columns if col < npx]],
                fillvalue=pixels[-1])):
            if pixel:  # shift the column upwards
                arr[:-pixel, start:end] = arr[pixel:, start:end]
                arr[-pixel:, start:end] = 0
                if df is not None:
                    df.iloc[:-pixel, col] = df.iloc[pixel:, col].values
                    df.iloc[-pixel:, col] = np.nan
        self.labels = self.get_labeled_array()
        self.plot_im.set_array(arr)
        if self.magni_plot_im is not None:
            self.magni_plot_im.set_array(arr)
        for child in self.children:
            child.shift_vertical(pixels, draw=False)
        if draw:
            self.draw_figure()

    def found_extrema_per_row(self):
        """Calculate how many columns have a potential sample in each pixel row

        Returns
        -------
        pandas.Series
            A series with one entry per pixel row. The values are the number of
            columns in the diagram that have a potential sample noted in the
            :attr:`rough_locs`
        """
        ret = pd.Series(np.zeros(len(self.full_df)), index=self.full_df.index,
                        name='Extrema')
        rough = self.rough_locs
        if rough is None:
            return ret
        for col in self.sample_locs.columns:
            for key, (imin, imax) in rough.loc[:, col].iterrows():
                ret.loc[int(imin):int(imax)] += 1
        return ret

    @property
    def column_bounds(self):
        """The boundaries for the data columns"""
        if self.column_starts is None:
            return
        return np.vstack([self.column_starts, self.column_ends]).T

    @property
    def all_column_bounds(self):
        """The boundaries for the data columns"""
        if self.all_column_starts is None:
            return
        return np.vstack([self.all_column_starts,
                          self.all_column_ends]).T

    @docstrings.get_sectionsf('DataReader.digitize')
    def digitize(self, use_sum=False, inplace=True):
        """Digitize the binary image to create the full dataframe

        Parameters
        ----------
        use_sum: bool
            If True, the sum of cells that are not background are used for each
            column, otherwise the value of the cell is used that has the
            maximal distance to the column start for each row
        inplace: bool
            If True (default), the :attr:`full_df` attribute is updated.
            Otherwise a DataFrame is returned

        Returns
        -------
        None or :class:`pandas.DataFrame`
            The digitization result if `inplace` is ``True``, otherwise None
        """
        binary = self.binary
        self._get_column_starts()  # estimate the column starts
        bounds = self.column_bounds

        vals = np.zeros((binary.shape[0], len(bounds)), dtype=float)

        for i, (vmin, vmax) in enumerate(bounds):
            if use_sum:
                vals[:, i] = np.nansum(binary[:, vmin:vmax], axis=1)
            else:
                for row in range(len(vals)):
                    notnull = np.where(binary[row, vmin:vmax])[0]
                    if len(notnull):
                        vals[row, i] = notnull.max() + 1

        # interpolate the values at :attr:`hline_locs`
        if len(self.hline_locs):
            from scipy.interpolate import interp1d
            y = np.arange(len(vals))
            indices = sorted(set(range(len(vals))).difference(self.hline_locs))
            data = vals[np.ix_(indices, list(range(vals.shape[1])))]
            for i in range(vals.shape[1]):
                vals[:, i] = interp1d(
                    y[indices], data[:, i], bounds_error=False,
                    fill_value='extrapolate')(y)
        if inplace:
            self.full_df = vals
        else:
            return pd.DataFrame(vals, columns=self.columns,
                                index=np.arange(len(self.binary)))

    def digitize_exaggerated(self, fraction=0.05, absolute=8, inplace=True,
                             return_mask=False):
        """Merge the exaggerated values into the original digitized result

        Parameters
        ----------
        fraction: float between 0 and 1
            The fraction under which the exaggerated data should be used.
            Set this to 0 to ignore it.
        absolute: int
            The absolute value under which the exaggerated data should be used.
            Set this to 0 to ignore it.
        inplace: bool
            If True (default), the :attr:`full_df` attribute is updated.
            Otherwise a DataFrame is returned
        return_mask: bool
            If True, a boolean 2D array is returned indicating where the
            exaggerations have been used

        Returns
        -------
        pandas.DataFrame or None
            If `inplace` is False, the digitized result. Otherwise, if
            `return_mask` is True, the mask where the exaggerated results have
            been used. Otherwise None
        pandas.DataFrame, optionally
            If `inplace` is False and `return_mask` is True, a pandas.DataFrame
            containing the boolean mask where the exaggerated results have been
            used. Otherwise, this is skipped
        """
        if not self.is_exaggerated:
            return self.exaggerated_reader.digitize_exaggerated(
                fraction=fraction, absolute=absolute, inplace=inplace,
                return_mask=return_mask)
        if inplace:
            non_exag = self.full_df.values
        else:
            non_exag = self.full_df.values.copy()
        new_vals = self.digitize(inplace=False).values

        # where we are below 5 percent of the column width, we use the
        # exaggerated value
        min_val = fraction * np.diff(self.column_bounds).T
        min_val[min_val <= absolute] = absolute
        mask = (non_exag < min_val) & (new_vals > 0)
        non_exag[mask] = new_vals[mask]
        non_exag[mask] /= self.is_exaggerated
        if return_mask:
            mask = pd.DataFrame(mask, columns=self.columns,
                                index=np.arange(len(self.binary)))
        if inplace:
            self.full_df = non_exag
        else:
            ret = pd.DataFrame(non_exag, columns=self.columns,
                               index=np.arange(len(self.binary)))
            if return_mask:
                return (ret, mask)
            else:
                return (ret, )
        if return_mask:
            return (mask, )

    _xaxis_px_orig = None

    @property
    def xaxis_px(self):
        """The x indices in column pixel coordinates that are used for x-axes
        translations"""
        if self._xaxis_px_orig is None:
            raise ValueError("X-limits have not yet been set!")
        elif self.parent._column_starts is None:
            raise ValueError("The columns have not yet been separated!")
        ret = np.array(self._xaxis_px_orig)
        if self.extent is not None:
            ret -= np.min(self.extent[:2])
        starts = self.column_starts
        indices = np.searchsorted(starts, ret) - 1
        if ret[0] in starts:
            indices[0] += 1
        col_starts = starts[indices]
        if len(np.unique(col_starts)) > 1:
            raise ValueError("X-values have been used from different columns! "
                             "Columns %s" % (
                                np.asarray(self.columns)[indices]))
        return ret - starts[indices[0]]

    @xaxis_px.setter
    def xaxis_px(self, value):
        """The x indices in column pixel coordinates that are used for x-axes
        translations"""
        if value is None:
            self._xaxis_px_orig = value
        else:
            value = np.array(value)
            nmax = value[1]
            if self.extent is not None:
                value += np.min(self.extent[:2])
            col = np.where(np.diff(self.column_bounds, axis=1) >= nmax)[0][0]
            self._xaxis_px_orig = value + self.column_starts[col]

    xaxis_data = None

    def px2data_x(self, coord):
        """Transform the pixel coordinates into data coordinates

        Parameters
        ----------
        coord: 1D np.ndarray
            The coordinate values in pixels

        Returns
        -------
        np.ndarray
            The numpy array starting from 0 with transformed coordinates

        Notes
        -----
        Since the x-axes for stratographic plots are usually interrupted, the
        return values here are relative and therefore always start from 0"""
        x_px = self.xaxis_px
        x_data = self.xaxis_data
        diff_px = np.diff(x_px)[0]
        diff_data = np.diff(x_data)[0]
        slope = diff_data / diff_px
        intercept = x_data[0] - slope * x_px[0]
        return np.where(coord == self.occurences_value, self.occurences_value,
                        intercept + slope * coord)

    @docstrings.get_sectionsf('DataReader._plot_df')
    def _plot_df(self, df, ax=None, *args, **kwargs):
        """Plot a data frame as line plot in the diagram

        Parameters
        ----------
        df: pandas.DataFrame
            The data frame to plot. The columns have to be the same as in the
            :attr:`columns` attribute
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on
        ``*args,**kwargs``
            Any other argument and keyword argument that is passed to the
            :func:`matplotlib.pyplot.plot` function"""
        vals = df.values
        starts = self.column_starts
        lines = []
        y = df.index.values + 0.5
        ax = ax or self.ax
        if self.extent is not None:
            y += self.extent[-1]
            starts = starts + self.extent[0]
        if 'lw' not in kwargs and 'linewidth' not in kwargs:
            kwargs['lw'] = 2.0
        for i in range(vals.shape[1]):
            mask = (~np.isnan(vals[:, i])) & (
                    vals[:, i] != self.occurences_value)
            x = starts[i] + vals[:, i][mask]
            lines.extend(ax.plot(x, y[mask], *args, **kwargs))
        return lines

    docstrings.delete_params('DataReader._plot_df.parameters', 'df')

    @docstrings.with_indent(8)
    def plot_full_df(self, ax=None, *args, **kwargs):
        """Plot the lines for the digitized diagram

        Parameters
        ----------
        %(DataReader._plot_df.parameters.no_df)s"""
        self.lines = self._plot_df(self.full_df, ax, *args, **kwargs)

    @docstrings.with_indent(8)
    def plot_samples(self, ax=None, *args, **kwargs):
        """Plot the diagram as lines reconstructed from the samples

        Parameters
        ----------
        %(DataReader._plot_df.parameters.no_df)s"""
        self.sample_lines = self._plot_df(
            self.sample_locs.loc[:, self.columns], ax, *args, **kwargs)

    def plot_sample_hlines(self, ax=None, **kwargs):
        """Plot one horizontal line per sample in the :attr:`sample_locs`

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on
        ``*args,**kwargs``
            Any other keyword argument that is passed to the
            :func:`matplotlib.pyplot.hlines` function"""
        ax = ax or self.ax
        xmin, xmax = sorted(self.extent[:2])
        y = self.sample_locs.index + min(self.extent[2:])
        kwargs.setdefault('color', 'r')
        if not len(y):
            return
        self.sample_hlines = [ax.hlines(y, xmin, xmax, **kwargs)]

    def get_surrounding_slopes(self, indices, arr):

        def get_next_interval(i, step=1):
            if step == 1:
                diffs = arr[i+1:] - arr[i+1] != 0
            else:
                diffs = arr[:i][::-1] - arr[i-1] != 0
            if not diffs.any():
                return len(diffs)
            return diffs.argmax()

        vmin, vmax = indices[0], indices[-1] - 1
        if vmax >= len(arr) - 1:
            return None, None
        # check
        #          /
        #         /
        #       /_
        #      /    pattern
        nlower = get_next_interval(vmin, -1)
        nhigher = get_next_interval(vmax, 1)
        if (nlower and nhigher and vmin - nlower - 1 > 0 and
                vmax + nhigher + 1 < len(arr)):
            slope0 = (arr[vmin - 1] - arr[vmin - nlower - 1]) / nlower
            slope1 = (arr[vmax + nhigher + 1] - arr[vmax + 1]) / nhigher
            return slope0, slope1
        return None, None

    def is_obstacle(self, indices, arr):
        """Check whether the found extrema is only an obstacle of the picture
        """
        # if the extremum is longer than 2, we don't assume an obstacle
        if np.diff(indices) > 2 or indices[-1] == len(arr) - 1:
            return False
        slope0, slope1 = self.get_surrounding_slopes(indices, arr)
        return slope0 is not None and np.sign(slope0) == np.sign(slope1)

    def _interp(self, x, y):
        """Estimate slope and interception"""
        slope = (y[-1] - y[0]) / (x[-1] - x[0])
        intercept = y[0] - slope * x[0]
        return intercept, slope

    @docstrings.get_sectionsf('DataReader.find_potential_samples',
                              sections=['Parameters', 'Returns'])
    def find_potential_samples(self, col, min_len=None,
                               max_len=None, filter_func=None):
        """
        Find potential samples in an array

        This method finds extrema in an array and returns the indices where
        the extremum might be. The algorithm thereby filters out obstacles by
        first going over the array, making sure, that there is a change of sign
        in the slope in the found extremum, and if not, ignores it and
        flattens it out.

        Parameters
        ----------
        col: int
            The column for which to find the extrema
        min_len: int
            The minimum length of one extremum. If the width of the interval
            where we found an extrumum is smaller than that, the extremum is
            ignored. If None, this parameter does not have an effect (i.e.
            ``min_len=1``).
        max_len: int
            The maximum length of one extremum. If the width of the interval
            where we found an extrumum is greater than that, the extremum is
            ignored. If None, this parameter does not have an effect.
        filter_func: function
            A function to filter the extreme. It must accept one argument which
            is a list of integers representing the indices of the extremum in
            `a`

        Returns
        -------
        list of list of int of shape (N, 2)
            The list of N extremum locations. Each tuple in this list
            represents an interval `a` where one extremum might be located
        list of list of int
            The excluded extremum locations that are ignored because we could
            not find a change of sign in the slope.

        See Also
        --------
        find_samples
        """
        def find_potential_samples():

            def do_append(indices):
                """Filter by `min_len`, `max_len` and the given `filter_func`
                """
                if min_len is not None and np.diff(indices) <= min_len:
                    return False
                elif max_len is not None and np.diff(indices) > max_len:
                    return False
                elif filter_func is not None:
                    return filter_func(indices)
                return True

            def notnan(idx):
                return not np.isnan(a[idx])

            #: Slope of the previous value. increasing: 1, decreasing: -1
            last_state = 0
            #: Index of the last change
            last_change = 0
            #: The list of indices for the potential extrema locations
            indices = []
            #: The previous value
            prev = a[0]
            #: Boolean that is True, if the previous value `prev` was zero
            was_zero = False
            # recursive iteration through the rows in the column to look for
            # slope changes and zeros.
            for i, val in enumerate(a[1:], 1):
                if np.isnan(val):
                    continue
                state = np.sign(val - prev)  # increasing or decreasing
                # -- 1: If the current value equals the previous, continue
                if not state:
                    pass
                # -- 2: when we encounter a 0 and the previous value was not 0,
                #       there is a sample right here
                elif prev > min_val and val <= min_val:
                    if do_append([i, i+1]):
                        indices.append([i, i+1])
                    was_zero = True
                # -- 3: otherwise, if we increase again, there was a
                #       sample before
                elif prev <= min_val and val > min_val:
                    # if we are closer then 6 pixels to the previous
                    # sample and we were 0 before, we assume that this is
                    # only one sample and merge them
                    if was_zero:
                        last0 = indices[-1][0]
                        # look for the last index, where the value was greater
                        # than 0 and estimate where it should be 0
                        val_last_non0 = a[last0 - 1]
                        last_non0 = last0 - 1 - len(list(takewhile(
                            lambda val: val == val_last_non0,
                            a[last0 - 1:0:-1])))
                        if last_non0:
                            intercept = self._interp(
                                [a[last_non0 - 1], val_last_non0],
                                [last_non0 - 1, last0-1])[0]
                        else:  # we cannot estimate and disable the next check
                            intercept = i - 5

                    else:
                        intercept = i - 5  # disable the next check
                    # if we are closer than 4 pixels to the extrapolated
                    # previous extremum, we assume they do belong to the same
                    if i - intercept <= 4:
                        if do_append([indices[-1][0], i + 1]):
                            indices[-1] = [indices[-1][0], i + 1]
                        else:
                            del indices[-1]
                    elif ((not indices or i-1 not in range(*indices[-1])) and
                          do_append([i-1, i])):
                        indices.append([i-1, i])
                    last_state = state
                    was_zero = False
                else:
                    if not last_state:
                        last_state = state  # set the state at the beginning
                    elif state != last_state:
                        r = list(filter(notnan, range(last_change, i+1)))
                        if do_append([r[0], r[-1]]):
                            indices.append([r[0], r[-1]])
                        last_state = state
                    last_change = i
                    was_zero = False
                prev = val
            # now we verify those locations by looking at their surrounding to
            # see if the slope changes. If not, we smooth the value out
            mask = np.array(list(starmap(self.is_obstacle,
                                         zip(indices, repeat(a)))))
            last = 0  #: the indice of the last obstacle
            old = a.copy()
            for b, l in zip(mask, indices):
                if b:  # the slope is not changing
                    if l[0] <= min_val:
                        v = old[l[-1]]
                    elif l[-1] == len(a) - 1:
                        v = old[l[0] - 1]
                    else:
                        v = min(old[l[0] - 1], old[l[-1]])
                    if last and np.abs(old[last + 1:l[-1]] -
                                       a[l[0]]).max() <= 1:
                        v = min(v, old[last])
                        a[last:l[0]] = v
                    last = l[0]
                    a[l[0]:l[1]] = v

            return ([l for b, l in zip(mask, indices) if not b],
                    [l for b, l in zip(mask, indices) if b])

        a = self.full_df[col].values.copy()
        min_val = 0  #: The minimum data value
        # first try to smooth out bad values
        included0, excluded0 = find_potential_samples()

        included1, excluded1 = find_potential_samples()
        excluded1.extend(excluded0)
        return included1, sorted(excluded1)

    docstrings.delete_params('DataReader.find_potential_samples.parameters',
                             'col')

    @docstrings.get_sectionsf('DataReader.plot_potential_samples')
    @docstrings.with_indent(8)
    def plot_potential_samples(
            self, excluded=False, ax=None, plot_kws={}, *args, **kwargs):
        """Plot the ranges for potential samples

        This method plots the rough locations of potential samples (see
        :meth:`find_potential_samples`

        Parameters
        ----------
        excluded: bool
            If True, plot the excluded samples instead of the included samples
            (see the return values in :meth:`find_potential_samples`)
        ax: matplotlib.axes.Axes
            The matplotlib axes to plot on
        plot_kws: dict
            Any other keyword argument that is passed to the
            :func:`matplotlib.pyplot.plot` function. By default, this is equal
            to ``{'marker': '+'}``
        %(DataReader.find_potential_samples.parameters.no_col)s"""
        vals = self.full_df.values.copy()
        starts = self.column_starts.copy()
        self.sample_ranges = lines = []
        y = np.arange(np.shape(self.image)[0]) + 0.5
        ax = ax or self.ax
        if self.extent is not None:
            y += self.extent[-1]
            starts = starts + self.extent[0]
        plot_kws = dict(plot_kws)
        plot_kws.setdefault('marker', '+')
        for i, (col, arr) in enumerate(zip(self.columns, vals.T)):
            all_indices, excluded_indices = self.find_potential_samples(
                col, *args, **kwargs)
            if excluded:
                all_indices = excluded_indices
            if not all_indices:
                continue
            mask = np.ones(arr.size, dtype=bool)
            for imin, imax in all_indices:
                mask[imin:imax] = False
            arr[mask] = np.nan
            for imin, imax in all_indices:
                lines.extend(ax.plot(starts[i] + arr[imin:imax], y[imin:imax],
                                     **plot_kws))

    @docstrings.with_indent(8)
    def plot_other_potential_samples(self, tol=1, already_found=None,
                                     *args, **kwargs):
        """Plot potential samples that are not yet in the :attr:`samples`
        attribute

        Parameters
        ----------
        tol: int
            The pixel tolerance for a sample. If the distance between a
            potential sample and all already existing sample is greater than
            tolerance, the potential sample will be plotted
        already_found: np.ndarray
            The pixel rows of samples that have already been found. If not
            specified, the index of the :attr:`sample_locs` is used
        %(DataReader.plot_potential_samples.parameters)s"""
        if already_found is None:
            already_found = self.sample_locs.index.values

        def filter_func(indices):
            return not any((np.abs(already_found - v) < tol).any()
                           for v in indices)

        self.plot_potential_samples(
            filter_func=filter_func, *args, **kwargs)

    def get_occurences(self):
        """Extract the positions of the occurences from the selection"""
        selected = self.selected_part
        labeled, num = skim.label(selected, 8, return_num=True)
        if self._column_starts is None:
            bounds = []
        else:
            bounds = self.all_column_bounds
        for l in range(1, num + 1):
            y, x = np.where(labeled == l)
            means = [(s+e)/2 for s, e in bounds
                     if ((x >= s) & (x <= e)).any()] or [x]
            self.occurences.add(
                (int(max(means)), int(np.round(y.mean()))))

    def get_reader_for_col(self, col):
        """Get the reader for a specific column

        Parameters
        ----------
        col: int
            The column of interest

        Returns
        -------
        DataReader or None
            Either the reader or None if no reader could be found"""
        return next((child for child in self.iter_all_readers
                     if not child.is_exaggerated and col in child.columns),
                    None)

    @docstrings.get_sectionsf('DataReader.unique_bars')
    @docstrings.dedent
    def unique_bars(self, min_fract=None, asdict=True, *args, **kwargs):
        """
        Estimate the unique bars

        This method puts the overlapping bars of the different columns together

        Parameters
        ----------
        min_fract: float
            The minimum fraction between 0 and 1 that two bars have to overlap
            such that they are considered as representing the same
            sample. If None, the :attr:`min_fract` attribute is used
        asdict: bool
            If True, dictionaries are returned

        Returns
        -------
        list
            A list of the bar locations. If asdict is True (default), each item
            in the returned list is a dictionary whose keys are the column
            indices and whose values are the indices for the corresponding
            column. Otherwise, a list of :class:`_Bar` objects is returned"""
        def insert_occs(col, indices):
            if col not in occurences:
                return indices
            occs = occurences[col].astype(int)
            for i, (s, e) in enumerate(indices):
                found = occs[(s <= occs) & (e >= occs)]
                if len(found):
                    indices.pop(i)
            indices.extend(zip(occs, occs+1))
            return indices

        min_fract = min_fract or self.min_fract
        occurences = self.occurences_dict
        df = self.parent._full_df
        get_child = self.get_reader_for_col
        bars = list(chain.from_iterable(
            (_Bar(col, indices) for indices in insert_occs(
                 col, get_child(col).find_potential_samples(
                    col, *args, **kwargs)[0]))
            for col in df.columns))
        for bar in bars:
            bar.get_overlaps(bars, min_fract)
        ret = []
        for bar in bars:
            if bar.all_overlaps is None:
                bar.get_all_overlaps()
                ret.append(bar)
        ret = sorted(ret, key=lambda b: b.mean_loc)
        return [b.asdict for b in ret] if asdict else ret

    docstrings.keep_params('DataReader.unique_bars.parameters', 'min_fract')
    docstrings.delete_params(
        'DataReader.find_potential_samples.parameters', 'col')

    @docstrings.get_sectionsf('DataReader.find_samples',
                              sections=['Parameters', 'Returns'])
    @docstrings.dedent
    @only_parent
    def find_samples(self, min_fract=None, pixel_tol=5, *args, **kwargs):
        """
        Find the samples in the diagram

        This function finds the samples using the
        :func:`find_potential_samples`
        function. It combines the found extrema from all columns and estimates
        the exact location using an interpolation of the slope

        Parameters
        ----------
        %(DataReader.unique_bars.parameters.min_fract)s
        %(DataReader.find_potential_samples.parameters.no_col)s

        Returns
        -------
        pandas.DataFrame
            The x- and y-locations of the samples. The index is the
            y-location, the columns are the columns in the :attr:`full_df`.
        pandas.DataFrame
            The rough locations of the samples. The index is the
            y-location of the columns, the values are lists of the potential
            sample locations."""
        # TODO: add iteration from min_len to max_len and uncertainty
        # estimation!
        bars = self.unique_bars(min_fract, asdict=True, *args, **kwargs)
        index = np.zeros(len(bars), dtype=int)
        ncols = len(self._full_df.columns)
        locations = np.zeros((len(bars), ncols))
        rough_locations = -np.ones((len(bars) + 2, ncols * 2), dtype=int)
        full_df = self._full_df
        all_cols = set(range(ncols))
        for i, d in enumerate(bars):
            if any(np.diff(l) == 1 for l in d.values()):
                loc = int(np.round(np.mean(list(chain.from_iterable(
                    np.arange(*l) for l in d.values() if np.diff(l) == 1)))))
            else:
                loc = int(np.round(np.mean(list(chain.from_iterable(
                    starmap(range, d.values()))))))
            index[i] = loc
            for col, (imin, imax) in d.items():
                locations[i, col] = np.round(
                    full_df.iloc[imin:imax, col].mean())
                rough_locations[i + 1, 2*col:2*col+2] = [imin, imax]
            for col in all_cols.difference(d):
                locations[i, col] = full_df.loc[loc, col]

        # check the boundaries if desired by the class
        sl_rough = slice(1, -1)
        if self.samples_at_boundaries:
            notnull = (full_df.notnull() & (full_df > 0)).any(axis=1).values
            first = full_df.index[notnull][0]
            last = full_df.index[notnull][-1]
            if first not in index:
                sl_rough = slice(0, -1)
                index = np.r_[[first], index]
                locations = np.vstack([full_df.loc[[first], :].values,
                                       locations])
                for col in range(ncols):
                    rough_locations[0, 2*col:2*col+2] = [first, first+1]
            if last not in index:
                sl_rough = slice(sl_rough.start, rough_locations.shape[0])
                index = np.r_[index, [last]]
                locations = np.vstack([locations,
                                       full_df.loc[[last], :].values])
                for col in range(ncols):
                    rough_locations[-1, 2*col:2*col+2] = [last, last+1]

        ret_locs = pd.DataFrame(locations, index=index).fillna(0)
        ret_rough = pd.DataFrame(
            rough_locations[sl_rough], index=index,
            columns=pd.MultiIndex.from_product([np.arange(ncols),
                                                ['vmin', 'vmax']]))

        not_duplicated = ~ret_locs.index.duplicated()
        ret_locs = ret_locs[not_duplicated].sort_index()
        ret_rough = ret_rough[not_duplicated].sort_index()

        if pixel_tol is not None:
            ret_locs, ret_rough = self.merge_close_samples(
                ret_locs, ret_rough, pixel_tol)
        # insert *occurences value*
        occurences = self.occurences_dict
        for col, occs in occurences.items():
            vmin, vmax = ret_rough.loc[:, col].T.values
            occs = occs[:, np.newaxis]
            ret_locs.iloc[
                ((vmin[np.newaxis] <= occs) & (vmax > occs)).any(axis=0),
                col] = self.occurences_value

        return ret_locs, ret_rough

    def merge_close_samples(self, locs, rough_locs=None, pixel_tol=5):
        samples = locs.index.values.copy()
        # now we check, that at least 2 pixels lie between the samples.
        # otherwise we merge them together
        mask = np.r_[True, samples[1:] - samples[:-1] > pixel_tol]
        keys, indices = groupby_arr(mask)

        istart = 0 if not keys[0] else 1
        # take the mean of where we have multiple consecutive minima
        # we take every second index, because we are interested in the
        # ``False`` values and the first entry in `keys` is True.
        for j, k in zip(indices[istart::2], indices[istart+1::2]):
            # use the extrema with the smallest widths
            if j - 1 == 0:
                samples[j-1:k] = samples[k-1]
                for i in range(j-1, k-1):
                    locs.iloc[i, :] = locs.iloc[k-1, :].values
            elif k == len(locs):
                samples[j-1:k] = samples[j-1]
            else:
                widths = (rough_locs.iloc[j-1:k, 1::2] -
                          rough_locs.iloc[j-1:k, ::2].values)
                minwidth = np.nanmin(widths[widths > 0].values)
                mask = (widths.values == minwidth).any(axis=1)
                new_loc = samples[j-1:k][mask].mean()
                samples[j-1:k] = new_loc
                for i, ((col, vals), (_, col_widths)) in enumerate(
                        zip(locs.items(), widths.items())):
                    locs.iloc[j-1:k, i] = vals.iloc[
                        vals.index.get_loc(new_loc, 'nearest')]

                    col_mask = (col_widths > 0).values
                    if col_mask.sum() > 1:
                        new_indices = rough_locs.iloc[j-1:k, i*2:i*2+2][
                            col_mask[:, np.newaxis]].values.ravel().tolist()
                        warn("Distinct samples merged from %s in "
                             "column %s!" % (new_indices, col))
                        new_indices.sort()
                        rough_locs.iloc[j-1, 2*i:2*i+2] = [new_indices[0],
                                                           new_indices[-1]]
        locs.index = samples
        rough_locs.index = samples
        not_duplicated = ~locs.index.duplicated()
        return locs.iloc[not_duplicated], rough_locs.iloc[not_duplicated]

    @only_parent
    def _get_sample_locs(self, *args, **kwargs):
        """
        :class:`pandas.DataFrame` of the x- and y-values of the samples

        The index represents the y-location, the columns the locations of the
        samples

        Parameters
        ----------
        ``*args,**kwargs``
            See the :meth:`find_samples` method. Note that parameters
            are ignored if the :attr:`sample_locs` attribute is not None

        See Also
        --------
        samples, rough_locs, find_samples, add_samples"""
        if self._sample_locs is None:
            self.sample_locs, self.rough_locs = self.find_samples(
                *args, **kwargs)
        return self.sample_locs

    @only_parent
    def add_samples(self, samples, rough_locs=None):
        """Add samples to the found ones

        Parameters
        ----------
        samples: series, 1d-array or DataFrame
            The samples. If it is series, we assume that the index
            represents the y-value of the sample and the value the
            x-position (see `xcolumns`). In case of a 1d-array, we assume
            that the data represents the y-values of the samples.
            In case of a DataFrame, we assume that the columns correspond to
            columns in the `full_df` attribute and are True where we have a
            sample.

            Note that the y-values must be in image coordinates (see
            :attr:`extent` attribute).
        rough_locs: DataFrame
            The rough locations of the new samples (see the
            :attr:`rough_locs` attribute)

        See Also
        --------
        samples, rough_locs, find_samples, sample_locs
        """
        if self.sample_locs is None:
            self.sample_locs = pd.DataFrame([], index='sample',
                                            columns=self._full_df.columns)
        if samples.ndim == 2:
            self._add_samples_from_df(samples)
        else:
            self._add_samples_from_array(samples)
        if rough_locs is not None:
            if self._rough_locs is None:
                self._rough_locs = rough_locs
            else:
                self.rough_locs = rough_locs.combine_first(self.rough_locs)
        self._update_rough_locs()

    def _add_samples_from_df(self, samples):
        df = self.sample_locs
        if not len(df):
            self.sample_locs = samples
        else:
            self.sample_locs = df = samples.combine_first(df)

    def _update_rough_locs(self):
        """Reset the rough locations by the samples"""
        df = self.sample_locs
        if self._rough_locs is None:
            missing = df.index
        else:
            missing = df.index[~df.index.isin(self._rough_locs.index)]
        # add missing samples
        if len(missing):
            rough = np.tile(missing[:, np.newaxis], (1, len(df.columns) * 2))
            rough[:, 1::2] += 1
            new = pd.DataFrame(
                rough.astype(int), index=missing,
                columns=pd.MultiIndex.from_product(
                    [df.columns, ['vmin', 'vmax']]))
            if self._rough_locs is None:
                self._rough_locs = new
            else:
                self._rough_locs = new.combine_first(
                    self._rough_locs).astype(int)
        rough = self._rough_locs
        # remove sample that are not in df
        if rough is not None:
            to_remove = rough.index[~rough.index.isin(df.index)]
            if len(to_remove):
                rough.drop(to_remove, inplace=True)

    def _add_samples_from_array(self, samples):
        df = self.sample_locs
        new = self._full_df.loc[samples]
        self.sample_locs = new.combine_first(df)

    @docstrings.get_sectionsf('DataReader.get_disconnected_parts')
    def get_disconnected_parts(self, fromlast=5, from0=10,
                               cross_column=False):
        """Identify parts in the :attr:`binary` data that are not connected

        Parameters
        ----------
        fromlast: int
            A pixel ``x1 > x0`` is considered as disconnected, if it is at
            least ``x1 - x0 >= fromlast``. If this is 0, it is ignored and only
            ``from0`` is considered.
        from0: int
            A pixel is considered as disconnected if it is more than `from0`
            pixels away from the column start. If this is 0, it is ignored and
            only ``fromlast`` is considered
        cross_column: bool
            If False, disconnected features are only marked in the column where
            the disconnection has been detected. Otherwise the entire feature
            is marked

        Returns
        -------
        np.ndarray of dtype bool
            The 2D boolean mask with the same shape as the :attr:`binary` array
            that is True if a data pixel is considered as to be disconnected"""
        def keep_full_labels(dist2prev, labels):
            mask = (dist2prev >= npixels)
            # now we select those cells, where the entire label is selected.
            # For this we compare the bins in the histogram
            selected_part = np.where(mask, labels, 0)
            selection = np.unique(selected_part[selected_part > 0])
            dist2colstart_2d = np.tile(
                np.arange(0, labels.shape[1])[np.newaxis, :],
                (labels.shape[0], 1))
            mask0 = (dist2colstart_2d >= from0) & np.isin(labels, selection)
            selected_part[mask0] = labels[mask0]
            selected_part[~mask0] = 0
            bins = np.arange(0.5, labels.max() + 0.6, 1.)
            selected_bins = np.histogram(selected_part, bins)[0]
            orig_bins = np.histogram(labels, bins)[0]
            return np.where(orig_bins.astype(bool) &
                            (selected_bins == orig_bins))[0] + 1

        labels = self.labels
        if not from0 and not fromlast:
            return np.zeros_like(labels)
        bounds = self.column_bounds
        npixels = fromlast or from0
        selected_labels = []
        if not cross_column:
            ret = np.zeros_like(labels)
        for start, end in bounds:
            col_labels = labels[:, start:end]
            dist2prev = np.zeros_like(col_labels)
            # Now we loop through each rows. This could for sure be speed up
            # using numpys iteration np.nditer or some array functions with
            # cumsum, etc. but it takes only about 1s for an 600dpi image,
            # which is probably okay
            for irow in range(len(labels)):

                row = col_labels[irow]
                locs = np.where(row)[0]
                if not len(locs):
                    continue
                if fromlast:
                    locs = np.r_[locs[0], locs]
                else:
                    locs = np.r_[0, locs]
                # look for gaps in the pixel row
                if fromlast:
                    diffs = locs[1:] - locs[:-1] - 1
                else:
                    diffs = locs[1:]  # check the distance to the column start
                # but only where the labels changed
                diffs[~(row[locs[1:]] - row[locs[:-1]]).astype(bool)] = 0
                # if we have a gap and differing labels, we have a disconnected
                # label and mark everything above as disconnected
                too_high = np.where(diffs >= npixels)[0]
                if len(too_high):
                    diffs[too_high[0]:] = npixels
                dist2prev[irow, :][row.astype(bool)] = diffs
            new_selection = keep_full_labels(dist2prev, col_labels)
            if cross_column:
                selected_labels.extend(new_selection)
            else:
                ret[:, start:end] = np.where(
                    np.isin(col_labels, new_selection), col_labels, 0)

        if not cross_column:
            return ret
        else:
            # now we take all the labels selected labels
            return np.where(np.isin(labels, np.unique(selected_labels)),
                            labels, 0)

    docstrings.delete_params(
        'LabelSelection.enable_label_selection.parameters', 'arr', 'ncolors')

    @docstrings.get_sectionsf('DataReader._show_parts2remove')
    @docstrings.with_indent(8)
    def _show_parts2remove(self, arr, remove=False, select_all=True,
                           selection=None, **kwargs):
        """Convenience method to enable the selection of parts to remove

        Parameters
        ----------
        arr: np.ndarray
            The labeled array that is non-zero where a pixel can be removed. It
            needs to have the same shape as the :attr:`binary` array
        remove: bool
            If True, remove the data in the :attr:`binary` array, etc. If
            False, the
            :meth:`~straditize.label_selection.LabelSelection.enable_label_selection`
            method is envoked and the user can select the features to remove
        select_all: bool
            If True and `remove` is False, all labels in `arr` will be selected
            and the given `selection` is ignored
        selection: np.ndarray of dtype bool
            A boolean mask with the same shape as `arr` that is True where a
            pixel should be selected. If `remove` is True, only this mask
            will be used.
        %(LabelSelection.enable_label_selection.parameters.no_arr|ncolors)s
        """
        kwargs['extent'] = self.extent
        if remove:
            mask = (arr if selection is None else selection).astype(bool)
            self.labels[mask] = 0
            self.binary[mask] = 0
            self.reset_labels()
            self.plot_im.set_array(self.labels)
            if self.magni_plot_im is not None:
                self.magni_plot_im.set_array(self.labels)
        else:
            kwargs.setdefault('zorder', self.plot_im.zorder + 0.1)
            labels, num_labels = skim.label(arr, 8, return_num=True)
            self.enable_label_selection(labels, num_labels, **kwargs)
            if select_all:
                self.select_all_labels()
            elif selection is not None:
                self._selection_arr[labels.astype(bool) &
                                    selection.astype(bool)] = num_labels + 1
                self._select_img.set_array(self._selection_arr)
                self._update_magni_img()

    docstrings.keep_params('DataReader.get_disconnected_parts.parameters',
                           'fromlast', 'from0')

    docstrings.delete_params('DataReader._show_parts2remove.parameters', 'arr')

    def show_disconnected_parts(self, fromlast=5, from0=10, remove=False,
                                **kwargs):
        """Highlight or remove disconnected parts

        Parameters
        ----------
        %(DataReader.get_disconnected_parts.parameters.fromlast|from0)s
        %(DataReader._show_parts2remove.parameters.no_arr)s"""
        arr = self.get_disconnected_parts(fromlast, from0)
        self._show_parts2remove(arr, remove, **kwargs)

    @only_parent
    def merged_binaries(self):
        """Get the binary data from all children and merge them into one array

        Returns
        -------
        np.ndarray of dtype int
            The binary image with the same shape as the :attr:`binary` data"""
        binary = self.binary.copy()
        for child in self.children:
            mask = child.binary.astype(bool)
            binary[mask] = child.binary[mask]
        return binary

    @only_parent
    def merged_labels(self):
        """Get the labeled binary data from all children merged into one array

        Returns
        -------
        np.ndarray of dtype int
            The labeled binary image with the same shape as the
            :attr:`label` data"""
        binary = self.merged_binaries()
        return skim.label(binary, 8, return_num=False)

    @only_parent
    @docstrings.get_sectionsf('DataReader.get_cross_column_features')
    def get_cross_column_features(self, min_px=50):
        """Get features that are contained in two or more columns

        Parameters
        ----------
        min_px: int
            The number of pixels that have to be contained in each column

        Returns
        -------
        np.ndarray of dtype bool
            The 2D boolean mask with the same shape as the :attr:`binary` array
            that is True if a data pixel is considered as to belong to a
            cross column feature"""
        labels = self.merged_labels()
        bins = np.arange(0.5, labels.max() + 0.6, 1.)
        bounds = self.all_column_bounds
        counts = np.zeros((len(bounds), len(bins) - 1))
        for col, (start, end) in enumerate(bounds):
            counts[col] = np.histogram(labels[:, start:end], bins=bins)[0]
        selection = np.where((counts >= min_px).sum(axis=0) > 1)[0] + 1
        self.remove_callbacks['labels'].append(self.remove_in_children)
        return np.where(np.isin(labels, selection), labels, 0)

    @docstrings.with_indent(8)
    def show_cross_column_features(self, min_px=50, remove=False, **kwargs):
        """Highlight and maybe remove cross column features

        Parameters
        ----------
        %(DataReader.get_cross_column_features.parameters)s
        %(DataReader._show_parts2remove.parameters.no_arr)s"""
        arr = self.get_cross_column_features(min_px)
        self._show_parts2remove(arr, remove, **kwargs)

    @docstrings.with_indent(8)
    def show_small_parts(self, n=10, remove=False, **kwargs):
        """Highlight and potentially remove small features in the image

        Parameters
        ----------
        n: int
            The maximal size of a feature to be considered as small
        %(DataReader._show_parts2remove.parameters.no_arr)s

        See Also
        --------
        skimage.morphology.remove_small_objects"""
        arr = self.merged_binaries().astype(bool)
        mask = arr & (~skim.remove_small_objects(arr, n))
        self._show_parts2remove(mask.astype(int), remove, **kwargs)

    @docstrings.get_sectionsf('DataReader.get_parts_at_column_ends')
    def get_parts_at_column_ends(self, npixels=2):
        """Identify parts in the :attr:`binary` data that touch the next column

        Parameters
        ----------
        npixels: int
            If a data pixel is less than `npixels` away from the column end, it
            is considered to be at the column end and marked

        Returns
        -------
        np.ndarray of dtype bool
            A boolean mask with the same shape as the :attr:`binary` data that
            is True where a pixel is considered to be at the column end
        """
        arr = self.binary
        arr_labels = self.labels
        bounds = self.column_bounds
        ret = np.zeros_like(arr)
        dist2colend = np.zeros(ret.shape[1], dtype=int)
        for start, end in bounds:
            dist2colend[start:end] = np.arange(end - start, 0, -1)
        # the distance to the right cell that is not null
        mask = np.zeros(ret.shape, dtype=bool)
        for start, end in bounds:
            labels = []
            for irow in range(len(ret)):
                # reversed row
                row = arr[irow, start:end][::-1]
                if row[0]:  # we are at the end of the column
                    locs = np.where(row)[0]
                    # get the difference to the right cell
                    diffs = locs[1:] - locs[:-1]
                    # find the first cell, that is still connected to the end
                    # of the column
                    still_connected = locs[
                        np.r_[[False], diffs > npixels].argmax() - 1]
                    labels.extend(np.unique(
                        arr_labels[irow, end - still_connected - 1:end]))
            if labels:
                mask[:, start:end] = np.isin(arr_labels[:, start:end], labels)
        ret[mask] = arr[mask]
        return ret

    def show_parts_at_column_ends(self, npixels=2, remove=False, **kwargs):
        """Highlight or remove features that touch the column ends

        Parameters
        ----------
        %(DataReader.get_parts_at_column_ends.parameters)s
        %(DataReader._show_parts2remove.parameters.no_arr)s"""
        arr = self.get_parts_at_column_ends(npixels)
        self._show_parts2remove(arr, remove, **kwargs)

    def draw_figure(self):
        """Draw the matplotlib :attr:`fig` and the :attr:`magni` figure"""
        self.fig.canvas.draw()
        if self.magni is not None:
            self.magni.ax.figure.canvas.draw()

    strat_plot_identifier = 'percentages'

    def plot_results(self, df, ax=None, fig=None, transformed=True):
        """Plot the reconstructed diagram

        This method plots the reconstructed diagram using the psy-strat module.

        Parameters
        ----------
        df: pandas.DataFrame
            The data to plot. E.g. the :attr:`sample_locs` or the
            :attr:`straditize.straditizer.Straditizer.final_df` data
        ax: matplotlib.axes.Axes
            The axes to plot on. If None, a new one is created inside the given
            `fig`
        fig: matplotlib.figure.Figure
            The matplotlib figure to plot on. If not given, the current figure
            (see :func:`matplotlib.pyplot.gcf`) is used
        transformed: bool
            If True, y-axes and x-axes have been translated (see the
            :meth:`px2data_x` and
            :meth:`~straditize.straditizer.Straditizer.px2data_y` methods)

        Returns
        -------
        psyplot.project.Project
            The newly created psyplot project with the plotters
        list of :class:`psy_strat.stratplot.StratGroup` instances
            The groupers for the different columns"""
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        import matplotlib.transforms as mt
        import psyplot.project as psy

        if ax is None:
            fig = fig or plt.figure()
            bbox = mt.Bbox.from_extents(
                mpl.rcParams['figure.subplot.left'],
                mpl.rcParams['figure.subplot.bottom'],
                mpl.rcParams['figure.subplot.right'],
                mpl.rcParams['figure.subplot.top'])
        elif isinstance(ax, (mpl.axes.SubplotBase, mpl.axes.Axes)):
            bbox = ax.get_position()
            fig = ax.figure
        else:  # the bbox is given
            bbox = ax
            fig = fig or plt.gcf()
        x0 = bbox.x0
        y0 = bbox.y0
        height = bbox.height
        total_width = bbox.width
        x1 = x0 + total_width
        r0 = self.get_reader_for_col(0)
        breaks = [0]
        ncols = len(self.all_column_starts)
        for i in range(1, ncols):
            if self.get_reader_for_col(i) is not r0:
                r0 = self.get_reader_for_col(i)
                breaks.append(i)
        groupers = []
        arr_names = []
        df = df.copy()
        df.columns = list(map(str, df.columns))
        ds = df.to_xarray()
        ax0 = None
        with psy.Project.block_signals:
            for i, j in zip(breaks, breaks[1:] + [ncols]):
                grouper = self.get_reader_for_col(i).create_grouper(
                    ds, list(range(i, j)), fig, x0, y0, total_width, height,
                    ax0=ax0, transformed=transformed, colnames=df.columns[i:j])
                arr_names.extend(
                    arr.psy.arr_name for arr in grouper.plotter_arrays)
                groupers.append(grouper)
                ax0 = ax0 or grouper.axes[0]
            sp = psy.gcp(True)(arr_name=arr_names)
            sp[0].psy.update(
                ylabel='%(name)s',
                maskbetween=[self.occurences_value, self.occurences_value+1],
                ytickprops={'left': True, 'labelleft': True}, draw=False)
            for ax, p in sp.axes.items():
                ax_bbox = ax.get_position()
                d = {}
                if ax_bbox.x0 != x0:
                    d['left'] = ':'
                if ax_bbox.x1 != x1:
                    d['right'] = ':'
                p.update(axislinestyle=d, draw=False)
        psy.scp(sp.main)
        psy.scp(sp)
        if df.index[0] < df.index[-1]:
            ax0.invert_yaxis()
        return sp, groupers

    @docstrings.get_sectionsf('DataReader.get_bbox_for_cols')
    def get_bbox_for_cols(self, columns, x0, y0, width, height):
        """Get the boundary boxes for the columns of this reader in the results
        plot

        This method is used by the :meth:`plot_results` method to get the
        Bbox for a :class:`psy_strat.stratplot.StratGroup` grouper

        Parameters
        ----------
        columns: list of int
            The column numbers to use
        x0: float
            The left boundary of the larger Bbox of the stratigraphic diagram
        y0: int
            The upper boundary of the larger Bbox of the stratigraphic diagram
        width: float
            The width of the final axes between 0 and 1
        height: float
            The height of the final axis between 0 and 1

        Returns
        -------
        matplotlib.transforms.Bbox
            The boundary box for the given `columns` in the matplotlib figure

        See Also
        --------
        plot_results"""
        import matplotlib.transforms as mt
        s0 = min(self.all_column_starts)
        total_width = max(self.all_column_ends) - s0
        i = min(columns)
        j = max(columns)
        col0 = self.all_column_starts[i]
        orig_width = self.all_column_ends[j] - col0
        return mt.Bbox.from_bounds(
            x0 + (col0 - s0) / total_width * width, y0,
            orig_width / total_width * width, height)

    docstrings.delete_params('DataReader.get_bbox_for_cols.parameters',
                             'columns')

    @docstrings.with_indent(8)
    def create_grouper(self, ds, columns, fig, x0, y0, width, height, ax0=None,
                       transformed=True, colnames=None, **kwargs):
        """Create the grouper that plots the results

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset with the data
        columns: list of int
            The numbers of the columns for which the grouper should be
            created
        fig: matplotlib.figure.Figure
            The matplotlib figure to plot on
        %(DataReader.get_bbox_for_cols.parameters.no_columns)s
        ax0: matplotlib.axes.Axes
            The larger matplotlib axes whose bounding box shall be used.
        transformed: bool
            If True, y-axes and x-axes have been translated (see the
            :meth:`px2data_x` and
            :meth:`~straditize.straditizer.Straditizer.px2data_y` methods)
        colnames: list of str
            The column names to use in the plot
        ``**kwargs``
            any other keyword argument that is passed to the
            :meth:`psy_strat.stratplot.StratGroup.from_dataset` method

        Returns
        -------
        psy_strat.stratplot.StratGroup
            The grouper that visualizes the given `columns` in the `fig`"""
        from psy_strat.stratplot import strat_groupers
        import psyplot.project as psy
        mp = psy.gcp(True)
        grouper_cls = strat_groupers[self.strat_plot_identifier]

        box = self.get_bbox_for_cols(columns, x0, y0, width, height)
        group = 'Columns %i - %i' % (min(columns), max(columns))
        ds[group] = xr.Variable(
            tuple(), '', attrs={'identifier': self.strat_plot_identifier})
        for col in colnames:
            ds.variables[col].attrs['group'] = group
            ds.variables[col].attrs['maingroup'] = group
        grouper = grouper_cls.from_dataset(
            fig, box, ds, colnames, ax0=ax0, project=mp, group=group, **kwargs)

        bounds = self.all_column_bounds - self.all_column_starts[:, np.newaxis]
        bounds = bounds[columns]
        if transformed:
            try:
                bounds = self.px2data_x(bounds)
            except ValueError:
                pass

        self.resize_axes(grouper, bounds)
        return grouper

    def resize_axes(self, grouper, bounds):
        """Resize the axes based on column boundaries

        This method sets the x-limits for the different columns to the given
        `bounds` and resizes the axes

        Parameters
        ----------
        grouper: psy_strat.stratplot.StratGroup
            The grouper that manages the plot
        bounds: np.ndarray of shape (N, 2)
            The boundaries for the columns handled by the `grouper`"""
        for plotter, (s, e) in zip(grouper.plotters, bounds):
            plotter.update(xlim=(s, e))
        grouper.resize_axes(grouper.axes)

    def remove_plots(self):
        """Remove all plotted artists by this reader"""
        for attr in ['plot_im', 'background', 'magni_plot_im',
                     'magni_background', 'color_plot_im',
                     'magni_color_plot_im']:
            try:
                getattr(self, attr, None).remove()
            except (ValueError, AttributeError):
                pass
            try:
                delattr(self, attr)
            except AttributeError:
                pass


class LineDataReader(DataReader):
    """A data reader for digitizing line diagrams

    This class does not have a significantly different behaviour than the
    base :class:`DataReader` class, but might be improved with more specific
    features in the future"""

    strat_plot_identifier = 'default'


class BarDataReader(DataReader):
    """A DataReader for digitizing bar pollen diagrams

    Compared to the base :class:`DataReader` class, this reader implements a
    different strategy in digitizing and finding the samples. When digitizing
    the full diagram, we try to find the distinct bars using the
    :meth:`get_bars` method. These bars might have to be splitted manually
    if they are not easy to distinguish. One key element to distinguish to
    adjacent bars is the specified `tolerance`.

    The base class works for rectangular bars. If you require rounded bars,
    use the :class:`RoundedBarDataReader`"""

    #: Tolerance to distinguish bars. If x0 is the value in a pixel row y and
    #: x1 the value in the next pixel row y+1, then the two pixel rows are
    #: considered as belonging to different bars if
    #: ``abs(x1 - x0) > tolerance``
    tolerance = 2

    min_len = None

    max_len = None

    _all_indices = None

    _splitted = None

    #: True if the bars are rounded (see the :class:`RoundedBarDataReader` and
    #: the implementation in the :meth:`get_bars` method
    _rounded = False

    #: There should not be samples at the boundaries because the first
    #: sample is in the middle of the first bar
    samples_at_boundaries = False

    #: The minimum fraction of overlap for two bars to be considered as the
    #: same sample (see :meth:`unique_bars`)
    min_fract = 0.9

    @docstrings.dedent
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        %(DataReader.parameters)s
        tolerance: int
            If x0 is the value in a pixel row y and x1 the value in the next
            pixel row y+1, then the two pixel rows are considered as belonging
            to different bars if ``abs(x1 - x0) > tolerance`` (see the
            :meth:`get_bars` method and the :attr:`tolerance` attribute)
        """
        self.tolerance = kwargs.pop('tolerance', self.tolerance)
        super(BarDataReader, self).__init__(*args, **kwargs)

    def __reduce__(self):
        ret = super(BarDataReader, self).__reduce__()
        ret[2]['tolerance'] = self.tolerance
        ret[2]['_all_indices'] = self._all_indices
        ret[2]['_splitted'] = self._splitted
        ret[2]['min_len'] = self.min_len
        ret[2]['max_len'] = self.max_len
        ret[2]['_rounded'] = self._rounded
        ret[2]['min_fract'] = self.min_fract
        if hasattr(self, '_full_df_orig'):
            ret[2]['_full_df_orig'] = self._full_df_orig
        return ret

    nc_meta = DataReader.nc_meta.copy()
    nc_meta.update({
        'bars{reader}_tolerance': {
            'dims': (), 'long_name': 'bar distinguishing tolerance'},
        'bars{reader}_nbars': {
            'dims': 'bars{reader}_column',
            'long_name': 'number of bars per column'},
        'bars{reader}_bars': {
            'dims': ('bars{reader}_bar', 'limit'),
            'long_name': 'Boundaries of bars', 'units': 'px'},
        'bars{reader}_nsplit': {
            'dims': 'bars{reader}_column',
            'long_name': 'number of the splitted bars'},
        'bars{reader}_splitted': {
            'dims': ('bar_split', 'limit'),
            'long_name': 'Boundaries of bars to split', 'units': 'px'},
        'bars{reader}_min_len': {
            'dims': (), 'long_name': 'Minimum length of a bar'},
        'bars{reader}_max_len': {
            'dims': (), 'long_name': 'Maximum length of a bar'},
        'bars{reader}_min_fract': {
            'dims': (),
            'long_name': 'Minimum fraction for overlap estimation'
            },
        'bars{reader}_full_data_orig': {
            'dims': ('ydata', 'bars{reader}_column'),
            'long_name': 'Full digitized data ignoring bars',
            'units': 'px'}
        })

    def to_dataset(self, ds=None):
        # reimplemented to include additional variables
        def v(s):
            return 'bars{reader}_' + s

        ds = super(BarDataReader, self).to_dataset(ds)
        self.create_variable(ds, v('tolerance'), self.tolerance)

        if self._all_indices is not None:
            # save the bars
            self.create_variable(
                ds, v('bars'), list(chain.from_iterable(
                    self._all_indices)))
            self.create_variable(
                ds, v('nbars'), list(map(len, self._all_indices)))

            # save the bars to split
            if self._splitted and any(self._splitted.values()):
                self.create_variable(
                    ds, v('splitted'), list(chain.from_iterable(
                        t[1] for t in sorted(self._splitted.items()))))
                nbars = [len(t[1]) for t in sorted(self._splitted.items())]
                self.create_variable(ds, v('nsplit'), nbars)

        if self.min_len is not None:
            self.create_variable(ds, v('min_len'), self.min_len)
        if self.max_len is not None:
            self.create_variable(ds, v('max_len'), self.max_len)
        self.create_variable(ds, v('min_fract'), self.min_fract)

        if hasattr(self, '_full_df_orig'):
            self.create_variable(ds, v('full_data_orig'),
                                 self._full_df_orig.values)
        return ds

    to_dataset.__doc__ = DataReader.to_dataset.__doc__

    @classmethod
    def from_dataset(cls, ds, *args, **kwargs):
        def v(s):
            return ('bars%i_' % ireader) + s
        if ds['reader_image'].ndim == 4:
            ds = ds.isel(reader=0)
        ret = super(BarDataReader, cls).from_dataset(ds, *args, **kwargs)
        ireader = ds.reader.values

        ret.tolerance = ds[v('tolerance')].values
        ret.min_fract = ds[v('min_fract')].values
        if v('bars') in ds:
            bars = ds[v('bars')].values.tolist()
            nbars = np.cumsum(ds[v('nbars')].values)
            ret._all_indices = [
                bars[s:e] for s, e in zip(chain([0], nbars[:-1]), nbars)]
            # splitted bars
            if v('splitted') in ds:
                bars = ds[v('splitted')].values.tolist()
                nbars = np.cumsum(ds[v('nsplit')].values)
                ret._splitted = {
                    i: bars[s:e]
                    for i, (s, e) in enumerate(zip(chain([0], nbars[:-1]),
                                                   nbars))}
            else:
                ret._splitted = {}
        if v('min_len') in ds:
            ret.min_len = ds[v('min_len')].values
        if v('max_len') in ds:
            ret.max_len = ds[v('max_len')].values
        if v('full_data_orig') in ds:
            ret._full_df_orig = pd.DataFrame(
                ds[v('full_data_orig')].values, columns=ds[v('column')].values)

        return ret

    @docstrings.get_sectionsf('BarDataReader.get_bars')
    def get_bars(self, arr, do_split=False):
        """Find the distinct bars in an array

        Parameters
        ----------
        arr: np.ndarray
            The array to find the bars in
        do_split: bool
            If True and a bar is 1.7 times longer than the mean, it is splitted
            into two.

        Returns
        -------
        list of list of ints
            The list of the distinct positions of the bars
        list of floats
            The heights for each of the bars
        list of list of ints
            The indices of bars that are longer than 1.7 times the mean of the
            other bars and should be splitted. If `do_split` is True, they have
            been splitted already
        """

        def isnan_or_0(v):
            return np.isnan(v) | (v == 0)

        def remove_too_short(val=None, fraction=None):
            lengths = np.array(list(map(np.diff, all_indices)))
            if fraction:
                val = fraction * np.median(lengths)
            too_short = lengths < val

            removed = 0
            for i in np.where(too_short)[0]:
                del all_indices[i - removed]
                del heights[i - removed]
                removed += 1

        def split_too_long(val=None, fraction=None):
            lengths = np.array(list(map(np.diff, all_indices)))
            median = np.median(lengths)
            rounded_median = np.round(median).astype(int)
            if fraction is not None:
                val = fraction * median
            too_long = lengths > val
            inserted = 0
            to_split = np.where(too_long)[0]
            for i in to_split:
                indices = all_indices[i + inserted]
                splitted.append(indices)
                if not do_split:
                    continue
                ni = np.diff(indices)
                nbars = np.ceil(ni / median).astype(int)
                not_inserted = 0
                del all_indices[i + inserted]
                del heights[i + inserted]
                for j in range(nbars-1, -1, -1):
                    sub_indices = [indices[0] + j*rounded_median,
                                   indices[0] + (j+1)*rounded_median]
                    if np.diff(sub_indices):
                        all_indices.insert(i + inserted, sub_indices)
                        heights.insert(i + inserted,
                                       arr[slice(*sub_indices)].max())
                    else:
                        not_inserted += 1
                inserted += nbars - 1 - not_inserted

        all_indices = []
        heights = []
        try:
            last_start = np.where(~isnan_or_0(arr))[0][0]
        except IndexError:  # no data in here
            return [], [], []
        last_end = last_start
        last_val = last_start_val = arr[last_end]
        last_state = state = 1  #: state for increasing (1) or decreasing (-1)
        nrows = len(arr) - 1
        for i, value in enumerate(arr[last_start+1:], last_start + 1):
            if not isnan_or_0(value) and not isnan_or_0(last_val):
                state = np.sign(value - last_val)
            else:
                state = 0
            if i == nrows:
                last_end += 1
            if isnan_or_0(last_val) and not isnan_or_0(value):
                last_start = i
                last_start_val = value
            elif ((isnan_or_0(value) and not isnan_or_0(last_val)) or
                  (self._rounded and state and state > last_state and
                   not self.is_obstacle([i], arr)) or
                  (np.abs(value - last_start_val) > self.tolerance) or
                  (not isnan_or_0(value) and i == nrows)):
                indices = [last_start, last_end + 1]
                all_indices.append(indices)
                heights.append(arr[slice(*indices)].max())
                last_start = i
                last_start_val = value
            last_end = i
            last_val = value
            if state:
                last_state = state
        # now we remove those indices, where we are way too short
        if self.min_len is not None:
            remove_too_short(self.min_len)
        remove_too_short(fraction=0.4)
        # now we check, if we accidently put multiple bars together
        splitted = []
        if self.max_len is not None:
            split_too_long(self.max_len)
        split_too_long(fraction=1.7)
        # now we remove those indices, where we are way too short
        remove_too_short(fraction=0.4)
        return all_indices, heights, splitted

    docstrings.keep_params('BarDataReader.get_bars.parameters', 'do_split')
    docstrings.keep_params('DataReader.digitize.parameters', 'inplace')

    @docstrings.with_indent(8)
    def digitize(self, do_split=False, inplace=True):
        """Reimplemented to ignore the rows between the bars

        Parameters
        ----------
        %(BarDataReader.get_bars.parameters.do_split)s
        %(DataReader.digitize.parameters.inplace)s
        """
        df = super(BarDataReader, self).digitize(inplace=False)
        # now we only keep those values that are the same as their surroundings
        if inplace:
            self._full_df_orig = df.copy(True)
        self._all_indices = []
        self._splitted = {}
        for col in df.columns:
            indices, values, splitted = self.get_bars(df[col].values,
                                                      do_split)
            self._all_indices.append(indices)
            self._splitted[col] = splitted
            df.loc[:, col] = np.nan
            for (i, j), v in zip(indices, values):
                df.loc[i:j, col] = v
        if inplace:
            self.full_df = df
        else:
            return df

    def shift_vertical(self, pixels):
        """Shift the columns vertically.

        Parameters
        ----------
        pixels: list of floats
            The y-value for each column for which to shift the values. Note
            that theses values have to be greater than or equal to 0"""
        super(BarDataReader, self).shift_vertical(pixels)
        if not self._all_indices:
            return
        pixels = np.asarray(pixels)
        npx = len(pixels)
        for col, pixel in zip_longest(
                self.columns,
                pixels[[col for col in self.columns if col < npx]],
                fillvalue=pixels[-1]):
            if pixel:  # shift the column upwards
                for l in chain(self._all_indices[col], self._splitted[col]):
                    for j in range(len(l)):
                        l[j] = max(0, l[j] - pixel)

    @docstrings.dedent
    def find_potential_samples(self, col, min_len=None,
                               max_len=None, filter_func=None):
        """
        Find the bars in the column

        This method gets the bars in the given `col` and returns the distinct
        indices

        Parameters
        ----------
        %(DataReader.find_potential_samples.parameters)s

        Returns
        -------
        %(DataReader.find_potential_samples.returns)s

        See Also
        --------
        find_samples
        """

        def do_append(indices):
            if min_len is not None and np.diff(indices) <= min_len:
                return False
            elif max_len is not None and np.diff(indices) > max_len:
                return False
            elif filter_func is not None:
                return filter_func(indices)
            return True
        col = list(self.columns).index(col)
        return list(filter(do_append, self._all_indices[col])), []

    def create_grouper(self, ds, columns, *args, **kwargs):
        group = 'Columns %i - %i' % (min(columns), max(columns))
        return super().create_grouper(ds, columns, *args, use_bars=[group],
                                      **kwargs)

    create_grouper.__doc__ = DataReader.create_grouper.__doc__


class _Bar(object):
    """An object representing one bar in a pollen diagramm"""

    @property
    def loc(self):
        """The location of the bar"""
        try:
            return self._loc
        except AttributeError:
            self._loc = np.mean(self.indices)
        return self._loc

    @property
    def iloc(self):
        """The :attr:`loc` as integer"""
        return np.round(self.loc).astype(int)

    @property
    def mean_loc(self):
        if self.all_overlaps is not None:
            return np.mean(list(chain.from_iterable(
                b.indices for b in self.all_overlaps)))
        elif self.overlaps is not None:
            return np.mean(list(chain.from_iterable(
                b.indices for b in self.overlaps + [self])))
        return self.loc

    @property
    def imean_loc(self):
        return np.round(self.mean_loc).astype(int)

    @property
    def cols_map(self):
        ret = defaultdict(list)
        if self.all_overlaps:
            bars = self.all_overlaps
        elif self.overlaps:
            bars = self.overlaps + [self]
        else:
            bars = [self]
        for bar in bars:
            ret[bar.col].append(bar)
        for col, bars in ret.items():
            if len(bars) > 1:
                warn("Could not separate bars at %s in column %s!" % (
                        self.mean_loc, col))
                break
        return dict(ret)

    @property
    def asdict(self):
        cols_map = self.cols_map
        ret = {col: sorted(chain.from_iterable(b.indices for b in bars))
               for col, bars in cols_map.items()}
        return {col: [l[0], l[1]] for col, l in ret.items()}

    #: Other bars that overlap for at least 70%
    overlaps = None

    #: bars from :attr:`overlaps` plus their :attr:`overlaps`
    all_overlaps = None

    def __init__(self, col, indices):
        self.col = col
        self.indices = indices

    def bar_filter(self, bar):
        """Check if the given bar might overlap"""
        if bar.col == self.col:
            return False
        elif bar.indices[0] > self.indices[-1]:
            return False
        elif bar.indices[-1] < self.indices[0]:
            return False
        return True

    def get_overlaps(self, bars, min_fract=0.9, closest=True):

        def dist(bar):
            return np.abs(self.loc - bar.loc)

        d = defaultdict(list)
        vmin1, vmax1 = self.indices
        n1 = vmax1 - vmin1
        for bar in filter(self.bar_filter, bars):
            vmin2, vmax2 = bar.indices
            min_len = min(n1, vmax2 - vmin2)
            if (min(vmax1, vmax2) - max(vmin1, vmin2) >=
                    min(min_len - 1, min_fract * min_len)):
                d[bar.col].append(bar)
        # if we found multiple bars per column, we take the one that is the
        # closest
        if closest:
            for col, l in filter(lambda t: len(t[1]) > 1, d.items()):
                d[col] = [min(l, key=dist)]
        self.overlaps = list(chain.from_iterable(d.values()))

    def get_all_overlaps(self):

        def insert_overlaps(bar):
            for b in bar.overlaps:
                if (b.all_overlaps is None and b not in all_overlaps and
                        b.col not in cols):
                    all_overlaps.append(b)
                    cols.append(b.col)
                    insert_overlaps(b)

        if self.all_overlaps is not None:
            return

        all_overlaps = [self]
        cols = [self.col]
        insert_overlaps(self)
        for bar in all_overlaps:
            bar.all_overlaps = all_overlaps[:]


class RoundedBarDataReader(BarDataReader):
    """A bar data reader that can be used for rounded bars"""

    _rounded = True

    tolerance = 10


readers = {
    'area': DataReader,
    'bars': BarDataReader,
    'rounded bars': RoundedBarDataReader,
    'line': LineDataReader,
    }
