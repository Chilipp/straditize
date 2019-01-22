# -*- coding: utf-8 -*-
"""Module for a cross mark to select one point in a matplotlib axes

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
import six
from psyplot.data import Signal
from psyplot.utils import _temp_bool_prop
from itertools import chain, repeat, product
from straditize.common import docstrings

if six.PY2:
    from itertools import izip_longest as zip_longest
else:
    from itertools import zip_longest


class CrossMarks(object):
    """
    A set of draggable marks in a matplotlib axes
    """

    @property
    def fig(self):
        """The :class:`matplotlib.figure.Figure` that this mark plots on"""
        return self.ax.figure

    @property
    def y(self):
        """The y-position of the mark"""
        return self.ya[self._i_hline]

    @y.setter
    def y(self, value):
        """The y-position of the mark"""
        self.ya[self._i_hline] = value

    @property
    def x(self):
        """The x-position of the mark"""
        return self.xa[self._i_vline]

    @x.setter
    def x(self, value):
        """The x-position of the mark"""
        self.xa[self._i_vline] = value

    @property
    def hline(self):
        """The current horizontal line"""
        return self.hlines[self._i_hline]

    @property
    def vline(self):
        """The current vertical line"""
        return self.vlines[self._i_vline]

    @property
    def pos(self):
        """The position of the current line"""
        return np.array(
            [self.xa[self._i_vline], self.ya[self._i_hline]])

    @pos.setter
    def pos(self, value):
        """The position of the current line"""
        self.xa[self._i_vline] = value[0] if np.ndim(value) else value
        self.ya[self._i_hline] = value[1] if np.ndim(value) else value

    @property
    def points(self):
        """The x-y-coordinates of the points as a (N, 2)-shaped array"""
        return np.array(list(product(self.xa, self.ya)))

    @property
    def line_connections(self):
        """The line connections to the current position"""
        return self._all_line_connections[self._i_hline][self._i_vline]

    @line_connections.setter
    def line_connections(self, value):
        """The line connections to the current position"""
        self._all_line_connections[self._i_hline][self._i_vline] = value

    @property
    def other_connections(self):
        """All other connections to the current position"""
        return self._all_other_connections[self._i_hline][self._i_vline]

    @other_connections.setter
    def other_connections(self, value):
        """All other connections to the current position"""
        self._all_other_connections[self._i_hline][self._i_vline] = value

    @property
    def idx_h(self):
        """The index for vertical lines"""
        return None if not self._idx_h else self._idx_h[self._i_vline]

    @idx_h.setter
    def idx_h(self, value):
        """The index for vertical lines"""
        if self._idx_h is None:
            self._idx_h = [None] * len(self.xa)
        self._idx_h[self._i_vline] = value

    @property
    def idx_v(self):
        """The index for horizontal lines"""
        return None if not self._idx_v else self._idx_v[self._i_hline]

    @idx_v.setter
    def idx_v(self, value):
        """The index for horizontal lines"""
        if self._idx_v is None:
            self._idx_v = [None] * len(self.ya)
        self._idx_v[self._i_hline] = value

    #: Boolean to control whether the vertical lines should be hidden
    hide_vertical = False

    #: Boolean to control whether the horizontal lines should be hidden
    hide_horizontal = False

    #: A signal that is emitted when the mark is moved. Connected function are
    #: expected to accept two arguments. One tuple with the old position and
    #: the CrossMarks instance itself
    moved = Signal('_moved')

    block_signals = _temp_bool_prop(
        'block_signals', "Block the emitting of signals of this instance")

    #: The index of the selected hline
    _i_hline = 0

    #: The index of the selected vline
    _i_vline = 0

    #: Boolean that is True, if the animated property of the lines should be
    #: used
    _animated = True

    #: The matplotlib axes to plot on
    ax = None

    #: The x-limits of the :attr:`hlines`
    xlim = None

    #: The x-limits of the :attr:`vlines`
    ylim = None

    #: Class attribute that is set to a :class:`CrossMark` instance to lock the
    #: selection of marks
    lock = None

    #: A boolean to control whether the connected artists should be shown
    #: at all
    show_connected_artists = True

    #: a list of :class:`matplotlib.artist.Artist` whose colors are changed
    #: when this mark is selected
    connected_artists = []

    #: The default properties of the unselected mark, complementing the
    #: :attr:`_select_props`
    _unselect_props = {}

    #: the list of horizontal lines
    hlines = []

    #: the list of vertical lines
    vlines = []

    @docstrings.get_sectionsf('CrossMarks')
    @docstrings.dedent
    def __init__(self, pos=(0, 0), ax=None, selectable=['h', 'v'],
                 draggable=['h', 'v'], idx_h=None, idx_v=None,
                 xlim=None, ylim=None, select_props={'c': 'r'},
                 auto_hide=False, connected_artists=[], lock=True,
                 draw_lines=True, hide_vertical=None, hide_horizontal=None,
                 **kwargs):
        """
        Parameters
        ----------
        pos: tuple of 2 arrays
            The initial positions of the crosses. The first item marks the
            x-coordinates of the points, the second the y-coordinates
        ax: matplotlib.axes.Axes
            The axes object to draw to. If not specified and draw_lines is
            True, the current axes object is used
        selectable: list of {'x', 'y'}
            Determine whether only the x-, y-, or both lines should be
            selectable
        draggable: list of {'x', 'y'}
            Determine whether only the x-, y-, or both lines should be
            draggable
        idx_h: pandas.Index
            The index for the horizontal coordinates. If not provided, we
            use a continuous movement along x.
        idx_v: pandas.Index
            The index for the vertical coordinates. If not provided, we
            use a continuous movement along y.
        xlim: tuple of floats (xmin, xmax)
            The minimum and maximum x value for the lines
        ylim: tuple for floats (ymin, ymax)
            The minimum and maximum y value for the lines
        select_props: color
            The line properties for selected marks
        auto_hide: bool
            If True, the lines are hidden if they are not selected.
        connected_artists: list of artists
            List of artists whose properties should be changed to
            `select_props` when this marks is selected
        lock: bool
            If True, at most one mark can be selected at a time
        draw_lines: bool
            If True, the cross mark lines are drawn. Otherwise, you must call
            the `draw_lines` method explicitly
        hide_vertical: bool
            Boolean to control whether the vertical lines should be hidden. If
            None, the default class attribute is used
        hide_horizontal: bool
            Boolean to control whether the horizontal lines should be hidden.
            If None, the default class attribute is used
        ``**kwargs``
            Any other keyword argument that is passed to the
            :func:`matplotlib.pyplot.plot` function"""
        self.xa = np.asarray([pos[0]] if not np.ndim(pos[0]) else pos[0],
                             dtype=float)
        self.ya = np.asarray([pos[1]] if not np.ndim(pos[1]) else pos[1],
                             dtype=float)
        self._xa0 = self.xa.copy()
        self._ya0 = self.ya.copy()
        self._constant_dist_x = []
        self._constant_dist_x_marks = []
        self._constant_dist_y = []
        self._constant_dist_y_marks = []
        self.selectable = list(selectable)
        self.draggable = list(draggable)
        if hide_horizontal is not None:
            self.hide_horizontal = hide_horizontal
        if hide_vertical is not None:
            self.hide_vertical = hide_vertical
        self._select_props = select_props.copy()
        self.press = None
        if idx_h is not None:
            try:
                idx_h[0][0]
            except IndexError:
                idx_h = [idx_h] * len(self.xa)
        if idx_v is not None and np.ndim(idx_v) != 2:
            try:
                idx_v[0][0]
            except IndexError:
                idx_v = [idx_v] * len(self.ya)
        self._idx_h = idx_h
        self._idx_v = idx_v
        self.xlim = xlim
        self.ylim = ylim
        self.other_marks = []
        self._connection_visible = []
        self._all_line_connections = [[[] for _ in range(len(self.xa))]
                                      for _ in range(len(self.ya))]
        self._all_other_connections = [[[] for _ in range(len(self.xa))]
                                       for _ in range(len(self.ya))]
        self._lock_mark = lock
        kwargs.setdefault('marker', '+')
        self.auto_hide = auto_hide
        self._line_kwargs = kwargs
        self.set_connected_artists(list(connected_artists))
        if draw_lines:
            self.ax = ax
            self.draw_lines()
            self.connect()
        elif ax is not None:
            self.ax = ax

    def set_connected_artists(self, artists):
        """Set the connected artists

        Parameters
        ----------
        artists: matplotlib.artist.Artist
            The artists (e.g. other lines) that should be connected and
            highlighted if this mark is selected"""
        self.connected_artists = artists
        self._connected_artists_props = [
            {key: getattr(a, 'get_' + key)() for key in self._select_props}
            for a in artists]

    def draw_lines(self, **kwargs):
        """Draw the vertical and horizontal lines

        Parameters
        ----------
        ``**kwargs``
            An keyword that is passed to the :func:`matplotlib.pyplot.plot`
            function"""
        if kwargs:
            self._line_kwargs = kwargs
        else:
            kwargs = self._line_kwargs

        if self.ax is None:
            import matplotlib.pyplot as plt
            self.ax = plt.gca()

        if self.ylim is None:
            self.ylim = ylim = self.ax.get_ylim()
        else:
            ylim = self.ylim
        if self.xlim is None:
            self.xlim = xlim = self.ax.get_xlim()
        else:
            xlim = self.xlim

        xmin = min(xlim)
        xmax = max(xlim)
        ymin = min(ylim)
        ymax = max(ylim)
        xy = zip(repeat(self.xa), self.ya)
        x, y = next(xy)
        # we plot the first separate line to get the correct color
        line = self.ax.plot(np.r_[[xmin], x, [xmax]],
                            [y] * (len(x) + 2), markevery=slice(1, len(x) + 1),
                            label='cross_mark_hline',
                            visible=not self.hide_horizontal, **kwargs)[0]
        if 'color' not in kwargs and 'c' not in kwargs:
            kwargs['c'] = line.get_c()
        # now the rest of the horizontal lines
        self.hlines = [line] + [
            self.ax.plot(np.r_[[xmin], x, [xmax]],
                         [y] * (len(x) + 2), markevery=slice(1, len(x) + 1),
                         label='cross_mark_hline',
                         visible=not self.hide_horizontal, **kwargs)[0]
            for x, y in xy]
        # and the vertical lines
        self.vlines = [
            self.ax.plot([x] * (len(y) + 2),
                         np.r_[[ymin], y, [ymax]],
                         markevery=slice(1, len(y) + 1),
                         label='cross_mark_vline',
                         visible=not self.hide_vertical, **kwargs)[0]
            for x, y in zip(self.xa, repeat(self.ya))]
        for h, v in zip(self.hlines, self.vlines):
            visible = v.get_visible()
            v.update_from(h)
            v.set_visible(visible)
        line = self.hlines[0]
        props = self._select_props
        if 'lw' not in props and 'linewidth' not in props:
            props.setdefault('lw', line.get_lw())
        # copy the current attributes from the lines
        self._unselect_props = {key: getattr(line, 'get_' + key)()
                                for key in props}
        if self.auto_hide:
            for l in chain(self.hlines, self.vlines, self.line_connections):
                l.set_lw(0)

    def set_visible(self, b):
        """Set the visibility of the mark

        Parameters
        ----------
        b: bool
            If False, hide all horizontal and vertical lines, and the
            :attr:`connected_artists`"""
        for l in self.hlines:
            l.set_visible(b and not self.hide_horizontal)
        for l in self.vlines:
            l.set_visible(b and not self.hide_vertical)
        show_connected = self.show_connected_artists and b
        for l in self.connected_artists:
            l.set_visible(show_connected)

    def __reduce__(self):
        return (
            self.__class__,
            ((self.xa, self.ya),        # pos
             None,                      # ax  --  do not make a plot
             self.selectable,           # selectable
             self.draggable,            # draggable
             self._idx_h,               # idx_h
             self._idx_v,               # idx_v
             self.xlim,                 # xlim
             self.ylim,                 # ylim
             self._select_props,        # select_props
             self.auto_hide,            # auto_hide
             [],                        # connected_artists
             self._lock_mark,           # lock
             False,                     # draw_lines  --  do not draw the lines
             ),
            {'_line_kwargs': self._line_kwargs,
             'hide_horizontal': self.hide_horizontal,
             'hide_vertical': self.hide_vertical,
             '_unselect_props': self._unselect_props,
             'xa': self.xa, 'ya': self.ya}
            )

    @staticmethod
    def maintain_y(marks):
        """Connect marks and maintain a constant vertical distance between them

        Parameters
        ----------
        marks: list of CrossMarks
            A list of marks. If one of the marks is moved vertically, the
            others are, too"""
        for mark in marks:
            mark._maintain_y([m for m in marks if m is not mark])

    def _maintain_y(self, marks):
        """Connect to marks and maintain a constant vertical distance

        Parameters
        ----------
        marks: list of CrossMarks
            A list of other marks. If this mark is moved vertically, the others
            are, too"""
        y = self.y
        self._constant_dist_y.extend(m.y - y for m in marks)
        self._constant_dist_y_marks.extend(marks)

    @staticmethod
    def maintain_x(marks):
        """Connect marks and maintain a constant horizontal distance

        Parameters
        ----------
        marks: list of CrossMarks
            A list of marks. If one of the marks is moved horizontally, the
            others are, too"""
        for mark in marks:
            mark._maintain_x([m for m in marks if m is not mark])

    def _maintain_x(self, marks):
        """Connect to marks and maintain a constant horizontal distance

        Parameters
        ----------
        marks: list of CrossMarks
            A list of other marks. If this mark is moved horizontally, the
            others are, too"""
        x = self.x
        self._constant_dist_x.extend(m.x - x for m in marks)
        self._constant_dist_x_marks.extend(marks)

    def connect_to_marks(self, marks, visible=False, append=True):
        """Append other marks that should be considered for aligning the lines

        Parameters
        ----------
        marks: list of CrossMarks
            A list of other marks
        visible: bool
            If True, the marks are connected through visible lines
        append: bool
            If True, the marks are appended. This is important if the mark
            will be moved by the `set_pos` method

        Notes
        -----
        This method can only be used to connect other marks with this mark.
        If you want to connect multiple marks within each other, use the
        :meth:`connect_marks` static method
        """
        if append:
            self.other_marks.extend(marks)
            self._connection_visible.extend([visible] * len(marks))
        if visible:
            ya = self.ya
            xa = self.xa
            ax = self.ax
            for m in marks:
                for i1, j1 in product(range(len(xa)), range(len(ya))):
                    self.set_current_point(i1, j1)
                    pos = self.pos
                    for i2, j2 in product(range(len(m.xa)), range(len(m.ya))):
                        m.set_current_point(i2, j2)
                        line = ax.plot([pos[0], m.pos[0]], [pos[1], m.pos[1]],
                                       label='cross_mark_connection',
                                       **self._unselect_props)[0]
                        if self.auto_hide:
                            line.set_lw(0)
                        self.line_connections.append(line)
                        m.other_connections.append(line)

    @staticmethod
    def connect_marks(marks, visible=False):
        """Connect multiple marks to each other

        Parameters
        ----------
        marks: list of CrossMarks
            A list of marks
        visible: bool
            If True, the marks are connected through visible lines

        Notes
        -----
        Different from the :meth:`connect_to_marks` method, this static
        function connects each of the marks to the others.
        """
        for mark in marks:
            mark.connect_to_marks([m for m in marks if m is not mark], visible)

    def connect(self):
        """Connect the marks matplotlib events"""
        fig = self.fig
        self.cidpress = fig.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = fig.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = fig.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)

    def is_selected_by(self, event, buttons=[1]):
        """Test if the given `event` selects the mark

        Parameters
        ----------
        event: matplotlib.backend_bases.MouseEvent
            The matplotlib event
        button: list of int
            Possible buttons to select this mark

        Returns
        -------
        bool
            True, if it is selected"""
        return not (
            self.lock is not None or
            event.inaxes != self.ax or event.button not in buttons or
            self.fig.canvas.manager.toolbar.mode != '' or
            not self.contains(event))

    def set_current_point(self, x, y, nearest=False):
        """Set the current point that is selected

        Parameters
        ----------
        x: int
            The index of the x-value in the :attr:`xa` attribute
        y: int
            The index of the y-value in the :attr:`ya` attribute
        nearest: bool
            If not None, `x` and `y` are interpreted as x- and y-values and
            we select the closest one
        """
        if nearest:
            x = np.abs(self.xa - x).argmin()
            y = np.abs(self.ya - y).argmin()
        self._i_vline = x
        self._i_hline = y

    def on_press(self, event, force=False, connected=True):
        """Select the mark

        Parameters
        ----------
        event: matplotlib.backend_bases.MouseEvent
            The mouseevent that selects the mark
        force: bool
            If True, the mark is selected although it does not contain
            the `event`
        connected: bool
            If True, connected marks that should maintain a constant x- and
            y-distance are selected, too"""
        if not force and not self.is_selected_by(event):
            return
        self.set_current_point(event.xdata, event.ydata, True)
        # use only the upper most CrossMarks
        if self._lock_mark and connected:
            CrossMarks.lock = self
        if self._animated:
            self.hline.set_animated(True)
            self.vline.set_animated(True)
            self.background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        self.hline.update(self._select_props)
        self.vline.update(self._select_props)

        # toggle line connections
        artist_props = self._select_props.copy()
        for a in chain(self.line_connections, self.other_connections):
            a.update(artist_props)

        # toggle connected artists
        artist_props['visible'] = (
            self.show_connected_artists and artist_props.get('visible', True))
        for a in self.connected_artists:
            a.update(artist_props)
        self.press = self.pos[0], self.pos[1], event.xdata, event.ydata
        # select the connected marks that should maintain the distance
        if connected:
            for m in set(chain(self._constant_dist_y_marks,
                               self._constant_dist_x_marks)):
                m._i_vline = self._i_vline
                m._i_hline = self._i_hline
                event.xdata, event.ydata = m.pos
                m.on_press(event, True, False)
            event.xdata, event.ydata = self.press[2:]

        for l in chain(self.other_connections, self.line_connections,
                       self.connected_artists):
            self.ax.draw_artist(l)

        self.ax.draw_artist(self.hline)
        self.ax.draw_artist(self.vline)
        if self._animated:
            self.fig.canvas.blit(self.ax.bbox)

    def contains(self, event):
        """Test if the mark is selected by the given `event`

        Parameters
        ----------
        event: ButtonPressEvent
            The ButtonPressEvent that has been triggered"""
        contains = None
        if 'h' in self.selectable:
            contains = any(l.contains(event)[0] for l in self.hlines)
        if not contains and 'v' in self.selectable:
            contains = any(l.contains(event)[0] for l in self.vlines)
        return contains

    def on_motion(self, event, force=False, move_connected=True,
                  restore=True):
        """Move the lines of this mark

        Parameters
        ----------
        event: matplotlib.backend_bases.MouseEvent
            The mouseevent that moves the mark
        force: bool
            If True, the mark is moved although it does not contain
            the `event`
        move_connected: bool
            If True, connected marks that should maintain a constant x- and
            y-distance are moved, too
        restore: bool
            If True, the axes background is restored"""
        if self.press is None or (not force and self._lock_mark and
                                  self.lock is not self):
            return
        if not force and event.inaxes != self.ax:
            return
        x0, y0, xpress, ypress = self.press
        dx = event.xdata - xpress
        dy = event.ydata - ypress
        canvas = self.fig.canvas

        if dy and 'h' in self.draggable:
            y1 = y0 + dy
            one_percent = np.abs(0.01 * np.diff(self.ax.get_ylim())[0])
            for mark in filter(lambda m: m.ax is self.ax, self.other_marks):
                if np.abs(mark.pos[1] - y1) < one_percent:
                    y1 = mark.pos[1]
                    break
            if self.idx_v is not None:
                y1 = self.idx_v[self.idx_v.get_loc(y1, method='nearest')]
            self.hline.set_ydata([y1] * len(self.hline.get_ydata()))
            self.y = y1
            # first we move the horizontal line that is associated with this
            # mark
            ydata = self.vline.get_ydata()[:]
            ydata[self._i_hline + 1] = y1
            for l in self.vlines:
                l.set_ydata(ydata)
            # now we move all connections that are connected to this horizontal
            # layer
            for l in chain.from_iterable(
                    self._all_line_connections[self._i_hline]):
                l.set_ydata([y1, l.get_ydata()[1]])
            for l in chain.from_iterable(
                    self._all_other_connections[self._i_hline]):
                l.set_ydata([l.get_ydata()[0], y1])
        if dx and 'v' in self.draggable:
            x1 = x0 + dx
            one_percent = np.abs(0.01 * np.diff(self.ax.get_xlim())[0])
            for mark in filter(lambda m: m.ax is self.ax, self.other_marks):
                if np.abs(mark.pos[0] - x1) < one_percent:
                    x1 = mark.pos[0]
                    break
            if self.idx_h is not None:
                x1 = self.idx_h[self.idx_h.get_loc(x1, method='nearest')]
            self.vline.set_xdata([x1] * len(self.vline.get_xdata()))
            self.x = x1
            # first we move the vertical line that is associated with this mark
            xdata = self.hline.get_xdata()[:]
            xdata[self._i_vline + 1] = x1
            for l in self.hlines:
                l.set_xdata(xdata)
            # now we move all connections that are connected to this vertical
            # layer
            for l in chain.from_iterable(
                    l[self._i_vline] for l in self._all_line_connections):
                l.set_xdata([x1, l.get_xdata()[1]])
            for l in chain.from_iterable(
                    l[self._i_vline] for l in self._all_other_connections):
                l.set_xdata([l.get_xdata()[0], x1])
        if restore and self._animated:
            canvas.restore_region(self.background)
        for l in chain(self.other_connections, self.line_connections,
                       self.connected_artists):
            self.ax.draw_artist(l)
        if restore and self._animated:
            self.ax.draw_artist(self.hline)
            self.ax.draw_artist(self.vline)
            canvas.blit(self.ax.bbox)
        else:
            self.ax.figure.canvas.draw_idle()

        # move the marks that should maintain a constant distance
        orig_xy = (event.xdata, event.ydata)
        if move_connected and dy and 'h' in self.draggable:
            for dist, m in zip(self._constant_dist_y,
                               self._constant_dist_y_marks):
                event.xdata = m.press[-2]
                event.ydata = y1 + dist
                m.on_motion(event, True, False, m.ax is not self.ax)
        if move_connected and dx and 'v' in self.draggable:
            for dist, m in zip(self._constant_dist_x,
                               self._constant_dist_x_marks):
                event.xdata = x1 + dist
                event.ydata = m.press[-1]
                m.on_motion(event, True, False, m.ax is not self.ax)
        event.xdata, event.ydata = orig_xy

    def set_connected_artists_visible(self, visible):
        """Set the visibility of the connected artists

        Parameters
        ----------
        visible: bool
            True, show the connected artists, else don't"""
        self.show_connected_artists = visible
        for a in self.connected_artists:
            a.set_visible(visible)
        for d in self._connected_artists_props:
            d['visible'] = visible

    def on_release(self, event, force=False, connected=True, draw=True,
                   *args, **kwargs):
        """Release the mark and unselect it

        Parameters
        ----------
        event: matplotlib.backend_bases.MouseEvent
            The mouseevent that releases the mark
        force: bool
            If True, the mark is released although it does not contain
            the `event`
        connected: bool
            If True, connected marks that should maintain a constant x- and
            y-distance are released, too
        draw: bool
            If True, the figure is drawn
        ``*args, **kwargs``
            Any other parameter that is passed to the connected lines"""
        if (not force and self._lock_mark and self.lock is not self or
                self.press is None):
            return
        self.hline.update(self._unselect_props)
        self.vline.update(self._unselect_props)
        for d, a in zip_longest(self._connected_artists_props,
                                self.connected_artists,
                                fillvalue=self._unselect_props):
            a.update(d)
        for l in chain(self.line_connections, self.other_connections):
            l.update(self._unselect_props)
        if self.auto_hide:
            self.hline.set_lw(0)
            self.vline.set_lw(0)
            for l in chain(self.line_connections, self.other_connections):
                l.set_lw(0)

        self.xa[self._i_vline] = self.pos[0]
        self.ya[self._i_hline] = self.pos[1]

        pos0 = self.press[:2]

        self.press = None
        if self._animated:
            self.hline.set_animated(False)
            self.vline.set_animated(False)
            self.background = None
        if connected:
            for m in set(chain(self._constant_dist_y_marks,
                               self._constant_dist_x_marks)):
                m.on_release(event, True, False, m.fig is not self.fig,
                             *args, **kwargs)
        if self._lock_mark and self.lock is self:
            CrossMarks.lock = None
        if draw:
            self.fig.canvas.draw_idle()
        self.moved.emit(pos0, self)

    def disconnect(self):
        """Disconnect all the stored connection ids"""
        fig = self.fig
        fig.canvas.mpl_disconnect(self.cidpress)
        fig.canvas.mpl_disconnect(self.cidrelease)
        fig.canvas.mpl_disconnect(self.cidmotion)

    def remove(self, artists=True):
        """Remove all lines and disconnect the mark

        Parameters
        ----------
        artists: bool
            If True, the :attr:`connected_artists` list is cleared and the
            corresponding artists are removed as well"""
        for l in chain(self.hlines, self.vlines,
                       self.connected_artists if artists else [],
                       chain.from_iterable(chain.from_iterable(
                           self._all_other_connections)),
                       chain.from_iterable(chain.from_iterable(
                           self._all_line_connections))):
            try:
                l.remove()
            except ValueError:
                pass
        self.hlines.clear()
        self.vlines.clear()
        if artists:
            self.connected_artists.clear()

        # Remove the line connections
        visible_connections = [
            m for m, v in zip(self.other_marks, self._connection_visible) if v]
        for m in visible_connections:
            for l in chain.from_iterable(chain.from_iterable(
                    self._all_line_connections)):
                for i, j in product(range(len(m.ya)), range(len(m.xa))):
                    if l in m._all_other_connections[i][j]:
                        m._all_other_connections[i][j].remove(l)
                        break
            for l in chain.from_iterable(chain.from_iterable(
                    self._all_other_connections)):
                for i, j in product(range(len(m.ya)), range(len(m.xa))):
                    if l in m._all_line_connections[i][j]:
                        m._all_line_connections[i][j].remove(l)
                        break

        self._all_line_connections = [[[] for _ in range(len(self.xa))]
                                      for _ in range(len(self.ya))]
        self._all_other_connections = [[[] for _ in range(len(self.xa))]
                                       for _ in range(len(self.ya))]

        self.disconnect()

    def set_pos(self, pos):
        """Move the point(s) to another position

        Parameters
        ----------
        pos: tuple of 2 arrays
            The positions of the crosses. The first item marks the
            x-coordinates of the points, the second the y-coordinates"""
        self.remove(artists=False)
        self.xa[:] = pos[0]
        self.ya[:] = pos[1]
        self.draw_lines(**self._line_kwargs)
        self.connect()
        visible_connections = [
            m for m, v in zip(self.other_marks, self._connection_visible) if v]
        if visible_connections:
            self.connect_to_marks(visible_connections, True, append=False)


