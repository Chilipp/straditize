# -*- coding: utf-8 -*-
"""Magnifier class for an image

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
from matplotlib.widgets import Slider
import matplotlib.colorbar as mcbar
from matplotlib.axes import SubplotBase


class Magnifier(object):
    """A magnification of a matplotlib axes

    It zooms into the region where the mouse pointer is, when it enters the
    source axes. The appearance of the plot is defined by the :meth:`make_plot`
    method."""

    @property
    def dx(self):
        val = self.slider.val
        ret = np.abs(np.diff(self.ax_src.get_xlim())) * (100 - val) / 200.
        return -ret if self.ax.xaxis_inverted() else ret

    @property
    def dy(self):
        val = self.slider.val
        ret = np.abs(np.diff(self.ax_src.get_ylim())) * (100 - val) / 200.
        return -ret if self.ax.yaxis_inverted() else ret

    cid_enter = None
    cid_motion = None
    cid_leave = None
    ax = None

    def __init__(self, ax_src, ax=None, *args, **kwargs):
        self.ax_src = ax_src
        if ax is None:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            fig.canvas.set_window_title(
                'Figure %i: Zoom of figure %i' % (fig.number,
                                                  ax_src.figure.number))
        self.ax = ax
        self.point = ax.plot(
            [np.mean(ax.get_xlim())], [np.mean(ax.get_ylim())], 'ro',
            visible=False, zorder=10)[0]
        self.make_plot(*args, **kwargs)
        self.enable_zoom()
        if isinstance(ax, SubplotBase):
            slider_ax, kw = mcbar.make_axes_gridspec(
                ax, orientation='horizontal', location='bottom')
        else:
            slider_ax, kw = mcbar.make_axes(
                ax, position='bottom', orientation='horizontal')
        slider_ax.set_aspect('auto')
        slider_ax._hold = True
        self.slider = Slider(slider_ax, 'Zoom', 0, 99.5, valfmt='%1.2g %%')
        self.slider.set_val(90)
        self.slider.on_changed(self.adjust_limits)
        self.adjust_limits(90)

    def adjust_limits(self, zoom_val):
        x = np.mean(self.ax.get_xlim())
        y = np.mean(self.ax.get_ylim())
        dx = self.dx
        dy = self.dy
        self.ax.set_xlim(x - dx, x + dx)
        self.ax.set_ylim(y - dy, y + dy)
        self.ax.figure.canvas.draw()

    def make_plot(self, image, *args, **kwargs):
        self.plot_image = self.ax.imshow(image, *args, **kwargs)

    def onmotion(self, event):
        if event.inaxes != self.ax_src or self.ax is None:
            return
        x, y = event.xdata, event.ydata
        dx = self.dx
        dy = self.dy
        ax = self.ax
        xmin, xmax = x - dx, x + dx
        ymin, ymax = y - dy, y + dy
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        self.point.set_xdata([x])
        self.point.set_ydata([y])
        self.point.set_visible(True)
        ax.figure.canvas.draw()

    def onenter(self, event):
        if event.inaxes != self.ax_src or self.ax is None:
            return
        canvas = self.ax_src.figure.canvas
        canvas.mpl_disconnect(self.cid_enter)
        self.cid_leave = canvas.mpl_connect('axes_leave_event', self.onleave)
        self.cid_motion = canvas.mpl_connect('motion_notify_event',
                                             self.onmotion)

    def close(self):
        """Close the magnifier and the associated plots"""
        import matplotlib.pyplot as plt
        try:
            self.plot_image.remove()
        except (AttributeError, ValueError):
            pass
        try:
            self.point.remove()
        except (AttributeError, ValueError):
            pass
        self.disconnect()
        fig = self.ax.figure
        fig.delaxes(self.ax)
        self.slider.disconnect_events()
        fig.delaxes(self.slider.ax)
        plt.close(self.ax.figure)
        del self.plot_image, self.ax, self.ax_src, self.slider

    def onleave(self, event):
        canvas = self.ax_src.figure.canvas
        canvas.mpl_disconnect(self.cid_leave)
        canvas.mpl_disconnect(self.cid_motion)
        self.enable_zoom()
        self.point.set_visible(False)
        if self.ax is not None:
            self.ax.figure.canvas.draw()

    def enable_zoom(self):
        self.cid_enter = self.ax_src.figure.canvas.mpl_connect(
            'axes_enter_event', self.onenter)

    def disconnect(self):
        canvas = self.ax_src.figure.canvas
        for cid in [self.cid_enter, self.cid_leave, self.cid_motion]:
            if cid is not None:
                canvas.mpl_disconnect(cid)
