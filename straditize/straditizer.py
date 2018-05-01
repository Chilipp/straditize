# -*- coding: utf-8 -*-
"""Core module of the Straditizer class"""
import six
from copy import copy
from itertools import chain, product, cycle
import numpy as np
import pandas as pd
import pickle
from importlib import import_module
import straditize.cross_mark as cm
import straditize.binary as binary
from straditize.label_selection import LabelSelection
from psyplot.data import Signal, safe_list
from straditize.magnifier import Magnifier
from psyplot.utils import _temp_bool_prop
import skimage.morphology as skim
import xarray as xr


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
        bounds = self.data_reader.column_bounds + self.data_xlim[0]
        return [
            pd.Index(np.arange(se)) for se in bounds]

    #: The :class:`straditize.binary.DataReader` instance to digitize the
    #: data
    data_reader = None

    data_xlim = None

    data_ylim = None

    _orig_format_coord = None

    _yaxis_px_orig = None

    @property
    def yaxis_px(self):
        if self._yaxis_px_orig is None:
            raise ValueError("Y-axis informations have not yet been inserted!")
        if self.data_ylim is None:
            raise ValueError("The data limits have not been set yet!")
        return np.asarray(self._yaxis_px_orig) - np.min(self.data_ylim)

    yaxis_data = None

    mark_cids = set()

    text_reader = None

    _indexes = None

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
                self.data_reader.measurement_locs is None):
            return None
        ret = self._finalize_df(self.data_reader.measurement_locs.copy(True))
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

    def __init__(self, image, ax=None, plot=True):
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
        """
        from PIL import Image
        if isinstance(image, six.string_types):
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
        if self._orig_format_coord is None:
            self._orig_format_coord = ax.format_coord
            ax.format_coord = self.format_coord

    def __reduce__(self):
        return (
            self.__class__,
            (self.image, None, False),
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
        stradi = cls(ds['image'].values, ax=ax, plot=plot)
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
            if len(self.marks) == 4:
                raise ValueError("Cannot use more than 4 marks!")
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

    def draw_data_box(self):
        # plot a box around the plot
        self.remove_data_box()
        x = self.data_xlim
        y = self.data_ylim
        self.data_box = self.ax.bar(x[0], np.diff(y)[0], np.diff(x)[0],
                                    y[0], edgecolor='r', facecolor='none',
                                    align='edge', linewidth=2)[0]
        if self.magni is not None:
            self.magni_data_box = self.magni.ax.bar(
                x[0], np.diff(y)[0], np.diff(x)[0], y[0], edgecolor='r',
                facecolor='none', align='edge', linewidth=2)[0]

    def remove_data_box(self):
        """Remove the data_box"""
        if hasattr(self, 'data_box'):
            try:
                self.data_box.remove()
            except ValueError:
                pass
            del self.data_box
        if hasattr(self, 'magni_data_box'):
            try:
                self.magni_data_box.remove()
            except ValueError:
                pass
            del self.magni_data_box

    def format_coord(self, x, y):
        """Format x and y to include the :attr:`data_reader` attribute

        Parameters
        ----------
        x: float
            The x-coordinate in the axes
        y: float
            The y-coordinate in the axes

        Returns
        -------
        function
            The function that can be used to replace `ax.format_coord`
        """
        orig_s = self._orig_format_coord(x, y)
        ax = self.ax
        if self.data_reader is not None:
            data_x = x - self.data_xlim[0]
            data_y = y - self.data_ylim[0]
            orig_s += 'DataReader: x=%s y=%s' % (ax.format_xdata(data_x),
                                                 ax.format_ydata(data_y))
            if (self.data_reader._column_starts is not None and
                    x > self.data_xlim[0] and x < self.data_xlim[1]):
                col = next(
                    (i for i, (s, e) in enumerate(
                        self.data_reader.all_column_bounds)
                     if data_x >= s and data_x <= e),
                    None)
                if col is not None:
                    col_x = data_x - self.data_reader.all_column_starts[col]
                    orig_s += 'Column %i x=%s' % (col, ax.format_xdata(col_x))
        return orig_s

    def marks_for_x_values(self):
        """Create two marks for selecting the x-values"""
        def new_mark(pos, **kwargs):
            if len(self.marks) == 2:
                raise ValueError("Cannot use more than 2 marks!")
            ret = cm.DraggableVLineText(
                np.round(pos[0]), ax=self.ax, idx_h=idx_h, zorder=2,
                message=msg, dtype=float, c='b', **kwargs)
            if 'value' not in kwargs:
                ret.ask_for_value()
            return ret

        idx_h = self.indexes['x']
        self.remove_marks()
        msg = 'Enter the corresponding percentage for this point.'
        self.marks = marks = []
        reader = self.data_reader
        if reader._xaxis_px_orig is not None:
            x0, x1 = reader._xaxis_px_orig
            marks.append(new_mark((x0, 0), value=reader.xaxis_data[0]))
            marks.append(new_mark((x1, 0), value=reader.xaxis_data[1]))

            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
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
                ret.ask_for_value()
            return ret
        idx_v = self.indexes['y']
        self.remove_marks()
        msg = 'Enter the corresponding percentage for this point.'
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
        fig = self.fig
        for cid in self.mark_cids:
            fig.canvas.mpl_disconnect(cid)
        self.mark_cids.clear()

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
        idx_h = self.indexes['x']
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
        """Remove a measurement by right-click"""
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
        def ret(event):
            if (event.key != 'shift' or event.button != 1 or
                    event.inaxes not in (axes if axes else [self.ax]) or
                    self.fig.canvas.manager.toolbar.mode != ''):
                return
            new_marks = self._new_mark(event.xdata, event.ydata)
            for m in new_marks:
                self.mark_added.emit(m)

        def _new_mark(x, y, **kwargs):
            new_marks = func((x, y), **kwargs)
            if new_marks:
                try:
                    self.marks.extend(new_marks)
                except TypeError:
                    new_marks = [new_marks]
                    self.marks.extend(new_marks)
                    self.create_magni_marks(new_marks)
                else:
                    if magnifier:
                        self.create_magni_marks(new_marks)
            self.marks[0].ax.figure.canvas.draw_idle()
            return new_marks
        self._new_mark = _new_mark
        return ret

    def marks_for_measurements(self):
        def _new_mark(pos, artists=[]):
            return cm.CrossMarks(
                pos, zorder=2, idx_v=idx_v, idx_h=idx_h,
                xlim=xlim, ylim=ylim, c='g', alpha=0.5,
                linewidth=0.5, selectable=['h'], auto_hide=True,
                marker='o', connected_artists=artists,
                ax=ax)

        def new_mark(pos):
            return _new_mark(
                [starts + full_df.loc[np.round(pos[-1] - ylim[0])],
                 np.round(pos[-1])])

        def new_mark_and_range(key, row):
            artists = []
            try:
                indices = reader.rough_locs.loc[key]
            except KeyError:
                pass
            else:
                for i, l in enumerate(indices):
                    if l:
                        artists.extend(ax.plot(
                            starts[i] + full_df.loc[l, i],
                            np.array(l) + ylim[0], c='0.5', lw=0, marker='+'))
            return _new_mark([starts + row.tolist(), key + ylim[0]],
                             artists=artists)

        reader = self.data_reader
        if reader.full_df is None:
            reader.digitize()
        df = reader.measurement_locs()
        full_df = reader.full_df
        self.remove_marks()
        ax = self.ax
        idx_v = self.indexes['y']
        idx_h = self.column_indexes
        xlim = self.data_xlim
        ylim = self.data_ylim
        starts = reader._get_column_starts() + xlim[0]
        self.marks = marks = [
            new_mark_and_range(key, row)
            for key, row in df.iterrows()]

        if marks:
            marks[0].connect_marks(marks)
            self.create_magni_marks(marks)
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._add_mark_event(new_mark)))
        self.mark_cids.add(self.fig.canvas.mpl_connect(
            'button_press_event', self._remove_mark_event))

    def update_measurements(self):
        index = np.array(np.ceil([mark.y for mark in self.marks]))
        data = np.array(np.ceil([mark.x for mark in self.marks]))
        df = pd.DataFrame(data, index=index)
        self.data_reader.measurement_locs = df
        # set the rough locations equal to the measurements if they have not
        # already been set, otherwise update
        if self.data_reader.rough_locs is None:
            self.data_reader.rough_locs = pd.DataFrame(
                data.reshape(data.shape + (1, )),
                index=index)
        else:
            old = self.data_reader.rough_locs
            old['in_old'] = True
            new = df[[]]
            new['in_new'] = True
            joined = old.join(new, how='right')
            missing_idx = joined[
                joined['in_old'].isnull().values &
                joined['in_new'].notnull().values].index.values
            missing = df.loc[missing_idx, :].values
            joined[missing_idx, :] = missing.reshape(
                missing.shape + (1, ))
            joined.drop(['in_old', 'in_new'], axis=1, inplace=True)
            joined.sort_index(inplace=True)
            self.data_reader.rough_locs = joined
        self.remove_marks()

    def marks_for_measurements_sep(self, nrows=3):
        def _new_mark(pos, ax, artists=[]):
            idx_h = all_idx_h[ax]
            ret = cm.CrossMarks(
                pos, zorder=2, idx_v=idx_v, idx_h=idx_h,
                xlim=(0, idx_h.max()),
                alpha=0.5, linewidth=1.5, selectable=['h'],
                marker='x', connected_artists=artists,
                ax=ax, select_props={'c': 'r', 'lw': 2.0})
            if self.marks:
                ret.hide_vertical = self.marks[0].hide_vertical
                ret.hide_horizontal = self.marks[0].hide_horizontal
            else:
                ret.hide_vertical = True
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
                marks.append(_new_mark([val, key], ax, artists))
            marks.append(_new_mark([full_df.loc[key, 'nextrema'], key],
                                   axes[-1]))
            marks[0].maintain_y(marks)
            return marks

        get_child = self.get_reader_for_column

        import matplotlib.pyplot as plt

        reader = self.data_reader
        if reader.full_df is None:
            reader.digitize()
        df = reader.measurement_locs
        full_df = reader._full_df.copy(True)
        full_df['nextrema'] = reader.found_extrema_per_row()
        self.remove_marks()
        fig, axes = plt.subplots(nrows,
                                 int(np.ceil((df.shape[1] + 1) / nrows)),
                                 sharey=True)
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
        return fig, axes

    def update_measurements_sep(self, remove=True):
        ncols = len(self.data_reader.all_column_starts)
        index = np.array(np.ceil([mark.y for mark in self.marks]))[::ncols + 1]
        index = np.round(index).astype(int)
        data = np.array(np.ceil([mark.x for mark in self.marks])).reshape(
            (len(index), ncols + 1))
        df = pd.DataFrame(data[:, :-1], index=index).sort_index()
        self.data_reader.measurement_locs = df
        # set the rough locations equal to the measurements if they have not
        # already been set, otherwise update
        if self.data_reader.rough_locs is None:
            self.data_reader.rough_locs = pd.DataFrame(
                data.reshape(data.shape + (1, )),
                index=index)
        else:
            old = self.data_reader.rough_locs
            old['in_old'] = True
            new = df[[]].copy(True)
            new['in_new'] = True
            joined = old.join(new, how='right')
            missing_idx = joined[
                joined['in_old', ''].isnull().values &
                joined['in_new'].notnull().values].index.values
            missing = df.loc[missing_idx, :].values.astype(int)
            del joined['in_old', '']
            del joined['in_new']
            joined.loc[missing_idx, ::2] = missing
            joined.loc[missing_idx, 1::2] = missing + 1
            joined.sort_index(inplace=True)
            self.data_reader.rough_locs = joined
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
        plt.close(self.ax.figure)
        if self.magni is not None:
            plt.close(self.magni.ax.figure)
            del self.magni
        del self.ax, self.image, self.plot_im, self.data_reader

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