class DraggableHLine(CrossMarks):
    """A draggable horizontal line"""

    @property
    def x(self):
        raise NotImplementedError(
            'There is no single x-value for a horizontal line!')

    hide_vertical = True

    docstrings.delete_params('CrossMarks.parameters', 'pos', 'ax',
                             'selectable', 'draggable')

    @docstrings.get_sectionsf('DraggableHLine')
    @docstrings.dedent
    def __init__(self, y, ax=None, *args, **kwargs):
        """
        Parameters
        ----------
        y: float
            The y-position for the horizontal line
        ax: matplotlib.axes.Axes
            The matplotlib axes
        %(CrossMarks.parameters.no_pos|ax|selectable|draggable)s
        """
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.gca()
        xlim = kwargs.get('xlim', ax.get_xlim())
        x = np.mean(xlim)
        super(DraggableHLine, self).__init__(
            (x, y), ax, ['h'], ['h'], *args, **kwargs)

    def __reduce__(self):
        ret = list(super(DraggableHLine, self).__reduce__())
        ret[1] = (self.ya, None) + ret[1][4:]
        return tuple(ret)

    def _maintain_x(self, marks):
        """Not implemented for DraggableHLine"""
        pass

    def set_visible(self, b):
        for l in self.hlines:
            l.set_visible(b)
        show_connected = self.show_connected_artists and b
        for a in self.connected_artists:
            a.set_visible(show_connected)


