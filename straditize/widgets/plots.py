# -*- coding: utf-8 -*-
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
    """A widget to control the plots"""

    @property
    def widgets2disable(self):
        return list(filter(None, chain.from_iterable(
            (self.cellWidget(row, 0), self.cellWidget(row, 1))
            for row in range(self.rowCount()))))

    col_lines = []

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

    def get_straditizer_image(self):
        try:
            ret = self.straditizer.plot_im
        except AttributeError:
            ret = None
        return [ret] if ret else []

    def get_data_reader_background(self):
        try:
            ret = self.straditizer.data_reader.background
        except AttributeError:
            return []
        else:
            if self.straditizer.data_reader.magni_background is not None:
                return [ret, self.straditizer.data_reader.magni_background]
            else:
                return [ret]

    def get_data_reader_image(self):
        try:
            ret = self.straditizer.data_reader.plot_im
        except AttributeError:
            return []
        else:
            if self.straditizer.data_reader.magni_plot_im is not None:
                return [ret, self.straditizer.data_reader.magni_plot_im]
            else:
                return [ret]

    def plot_data_reader_color_image(self):
        self.straditizer.data_reader.plot_color_image()

    def get_data_reader_color_image(self):
        try:
            ret = self.straditizer.data_reader.color_plot_im
        except AttributeError:
            return []
        else:
            if self.straditizer.data_reader.magni_color_plot_im is not None:
                return [ret, self.straditizer.data_reader.magni_color_plot_im]
            else:
                return [ret]

    def remove_data_reader_color_image(self):
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

    def can_plot_data_reader_color_image(self):
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None)

    def get_data_box(self):
        try:
            ret = [self.straditizer.data_box]
        except AttributeError:
            ret = [None]
        try:
            ret.append(self.straditizer.magni_data_box)
        except AttributeError:
            pass
        return ret if ret else []

    def plot_data_box(self):
        self.straditizer.draw_data_box()

    # -------- plot full df ---------

    def plot_full_df(self):
        """Plot the :attr:`~straditize.binary.DataReader.full_df` of the reader
        """
        stradi = self.straditizer
        stradi.data_reader.plot_full_df()
        if stradi.magni is not None:
            lines = stradi.data_reader.lines[:]
            stradi.data_reader.plot_full_df(ax=stradi.magni.ax)
            stradi.data_reader.lines += lines

    def remove_full_df_plot(self):
        stradi = self.straditizer
        for l in stradi.data_reader.lines[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.lines.clear()

    def get_full_df_lines(self):
        try:
            return self.straditizer.data_reader.lines
        except AttributeError:
            return []

    def can_plot_full_df(self):
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader.full_df is not None)

    # --------- plot samples ------------

    def plot_samples(self):
        """Plot the :attr:`~straditize.binary.DataReader.full_df` of the reader
        """
        stradi = self.straditizer
        stradi.data_reader.plot_samples()
        if stradi.magni is not None:
            lines = stradi.data_reader.sample_lines[:]
            stradi.data_reader.plot_samples(ax=stradi.magni.ax)
            stradi.data_reader.sample_lines += lines

    def remove_samples_plot(self):
        stradi = self.straditizer
        for l in stradi.data_reader.sample_lines[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.sample_lines.clear()

    def get_samples_lines(self):
        try:
            return self.straditizer.data_reader.sample_lines
        except AttributeError:
            return []

    def can_plot_samples(self):
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader.full_df is not None and
                self.straditizer.data_reader._sample_locs is not None)

    # --------- plot horizontal sample lines ------------

    def plot_sample_hlines(self):
        """Plot the :attr:`~straditize.binary.DataReader.full_df` of the reader
        """
        stradi = self.straditizer
        stradi.data_reader.plot_sample_hlines()
        if stradi.magni is not None:
            lines = stradi.data_reader.sample_hlines[:]
            stradi.data_reader.plot_sample_hlines(ax=stradi.magni.ax)
            stradi.data_reader.sample_hlines += lines

    def remove_sample_hlines_plot(self):
        stradi = self.straditizer
        for l in stradi.data_reader.sample_hlines[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.sample_hlines.clear()

    def get_sample_hlines(self):
        try:
            return self.straditizer.data_reader.sample_hlines
        except AttributeError:
            return []

    def can_plot_sample_hlines(self):
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader.full_df is not None and
                self.straditizer.data_reader._sample_locs is not None)

    # --------- plot potential samples ------------

    def plot_potential_samples(self):
        stradi = self.straditizer
        stradi.data_reader.plot_potential_samples()
        if stradi.magni is not None:
            lines = stradi.data_reader.sample_ranges[:]
            stradi.data_reader.plot_potential_samples(ax=stradi.magni.ax)
            stradi.data_reader.sample_ranges += lines

    def remove_potential_samples_plot(self):
        stradi = self.straditizer
        for l in stradi.data_reader.sample_ranges[:]:
            try:
                l.remove()
            except ValueError:
                pass
        stradi.data_reader.sample_ranges.clear()

    def get_potential_samples_lines(self):
        try:
            return self.straditizer.data_reader.sample_ranges
        except AttributeError:
            return []

    def can_plot_potential_samples(self):
        return self.can_plot_full_df()

    def can_plot_data_box(self):
        return (self.straditizer is not None and
                self.straditizer.data_xlim is not None and
                self.straditizer.data_ylim is not None)

    def can_plot_column_starts(self):
        return (self.straditizer is not None and
                self.straditizer.data_reader is not None and
                self.straditizer.data_reader._column_starts is not None)

    def plot_column_starts(self):
        reader = self.straditizer.data_reader
        cols = reader._column_starts
        if reader.extent is not None:
            cols = cols + reader.extent[0]
        ymin, ymax = self.straditizer.data_ylim
        self.col_lines = [reader.ax.vlines(cols, ymax, ymin,
                                           color='r')]
        if reader.magni is not None:
            self.col_lines.append(reader.magni.ax.vlines(cols, ymax, ymin,
                                                         color='r'))

    def remove_column_starts(self):
        for l in self.col_lines:
            try:
                l.remove()
            except ValueError:
                pass
        self.col_lines.clear()

    def get_column_start_lines(self):
        return self.col_lines

    def remove_data_box(self):
        self.straditizer.remove_data_box()

    def always_true(self):
        return True

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
    """A widget for plotting the final results"""

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
    """A widget for controlling the plot"""

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
        self.straditizer.show_full_image()
        self.straditizer.draw_figure()

    def zoom_data(self):
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
