# -*- coding: utf-8 -*-
"""Module for text recognition

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
import re
import xarray as xr
from PIL import ImageOps, Image
from straditize.common import rgba2rgb
import numpy as np
import subprocess as spr
from collections import namedtuple
from psyplot.data import safe_list

from functools import partial


# check tesseract version and import tesserocr. If the tesseract version
# is 4.0.*, then we have to locale.setlocale(locale.LC_ALL, 'C')
# (see https://github.com/sirfz/tesserocr/issues/137)
try:
    tesseract_version = spr.check_output('tesseract --version'.split())
except FileNotFoundError:
    tesseract_version = tesserocr = None
else:
    tesseract_version = re.findall(
        '\d+\.\d+\.*', tesseract_version.decode('utf-8'))[0]
    if tesseract_version.startswith('4.0.'):
        import locale
        locale.setlocale(locale.LC_ALL, 'C')
    try:
        import tesserocr
    except ImportError:
        tesserocr = None


_Bbox = namedtuple('_Bbox', tuple('xywh'))


class Bbox(_Bbox):
    """A bounding box for a column name"""

    @property
    def top(self):
        """The top of the box"""
        return self.y

    @property
    def bottom(self):
        """The bottom of the box"""
        return self.y + self.h

    @property
    def right(self):
        """The right edge of the box"""
        return self.x + self.w

    @property
    def left(self):
        """The left edge of the box"""
        return self.x

    @property
    def bounds(self):
        """A list ``[x, y, width, height]``"""
        return list(self)

    @property
    def extents(self):
        """A list ``[x0, x1, y0, y1]`` with ``x0 <= x1`` and ``y0 <= y1``"""
        return sorted([self.x0, self.x1]) + sorted([self.y0, self.y1])

    @property
    def crop_extents(self):
        """The extents necessary for PIL.Image.crop"""
        return self.left, self.top, self.right, self.bottom

    @property
    def corners(self):
        """A np.ndarray of shape (4, 2) with the corners of the box"""
        return np.array([
            [self.left, self.bottom],
            [self.left, self.top],
            [self.right, self.bottom],
            [self.right, self.top]
            ])

    @property
    def x0(self):
        """The left edge"""
        return self.left

    @property
    def height(self):
        """The (positive) height"""
        return abs(self.h)

    @property
    def width(self):
        """The (positive) width"""
        return abs(self.w)

    @property
    def x1(self):
        """The right edge"""
        return self.right

    @property
    def y0(self):
        """The lower (bottom) edge"""
        return self.bottom

    @property
    def y1(self):
        """The upper (top) edge"""
        return self.top

    @classmethod
    def from_dict(cls, d):
        """Construct a box from the dictionary"""
        return cls(**d)


class ColNamesReader(object):
    """A class to recognize the text in an image

    This object handles the column names in the :attr:`column_names` attribute.
    It also implements several algorithms to automatically read in the column
    names using the tesserocr package. In particular these are the
    :meth:`recognize_text` method to read in one small image and the
    :meth:`find_colnames` method to find the column names automatically."""

    _images = None

    _boxes = None

    #: The RGBA :class:`PIL.Image.Image` that stores the column names
    image = None

    #: Boolean flag. If True, the data part is masked out in the
    #: :attr:`highres_image`
    ignore_data_part = True

    #: The vertical data limits of the data part that shall be exluded in the
    #: :attr:`highres_image` if the :attr:`ignore_data_part` is True
    data_ylim = None

    @property
    def highres_image(self):
        """The :attr:`image` attribute with higher resolution and with masked
        out data part if the :attr:`ignore_data_part` attribute is True and the
        :attr:`data_ylim` attribute is not None. The data part is then set to
        white with 0 alpha"""
        ret = (self.image if self._highres_image is None else
               self._highres_image)
        if self.data_ylim is not None and self.ignore_data_part:
            arr = np.array(ret)
            ylim = self.data_ylim * ret.size[1] / self.image.size[1]
            arr[slice(*ylim.astype(int)), :, :-1] = 255
            arr[slice(*ylim.astype(int)), :, -1] = 0
            ret = Image.fromarray(arr)
        return ret

    @highres_image.setter
    def highres_image(self, value):
        """The :attr:`image` attribute with higher resolution and with masked
        out data part if the :attr:`ignore_data_part` attribute is True and the
        :attr:`data_ylim` attribute is not None. The data part is then set to
        white with 0 alpha"""
        self._highres_image = value

    _highres_image = None

    @property
    def column_names(self):
        """The names of the columns"""
        nnames = len(self._column_names)
        ncols = len(self.column_bounds)
        if nnames < ncols:
            self._column_names += list(map(str, range(nnames, ncols)))
        return self._column_names[:ncols]

    @column_names.setter
    def column_names(self, value):
        """The names of the columns"""
        self._column_names = value

    @property
    def colpics(self):
        """The pictures of the column names"""
        npics = len(self._colpics)
        ncols = len(self.column_bounds)
        if npics < ncols:
            self._colpics += [None] * (ncols - npics)
        return self._colpics[:ncols]

    @colpics.setter
    def colpics(self, value):
        """The pictures of the column names"""
        self._colpics = value

    @property
    def rotated_image(self):
        """The rotated :attr:`image` based on the :meth:`rotate_image` method
        """
        return self.rotate_image(self.image)

    def __init__(self, image, bounds, rotate=45, mirror=False, flip=False,
                 highres_image=None, data_ylim=None):
        """
        Parameters
        ----------
        image: PIL.Image.Image
            The RGBA image that has the same shape as the original
            stratigraphic diagram
        bounds: np.ndarray of shape (N, 2)
            The boundaries for each column. These are essential for the
            :meth:`find_colnames` and the :meth:`highlight_column` methods
        rotate: float
            An angle between 0 and 90 that corresponds to the rotation of the
            column names
        mirror: bool
            If True, the image is mirrored (horizontally)
        flip: bool
            If True, the image is flipped (vertically)
        highres_image: PIL.Image.Image
            A high resolution version of the `image` with the same
            width-to-height ratio
        data_ylim: tuple (y0, y1)
            The vertical data limits of the data part that should be ignored
            in the :meth:`find_colnames` method if the :attr:`ignore_data_part`
            is True
        """
        from PIL import Image

        try:
            mode = image.mode
        except AttributeError:
            image = Image.fromarray(image, mode='RGBA')
        else:
            if mode != 'RGBA':
                image = image.convert('RGBA')
        self.image = image
        self.column_bounds = bounds
        self.rotate = rotate
        self.mirror = mirror
        self.flip = flip
        if highres_image is not None:
            try:
                mode = highres_image.mode
            except AttributeError:
                highres_image = Image.fromarray(highres_image, mode='RGBA')
            else:
                if mode != 'RGBA':
                    highres_image = highres_image.convert('RGBA')
        self.highres_image = highres_image
        self.data_ylim = None if data_ylim is None else np.asarray(data_ylim)
        self._column_names = []
        self._colpics = []

    def __reduce__(self):
        return (
            self.__class__,
            (self.image, self.column_bounds, self.rotate, self.mirror,
             self.flip),
            {'_colpics': self._colpics,
             '_column_names': self._column_names,
             '_highres_image': self._highres_image,
             'data_ylim': self.data_ylim})

    def close(self):
        """Close the column names reader"""
        self._colpics.clear()
        self._column_names.clear()
        self.image.close()
        del self.image
        if self._highres_image is not None:
            self._highres_image.close()
            del self._highres_image

    nc_meta = {
        'colnames_image': {
            'dims': ('ycolname', 'xcolname', 'rgba'),
            'long_name': 'RGBA images for column names reader',
            'units': 'color'},
        'colnames_hr_image': {
            'dims': ('ycolname_hr', 'xcolname_hr', 'rgba'),
            'long_name': "Highres image for column names reader",
            'units': 'color'},
        'colnames_bounds': {
            'dims': ('column', 'limit'), 'units': 'px',
            'long_name': ('The boundaries of the columns for the column names '
                          'reader')},
        'colname': {
            'dims': 'column', 'long_name': 'Name of the columns'},
        'colpic': {
            'dims': ('column', 'colpic_y', 'colpic_x', 'rgba'),
            'long_name': 'The pictures of the column names', 'units': 'color'},
        'colpic_extents': {
            'dims': ('column', 'limit'),
            'long_name': 'The limits of the column names pictures',
            'units': 'px'},
        'rotate_colnames': {
            'dims': (), 'long_name': 'The rotation angle for column names'},
        'mirror_colnames': {
            'dims': (),
            'long_name': "Mirror the column names picture (horizontally)"},
        'flip_colnames': {
            'dims': (),
            'long_name': "Flip the column names picture (vertically)"},
        }

    def create_variable(self, ds, vname, data, **kwargs):
        """Insert the data into a variable in an :class:`xr.Dataset`"""
        attrs = self.nc_meta[vname].copy()
        dims = safe_list(attrs.pop('dims', vname))
        if vname in ds:
            ds.variables[vname][kwargs] = data
        else:
            v = xr.Variable(dims, np.asarray(data), attrs=attrs)
            ds[vname] = v
        return vname

    def get_colpic(self, x0, y0, x1, y1):
        """Extract the picture of the column name

        Parameters
        ----------
        x0: int
            The left edge
        y0: int
            The upper edge
        x1: int
            The right edge
        y1: int
            The lower edge

        Returns
        -------
        PIL.Image.Image
            The part of the rotated :attr:`highres_image` cropped out from the
            given parameters"""
        hr = self.highres_image
        image = self.rotate_image(hr)
        xs_hr, ys_hr = hr.size
        xs, ys = self.image.size
        x01, y01 = self.transform_point(x0, y0, invert=True)
        x11, y11 = self.transform_point(x1, y1, invert=True)
        x02, y02 = self.transform_point(
            x01 * xs_hr / xs, y01 * ys_hr / ys, image=hr)
        x12, y12 = self.transform_point(
            x11 * xs_hr / xs, y11 * ys_hr / ys, image=hr)
        return image.crop([x02, y02, x12, y12])

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
        self.create_variable(ds, 'colnames_image', self.image)
        if self._highres_image is not None:
            self.create_variable(ds, 'colnames_hr_image', self._highres_image)
        self.create_variable(ds, 'colnames_bounds', self.column_bounds)
        self.create_variable(ds, 'colname', self.column_names)
        self.create_variable(ds, 'rotate_colnames', self.rotate)
        self.create_variable(ds, 'mirror_colnames', self.mirror)
        self.create_variable(ds, 'flip_colnames', self.flip)
        if any(self.colpics):
            extents = np.array([colpic.size[::-1] if colpic else (0, 0)
                                for colpic in self.colpics])
            self.create_variable(ds, 'colpic_extents', extents)
            colpics_shp = (len(extents), ) + tuple(extents.max(axis=0)) + (4, )
            colpics = np.zeros(
                colpics_shp,
                dtype=next(np.asarray(pic).dtype for pic in self.colpics))
            for i, (pic, (ys, xs)) in enumerate(zip(self.colpics, extents)):
                colpics[i, :ys, :xs, :] = np.asarray(pic)
            self.create_variable(ds, 'colpic', colpics)
        return ds

    @classmethod
    def from_dataset(cls, ds):
        """Create a :class:`ColNamesReader` for a xarray.Dataset

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset as obtained from the :meth:`to_dataset` method"""
        from PIL import Image
        ret = cls(ds['colnames_image'].values, ds['colnames_bounds'].values,
                  rotate=ds['rotate_colnames'].values,
                  mirror=bool(ds['mirror_colnames'].values),
                  flip=bool(ds['flip_colnames'].values))
        if 'colnames_hr_image' in ds:
            ret.highres_image = Image.fromarray(ds['colnames_hr_image'].values,
                                                mode='RGBA')
        ret._column_names = list(ds['colname'].values)
        if 'colpic' in ds:
            ret._colpics = [
                Image.fromarray(arr[:ys, :xs].values, mode='RGBA')
                if xs and ys else None
                for arr, (ys, xs) in zip(ds['colpic'],
                                         ds['colpic_extents'].values)]
        if 'data_lims' in ds:
            ret.data_ylim = ds['data_lims'].sel(axis='y').values
        return ret

    def transform_point(self, x, y, invert=False, image=None):
        """Transform a point between un-rotated and rotated coordinate system

        Parameters
        ----------
        x: float
            The x-coordinate of the point in the source coordinate system
        y: float
            The y-coordinate of the point in the source coordinate system
        invert: bool
            If True, the source coordinate system is the rotated one (i.e.
            this method transform from the :attr:`rotated_image` to the
            coordinate system of the :attr:`image`), other wise from the
            :attr:`image` to the :attr:`rotated_image`
        image: PIL.Image.Image
            The unrotated source image. If None, the :attr:`image` is used.
            This image defines the source coordinate system (or the target
            coordinate system if `invert` is True)

        Returns
        -------
        float
            The transformed `x`-coordinate
        float
            The transformed `y`-coordinate
        """
        import matplotlib.transforms as mt
        angle = np.deg2rad(self.rotate)
        if image is None:
            image = self.image
        xs, ys = image.size
        trans = mt.Affine2D().rotate(angle).translate(ys*np.sin(angle), 0)
        if invert:
            x, y = trans.inverted().transform_point([x, y])
        if self.mirror:
            x = xs - x
        if self.flip:
            y = ys - y
        if invert:
            return x, y
        else:
            return trans.transform_point([x, y])

    def navigate_to_col(self, col, ax):
        """Navigate to the specified column

        Change the x- and y-limits of the `ax` to display the given `col` based
        on the :attr:`column_bounds`

        Parameters
        ----------
        col: int
            The column number
        ax: matplotlib.axes.Axes
            The matplotlib axes for which to update the limits. This `ax` is
            expected to show the :attr:`rotated_image`"""
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        dx = (xmax - xmin) / 2.
        dy = (ymax - ymin) / 2.
        xc = xmin + dx
        yc = ymin + dy
        xc_t, yc_t = self.transform_point(xc, yc, True)
        xc_col = np.mean(self.column_bounds[col])
        xc_new, yc_new = self.transform_point(xc_col, yc_t)
        ax.set_xlim(xc_new - dx, xc_new + dx)
        ax.set_ylim(yc_new - dy, yc_new + dy)

    def highlight_column(self, col, ax):
        """Highlight the column in the given axes displaying the
        :attr:`rotated_image`

        This method draws a rotated rectangle highlighting the given column
        `col` in the given `ax`.

        Parameters
        ----------
        col: int
            The column number
        ax: matplotlib.axes.Axes
            The matplotlib axes on which to plot the rectangle. This `ax` is
            expected to show the :attr:`rotated_image`"""
        import matplotlib.patches as patches
        import matplotlib as mpl
        xmin, xmax = self.column_bounds[col]
        xs, ys = self.image.size
        if self.mirror:
            xmin, xmax = xs - xmax, xs - xmin
        angle = np.deg2rad(self.rotate)
        x = ys * np.sin(angle) + xmin * np.cos(angle)
        y = xmin * np.sin(angle)
        patch = patches.Rectangle((x, y), xmax-xmin, ys, color="red",
                                  alpha=0.50)
        tr = mpl.transforms.Affine2D().rotate_around(x, y, angle)
        patch.set_transform(tr + ax.transData)
        ax.add_patch(patch)

        return patch

    def rotate_image(self, image):
        """Modify an image with :attr:`rotate`, :attr:`flip`, :attr:`mirror`

        This method rotated, mirrors and/or flips the given `image` based on
        the :attr:`rotate`, :attr:`mirror` and :attr:`flip` attributes

        Parameters
        ----------
        image: PIL.Image.Image
            The source image

        Returns
        -------
        PIL.Image.Image
            The target image
        """
        ret = image
        if self.mirror:
            ret = ImageOps.mirror(ret)
        if self.flip:
            ret = ImageOps.flip(ret)
        ret = ret.rotate(-self.rotate, expand=True)
        return ret

    def recognize_text(self, image):
        """Recognize the text in an image using tesserocr

        This method uses the :func:`tesserocr.image_to_text` to read in the
        text in a given `image`

        Parameters
        ----------
        image: PIL.Image.Image
            The image to read in

        Returns
        -------
        str
            The text found in it without newline characters"""
        if tesserocr is None:
            raise ImportError("tesserocr module not found!")

        if image.mode == 'RGBA':
            image = rgba2rgb(image)

        return tesserocr.image_to_text(image).strip().replace('\n', ' ')

    def find_colnames(self, extents=None):
        """Find the names for the columns using tesserocr

        Parameters
        ----------
        extents: list of floats (x0, y0, x1, y1)
            The extents to crop the :attr:`rotated_image`. We only look for
            column names in this image

        Returns
        -------
        dict
            A mapping from column number to a string (the column name)
        dict
            A mapping from column number to a :class:`PIL.Image.Image` (the
            image of the column name)
        dict
            A mapping from column number to a :class:`Bbox` (the bounding box
            of the corresponding column name)"""

        def get_overlap(col, box):
            s, e = bounds[col]
            x0, y0 = extents[:2]
            xmin = self.transform_point(
                box.x0 + x0, box.y0 + y0, invert=True, image=hr)[0]
            xmax = self.transform_point(
                box.x0 + x0, box.y1 + y0, invert=True, image=hr)[0]
            xmin, xmax = sorted([xmin, xmax])
            return max(min(e, xmax) - max(s, xmin), 0)

        def vbox_distance(b1, b2):
            if b1.left > b2.right or b1.right < b2.left:
                return np.inf  # no overlap
            return min(abs(b1.top - b2.bottom), abs(b2.top - b1.bottom))

        if tesserocr is None:
            raise ImportError("tesserocr module not found!")

        bounds = self.column_bounds
        cols = list(range(len(bounds)))
        rotated = self.rotated_image
        hr = self.highres_image
        rotated_hr = self.rotate_image(hr)
        fx, fy = np.round(
            np.array(rotated_hr.size) / rotated.size).astype(int)
        bounds = bounds * fx

        if extents is None:
            image = rotated_hr
            x0 = y0 = 0
        else:
            extents = np.asarray(extents)
            extents[::2] *= fx
            extents[1::2] *= fy
            image = rotated_hr.crop(extents)

            x0, y0 = self.transform_point(
                *extents[:2], image=hr,
                invert=True)

        if tesseract_version.startswith('4.0.'):
            # LC_ALL might have been changed by some other module, so we set
            # it here again to "C"
            import locale
            locale.setlocale(locale.LC_ALL, 'C')

        with tesserocr.PyTessBaseAPI() as api:
            api.SetImage(rgba2rgb(image))
            im_boxes = api.GetComponentImages(tesserocr.RIL.TEXTLINE, True)
            texts = {}
            images = {}
            for i, (im, d, _, _) in enumerate(im_boxes):
                box = Bbox(**d)
                if not any(get_overlap(col, box) for col in cols):
                    continue
                # expand the image to improve text recognition
                im = ImageOps.expand(rgba2rgb(image.crop(box.crop_extents)),
                                     int(im.size[1] / 2.), (255, 255, 255))
                text = tesserocr.image_to_text(im).strip()
                if len(text) >= 3:
                    texts[box] = text
                    images[box] = im.convert('RGBA')

        if not texts:
            return {}, {}, {}

        # merge boxes that are closer than one 1em
        em = min(b.h for b in texts)
        merged = {None}
        while merged:
            merged = set()
            for b1, t in list(texts.items()):
                if b1 in merged:
                    continue
                col = max(cols, key=partial(get_overlap, box=b1))
                for b2, t in list(texts.items()):
                    if (b1 is b2 or b2 in merged or not get_overlap(col, b2) or
                            vbox_distance(b1, b2) > 0.5*em):
                        continue
                    merged.update([b1, b2])
                    box = Bbox(min(b1.x, b2.x), min(b1.y, b2.y),
                               max(b1.x1, b2.x1) - min(b1.x0, b2.x0),
                               max(b1.y0, b2.y0) - min(b1.y1, b2.y1))
                    texts[box] = texts[b1] + (
                        ' ' if not texts[b1].endswith('-') else '') + texts[b2]
                    images[box] = image.crop(box.crop_extents)
                    b1 = box
            for b in merged:
                del texts[b], images[b]

        # get a mapping from box to column from the overlap
        boxes = dict(filter(
            lambda t: get_overlap(*t),
            ((col, max(texts, key=partial(get_overlap, col)))
             for col in range(len(bounds)))))
        x0, y0 = extents[:2]

        return (
            {col: texts[box] for col, box in boxes.items()},
            {col: images[box] for col, box in boxes.items()},
            {col: Bbox((x0 + b.x0) / fx, (y0 + b.y) / fy, b.w / fx, b.h / fy)
             for col, b in boxes.items()})