class DraggableVLine(CrossMarks):
    """A draggable vertical line"""

    @property
    def y(self):
        raise NotImplementedError(
            'There is no single y-value for a vertical line!')

    hide_horizontal = True

    @docstrings.get_sectionsf('DraggableVLine')
    @docstrings.dedent
    def __init__(self, x, ax=None, *args, **kwargs):
        """
        Parameters
        ----------
        x: float
            The x-position for the vertical line
        ax: matplotlib.axes.Axes
            The matplotlib axes
        %(CrossMarks.parameters.no_pos|ax|selectable|draggable)s
        """
        if ax is None:
            import matplotlib.pyplot as plt
            ax = plt.gca()
        ylim = kwargs.get('ylim', ax.get_ylim())
        y = np.mean(ylim)
        super(DraggableVLine, self).__init__(
            (x, y), ax, ['v'], ['v'], *args, **kwargs)

    def __reduce__(self):
        ret = list(super(DraggableVLine, self).__reduce__())
        ret[1] = (self.xa, None) + ret[1][4:]
        return tuple(ret)

    def _maintain_y(self, marks):
        """Not implemented for DraggableVLine"""
        pass

    def set_visible(self, b):
        for l in self.vlines:
            l.set_visible(b)
        show_connected = self.show_connected_artists and b
        for a in self.connected_artists:
            a.set_visible(show_connected)


