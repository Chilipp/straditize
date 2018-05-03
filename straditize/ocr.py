# -*- coding: utf-8 -*-
"""Module for text recognition
"""
from PIL import Image
import numpy as np
from tesserocr import PyTessBaseAPI, RIL
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


class TextRecognizer(object):
    """A class to recognize the text in an image"""

    _images = None

    _boxes = None

    def __init__(self, image, extent=None, ax=None, plot=False):
        if image.mode != 'RGB':
            image = rgba2rgb(image)
        self.image = image
        self.extent = extent
        self.ax = ax
        if plot:
            self.plot_image()

    def plot_image(self, ax=None):
        if ax is None:
            ax = self.ax
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.subplots()[1]
        self.ax = ax
        self.ax.imshow(self.image)

    def __reduce__(self):
        return self.__class__, (self.image, self.extent, None, False)

    def get_text_and_boxes(self):
        with PyTessBaseAPI() as api:
            api.SetImage(self.image)
            boxes = api.GetComponentImages(RIL.TEXTLINE, True)
            return [t[0] for t in boxes], list(map(Bbox,
                                                   (t[1] for t in boxes)))
