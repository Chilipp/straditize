# -*- coding: utf-8 -*-
"""Core module of the Straditizer class"""
import six
import gc
import weakref
from copy import copy
from collections import OrderedDict
from itertools import chain
import numpy as np
import pandas as pd
import pickle
from importlib import import_module
import straditize.cross_mark as cm
import straditize.binary as binary
from straditize.label_selection import LabelSelection
from psyplot.data import Signal, safe_list
from straditize.magnifier import Magnifier
from straditize.navigation_slider import (HorizontalNavigationSlider,
                                          VerticalNavigationSlider)
from psyplot.utils import _temp_bool_prop
import skimage.morphology as skim
import xarray as xr


common_attributes = [
    'Digitized by', 'sitename', 'sigle', 'Lon', 'Lat', 'Archive', 'Country',
    'Elevation', 'Restricted', 'Reference', 'DOI', 'Y-axis name',
    'Data type', 'Is modern']

default_attrs = pd.DataFrame(
    np.zeros((len(common_attributes), 1), dtype=object),
    columns=[0], index=common_attributes)

default_attrs.loc[:, :] = ''


def format_coord_func(ax, ref):
    """Create a function that can replace the
    :func:`matplotlib.axes.Axes.format_coord`

    Parameters
    ----------
    ax: matplotlib.axes.Axes
        The axes instance
    ref: weakref.weakref
        The reference to the :class:`Straditizer` instance

    Returns
    -------
    function
        The function that can be used to replace `ax.format_coord`
    """
    orig_format_coord = ax.format_coord

    def func(x, y):
        orig_s = orig_format_coord(x, y)
        stradi = ref()
        if stradi is None or stradi.data_reader is None:
            return orig_s
        data_x = x - stradi.data_xlim[0]
        data_y = y - stradi.data_ylim[0]
        orig_s += 'DataReader: x=%s y=%s' % (ax.format_xdata(data_x),
                                             ax.format_ydata(data_y))
        if (stradi.data_reader._column_starts is not None and
                x > stradi.data_xlim[0] and x < stradi.data_xlim[1]):
            col = next(
                (i for i, (s, e) in enumerate(
                    stradi.data_reader.all_column_bounds)
                 if data_x >= s and data_x <= e),
                None)
            if col is not None:
                col_x = data_x - stradi.data_reader.all_column_starts[col]
                orig_s += 'Column %i x=%s' % (col, ax.format_xdata(col_x))
        return orig_s

    return func


def _create_magni_marks(magni, marks):
    """Copy the created marks to the magnifiers axes"""
    magni_marks = []
    if magni is not None:
        ax = magni.ax
        for m in marks:
            m2 = copy(m)
            m2.ax = ax
            m2.draw_lines()
            m2._animated = False
            m2.connect()
            m.maintain_x([m, m2])
            m.maintain_y([m, m2])
        magni.ax.figure.canvas.draw()
    return magni_marks


def _new_mark_factory(marks, mark_added, func, fignum, magnifier=None,
                      magni_marks=None):
    def ret(event):
        import matplotlib.pyplot as plt
        fig = plt.figure(fignum)
        axes = fig.axes
        if (event.key != 'shift' or event.button != 1 or
                event.inaxes not in axes or
                fig.canvas.manager.toolbar.mode != ''):
            return
        new_marks = _new_mark(event.xdata, event.ydata)
        for m in new_marks:
            mark_added.emit(m)

    def _new_mark(x, y, **kwargs):
        new_marks = func((x, y), **kwargs)
        if new_marks:
            try:
                marks.extend(new_marks)
            except TypeError:
                new_marks = [new_marks]
                marks.extend(new_marks)
            if magnifier is not None:
                magni_marks.extend(_create_magni_marks(magnifier, new_marks))
        marks[0].ax.figure.canvas.draw_idle()
        return new_marks
    return ret, _new_mark