docstrings.params['CrossMarksText.parameters.new'] = """
dtype: object
    The data type for the data conversion
message: str
    The message to display in the dialog
label: str
    The label to how this value should be named
value: float
    The initial value to use""".strip()


class CrossMarkText(CrossMarks):
    """A CrossMarks that opens a QInputDialog after changing the position
    """

    #: The value of this cross mark
    value = None

    @docstrings.get_sectionsf('CrossMarkText')
    @docstrings.dedent
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        %(CrossMarks.parameters)s
        %(CrossMarksText.parameters.new)s"""
        self.dtype = kwargs.pop('dtype', str)
        self.message = kwargs.pop('message',
                                  'Enter the value for this position')
        self.label = kwargs.pop('label', self.message)
        self.value = kwargs.pop('value', None)
        super(CrossMarkText, self).__init__(*args, **kwargs)

    def ask_for_value(self, val=None, label=None):
        """Ask for a value for the cross mark

        This method opens a QInputDialog to ask for a new :attr:`value`

        Parameters
        ----------
        val: float
            The initial value
        label: str
            the name of what to ask for"""
        from psyplot_gui.compat.qtcompat import QInputDialog, QLineEdit
        from psyplot_gui.main import mainwindow
        initial = str(val) if val is not None else ''
        value, ok = QInputDialog().getText(
            mainwindow, self.message, label or self.label, QLineEdit.Normal,
            initial)
        if ok:
            self.value = self.dtype(value)

    def on_release(self, event, *args, **kwargs):
        """reimplemented to ask for the value if the shift key is not pressed
        """
        if (kwargs.get('ask', True) and self.press is not None and
                event.key != 'shift'):
            self.ask_for_value()
        kwargs['ask'] = False
        super(CrossMarkText, self).on_release(event, *args, **kwargs)

    on_release.__doc__ = CrossMarks.on_release.__doc__

    def __reduce__(self):
        ret = super(CrossMarkText, self).__reduce__()
        ret[2]['dtype'] = self.dtype
        ret[2]['message'] = self.message
        return ret


class DraggableHLineText(DraggableHLine):
    """A CrossMarks that opens a QInputDialog after changing the position
    """

    @docstrings.dedent
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        %(DraggableHLine.parameters)s
        %(CrossMarksText.parameters.new)s"""
        self.dtype = kwargs.pop('dtype', str)
        self.message = kwargs.pop('message',
                                  'Enter the value for this position')
        self.label = kwargs.pop('label', self.message)
        self.value = kwargs.pop('value', None)
        super(DraggableHLineText, self).__init__(*args, **kwargs)

    def on_release(self, event, *args, **kwargs):
        # ask for the value if the shift key is not pressed
        if (kwargs.get('ask', True) and self.press is not None and
                event.key != 'shift'):
            self.ask_for_value()
        kwargs['ask'] = False
        super(DraggableHLineText, self).on_release(event, *args, **kwargs)

    on_release.__doc__ = CrossMarks.on_release.__doc__

    def ask_for_value(self, val=None, label=None):
        from psyplot_gui.compat.qtcompat import QInputDialog, QLineEdit
        from psyplot_gui.main import mainwindow
        initial = str(val) if val is not None else ''
        value, ok = QInputDialog().getText(
            mainwindow, self.message, label or self.label, QLineEdit.Normal,
            initial)
        if ok:
            self.value = self.dtype(value)

    ask_for_value.__doc__ = CrossMarkText.ask_for_value.__doc__

    def __reduce__(self):
        ret = super(DraggableHLineText, self).__reduce__()
        ret[2]['dtype'] = self.dtype
        ret[2]['message'] = self.message
        ret[2]['label'] = self.label
        ret[2]['value'] = self.value
        return ret


