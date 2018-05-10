"""Module for the :class:`LabelSelection` class

This module defines the :class:`LabelSelection` class, a base class for the
:class:`straditize.straditizer.Straditizer`
:class:`straditize.binary.DataReader` classes. This class implements the
features to select parts of an image and deletes them"""
import numpy as np
import matplotlib.colors as mcol
from itertools import product


class LabelSelection(object):

    _selection_arr = None

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
    remove_callbacks = {}

    _remove = True

    cid_select = None

    _magni_img = None

    _ellipses = []

    @property
    def selected_labeled_part(self):
        """The selected part of the polygons"""
        if self._selection_arr is None:
            return np.zeros_like(self.labels, dtype=bool)
        selection = self.selected_labels
        return np.isin(self._selection_arr, selection)

    @property
    def selected_part(self):
        """The selected part of the polygons"""
        if self._selection_arr is None:
            return np.zeros_like(self.labels, dtype=bool)
        return self.selected_labeled_part | (
            self._selection_arr > self._select_nlabels)

    @property
    def selected_labels(self):
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
        # The default colormap for binary images
        colors = np.array([self.cunselect for i in range(ncolors)])
        cmap = mcol.LinearSegmentedColormap.from_list('invisible', colors,
                                                      ncolors)
        cmap.set_over(self.cselect)
        return cmap

    @staticmethod
    def copy_cmap(cmap_src, colors):
        cmap = mcol.LinearSegmentedColormap.from_list(cmap_src.name, colors,
                                                      len(colors))
        cmap.set_under(cmap_src(-0.1))
        cmap.set_over(cmap_src(1.1))
        cmap.set_bad(cmap(np.ma.masked_array([np.nan], [True]))[0])
        return cmap

    def pick_label(self, event):
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
        for a in self._ellipses:
            a.remove()
        self._ellipses.clear()

    def select_labels(self, selected):
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

    def enable_label_selection(self, arr, ncolors, img=None,
                               set_picker=False, **kwargs):
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
            self.magni.ax.figure.canvas.draw_idle()

    def unselect_all_labels(self):
        self._select_img.set_cmap(self._select_cmap)
        self._select_img.set_norm(self._select_norm)
        self._update_magni_img()

    def select_all_other_labels(self):
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
