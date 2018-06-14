# -*- coding: utf-8 -*-
"""Module for text recognition
"""
from PIL import Image, ImageOps
import numpy as np
from tesserocr import PyTessBaseAPI
from collections import namedtuple


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

    def y1(self):
        return self.top

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


def rgba2rgb(image, color=(255, 255, 255)):
    """Alpha composite an RGBA Image with a specified color.

    Source: http://stackoverflow.com/a/9459208/284318

    Parameters
    ----------
    image: PIL.Image
        The PIL RGBA Image object
    color: tuple
        The rgb color for the background

    Returns
    -------
    PIL.Image
        The rgb image
    """
    image.load()  # needed for split()
    background = Image.new('RGB', image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background


class ColNamesReader(object):
    """A class to recognize the text in an image"""

    _images = None

    _boxes = None

    @property
    def extent(self):
        if self._extent is not None:
            return self._extent
        return [0] + list(np.shape(self.image))[::-1] + [0]

    @extent.setter
    def extent(self, value):
        self._extent = value

    @property
    def rotated_image(self):
        ret = self.image.rotate(-self.rotate, expand=True)
        if self.mirror:
            return ImageOps.mirror(ret)
        return ret

    def __init__(self, image, extent=None, rotate=0, mirror=False, lang=None,
                 ax=None, plot=True, magni=None):
        self.image = image
        self.extent = extent
        self.ax = ax
        self.rotate = rotate
        self.mirror = mirror
        self.magni = magni
        self.lang = lang
        if plot:
            self.plot_image()

    def plot_image(self, ax=None, **kwargs):
        if ax is None:
            ax = self.ax
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.subplots()[1]
        self.ax = ax
        kwargs.setdefault('extent', self.extent)
        self.plot_im = self.ax.imshow(self.image, **kwargs)
        if self.magni is not None:
            self.magni_plot_im = self.magni.ax.imshow(self.image, **kwargs)

    def __reduce__(self):
        return self.__class__, (self.image, self.extent, self.rotate,
                                self.mirror, self.lang, None, False)

    def get_text_and_images(self):
        kws = {} if self.lang is None else {'lang': self.lang}
        with PyTessBaseAPI(**kws) as api:
            api.SetImage(rgba2rgb(self.rotated_image))
            lines = api.GetTextlines()
            images = [t[0] for t in lines]
            text = api.GetUTF8Text()
            text_lines = list(filter(None, map(str.strip, text.splitlines())))
        if self.mirror:
            text_lines = text_lines[::-1]
            images = images[::-1]
        return text_lines, images

    def remove_plots(self):
        """Remove all plotted artists by this reader"""
        for attr in ['plot_im', 'magni_plot_im']:
            try:
                getattr(self, attr, None).remove()
            except (ValueError, AttributeError):
                pass
            try:
                delattr(self, attr)
            except AttributeError:
                pass