class DraggableVLineText(DraggableVLine):
    """A CrossMarks that opens a QInputDialog after changing the position
    """

    @docstrings.dedent
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        %(DraggableVLine.parameters)s
        %(CrossMarksText.parameters.new)s"""
        self.dtype = kwargs.pop('dtype', str)
        self.message = kwargs.pop('message',
                                  'Enter the value for this position')
        self.label = kwargs.pop('label', self.message)
        self.value = kwargs.pop('value', None)
        super(DraggableVLineText, self).__init__(*args, **kwargs)

    def on_release(self, event, *args, **kwargs):
        # ask for the value if the shift key is not pressed
        if (kwargs.get('ask', True) and self.press is not None and
                event.key != 'shift'):
            self.ask_for_value()
        kwargs['ask'] = False
        super(DraggableVLineText, self).on_release(event, *args, **kwargs)

    on_release.__doc__ = CrossMarks.on_release.__doc__

    def ask_for_value(self, val=None, label=None):
        from psyplot_gui.compat.qtcompat import QInputDialog, QLineEdit
        from psyplot_gui.main import mainwindow
        initial = str(val) if val is not None else ''
        value, ok = QInputDialog().getText(
            mainwindow, self.message, label or self.label, QLineEdit.Normal,
            initial)
        if ok:
            self.value = self.dtype(value)

    ask_for_value.__doc__ = CrossMarkText.ask_for_value.__doc__

    def __reduce__(self):
        ret = super(DraggableVLineText, self).__reduce__()
        ret[2]['dtype'] = self.dtype
        ret[2]['message'] = self.message
        ret[2]['label'] = self.label
        ret[2]['value'] = self.value
        return ret
