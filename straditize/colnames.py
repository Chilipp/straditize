# -*- coding: utf-8 -*-
"""Module for text recognition
"""
import os
import xarray as xr
from PIL import ImageOps
from straditize.common import rgba2rgb
import numpy as np
import subprocess as spr
import tempfile
from collections import namedtuple
from psyplot.data import safe_list

from functools import partial

try:
    import tesserocr
except ImportError:
    tesserocr = None


_Bbox = namedtuple('_Bbox', tuple('xywh'))


class Bbox(_Bbox):
    """A bounding box"""

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def right(self):
        return self.x + self.w

    @property
    def left(self):
        return self.x

    @property
    def bounds(self):
        return list(self)

    @property
    def extents(self):
        return sorted([self.x0, self.x1]) + sorted([self.y0, self.y1])

    @property
    def corners(self):
        return np.array([
            [self.left, self.bottom],
            [self.left, self.top],
            [self.right, self.bottom],
            [self.right, self.top]
            ])

    @property
    def x0(self):
        return self.left

    @property
    def x1(self):
        return self.right

    @property
    def y0(self):
        return self.bottom

    @property
    def y1(self):
        return self.top

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


class ColNamesReader(object):
    """A class to recognize the text in an image"""

    _images = None

    _boxes = None

    @property
    def highres_image(self):
        return (self.image if self._highres_image is None else
                self._highres_image)

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
        self._colpics = value

    @property
    def rotated_image(self):
        return self.rotate_image(self.image)

    def __init__(self, image, bounds, rotate=45, mirror=False, flip=False,
                 highres_image=None):
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
        self._column_names = []
        self._colpics = []

    def __reduce__(self):
        return (
            self.__class__,
            (self.image, self.column_bounds, self.rotate, self.mirror,
             self.flip),
            {'_colpics': self._colpics,
             '_column_names': self._column_names,
             'highres_image': self.highres_image})

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
        """Extract the picture of the column name"""
        if self.highres_image is not None:
            image = self.rotate_image(self.highres_image)
            xs_hr, ys_hr = self.highres_image.size
            xs, ys = self.image.size
            x01, y01 = self.transform_point(x0, y0, invert=True)
            x11, y11 = self.transform_point(x1, y1, invert=True)
            x02, y02 = self.transform_point(
                x01 * xs_hr / xs, y01 * ys_hr / ys, image=self.highres_image)
            x12, y12 = self.transform_point(
                x11 * xs_hr / xs, y11 * ys_hr / ys, image=self.highres_image)
            return image.crop([x02, y02, x12, y12])
        else:
            return self.rotated_image.crop([x0, y0, x1, y1])

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
        if self.highres_image is not None:
            self.create_variable(ds, 'colnames_hr_image', self.highres_image)
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
        """Create a :class:`ColNamesReader` for a xarray.Dataset"""
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
        return ret

    def transform_point(self, x, y, invert=False, image=None):
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
        """Navigate to the specified column"""
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
        :attr:`rotated_image`"""
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
        ret = image
        if self.mirror:
            ret = ImageOps.mirror(ret)
        if self.flip:
            ret = ImageOps.flip(ret)
        ret = ret.rotate(-self.rotate, expand=True)
        return ret

    def recognize_text(self, image):
        fname = tempfile.NamedTemporaryFile(
            suffix='.png', prefix='stradi_').name
        fname2 = tempfile.NamedTemporaryFile(
            suffix='.txt', prefix='stradi_').name
        image.save(fname)
        spr.check_call(['tesseract', fname, fname2[:-4]])
        with open(fname2) as f:
            text = f.read()
        os.remove(fname)
        os.remove(fname2)
        return text.strip()

    def find_colnames(self, extents=None):
        """Find the names for the columns using tesserocr"""

        def get_overlap(col, box):
            s, e = bounds[col]
            image = self.highres_image if hr else self.image
            x0, y0 = extents[:2]
            xmin = self.transform_point(
                box.x0 + x0, box.y0 + y0, invert=True, image=image)[0]
            xmax = self.transform_point(
                box.x0 + x0, box.y1 + y0, invert=True, image=image)[0]
            xmin, xmax = sorted([xmin, xmax])
            return min(e, xmax) - max(s, xmin)

        bounds = self.column_bounds
        hr = self.highres_image is not None
        rotated = self.rotated_image
        if hr:
            rotated_hr = self.rotate_image(self.highres_image)
            fx, fy = np.round(
                np.array(rotated_hr.size) / rotated.size).astype(int)
            bounds = bounds * fx
        else:
            fx = fy = 1
        if extents is None:
            if hr:
                image = rotated_hr
            else:
                image = rotated
            x0 = y0 = 0
        else:
            extents = np.asarray(extents)
            if hr:
                extents[::2] *= fx
                extents[1::2] *= fy
                image = rotated_hr.crop(extents)
            else:
                image = rotated.crop(extents)

            x0, y0 = self.transform_point(
                *extents[:2], image=self.highres_image if hr else self.image,
                invert=True)

        with tesserocr.PyTessBaseAPI() as api:
            api.SetImage(rgba2rgb(image))
            im_boxes = api.GetComponentImages(tesserocr.RIL.TEXTLINE, True)
            texts = {}
            images = {}
            for i, (im, d, _, _) in enumerate(im_boxes):
                box = Bbox(d['x'], d['y'], d['w'], d['h'])
                api.SetRectangle(*box)
                text = api.GetUTF8Text().strip()
                if len(text) >= 3:
                    texts[box] = text
                    images[box] = im

        if not texts:
            return {}, {}, {}

        boxes = dict(filter(
            lambda t: get_overlap(*t) > 0,
            ((col, max(texts, key=partial(get_overlap, col)))
             for col in range(len(bounds)))))
        x0, y0 = extents[:2]

        return (
            {col: texts[box] for col, box in boxes.items()},
            {col: images[box] for col, box in boxes.items()},
            {col: Bbox((x0 + b.x0) / fx, (y0 + b.y) / fy, b.w / fx, b.h / fy)
             for col, b in boxes.items()})