class Straditizer(LabelSelection):
    """An object to digitize a stratographic pollen diagram
    """

    #: A signal that is emitted if a mark has been added. Functions are
    #: expected to accept one argument, the newly created
    #: :class:`straditize.cross_mark.CrossMarks` instance
    mark_added = Signal('_mark_added')

    #: A signal that is emitted, if a mark has been removed. Functions are
    #: expected to accept one argument, the removed
    #: :class:`straditize.cross_mark.CrossMarks` instance
    mark_removed = Signal('_mark_removed')

    block_signals = _temp_bool_prop(
        'block_signals', "Block the emitting of signals of this instance")

    #: :class:`pandas.DataFrame`. The attributes of this straditizer
    attrs = None

    @property
    def valid_attrs(self):
        attrs = self.attrs
        return attrs[attrs.index.notnull() &
                     np.asarray(attrs.index.astype(bool))]

    @property
    def attrs_dict(self):
        return OrderedDict(self.valid_attrs.iloc[:, 0].items())

    @attrs_dict.setter
    def attrs_dict(self, value):
        self.attrs = pd.DataFrame.from_dict(value, orient='index')

    @property
    def fig(self):
        return getattr(self.ax, 'figure', None)

    @property
    def indexes(self):
        if self._indexes is None:
            shape = np.shape(self.image)
            self._indexes = {'x': pd.Index(np.arange(shape[1])),
                             'y': pd.Index(np.arange(shape[0]))}
        return self._indexes

    @property
    def column_indexes(self):
        """The horizontal indexes for each column"""
        bounds = self.data_reader.all_column_bounds + self.data_xlim[0]
        return [
            pd.Index(np.arange(*se)) for se in bounds]

    #: The :class:`straditize.binary.DataReader` instance to digitize the
    #: data
    data_reader = None

    data_xlim = None

    data_ylim = None

    #: The :class:`straditize.ocr.ColNamesReader` for reading the column names
    colnames_reader = None

    colnames_xlim = None

    colnames_ylim = None

    _orig_format_coord = None

    _yaxis_px_orig = None

    @property
    def yaxis_px(self):
        if self._yaxis_px_orig is None:
            raise ValueError("Y-axis informations have not yet been inserted!")
        if self.data_ylim is None:
            raise ValueError("The data limits have not been set yet!")
        return np.asarray(self._yaxis_px_orig) - np.min(self.data_ylim)

    @yaxis_px.setter
    def yaxis_px(self, value):
        if value is None:
            self._yaxis_px_orig = None
        else:
            self._yaxis_px_orig = np.asarray(value) + np.min(self.data_ylim)

    yaxis_data = None

    mark_cids = set()

    text_reader = None

    _indexes = None

    _horizontal_slider = None

    _vertical_slider = None

    #: The matplotlib axes
    ax = None

    @property
    def full_df(self):
        if self.data_reader is None or self.data_reader.full_df is None:
            return None
        return self._finalize_df(self.data_reader.full_df.copy(True))

    @property
    def final_df(self):
        if (self.data_reader is None or self.data_reader.full_df is None or
                self.data_reader.sample_locs is None):
            return None
        ret = self._finalize_df(self.data_reader.sample_locs.copy(True))
        ret.fillna(0.0, inplace=True)
        return ret

    def get_labels(self, categorize=1):
        arr = binary.DataReader.to_grey_pil(self.image)
        if categorize > 1:
            import pandas as pd
            shape = arr.shape
            bins = np.r_[0, np.arange(1, 260 + categorize, categorize)]
            arr = pd.cut(arr.ravel(), bins, labels=False).reshape(shape)
        return skim.label(arr, 8, return_num=False)

    def image_array(self):
        return np.asarray(self.image)

    label_arrs = ['image_array']

    def __init__(self, image, ax=None, plot=True, attrs=None):
        """
        Parameters
        ----------
        image: PIL.Image.Image or np.ndarray
            The image file to process. A numpy array should be 3D with shape
            ``(Y, X, 4)``, where the last channel [..., -1] should represent
            the alpha channel. A PIL.Image.Image will be converted to a
            RGBA image (if not already)
        ax: matplotlib.axes.Axes
            The matplotlib axes. If None, a new one will be created
        attrs: dict or :class:`pandas.DataFrame`
            The attributes for this straditizer
        """
        from PIL import Image
        if attrs is None:
            self.attrs = default_attrs.copy(True)
        elif isinstance(attrs, dict):
            self.attrs_dict = attrs
        else:
            self.attrs = attrs
        if isinstance(image, six.string_types):
            self.set_attr('image_file', image)
            image = Image.open(image)
        try:
            mode = image.mode
        except AttributeError:
            image = Image.fromarray(image, mode='RGBA')
        else:
            if mode != 'RGBA':
                image = image.convert('RGBA')
        self.image = image
        self.ax = ax
        if plot:
            self.plot_image()
        self.marks = None
        self.magni_marks = []
        self.mark_cids = set()
        self.remove_callbacks = {'image_array': [self.update_image]}

    def plot_image(self, ax=None, **kwargs):
        draw_slider = (self._horizontal_slider is None or self.ax is None or
                       ax is not self.ax)
        ax = ax or self.ax
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.subplots()[1]
        self.ax = ax
        extent = [0] + list(np.shape(self.image)[:2][::-1]) + [0]
        kwargs.setdefault('extent', extent)
        self.plot_im = ax.imshow(self.image, **kwargs)
        ax.grid(False)
        self.magni = Magnifier(ax, image=self.image, **kwargs)
        if draw_slider:
            self._horizontal_slider = HorizontalNavigationSlider(ax)
            self._vertical_slider = VerticalNavigationSlider(ax)
        if self._orig_format_coord is None:
            self._orig_format_coord = ax.format_coord
            ax.format_coord = format_coord_func(ax, weakref.ref(self))

    def set_attr(self, key, value):
        """Update an attribute in the :attr:`attrs`"""
        self.attrs.loc[key] = value

    def get_attr(self, key):
        return self.attrs.loc[key].iloc[0]

    def __reduce__(self):
        return (
            self.__class__,
            (self.image, None, False, self.attrs),
            {'data_reader': self.data_reader,
             'data_xlim': self.data_xlim, 'data_ylim': self.data_ylim,
             '_yaxis_px_orig': self._yaxis_px_orig,
             'yaxis_data': self.yaxis_data}
            )

    nc_meta = {
        'axis': {'long_name': 'Axis coordinate'},
        'limit': {'long_name': 'Minimum and maximum limit'},
        'px_data': {
            'long_name': 'Coordinate for pixel-to-data translations'},
        'image': {
            'dims': ('y', 'x', 'rgba'),
            'long_name': 'Full stratigraphic diagram',
            'units': 'color'},
        'data_lims': {
            'dims': ('axis', 'limit'),
            'long_name': 'Limits of the data diagram',
            'units': 'px'},
        'yaxis_translation': {
            'dims': ('px_data', 'limit'),
            'long_name': 'Pixel to data mapping for y-axis'},
        }

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
        for key, val in self.attrs_dict.items():
            ds.attrs[key] = val

        self.create_variable(ds, 'axis', ['y', 'x'])
        self.create_variable(ds, 'limit', ['vmin', 'vmax'])
        self.create_variable(ds, 'px_data', ['pixel', 'data'])

        # full straditizer image
        self.create_variable(ds, 'image', self.image)
        # get the data_xlim and data_ylim
        if self.data_xlim is not None and self.data_ylim is not None:
            self.create_variable(
                ds, 'data_lims', np.vstack([self.data_ylim, self.data_xlim]))
        if self._yaxis_px_orig is not None:
            self.create_variable(
                ds, 'yaxis_translation',
                np.vstack([self._yaxis_px_orig, self.yaxis_data]))
        if self.data_reader is not None:
            self.data_reader.to_dataset(ds)
        return ds

    def create_variable(self, ds, vname, data, **kwargs):
        """Insert the data into a variable in an :class:`xr.Dataset`"""
        attrs = self.nc_meta[vname].copy()
        dims = safe_list(attrs.pop('dims', vname))
        if vname in ds:
            ds.variables[vname][kwargs] = data
        else:
            v = xr.Variable(
                dims, np.asarray(data), attrs=attrs)
            ds[vname] = v
        return vname

    @classmethod
    def from_dataset(cls, ds, ax=None, plot=True):
        """Create a new :class:`Straditizer` from a dataset

        This method uses a dataset that has been exported with the
        :meth:`to_dataset` method to intialize a new reader"""
        stradi = cls(ds['image'].values, ax=ax, plot=plot,
                     attrs=ds.attrs)
        if 'data_lims' in ds:
            stradi.data_xlim = ds['data_lims'].sel(axis='x').values
            stradi.data_ylim = ds['data_lims'].sel(axis='y').values
        if 'yaxis_translation' in ds:
            stradi._yaxis_px_orig = ds['yaxis_translation'].sel(
                px_data='pixel').values
            stradi.yaxis_data = ds['yaxis_translation'].sel(
                px_data='data').values
        if 'reader_image' in ds:
            parent = None
            x0, x1 = map(int, stradi.data_xlim)
            y0, y1 = map(int, stradi.data_ylim)
            extent = [x0, x1, y1, y0]
            for i, (modname, clsname) in enumerate(zip(ds.reader_mod.values,
                                                       ds.reader_cls.values)):
                mod = import_module(str(modname))
                reader_cls = getattr(mod, str(clsname))
                reader = reader_cls.from_dataset(
                    ds.isel(reader=i), ax=stradi.ax, plot=plot, extent=extent,
                    parent=parent, magni=stradi.magni,
                    plot_background=plot and parent is None)
                if parent is not None:
                    parent.children.append(reader)
                else:
                    stradi.data_reader = parent = reader
        return stradi

    def draw_figure(self):
        self.ax.figure.canvas.draw()
        if self.magni is not None:
            self.magni.ax.figure.canvas.draw()

    def marks_for_data_selection(self, nums=2):
        def new_mark(pos):
            if len(self.marks) == nums:
                raise ValueError("Cannot use more than %i marks!" % nums)
            return cm.CrossMarks(pos, ax=self.ax, idx_h=idx_h,
                                 idx_v=idx_v, zorder=2, c='b',
                                 xlim=xlim, ylim=ylim)

        if self.data_xlim is not None and self.data_ylim is not None:
            x0, x1 = self.data_xlim
            y0, y1 = self.data_ylim
        else:
            x0 = x1 = np.mean(self.ax.get_xlim())
            y0 = y1 = np.mean(self.ax.get_ylim())
        Ny, Nx = np.shape(self.image)[:2]
        xlim = (0, Nx)
        ylim = (Ny, 0)
        positions = [(x0, y0), (x1, y1), (x0, y1), (x1, y0)]
        indexes = self.indexes
        idx_h = indexes['x']
        idx_v = indexes['y']
        self.remove_marks()
        if self.data_xlim is not None and self.data_ylim is not None:
            self.marks = [
                cm.CrossMarks(positions[i], ax=self.ax, idx_h=idx_h,
                              idx_v=idx_v, zorder=2, c='b',
                              xlim=xlim, ylim=ylim)
                for i in range(nums)]
            self.marks[0].connect_marks(self.marks)
            self.create_magni_marks(self.marks)
        else:
            self.marks = []
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark)))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))

    def create_magni_marks(self, marks):
        """Copy the created marks to the magnifiers axes"""
        if self.magni is not None:
            ax = self.magni.ax
            for m in marks:
                m2 = copy(m)
                m2.ax = ax
                m2.draw_lines()
                m2._animated = False
                m2.connect()
                m.maintain_x([m, m2])
                m.maintain_y([m, m2])
                self.magni_marks.append(m2)
            self.magni.ax.figure.canvas.draw()

    def update_data_part(self):
        marks = self.marks
        x = np.unique(np.ceil([m.pos[0] for m in marks]))
        y = np.unique(np.ceil([m.pos[1] for m in marks]))
        if len(x) != 2:
            raise ValueError(
                "Need exactly two x-values for extracting the data! Got %i" % (
                    len(x)))
        if len(y) != 2:
            raise ValueError(
                "Need exactly two y-values for extracting the data! Got %i" % (
                    len(y)))
        self.data_xlim = x
        self.data_ylim = y
        self.remove_marks()
        self.draw_data_box()

    def update_colnames_part(self):
        marks = self.marks
        x = np.unique(np.ceil([m.pos[0] for m in marks]))
        y = np.unique(np.ceil([m.pos[1] for m in marks]))
        if len(x) != 2:
            raise ValueError(
                "Need exactly two x-values for extracting the data! Got %i" % (
                    len(x)))
        if len(y) != 2:
            raise ValueError(
                "Need exactly two y-values for extracting the data! Got %i" % (
                    len(y)))
        self.colnames_xlim = x
        self.colnames_ylim = y
        self.remove_marks()
        self.draw_colnames_box()

    def _draw_box(self, xlim, ylim):
        box = self.ax.bar(xlim[0], np.diff(ylim)[0], np.diff(xlim)[0],
                          ylim[0], edgecolor='r', facecolor='none',
                          align='edge', linewidth=2)[0]
        if self.magni is not None:
            magni_box = self.magni.ax.bar(
                xlim[0], np.diff(ylim)[0], np.diff(xlim)[0], ylim[0],
                edgecolor='r', facecolor='none', align='edge', linewidth=2)[0]
        else:
            magni_box = None
        return box, magni_box

    def draw_data_box(self):
        # plot a box around the plot
        self.remove_data_box()
        self.data_box, self.magni_data_box = self._draw_box(
            self.data_xlim, self.data_ylim)

    def remove_data_box(self):
        """Remove the data_box"""
        if getattr(self, 'data_box', None) is not None:
            try:
                self.data_box.remove()
            except ValueError:
                pass
            del self.data_box
        if getattr(self, 'magni_data_box', None) is not None:
            try:
                self.magni_data_box.remove()
            except ValueError:
                pass

    def draw_colnames_box(self):
        # plot a box around the plot
        self.remove_colnames_box()
        self.colnames_box, self.magni_colnames_box = self._draw_box(
            self.colnames_xlim, self.colnames_ylim)

    def remove_colnames_box(self):
        """Remove the colnames_box"""
        if getattr(self, 'colnames_box', None) is not None:
            try:
                self.colnames_box.remove()
            except ValueError:
                pass
            del self.colnames_box
        if getattr(self, 'magni_colnames_box', None) is not None:
            try:
                self.magni_colnames_box.remove()
            except ValueError:
                pass

    def marks_for_x_values(self, at_col_start=True):
        """Create two marks for selecting the x-values

        Parameters
        ----------
        at_col_start: bool
            If True, and no translation has yet been performed, create a mark
            at the column start and ask for the corresponding value
        """
        def new_mark(pos, initial=None, label=None, **kwargs):
            if len(self.marks) == 2:
                raise ValueError("Cannot use more than 2 marks!")
            ret = cm.DraggableVLineText(
                np.round(pos[0]), ax=self.ax, idx_h=idx_h, zorder=2,
                message=msg, dtype=float, c='b', **kwargs)
            if 'value' not in kwargs:
                ret.ax.figure.canvas.draw_idle()
                ret.ask_for_value(initial, label)
            return ret

        idx_h = self.indexes['x']
        self.remove_marks()
        msg = 'Enter the x-axis value for this point.'
        self.marks = marks = []
        reader = self.data_reader
        if reader._xaxis_px_orig is not None:
            x0, x1 = reader._xaxis_px_orig
            marks.append(new_mark((x0, 0), value=reader.xaxis_data[0]))
            marks.append(new_mark((x1, 0), value=reader.xaxis_data[1]))

            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        elif at_col_start:
            starts = reader.column_starts + self.data_xlim[0]
            xmin, xmax = self.ax.get_xlim()
            visible_col = next(
                (s for s in starts if s >= xmin and s <= xmax), None)
            if visible_col is not None:
                marks.append(new_mark(
                    (visible_col, 0), 0, 'Enter the value at column start'))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark)))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))

    def update_xvalues(self):
        minmark, maxmark = sorted(self.marks, key=lambda m: m.value)
        self.data_reader._xaxis_px_orig = np.ceil([minmark.x, maxmark.x])
        self.data_reader.xaxis_data = np.array([minmark.value, maxmark.value])
        self.remove_marks()

    def marks_for_y_values(self):
        """Create two marks for selecting the x-values"""
        def new_mark(pos, **kwargs):
            if len(self.marks) == 2:
                raise ValueError("Cannot use more than 2 marks!")
            ret = cm.DraggableHLineText(
                np.round(pos[1]), ax=self.ax, idx_v=idx_v, c='b', zorder=2,
                message=msg, dtype=float, **kwargs)
            if 'value' not in kwargs:
                ret.ax.figure.canvas.draw_idle()
                ret.ask_for_value()
            return ret
        idx_v = self.indexes['y']
        self.remove_marks()
        msg = 'Enter the y-axis value for this point.'
        self.marks = marks = []
        if self._yaxis_px_orig is not None:
            y0, y1 = self._yaxis_px_orig
            marks.append(new_mark((0, y0), value=self.yaxis_data[0]))
            marks.append(new_mark((0, y1), value=self.yaxis_data[1]))

            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark)))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))

    def update_yvalues(self):
        minmark, maxmark = sorted(self.marks, key=lambda m: m.value)
        self._yaxis_px_orig = np.ceil([minmark.y, maxmark.y])
        self.yaxis_data = np.array([minmark.value, maxmark.value])
        self.remove_marks()

    def marks_for_vertical_alignment(self):
        """Create marks for vertical alignment of the columns

        This method creates one mark for each column. These marks should then
        be moved to positions that should be on the same vertical level.
        After that, the :meth:`align_columns` method has to be called"""
        if self.data_reader is None:
            raise ValueError(
                "The data_reader has not yet been initialized! Use the "
                "init_reader method!")
        extent = self.data_reader.extent
        y0 = min(extent[2:]) if extent else 0
        x0 = extent[0] if extent else 0
        bounds = x0 + self.data_reader.column_bounds.astype(int)
        self.marks = [
            cm.CrossMarks((x0, y0), ax=self.ax,
                          idx_v=self.indexes['y'],
                          idx_h=pd.Index(np.arange(x0, x1)),
                          xlim=self.data_xlim, ylim=self.data_ylim, lock=False,
                          zorder=2)
            for x0, x1 in bounds]
        self.create_magni_marks(self.marks)

    def align_columns(self):
        """Shift the columns after the marks have been moved

        This method should be called after the
        :meth:`marks_for_vertical_alignment` method to align the columns
        """
        shifts = np.array([m.y for m in self.marks]).astype(int)
        shifts -= shifts.min()
        self.data_reader.shift_vertical(shifts)
        self.remove_marks()

    def px2data_y(self, coord):
        """Transform the pixel coordinates into data coordinates

        Parameters
        ----------
        coord: 1D np.ndarray
            The coordinate values in pixels

        Returns
        -------
        np.ndarray
            The numpy array with transformed coordinates"""
        y_px = self.yaxis_px
        y_data = self.yaxis_data
        diff_px = np.diff(y_px)[0]
        diff_data = np.diff(y_data)[0]
        slope = diff_data / diff_px
        intercept = y_data[0] - slope * y_px[0]
        return intercept + slope * coord

    def data2px_y(self, coord):
        """Transform the data coordinates into pixel coordinates

        Parameters
        ----------
        coord: 1D np.ndarray
            The coordinate values

        Returns
        -------
        np.ndarray
            The numpy array with transformed coordinates"""
        y_px = self.yaxis_px
        y_data = self.yaxis_data
        diff_px = np.diff(y_px)[0]
        diff_data = np.diff(y_data)[0]
        slope = diff_px / diff_data
        intercept = y_px[0] - slope * y_data[0]
        return intercept + slope * coord

    def remove_marks(self):
        """Remove any drawn marks"""
        if self.marks is not None:
            for m in self.marks + self.magni_marks:
                m.remove()
            self.marks = None
        self.magni_marks.clear()
        if hasattr(self, '_mark_fig_num'):
            import matplotlib.pyplot as plt
            fig = plt.figure(self._mark_fig_num)
            del self._mark_fig_num
        else:
            fig = self.fig
        for cid in self.mark_cids:
            fig.canvas.mpl_disconnect(cid)
        self.mark_cids.clear()
        if hasattr(self, '_new_mark'):
            del self._new_mark

    def init_colnames_reader(self, ax=None, **kwargs):
        from straditize.ocr import ColNamesReader
        x0, x1 = map(int, self.colnames_xlim)
        y0, y1 = map(int, self.colnames_ylim)
        ax = ax or self.ax
        self.colnames_reader = ColNamesReader(
            self.image.crop([x0, y0, x1, y1]), ax=ax, extent=[x0, x1, y1, y0],
            magni=self.magni, **kwargs)

    def init_reader(self, reader_type='area', ax=None, **kwargs):
        x0, x1 = map(int, self.data_xlim)
        y0, y1 = map(int, self.data_ylim)
        kwargs.setdefault('plot_background', True)
        ax = ax or self.ax
        self.data_reader = binary.readers[reader_type](
            self.image.crop([x0, y0, x1, y1]), ax=ax, extent=[x0, x1, y1, y0],
            magni=self.magni, **kwargs)

    def _finalize_df(self, df):
        """Combine the column informations and data"""
        try:
            df.index = self.px2data_y(df.index.values)
        except ValueError:
            pass
        try:
            for i, col in enumerate(df.columns):
                df.loc[:, col] = self.get_reader_for_column(col).px2data_x(
                    df[col].values)
        except ValueError:
            pass
        return df

    def show_full_image(self):
        self.ax.set_xlim(0, np.shape(self.image)[1])
        self.ax.set_ylim(np.shape(self.image)[0], 0)

    def show_data_diagram(self):
        self.ax.set_xlim(*self.data_xlim)
        self.ax.set_ylim(*self.data_ylim[::-1])

    def get_reader_for_column(self, col):
            return next(
                child for child in self.data_reader.iter_all_readers
                if not child.is_exaggerated and col in child.columns)

    def marks_for_column_starts(self, threshold=None):
        def new_mark(pos):
            x = pos[0]
            ret = cm.DraggableVLine(x, ax, idx_h, ylim=ylim, zorder=2, c='b')
            return ret
        extent = self.data_reader.extent
        x0 = extent[0] if extent else 0
        starts = self.data_reader._column_starts
        if starts is None:
            starts = self.data_reader.estimated_column_starts(threshold)
        current_starts = x0 + starts
        self.remove_marks()
        ax = self.ax
        idx_h = self.indexes['x'][slice(*map(int, self.data_xlim))]
        ylim = self.data_ylim
        self.marks = marks = [
            new_mark((x, 0)) for i, x in enumerate(current_starts)]
        if marks:
            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark)))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))

    def update_column_starts(self):
        starts = np.ceil(np.unique([m.x for m in self.marks])).astype(int)
        extent = self.data_reader.extent
        x0 = extent[0] if extent else 0
        for reader in [self.data_reader] + self.data_reader.children:
            reader._column_starts = starts - x0
        if not self.data_reader.children:
            self.data_reader.columns = None
        self.remove_marks()

    def marks_for_column_ends(self, threshold=None):
        def new_mark(pos):
            x = pos[0]
            ret = cm.DraggableVLine(x, ax, idx_h, ylim=ylim, zorder=2, c='b')
            return ret
        extent = self.data_reader.extent
        x0 = extent[0] if extent else 0
        ends = self.data_reader._column_ends
        if ends is None:
            ends = np.r_[
                self.data_reader.estimated_column_starts(threshold)[1:],
                [self.data_reader.binary.shape[1]]]
        current_ends = x0 + ends
        self.remove_marks()
        ax = self.ax
        idx_h = self.indexes['x']
        ylim = self.data_ylim
        self.marks = marks = [
            new_mark((x, 0)) for i, x in enumerate(current_ends)]
        if marks:
            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        if not self.data_reader.children:
            self.mark_cids.add(self.fig.canvas.mpl_connect(
                'button_press_event', self._add_mark_event(new_mark)))
            self.mark_cids.add(self.fig.canvas.mpl_connect(
                'button_press_event', self._remove_mark_event))

    def update_column_ends(self):
        ends = np.ceil(np.unique([m.x for m in self.marks])).astype(int)
        extent = self.data_reader.extent
        x0 = extent[0] if extent else 0
        for reader in chain([self.data_reader], self.data_reader.children):
            reader._column_ends = ends - x0
        if not self.data_reader.children:
            self.data_reader.columns = None
        self.remove_marks()

    def marks_for_occurences(self):
        """Create marks for editing the occurences"""
        def get_col(x):
            return next(i for i, (s, e) in enumerate(bounds)
                        if s <= x and e >= x)

        def new_mark(pos):
            col = get_col(pos[0])
            xlim = tuple(bounds[col])
            return [cm.DraggableHLine(
                        pos[1], xlim=xlim, ax=self.ax, idx_v=idx_v,
                        zorder=2)]

        def _new_mark(pos):
            pos = list(pos)
            pos[0] += self.data_xlim[0]
            pos[1] += self.data_ylim[0]
            return new_mark(pos)

        reader = self.data_reader
        bounds = reader.all_column_bounds + self.data_xlim[0]
        idx_v = self.indexes['y']

        self.marks = marks = list(chain.from_iterable(
            map(_new_mark, sorted(reader.occurences))))
        if marks:
            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        if not self.data_reader.children:
            self.mark_cids.add(self.fig.canvas.mpl_connect(
                'button_press_event', self._add_mark_event(new_mark)))
            self.mark_cids.add(self.fig.canvas.mpl_connect(
                'button_press_event', self._remove_mark_event))

    def update_occurences(self, remove=True):
        """Set the occurences from the given marks"""
        def get_pos(mark):
            pos = mark.pos
            return (int(pos[0] - x0), int(pos[1] - y0))
        x0 = self.data_xlim[0]
        y0 = self.data_ylim[0]
        self.data_reader.occurences = set(map(get_pos, self.marks))
        if remove:
            self.remove_marks()

    def digitize_diagram(self):
        self.data_reader.digitize()
        self.data_reader.plot_full_df()

    def _get_mark_from_event(self, event, buttons=[3]):
        """Get a mark from a mouse event"""
        if (not self.marks or
                event.inaxes not in (m.ax for m in self.marks) or
                event.button == 1 or
                any(m.fig.canvas.manager.toolbar.mode != ''
                    for m in self.marks)):
            return
        return next(filter(lambda m: m.is_selected_by(event, buttons),
                           self.marks), None)

    def _remove_mark_event(self, event):
        """Remove a mark by right-click"""
        if event.button != 3:  # right mouse button
            return
        mark = self._get_mark_from_event(event)
        if mark is not None:
            removed = self._remove_mark(mark)
            for m in removed:
                self.mark_removed.emit(m)

    def _remove_mark(self, mark):
        mark.remove()
        self.marks.remove(mark)
        removed = [mark]
        for m in chain(mark._constant_dist_x_marks,
                       mark._constant_dist_y_marks):
            m.remove()
            try:
                self.marks.remove(m)
            except ValueError:
                pass
            removed.append(m)
        mark.ax.figure.canvas.draw_idle()
        if self.magni is not None:
            self.magni.ax.figure.canvas.draw_idle()
        return removed

    def _add_mark_event(self, func, axes=None, magnifier=True):
        """Create a function that returns a mark

        Parameters
        ----------
        func: function
            The factory for the marks. It must accept a single argument as a
            tuple

        Returns
        -------
        function
            The function that can be connected via button_press_event
        """
        if axes is None:
            axes = [self.ax]
        else:
            axes = list(axes)
        ret, self._new_mark = _new_mark_factory(
            self.marks, self.mark_added, func, axes[0].figure.number,
            self.magni, self.magni_marks)
        return ret

    def marks_for_samples(self):
        def _new_mark(pos, artists=[]):
            ret = cm.CrossMarks(
                pos, zorder=2, idx_v=idx_v, idx_h=idx_h,
                xlim=xlim, ylim=ylim, alpha=0.5,
                linewidth=1.5, selectable=['h'], marker='x',
                select_props={'c': 'r', 'lw': 2.0},
                connected_artists=artists, ax=ax, hide_vertical=True)
            ret._is_occurence = [False] * len(ret.xa)
            return ret

        def new_mark(pos):
            return [_new_mark(
                [np.array(starts + full_df.loc[np.round(pos[-1] - ylim[0])]),
                 np.round(pos[-1])])]

        def new_mark_and_range(key, row, row_indices):
            artists = []
            for (col, val), s in zip(row.items(), starts):
                try:
                    imin, imax = row_indices[2*col:2*col+2]
                except KeyError:
                    pass
                else:
                    if imin >= 0:
                        artists.extend(ax.plot(
                            s + full_df.iloc[imin:imax, col],
                            ylim[0] + np.arange(imin, imax), c='0.5', lw=0,
                            marker='+'))
            mark = _new_mark([starts + np.where(row == occ_val, means, row),
                              min(ylim) + key], artists)
            mark._is_occurence = [val == occ_val for val in row]
            return [mark]

        reader = self.data_reader
        occ_val = reader.occurences_value
        means = reader.all_column_bounds.mean(axis=1)
        if reader.full_df is None:
            reader.digitize()
        df = reader.sample_locs
        full_df = reader._full_df
        self.remove_marks()
        ax = self.ax
        idx_v = self.indexes['y']
        idx_h = self.column_indexes
        xlim = self.data_xlim
        ylim = self.data_ylim
        starts = reader.all_column_starts + xlim[0]
        if not len(df):
            self.marks = marks = []
        else:
            self.marks = marks = list(chain.from_iterable(
                new_mark_and_range(key, row, indices)
                for (key, row), (key2, indices) in zip(
                    df.iterrows(), reader.rough_locs.iterrows())))
        if marks:
            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark)))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))

    def update_samples(self, remove=True):
        if not self.marks:
            self.data_reader.reset_samples()
        else:
            y0 = min(self.data_ylim)
            x0 = min(self.data_xlim)
            starts = self.data_reader.all_column_starts[np.newaxis] + x0
            index = np.array(np.ceil([mark.y for mark in self.marks])) - y0
            data = np.array(np.ceil([mark.xa for mark in self.marks])) - starts
            is_occurence = np.array(
                [mark._is_occurence for mark in self.marks], bool)
            data[is_occurence] = self.data_reader.occurences_value
            df = pd.DataFrame(data, index=index.astype(int)).sort_index()
            self.data_reader.sample_locs = df.drop_duplicates()
            self.data_reader._update_rough_locs()
        if remove:
            self.remove_marks()
            try:
                del self._plotted_full_df
            except AttributeError:
                    pass

    def marks_for_samples_sep(self, nrows=3):
        def _new_mark(pos, ax, artists=[]):
            idx_h = all_idx_h[ax]
            ret = cm.CrossMarks(
                pos, zorder=2, idx_v=idx_v, idx_h=idx_h,
                xlim=(0, idx_h.max()),
                alpha=0.5, linewidth=1.5, selectable=['h'],
                marker='x', connected_artists=artists,
                ax=ax, select_props={'c': 'r', 'lw': 2.0}, hide_vertical=True)
            ret._is_occurence = [False]
            return ret

        def new_mark(pos):
            y = np.round(pos[-1])
            marks = []
            for (col, val), ax in zip(full_df.loc[y, :].items(), axes):
                if np.isnan(val).all():
                    val = 0
                marks.append(_new_mark([val, y], ax))
            marks[0].maintain_y(marks)
            return marks

        def new_mark_and_range(key, row, row_indices):
            marks = []
            for (col, val), ax in zip(row.items(), axes):
                try:
                    imin, imax = row_indices[2*col:2*col+2]
                except KeyError:
                    artists = []
                else:
                    if imin >= 0:
                        artists = ax.plot(
                            full_df.iloc[imin:imax, col],
                            np.arange(imin, imax), c='0.5', lw=0,
                            marker='+')
                    else:
                        artists = []
                if val == occ_val:
                    val = bounds[col].mean()
                marks.append(_new_mark([val, key], ax, artists))
            for mark, val in zip(marks, row):
                mark._is_occurence = [val == occ_val]
            marks.append(_new_mark([full_df.loc[key, 'nextrema'], key],
                                   axes[-1]))
            marks[-1]._is_occurence = [False]
            marks[0].maintain_y(marks)
            return marks

        get_child = self.get_reader_for_column

        import matplotlib.pyplot as plt

        reader = self.data_reader
        occ_val = reader.occurences_value
        if reader._full_df is None:
            reader.digitize()
        df = reader.sample_locs
        bounds = reader.all_column_bounds
        full_df = reader._full_df.copy(True)
        full_df['nextrema'] = reader.found_extrema_per_row()
        self.remove_marks()
        fig, axes = plt.subplots(
            nrows, int(np.ceil((df.shape[1] + 1) / nrows)), sharey=True)
        for ax in axes.ravel()[len(df.columns) + 1:]:
            fig.delaxes(ax)
        axes = axes.ravel()[:len(df.columns) + 1]
        idx_v = self.indexes['y'][:full_df.shape[0]]
        for (col, s), ax in zip(full_df.iteritems(), axes):
            if col != 'nextrema':
                ax.imshow(get_child(col).get_binary_for_col(col),
                          cmap='binary')
            else:
                ax.invert_yaxis()
                ax.set_ylim(idx_v.max(), idx_v.min())
                ax.fill_betweenx(idx_v, 0, s.values)
            ax.set_title(col)
        all_idx_h = dict(zip(axes, map(
            pd.Index, map(np.arange, full_df.max(axis=0).values))))
        if not len(df):
            self.marks = marks = []
        else:
            self.marks = marks = list(chain.from_iterable(
                new_mark_and_range(key, row, indices)
                for (key, row), (key2, indices) in zip(
                    df.iterrows(), reader.rough_locs.iterrows())))
        for ax, idx in all_idx_h.items():
            if ~np.isnan(idx.min()):
                ax.set_xlim(idx.min(), idx.max())
            elif ax is axes[-1]:
                ax.set_xlim(0, 1)

        if marks:
            marks[0].connect_marks(marks)
        self.mark_cids.add(fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark, list(axes))))
        self.mark_cids.add(fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))
        self._plotted_full_df = full_df
        self._mark_fig_num = fig.number
        return fig, axes

    def update_samples_sep(self, remove=True):
        ncols = len(self.data_reader.all_column_starts)
        index = np.array(np.ceil([mark.y for mark in self.marks]))[::ncols + 1]
        index = np.round(index).astype(int)
        data = np.array(np.ceil([mark.x for mark in self.marks])).reshape(
            (len(index), ncols + 1))
        is_occurence = np.array(
            [mark._is_occurence[0] for mark in self.marks], bool).reshape(
                (len(index), ncols + 1))
        data[is_occurence] = self.data_reader.occurences_value
        df = pd.DataFrame(data[:, :-1], index=index).sort_index()
        self.data_reader.sample_locs = df.drop_duplicates()
        self.data_reader._update_rough_locs()
        if remove:
            self.remove_marks()
            try:
                del self._plotted_full_df
            except AttributeError:
                pass

    @classmethod
    def load(cls, fname, ax=None, plot=True):
        if isinstance(fname, six.string_types):
            with open(fname, 'rb') as f:
                obj = pickle.load(f)
        elif isinstance(fname, cls):
            obj = fname
        else:
            obj = pickle.load(fname)
        if plot:
            obj.plot_image(ax=ax)
            if obj.data_reader is not None:
                plot_background = True
                for reader in obj.data_reader.iter_all_readers:
                    if obj.magni is not None:
                        reader.magni = obj.magni
                    if plot_background:
                        reader.plot_background(ax=obj.ax)
                        plot_background = False
                    reader.plot_image(ax=obj.ax)
        return obj

    def close(self):
        import matplotlib.pyplot as plt
        self.remove_marks()
        plt.close(self.ax.figure)
        if self.magni is not None:
            plt.close(self.magni.ax.figure)
            del self.magni.plot_image, self.magni.ax, self.magni
        self.image.close()
        # close signals
        self.mark_added.disconnect()
        self.mark_removed.disconnect()
        for sig in [self.mark_added, self.mark_removed]:
            try:
                del sig.instance
            except AttributeError:
                pass
        # close reader
        if getattr(self, 'data_reader', None) is not None:
            self.data_reader.image.close()
            self.data_reader.remove_callbacks.clear()
        # remove data intensive attributes
        for obj in [self.data_reader, self]:
            for attr in ['ax', 'image', 'plot_im', 'data_reader',
                         'remove_callbacks']:
                try:
                    delattr(obj, attr)
                except AttributeError:
                    pass

    def save(self, fname):
        """Dump the :class:`Straditizer` instance to a file

        Parameters
        ----------
        fname: str
            The file name where to save the instance"""
        if isinstance(fname, six.string_types):
            with open(fname, 'wb') as f:
                pickle.dump(self, f)
        else:
            pickle.dump(self, fname)

    def update_image(self, arr, mask):
        """Update the image from the given 3D-array

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
        self.plot_im.set_array(arr)
