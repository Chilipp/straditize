# -*- coding: utf-8 -*-
"""Plot control widgets for straditize

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
from itertools import chain
from collections import OrderedDict
from straditize.widgets import StraditizerControlBase
from psyplot_gui.compat.qtcompat import (
    QTableWidget, QCheckBox, QToolButton, QIcon, Qt, with_qt5, QtCore, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem)
from psyplot_gui.common import get_icon

if with_qt5:
    from PyQt5.QtWidgets import QHeaderView
else:
    from PyQt4.QtGui import QHeaderView


class PlotControlTable(StraditizerControlBase, QTableWidget):
    """A widget to control the plots

    This control widget is a table to plot, remove and toggle the
    visiblity of visual diagnostics for the straditizer. It has two columns:
    the first to toggle the visibility of the plot, the second to plot and
    remove the matplotlib artists. The vertical header are the items in the
    corresponding :attr:`plot_funcs`, :attr:`can_be_plotted_funcs` and/or
    :attr:`hide_funcs`.

    Rows are added to this table using the :meth:`add_item` method which stores
    the plotting functions in the :attr:`plot_funcs` and the functions to
    hide the plot in the :attr:`hide_funcs`. Whether an item can be plotted or
    not depends on the results of the corresponding callable in the
    :attr:`can_be_plotted_funcs`."""

    @property
    def widgets2disable(self):
        return list(filter(None, chain.from_iterable(
            (self.cellWidget(row, 0), self.cellWidget(row, 1))
            for row in range(self.rowCount()))))

    col_lines = []

    #: A mapping from plot identifier to a callable that returns ``True`` if
    #: the corresponding function in the :attr:`plot_funcs` mapping can be
    #: called
    can_be_plotted_funcs = {}

    #: A mapping from plot identifier to a callable to plot the corresponding
    #: artists
    plot_funcs = {}

    #: A mapping from plot identifier to a callable to hide the corresponding
    #: artists
    hide_funcs = {}

    def __init__(self, straditizer_widgets, *args, **kwargs):
        super(PlotControlTable, self).__init__(*args, **kwargs)
        self.init_straditizercontrol(straditizer_widgets)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Visible', 'Plot/Remove'])
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setRowCount(0)
        self.get_artists_funcs = OrderedDict()
        self.hide_funcs = {}
        self.plot_funcs = {}
        self.can_be_plotted_funcs = {}

        self.add_item('Full image', self.get_straditizer_image)
        self.add_item('Reader color image',
                      self.get_data_reader_color_image,
                      self.plot_data_reader_color_image,
                      self.remove_data_reader_color_image,
                      self.can_plot_data_reader_color_image)
        self.add_item('Data background', self.get_data_reader_background)
        self.add_item('Binary image', self.get_data_reader_image)
        self.add_item('Diagram part', self.get_data_box, self.plot_data_box,
                      self.remove_data_box, self.can_plot_data_box)
        self.add_item('Column starts', self.get_column_start_lines,
                      self.plot_column_starts,
                      self.remove_column_starts, self.can_plot_column_starts)
        self.add_item('Full digitized data', self.get_full_df_lines,
                      self.plot_full_df, self.remove_full_df_plot,
                      self.can_plot_full_df)
        self.add_item('Potential samples',
                      self.get_potential_samples_lines,
                      self.plot_potential_samples,
                      self.remove_potential_samples_plot,
                      self.can_plot_potential_samples)
        self.add_item('Samples', self.get_sample_hlines,
                      self.plot_sample_hlines, self.remove_sample_hlines_plot,
                      self.can_plot_sample_hlines)
        self.add_item('Reconstruction', self.get_samples_lines,
                      self.plot_samples, self.remove_samples_plot,
                      self.can_plot_samples)
        self.resizeColumnsToContents()
        self.adjust_height()

    def draw_figs(self, artists):
        """Draw the figures of the given `artists`

        Parameters
        ----------
        artists: list of :class:`matplotlib.artist.Artist`
            The artists to draw the canvas from"""
        for canvas in {a.axes.figure.canvas for a in artists}:
            canvas.draw_idle()

    def add_item(self, what, get_artists, plot_func=None, remove_func=None,
                 can_be_plotted=None):
        """Add a plot object to the table

        Parameters
        ----------
        what: str
            The description of the plot object
        get_artists: function
            A function that takes no arguments and returns the artists
        plot_func: function, optional
            A function that takes no arguments and makes the plot.
        remove_func: function, optional
            A function that takes no arguments and removes the plot.
        can_be_plotted: function, optional
            A function that takes no argument and returns True if the plot can
            be made.
        """
        def hide_or_show(checked):
            checked = checked is True or checked == Qt.Checked
            artist = None
            for artist in get_artists():
                artist.set_visible(checked)
            if artist is not None:
                self.draw_figs(get_artists())

        def trigger_plot_btn():
            a = next(iter(get_artists()), None)
            if a is None:
                if can_be_plotted is None or can_be_plotted():
                    plot_func()
                    cb.setChecked(True)
                    btn.setIcon(QIcon(get_icon('invalid.png')))
                    btn.setToolTip('Remove ' + what)
                    self.draw_figs(get_artists())
                    cb.setEnabled(True)
            else:
                fig = a.axes.figure
                figs = {a.axes.figure for a in get_artists()}
                remove_func()
                btn.setIcon(QIcon(get_icon('valid.png')))
                btn.setToolTip('Show ' + what)
                for fig in figs:
                    fig.canvas.draw_idle()
                cb.setEnabled(False)

        self.get_artists_funcs[what] = get_artists

        a = next(iter(get_artists()), None)

        cb = QCheckBox()
        cb.label = what
        self.hide_funcs[what] = hide_or_show
        cb.setChecked(Qt.Checked if a is not None and a.get_visible()
                      else Qt.Unchecked)
        cb.stateChanged.connect(hide_or_show)

        row = self.rowCount()
        self.setRowCount(row + 1)
        self.setVerticalHeaderLabels(list(self.get_artists_funcs))

        self.setCellWidget(row, 0, cb)

        if plot_func is not None:
            btn = QToolButton()
            btn.setIcon(QIcon(get_icon(
                ('in' if a is None else '') + 'valid.png')))
            btn.clicked.connect(trigger_plot_btn)
            btn.setEnabled(can_be_plotted is None or can_be_plotted())
            btn.setToolTip(('Remove ' if a else 'Show ') + what)
            self.can_be_plotted_funcs[what] = can_be_plotted
            btn.label = what

            self.setCellWidget(row, 1, btn)

    # -------- straditizer data image --------------

    def get_straditizer_image(self):
        """Get the :attr:`straditize.straditizer.Straditizer.plot_im`"""
        try:
            ret = self.straditizer.plot_im
        except AttributeError:
            ret = None
        return [ret] if ret else []

    # -------- white data reader background ---------

    def get_data_reader_background(self):
        """Get the :attr:`straditize.binary.DataReader.background`"""
        try:
            ret = self.straditizer.data_reader.background
        except AttributeError:
            return []
        else:
            if self.straditizer.data_reader.magni_background is not None:
                return [ret, self.straditizer.data_reader.magni_background]
            else:
                return [ret]

    # -------- binary data image --------------

    def get_data_reader_image(self):
        """Get the :attr:`straditize.binary.DataReader.plot_im`"""
        try:
            ret = self.straditizer.data_reader.plot_im
        except AttributeError:
            return []
        else:
            if self.straditizer.data_reader.magni_plot_im is not None:
                return [ret, self.straditizer.data_reader.magni_plot_im]
            else:
                return [ret]

    # -------- reader color image --------------

    def plot_data_reader_color_image(self):
        """Plot the data reader color image

        See Also
        --------
        straditize.binary.DataReader.plot_color_image
        remove_data_reader_color_image
        can_plot_data_reader_color_image"""
        self.straditizer.data_reader.plot_color_image()

    def remove_data_reader_color_image(self):
        """Remove the :attr:`straditize.binary.DataReader.color_plot_im`

        See Also
        --------
        plot_data_reader_color_image"""
        for a in self.get_data_reader_color_image():
            try:
                a.remove()
            except ValueError:
                pass
        try:
            del self.straditizer.data_reader.magni_color_plot_im
        except AttributeError:
            pass
        try:
            del self.straditizer.data_reader.color_plot_im
        except AttributeError:
            pass

    def get_data_reader_color_image(self):
        """Get the :attr:`straditize.binary.DataReader.color_plot_im`

        See Also
        --------
        plot_data_reader_color_image"""
        try:
            ret = self.straditizer.data_reader.color_plot_im
        except AttributeError:
            return []
        else:
            if self.straditizer.data_reader.magni_color_plot_im is not None:
                return [ret, self.straditizer.data_reader.magni_color_plot_im]
            else:
                return [ret]

    def can_plot_data_reader_color_image(self):
        """Test if the reader color image can be plotted

        See Also
        --------
        plot_data_reader_color_image"""
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None)

    # -------- data box --------------

    def plot_data_box(self):
        """Plot the data box around the diagram part

        See Also
        --------
        straditize.straditizer.Straditizer.draw_data_box
        remove_data_box
        get_data_box
        can_plot_data_box"""
        self.straditizer.draw_data_box()

    def remove_data_box(self):
        """Remove the box around the diagram part

        See Also
        --------
        plot_data_box"""
        self.straditizer.remove_data_box()

    def get_data_box(self):
        """Get the plotted :attr:`straditize.straditizer.Straditizer.data_box`

        See Also
        --------
        plot_data_box
        """
        try:
            ret = [self.straditizer.data_box]
        except AttributeError:
            ret = [None]
        try:
            ret.append(self.straditizer.magni_data_box)
        except AttributeError:
            pass
        return ret if ret else []

    def can_plot_data_box(self):
        """Test whether the box around the diagram part can be plotted

        See Also
        --------
        plot_data_box"""
        return (self.straditizer is not None and
                self.straditizer.data_xlim is not None and
                self.straditizer.data_ylim is not None)

    # -------- plot full df ---------

    def plot_full_df(self):
        """Plot the :attr:`~straditize.binary.DataReader.full_df` of the reader

        See Also
        --------
        straditize.binary.DataReader.plot_full_df
        remove_full_df_plot
        get_full_df_lines
        can_plot_full_df
        """
        stradi = self.straditizer
        stradi.data_reader.plot_full_df()
        if stradi.magni is not None:
            lines = stradi.data_reader.lines[:]
            stradi.data_reader.plot_full_df(ax=stradi.magni.ax)
            stradi.data_reader.lines += lines

    def remove_full_df_plot(self):
        """Remove the plot of the full_df

        See Also
        --------
        plot_full_df"""
        stradi = self.straditizer
        for l in stradi.data_reader.lines[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.lines.clear()

    def get_full_df_lines(self):
        """Get the artists of the full_df plot

        See Also
        --------
        plot_full_df"""
        try:
            return self.straditizer.data_reader.lines
        except AttributeError:
            return []

    def can_plot_full_df(self):
        """Test whether the full_df can be plotted

        See Also
        --------
        plot_full_df"""
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader.full_df is not None)

    # --------- plot samples ------------

    def plot_samples(self):
        """Plot the samples of the reader

        See Also
        --------
        straditize.binary.DataReader.plot_samples
        remove_samples_plot
        get_samples_lines
        can_plot_samples
        """
        stradi = self.straditizer
        stradi.data_reader.plot_samples()
        if stradi.magni is not None:
            lines = stradi.data_reader.sample_lines[:]
            stradi.data_reader.plot_samples(ax=stradi.magni.ax)
            stradi.data_reader.sample_lines += lines

    def remove_samples_plot(self):
        """Remove the plotted samples

        See Also
        --------
        plot_samples"""
        stradi = self.straditizer
        for l in stradi.data_reader.sample_lines[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.sample_lines.clear()

    def get_samples_lines(self):
        """Get the artists of the plotted samples

        See Also
        --------
        plot_samples"""
        try:
            return self.straditizer.data_reader.sample_lines
        except AttributeError:
            return []

    def can_plot_samples(self):
        """Test whether the samples can be plotted

        See Also
        --------
        plot_samples"""
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader.full_df is not None and
                self.straditizer.data_reader._sample_locs is not None)

    # --------- plot horizontal sample lines ------------

    def plot_sample_hlines(self):
        """Plot the horizontal sample lines of the reader

        See Also
        --------
        straditize.binary.DataReader.plot_sample_hlines
        remove_sample_hlines_plot
        get_sample_hlines
        can_plot_sample_hlines
        """
        stradi = self.straditizer
        stradi.data_reader.plot_sample_hlines()
        if stradi.magni is not None:
            lines = stradi.data_reader.sample_hlines[:]
            stradi.data_reader.plot_sample_hlines(ax=stradi.magni.ax)
            stradi.data_reader.sample_hlines += lines

    def remove_sample_hlines_plot(self):
        """Remove the sample lines

        See Also
        --------
        plot_sample_hlines"""
        stradi = self.straditizer
        for l in stradi.data_reader.sample_hlines[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.sample_hlines.clear()

    def get_sample_hlines(self):
        """Get the plotted the sample lines

        See Also
        --------
        plot_sample_hlines"""
        try:
            return self.straditizer.data_reader.sample_hlines
        except AttributeError:
            return []

    def can_plot_sample_hlines(self):
        """Test whether the sample lines can be plotted

        See Also
        --------
        plot_sample_hlines"""
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader.full_df is not None and
                self.straditizer.data_reader._sample_locs is not None)

    # --------- plot potential samples ------------

    def plot_potential_samples(self):
        """Highlight the regions with potential samples in the plot

        See Also
        --------
        straditize.binary.DataReader.plot_potential_samples
        remove_potential_samples_plot
        get_potential_samples_lines
        can_plot_potential_samples"""
        stradi = self.straditizer
        stradi.data_reader.plot_potential_samples()
        if stradi.magni is not None:
            lines = stradi.data_reader.sample_ranges[:]
            stradi.data_reader.plot_potential_samples(ax=stradi.magni.ax)
            stradi.data_reader.sample_ranges += lines

    def remove_potential_samples_plot(self):
        """Remove the plot of potential samples

        See Also
        --------
        plot_potential_samples"""
        stradi = self.straditizer
        for l in stradi.data_reader.sample_ranges[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.sample_ranges.clear()

    def get_potential_samples_lines(self):
        """Get the artists of the plot of potential samples

        See Also
        --------
        plot_potential_samples"""
        try:
            return self.straditizer.data_reader.sample_ranges
        except AttributeError:
            return []

    def can_plot_potential_samples(self):
        """Test whether potential sample regions can be plotted

        See Also
        --------
        plot_potential_samples"""
        return self.can_plot_full_df()

    # -------- column starts ----------------

    def plot_column_starts(self):
        """Plot horizontal lines for the column starts

        See Also
        --------
        remove_column_starts
        get_column_start_lines
        can_plot_column_starts"""
        reader = self.straditizer.data_reader
        cols = reader._column_starts
        if reader.extent is not None:
            cols = cols + reader.extent[0]
        ymin, ymax = self.straditizer.data_ylim
        reader.__col_lines = [reader.ax.vlines(cols, ymax, ymin, color='r')]
        if reader.magni is not None:
            reader.__col_lines.append(reader.magni.ax.vlines(cols, ymax, ymin,
                                                             color='r'))

    def remove_column_starts(self):
        """Remove the plotted lines of the column starts

        See Also
        --------
        plot_column_starts"""
        for l in self.straditizer.data_reader.__col_lines:
            try:
                l.remove()
            except ValueError:
                pass
        self.straditizer.data_reader.__col_lines.clear()

    def get_column_start_lines(self):
        """Get the artists of the column starts

        See Also
        --------
        plot_column_starts"""
        try:
            return self.straditizer.data_reader.__col_lines
        except AttributeError:
            return []

    def can_plot_column_starts(self):
        """Test whether the column starts can be visualized

        See Also
        --------
        plot_column_starts"""
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader._column_starts is not None)

    def refresh(self):
        for row, (what, func) in enumerate(self.get_artists_funcs.items()):
            a = next(iter(func()), None)
            cb = self.cellWidget(row, 0)
            cb.setEnabled(a is not None)
            if a is not None:
                cb.setChecked(Qt.Checked if a.get_visible() else Qt.Unchecked)
            btn = self.cellWidget(row, 1)
            if btn is not None:
                can_be_plotted = self.can_be_plotted_funcs[what]
                if can_be_plotted is None or can_be_plotted():
                    if a is not None:
                        btn.setIcon(QIcon(get_icon('invalid.png')))
                        btn.setToolTip('Remove ' + what)
                    else:
                        btn.setIcon(QIcon(get_icon('valid.png')))
                        btn.setToolTip('Show ' + what)
                    btn.setEnabled(True)
                else:
                    btn.setEnabled(False)

    def should_be_enabled(self, w):
        get_artists = self.get_artists_funcs[w.label]
        row = list(self.get_artists_funcs).index(w.label)
        if w is self.cellWidget(row, 0):
            if next(iter(get_artists()), None) is not None:
                return True
        elif w is self.cellWidget(row, 1):
            can_plot_func = self.can_be_plotted_funcs[w.label]
            if can_plot_func is None or can_plot_func():
                return True
        return False

    def enable_or_disable_widgets(self, b):
        """b is ignored and is always set to True"""
        super(PlotControlTable, self).enable_or_disable_widgets(False)

    def adjust_height(self):
        header_height = self.horizontalHeader().height()
        h = self.rowHeight(0) * self.rowCount() + header_height
        self.setMaximumHeight(h)
        self.setMinimumHeight(h)

    def sizeHint(self):
        header = self.horizontalHeader().sizeHint().height()
        s = super(PlotControlTable, self).sizeHint()
        return QtCore.QSize(s.width(),
                            self.rowHeight(0) * self.rowCount() + header)


class ResultsPlot(StraditizerControlBase):
    """A widget for plotting the final results

    This widgets contains a QPushButton :attr:`btn_plot` to plot the results
    using the :meth:`straditize.binary.DataReader.plot_results` method"""

    #: The QPushButton to call the :meth:`plot_results` method
    btn_plot = None

    #: A QCheckBox whether x- and y-axis should be translated from pixel to
    #: data units
    cb_transformed = None

    #: A QCheckBox whether the samples or the full digitized data shall be
    #: plotted
    cb_final = None

    def __init__(self, straditizer_widgets):
        self.init_straditizercontrol(straditizer_widgets)

        self.btn_plot = QPushButton("Plot results")

        self.cb_final = QCheckBox("Samples")
        self.cb_final.setToolTip(
            "Create the diagram based on the samples only, not on the full "
            "digized data")
        self.cb_final.setChecked(True)
        self.cb_final.setEnabled(False)

        self.cb_transformed = QCheckBox("Translated")
        self.cb_transformed.setToolTip(
            "Use the x-axis and y-axis translation")
        self.cb_transformed.setChecked(True)
        self.cb_transformed.setEnabled(False)

        self.btn_plot.clicked.connect(self.plot_results)

    def setup_children(self, item):
        tree = self.straditizer_widgets.tree
        tree.setItemWidget(item, 0, self.btn_plot)

        child = QTreeWidgetItem(0)
        item.addChild(child)
        widget = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(self.cb_final)
        vbox.addWidget(self.cb_transformed)
        widget.setLayout(vbox)

        tree.setItemWidget(child, 0, widget)

    def refresh(self):
        try:
            self.straditizer.yaxis_px
            self.straditizer.data_reader.xaxis_px
        except (AttributeError, ValueError):
            self.cb_transformed.setEnabled(False)
        else:
            self.cb_transformed.setEnabled(True)
        try:
            assert self.straditizer.data_reader.sample_locs is not None
        except (AssertionError, AttributeError):
            self.cb_final.setEnabled(False)
        else:
            self.cb_final.setEnabled(True)
        try:
            self.btn_plot.setEnabled(
                self.straditizer.data_reader._full_df is not None)
        except AttributeError:
            self.btn_plot.setEnabled(False)

    def plot_results(self):
        """Plot the results

        What is plotted depends on the :attr:`cb_transformed` and the
        :attr:`cb_final`

        :attr:`cb_transformed` and :attr:`cb_final` are checked
            Plot the :attr:`straditize.straditizer.Straditizer.final_df`
        :attr:`cb_transformed` is checked but not :attr:`cb_final`
            Plot the :attr:`straditize.straditizer.Straditizer.full_df`
        :attr:`cb_transformed` is not checked but :attr:`cb_final`
            Plot the :attr:`straditize.binary.DataReader.sample_locs`
        :attr:`cb_transformed` and :attr:`cb_final` are both not checked
            Plot the :attr:`straditize.binary.DataReader.full_df`"""
        transformed = self.cb_transformed.isEnabled() and \
            self.cb_transformed.isChecked()
        if self.cb_final.isEnabled() and self.cb_final.isChecked():
            df = self.straditizer.final_df if transformed else \
                self.straditizer.data_reader.sample_locs
        else:
            df = self.straditizer.full_df if transformed else \
                self.straditizer.data_reader._full_df
        return self.straditizer.data_reader.plot_results(
            df, transformed=transformed)


class PlotControl(StraditizerControlBase, QWidget):
    """A widget for controlling the plot

    This widgets holds a :class:`PlotControlTable` to display visual
    diagnostics in the plot. Additionally it contains zoom buttons
    (:attr:`btn_view_global` and :attr:`btn_view_data`) and a widget to plot
    the results (:attr:`results_plot`)"""

    #: A :class:`PlotControlTable` to display visual diagnostics
    table = None

    #: A button to zoom out to the entire stratigraphic diagram
    #: (see :meth:`zoom_global`)
    btn_view_global = None

    #: A button to zoom to the data
    #: (see :meth:`zoom_data`)
    btn_view_data = None

    #: A :class:`ResultsPlot` to plot the digitized data in a new diagram
    results_plot = None

    def __init__(self, straditizer_widgets, item, *args, **kwargs):
        super(PlotControl, self).__init__(*args, **kwargs)
        self.btn_view_global = QPushButton('Zoom out')
        self.btn_view_data = QPushButton('Zoom to data')
        self.table = PlotControlTable(straditizer_widgets)

        self.results_plot = ResultsPlot(straditizer_widgets)

        self.init_straditizercontrol(straditizer_widgets, item)

        # ---------------------------------------------------------------------
        # ------------------------------ Layout -------------------------------
        # ---------------------------------------------------------------------

        hbox = QHBoxLayout()
        hbox.addWidget(self.btn_view_global)
        hbox.addWidget(self.btn_view_data)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.table)

        self.setLayout(vbox)

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------

        self.btn_view_global.clicked.connect(self.zoom_global)
        self.btn_view_data.clicked.connect(self.zoom_data)

    def setup_children(self, item):
        super().setup_children(item)
        child = QTreeWidgetItem(0)
        item.addChild(child)
        self.results_plot.setup_children(child)

    def zoom_global(self):
        """Zoom out to the full straditgraphic diagram

        See Also
        --------
        straditize.straditizer.Straditizer.show_full_image"""
        self.straditizer.show_full_image()
        self.straditizer.draw_figure()

    def zoom_data(self):
        """Zoom to the data part

        See Also
        --------
        straditize.straditizer.Straditizer.show_data_diagram"""
        self.straditizer.show_data_diagram()
        self.straditizer.draw_figure()

    def refresh(self):
        self.table.refresh()
        self.results_plot.refresh()
        if self.straditizer is None:
            self.btn_view_global.setEnabled(False)
            self.btn_view_data.setEnabled(False)
        else:
            self.btn_view_global.setEnabled(True)
            self.btn_view_data.setEnabled(
                self.straditizer.data_xlim is not None and
                self.straditizer.data_ylim is not None)
