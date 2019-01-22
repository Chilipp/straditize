# -*- coding: utf-8 -*-
"""Module for the :class:`LabelSelection` class

This module defines the :class:`LabelSelection` class, a base class for the
:class:`straditize.straditizer.Straditizer`
:class:`straditize.binary.DataReader` classes. This class implements the
features to select parts of an image and deletes them. The
:class:`straditize.widgets.selection_toolbar.SelectionToolbar` interfaces
with instances of this class.

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
along with this program. If not, see <https://www.gnu.org/licenses/>."""
import numpy as np
import matplotlib.colors as mcol
from straditize.common import docstrings


class LabelSelection(object):
    """Class to provide selection functionalities for an image

    This class provides functionalities to select features in an image. A new
    selection can be started through :meth:`enable_label_selection` method
    and selected parts can be removed through the
    :meth:`remove_selected_labels` method.

    A 2D boolean mask of the selected pixels can be accessed through the
    :attr:`selected_part` attribute.

    This class generally assumes that the array for the selection is a 2D
    integer array, e.g. obtained from the :func:`skimage.morphology.label`
    function.

    The selection of labels is handled through the colormap. The selection is
    displayed as a matplotlib image on the :attr:`ax` attribute of this
    instance. If the color for one label is equal to the :attr:`cselect` color,
    it is considered as selected. Additionally every cell that has a value
    greater than the original number of labels is considered to be selected.

    Cells with a value of -1 are not selected and cells with a value of 0
    cannot be selected."""

    _selection_arr = None

    #: matplotlib image of the selection
    _select_img = None

    #: The RGBA color for selected polygons
    cselect = [1., 0., 0., 1.]

    #: The RGBA color for unselected polygons
    cunselect = [0., 0., 0., 0.]

    #: List of attribute names of arrays that should be modified if the
    #: labels are about to be removed. The attributes might be callable and
    #: should then provide the array
    label_arrs = []

    #: Functions that shall be called before the labels are removed. The keys
    #: must be the attributes in the :attr:`label_attrs` list, values must be
    #: list of function that accept too arguments, the array and the boolean
    #: mask highlighting the cells that will be set to 0
    remove_callbacks = None

    _remove = True

    cid_select = None

    _magni_img = None

    _ellipses = []

    @property
    def selected_labeled_part(self):
        """The selected part as a 2D boolean mask"""
        if self._selection_arr is None:
            return np.zeros_like(self.labels, dtype=bool)
        selection = self.selected_labels
        return np.isin(self._selection_arr, selection)

    @property
    def selected_part(self):
        """The selected part as a 2D boolean mask"""
        if self._selection_arr is None:
            return np.zeros_like(self.labels, dtype=bool)
        return self.selected_labeled_part | (
            self._selection_arr > self._select_nlabels)

    @property
    def selected_labels(self):
        """A list of selected labels in the selection array"""
        bounds = self._select_img.norm.boundaries[1:] + 0.5
        bounds = bounds.astype(int)
        cmap = self._select_img.get_cmap()
        colors = cmap(np.linspace(0, 1, cmap.N))
        if np.allclose(colors[1], self.cselect):
            if len(colors) == 2:
                ret = np.unique(self._selection_arr)
                return ret[ret > 0]
            else:
                istart = 0
        else:
            if len(colors) == 2:
                return np.array([], dtype=int)
            istart = 1
        starts = bounds[istart::2]
        ends = bounds[istart + 1::2]
        return np.concatenate(
            list(np.arange(max(1, s), max(1, e))
                 for s, e in zip(starts, ends)))

    def get_default_cmap(self, ncolors):
        """The default colormap for binary images"""
        colors = np.array([self.cunselect for i in range(ncolors)])
        cmap = mcol.LinearSegmentedColormap.from_list('invisible', colors,
                                                      ncolors)
        cmap.set_over(self.cselect)
        return cmap

    @staticmethod
    def copy_cmap(cmap_src, colors):
        """Copy a colormap with replaced colors

        This function creates a method that has the same name and the same
        *under*, *over* and *bad* values as the given `cmap_src` but with
        replaced colors

        Parameters
        ----------
        cmap_src: matplotlib.colors.Colormap
            The source colormap
        colors: np.ndarray
            The colors for the colormap

        Returns
        -------
        matplotlib.colors.Colormap
            The new colormap"""
        cmap = mcol.LinearSegmentedColormap.from_list(cmap_src.name, colors,
                                                      len(colors))
        cmap.set_under(cmap_src(-0.1))
        cmap.set_over(cmap_src(1.1))
        cmap.set_bad(cmap(np.ma.masked_array([np.nan], [True]))[0])
        return cmap

    def pick_label(self, event):
        """Pick the label selected by the given mouseevent"""
        self.event = event
        artist = event.artist
        if artist is not self._select_img:
            return
        x, y = event.mouseevent.xdata, event.mouseevent.ydata
        x = int(np.round(x))
        y = int(np.round(y))
        extent = getattr(self, 'extent', None)
        if extent is not None:
            x -= extent[0]
            y -= min(extent[2:])
        val = self._selection_arr[y, x]
        if val == -1 or val > self._select_nlabels:
            val = self._orig_selection_arr[y, x]
            if not np.isnan(val) and val != 0:
                self._selection_arr[self._orig_selection_arr == val] = val
        if val == 0 or np.isnan(val):
            return
        selected = self.selected_labels
        if val in selected:
            selected = np.delete(selected, selected.searchsorted(val))
        else:
            selected = np.insert(selected, selected.searchsorted(val),
                                 val)
        self.select_labels(selected)
        self._select_img.axes.figure.canvas.draw()

    def highlight_small_selections(self, n=20):
        """Highlight labels that cover only a small portion of cells

        This method uses the :func:`skimage.morphology.remove_small_objects`
        to detect and highlight small features in the diagram. Each feature
        will be highlighted through an ellipsis around it.

        See Also
        --------
        remove_small_selection_ellipses"""
        from matplotlib.patches import Ellipse
        import skimage.morphology as skim
        if self._selection_arr is None:
            return
        arr = self.selected_part
        arr &= ~skim.remove_small_objects(arr, n)
        if not arr.any():
            return
        labeled, num_labels = skim.label(arr, 8, return_num=True)
        min_height = np.ceil(0.05 * arr.shape[0])
        min_width = np.ceil(0.05 * arr.shape[1])
        self._ellipses = artists = []
        extent = getattr(self, 'extent', None)
        if extent is not None:
            x0 = extent[0]
            y0 = min(extent[2:])
        else:
            x0 = y0 = 0
        for label in range(1, num_labels + 1):
            mask = labeled == label
            xmask = np.where(mask.any(axis=0))[0]
            width = xmask[-1] - xmask[0]
            xc = x0 + xmask[0] + width / 2. + 0.5
            ymask = np.where(mask.any(axis=1))[0]
            height = ymask[-1] - ymask[0]
            yc = y0 + ymask[0] + height / 2. + 0.5
            a = Ellipse((xc, yc), max(min_width, width + 2),
                        max(min_height, height + 2), edgecolor='b',
                        facecolor='b', alpha=0.3)
            artists.append(a)
            self._select_img.axes.add_patch(a)

    def remove_small_selection_ellipses(self):
        """Remove the ellipes for small features

        Removes the ellipses plotted by the :meth:`highlight_small_selections`
        method"""
        for a in self._ellipses:
            a.remove()
        self._ellipses.clear()

    def select_labels(self, selected):
        """Select a list of labels

        Parameters
        ----------
        selected: np.ndarray
            The numpy array of labels that should be selected"""
        if len(selected) == 0:
            self._select_img.set_cmap(self._select_cmap)
            self._select_img.set_norm(self._select_norm)
        else:
            diffs = selected[1:] - selected[:-1]
            mask = diffs > 1
            if mask.any():
                starts = np.r_[[selected[0]], selected[1:][mask]]
                ends = np.r_[selected[:-1][mask], selected[-1]] + 1
            else:
                starts = [selected[0]]
                ends = [selected[-1] + 1]
            notnull = self._selection_arr[self._selection_arr.astype(bool)]
            min_label = notnull.min()
            max_label = notnull.max()
            bounds = [0.1] if selected[0] == min_label else [0.1, 0.5]
            bounds = np.r_[bounds,
                           np.array(list(zip(starts, ends))).ravel() - 0.5]
            if selected[-1] != max_label:
                bounds = np.r_[bounds, [self._select_nlabels + 0.5]]
            ncolors = len(bounds) - 1
            cunselect = self.cunselect
            cselect = self.cselect
            if selected[0] != min_label:
                colors = [cunselect] + [
                    cselect if i % 2 else cunselect
                    for i in range(ncolors - 1)]
            else:
                colors = [cunselect] + [
                    cunselect if i % 2 else cselect
                    for i in range(ncolors - 1)]
            self._select_img.set_cmap(self.copy_cmap(
                self._select_img.get_cmap(), colors))
            self._select_img.set_norm(mcol.BoundaryNorm(bounds, len(bounds)-1))
            self._update_magni_img()

    @docstrings.get_sectionsf('LabelSelection.enable_label_selection')
    def enable_label_selection(self, arr, ncolors, img=None,
                               set_picker=False, **kwargs):
        """Start the selection of labels

        Parameters
        ----------
        arr: 2D np.ndarray of dtype int
            The labeled array that contains the features to select.
        ncolors: int
            The maximum of the labels in `arr`
        img: matplotlib image
            The image for the selection. If not provided, a new image is
            created
        set_picker: bool
            If True, connect the matplotlib pick_event to the
            :meth:`pick_label` method

        See Also
        --------
        disable_label_selection
        remove_selected_labels"""
        if img is None:
            cmap = self.get_default_cmap(2)
            cmap.set_under('none')
            kwargs.setdefault('cmap', cmap)
            norm = mcol.BoundaryNorm([0.1, 0.5, ncolors+0.5], 2)
            kwargs.setdefault('norm', norm)
            img = self.ax.imshow(arr, **kwargs)
            if getattr(self, 'magni', None) is not None:
                magni_img = self.magni.ax.imshow(arr, **kwargs)
            else:
                magni_img = None
            self._remove = True
        else:
            self._remove = False
            magni_img = None
        cmap = img.get_cmap()
        self._select_cmap = cmap
        self._select_norm = img.norm
        self._select_nlabels = ncolors
        self._selection_arr = arr
        self._orig_selection_arr = arr.copy()
        self._select_img = img
        self._magni_img = magni_img
        if set_picker:
            img.set_picker(True)
            self.cid_select = self.fig.canvas.mpl_connect(
                'pick_event', self.pick_label)

    def select_all_labels(self):
        """Select the entire array"""
        colors = [self.cunselect, self.cselect]
        self._selection_arr = self._orig_selection_arr.copy()
        self._select_img.set_cmap(self.copy_cmap(self._select_img.get_cmap(),
                                                 colors))
        self._select_img.set_norm(self._select_norm)
        self._select_img.set_array(self._selection_arr)
        self._update_magni_img()

    def _update_magni_img(self):
        if self._magni_img is not None:
            img = self._select_img
            magni_img = self._magni_img
            magni_img.set_cmap(img.get_cmap())
            magni_img.set_array(img.get_array())
            magni_img.set_norm(img.norm)
            magni_img.set_alpha(img.get_alpha())
            self.magni.ax.figure.canvas.draw_idle()

    def unselect_all_labels(self):
        """Clear the selection"""
        self._select_img.set_cmap(self._select_cmap)
        self._select_img.set_norm(self._select_norm)
        self._update_magni_img()

    def select_all_other_labels(self):
        """Invert the selection"""
        cmap = self._select_img.get_cmap()
        arr = np.linspace(0, 1., cmap.N)
        colors = cmap(arr)
        c1 = colors[1].copy()
        try:
            c2 = colors[2].copy()
        except IndexError:
            c2 = colors[0].copy()
        for i in range(1, len(colors), 2):
            colors[i, :] = c2
            if i+1 < len(colors):
                colors[i+1, :] = c1
        self._select_img.set_cmap(self.copy_cmap(cmap, colors))
        self._update_magni_img()

    def remove_selected_labels(self, disable=False):
        """Remove the selected parts of the diagram

        This method will call the callbackes in the :attr:`remove_callbacks`
        attribute for all the attributes in the :attr:`label_arrs` list.

        Parameters
        ----------
        disable: bool
            If True, call the :meth:`disable_label_selection` method at the end

        See Also
        --------
        enable_label_selection
        disable_label_selection
        """
        selection = self.selected_labels
        to_big = self._selection_arr > self._select_nlabels
        if not len(selection) and not to_big.any():
            if disable:
                self.disable_label_selection()
            return
        mask = np.isin(self._selection_arr, selection) | to_big
        plottet_arr_in_attrs = False
        for attr in self.label_arrs:
            arr = getattr(self, attr)
            if callable(arr):
                arr = arr()
            if arr is self._selection_arr:
                plottet_arr_in_attrs = True
            if arr.ndim == 3:
                amask = np.tile(mask[:, :, np.newaxis], (1, 1, arr.shape[-1]))
                amask[..., :-1] = False
            else:
                amask = mask
            for func in self.remove_callbacks.get(attr, []):
                func(arr, amask)
            try:
                arr[amask] = 0
            except ValueError:  # assignment destination is read-only
                pass
        if not plottet_arr_in_attrs:
            self._selection_arr[mask] = 0
        self._select_img.set_array(self._selection_arr)
        self._select_img.set_cmap(self._select_cmap)
        self._select_img.set_norm(self._select_norm)
        self._update_magni_img()
        if disable:
            self.disable_label_selection()

    def disable_label_selection(self, remove=None):
        """Disable the label selection

        This will disconnect the *pick_event* and remove the selection images

        Parameters
        ----------
        remove: bool
            Whether to remove the selection image from the plot. If None, the
            :attr:`_remove` attribute is used

        See Also
        --------
        enable_label_selection
        remove_selected_labels"""
        if remove is None:
            remove = self._remove
        if remove:
            try:
                self._select_img.remove()
            except (AttributeError, ValueError) as e:
                pass
        else:
            self._select_img.set_picker(False)
        try:
            self._magni_img.remove()
        except (AttributeError, ValueError) as e:
            pass
        if self.cid_select is not None:
            self.fig.canvas.mpl_disconnect(self.cid_select)
        for attr in ['_select_cmap', '_select_img', '_selection_arr',
                     '_select_norm', 'cid_select', '_magni_img']:
            try:
                delattr(self, attr)
            except AttributeError:
                pass
