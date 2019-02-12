# -*- coding: utf-8 -*-
"""Widget for handling column names

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
import os
from straditize.widgets import StraditizerControlBase
from straditize.widgets.pattern_selection import EmbededMplCanvas
from straditize.common import docstrings
from psyplot_gui.common import DockMixin
from psyplot.utils import _temp_bool_prop
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.widgets import RectangleSelector

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt


class DummyNavigationToolbar2(NavigationToolbar2):
    """Reimplemented NavigationToolbar2 just to add an _init_toolbar method"""

    def _init_toolbar(self):
        pass

    def set_cursor(self, cursor):
        from matplotlib.backends.backend_qt5 import cursord
        self.canvas.setCursor(cursord[cursor])


class ColumnNamesManager(StraditizerControlBase, DockMixin,
                         QtWidgets.QSplitter):
    """Manage the column names of the reader"""

    refreshing = _temp_bool_prop(
        'refreshing', doc="True if the widget is refreshing")

    #: The matplotlib image of the
    #: :attr:`straditize.colnames.ColNamesReader.rotated_image`
    im_rotated = None

    #: The rectangle to highlight a column (see :meth:`highlight_selected_col`)
    rect = None

    #: The canvas to display the :attr:`im_rotated`
    main_canvas = None

    #: The :class:`matplotlib.axes.Axes` to display the :attr:`im_rotated`
    main_ax = None

    #: The original width of the :attr:`main_canvas`
    fig_w = None

    #: The original height of the :attr:`main_canvas`
    fig_h = None

    #: The matplotlib image of the :attr:`colpic`
    colpic_im = None

    #: The canvas to display the :attr:`colpic_im`
    colpic_canvas = None

    #: The :class:`matplotlib.axes.Axes` to display the :attr:`colpic_im`
    colpic_ax = None

    #: The extents of the :attr:`colpic` in the :attr:`im_rotated`
    colpic_extents = None

    #: A QTableWidget to display the column names
    colnames_table = None

    #: The :class:`matplotlib.widgets.RectangleSelector` to select the
    #: :attr:`colpic`
    selector = None

    #: The :class:`PIL.Image.Image` of the column name (see also
    #: :attr:`straditize.colnames.ColNamesReader.colpics`)
    colpic = None

    #: A QPushButton to load the highres image
    btn_load_image = None

    #: A QPushButton to find column names in the visible part of the
    #: :attr:`im_rotated`
    btn_find = None

    #: A QPushButton to recognize text in the :attr:`colpic`
    btn_recognize = None

    #: A checkable QPushButton to initialize a :attr:`selector` to select the
    #: :attr:`colpic`
    btn_select_colpic = None

    #: The QPushButton in the :class:`straditize.widgets.StraditizerWidgets`
    #: to toggle the column names dialog
    btn_select_names = None

    #: A QCheckBox to find the column names (see :attr:`btn_find`) for all
    #: columns and not just the one selected in the :attr:`colnames_table`
    cb_find_all_cols = None

    #: A QCheckBox to ignore the part within the
    #: :attr:`straditize.colnames.ColNamesReader.data_ylim`
    cb_ignore_data_part = None

    #: A QLineEdit to set the :attr:`straditize.colnames.ColNamesReader.rotate`
    txt_rotate = None

    #: A QCheckBox to set the :attr:`straditize.colnames.ColNamesReader.mirror`
    cb_fliph = None

    #: A QCheckBox to set the :attr:`straditize.colnames.ColNamesReader.flip`
    cb_flipv = None

    NAVIGATION_LABEL = ("Use left-click of your mouse to move the image below "
                        "and right-click to zoom in and out.")

    SELECT_LABEL = "Left-click and hold on the image to select the column name"

    @property
    def current_col(self):
        """The currently selected column"""
        indexes = self.colnames_table.selectedIndexes()
        if len(indexes):
            return indexes[0].row()

    @property
    def colnames_reader(self):
        """The :attr:`straditize.straditizer.Straditizer.colnames_reader`
        of the current straditizer"""
        return self.straditizer.colnames_reader

    @docstrings.dedent
    def __init__(self, straditizer_widgets, item=None, *args, **kwargs):
        """
        Parameters
        ----------
        %(StraditizerControlBase.init_straditizercontrol.parameters)s
        """
        # Create the button for the straditizer_widgets tree
        self.btn_select_names = QtWidgets.QPushButton('Edit column names')
        self.btn_select_names.setCheckable(True)

        self.btn_select_colpic = QtWidgets.QPushButton('Select column name')
        self.btn_select_colpic.setCheckable(True)
        self.btn_select_colpic.setEnabled(False)
        self.btn_cancel_colpic_selection = QtWidgets.QPushButton('Cancel')
        self.btn_cancel_colpic_selection.setVisible(False)

        self.btn_load_image = QtWidgets.QPushButton('Load HR image')
        self.btn_load_image.setToolTip(
            'Select a version of this image with a higher resolution to '
            'improve the text recognition')
        self.btn_load_image.setCheckable(True)

        self.btn_recognize = QtWidgets.QPushButton('Recognize')
        self.btn_recognize.setToolTip('Use tesserocr to recognize the column '
                                      'name in the given image')

        self.btn_find = QtWidgets.QPushButton('Find column names')
        self.btn_find.setToolTip(
            'Find the columns names automatically in the image above using '
            'tesserocr')

        self.cb_find_all_cols = QtWidgets.QCheckBox(
            "all columns")
        self.cb_find_all_cols.setToolTip(
            "Find the column names in all columns or only in the selected one")
        self.cb_find_all_cols.setChecked(True)

        self.cb_ignore_data_part = QtWidgets.QCheckBox("ignore data part")
        self.cb_ignore_data_part.setToolTip("ignore everything from the top "
                                            "to the bottom of the data part")

        super().__init__(Qt.Horizontal)

        # centers of the image
        self.xc = self.yc = None

        self.txt_rotate = QtWidgets.QLineEdit()
        self.txt_rotate.setValidator(QtGui.QDoubleValidator(0., 90., 3))
        self.txt_rotate.setPlaceholderText('0˚..90˚')

        self.cb_fliph = QtWidgets.QCheckBox('Flip horizontally')
        self.cb_flipv = QtWidgets.QCheckBox('Flip vertically')

        self.info_label = QtWidgets.QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet('border: 1px solid black')

        self.main_canvas = EmbededMplCanvas()
        self.main_ax = self.main_canvas.figure.add_axes([0, 0, 1, 1])
        self.main_toolbar = DummyNavigationToolbar2(self.main_canvas)
        self.main_toolbar.pan()

        left_widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        layout.addRow(self.btn_load_image)
        layout.addRow(QtWidgets.QLabel('Rotate:'), self.txt_rotate)
        layout.addRow(self.cb_fliph)
        layout.addRow(self.cb_flipv)
        layout.addRow(self.cb_ignore_data_part)
        layout.addRow(self.info_label)
        layout.addRow(self.main_canvas)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.btn_select_colpic)
        hbox.addWidget(self.btn_cancel_colpic_selection)
        layout.addRow(hbox)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.btn_find)
        hbox.addWidget(self.cb_find_all_cols)
        layout.addRow(hbox)
        left_widget.setLayout(layout)

        self.colpic_canvas = EmbededMplCanvas()
        self.colpic_ax = self.colpic_canvas.figure.add_subplot(111)
        self.colpic_ax.axis("off")
        self.colpic_ax.margins(0)
        self.colpic_canvas.figure.subplots_adjust(bottom=0.3)

        self.colnames_table = QtWidgets.QTableWidget()
        self.colnames_table.setColumnCount(1)
        self.colnames_table.horizontalHeader().setHidden(True)
        self.colnames_table.setSelectionMode(
            QtWidgets.QTableView.SingleSelection)
        self.colnames_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch)

        self.vsplit = QtWidgets.QSplitter(Qt.Vertical)

        self.addWidget(left_widget)
        self.addWidget(self.vsplit)
        self.vsplit.addWidget(self.colnames_table)
        w = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.colpic_canvas)
        vbox.addWidget(self.btn_recognize)
        w.setLayout(vbox)
        self.vsplit.addWidget(w)

        self.init_straditizercontrol(straditizer_widgets, item)

        self.widgets2disable = [self.btn_select_names, self.btn_find,
                                self.btn_load_image, self.btn_select_colpic]

        self.btn_select_names.clicked.connect(self.toggle_dialog)
        self.btn_select_colpic.clicked.connect(self.toggle_colpic_selection)
        self.btn_cancel_colpic_selection.clicked.connect(
            self.cancel_colpic_selection)
        self.txt_rotate.textChanged.connect(self.rotate)
        self.cb_fliph.stateChanged.connect(self.mirror)
        self.cb_flipv.stateChanged.connect(self.flip)
        self.colnames_table.itemSelectionChanged.connect(
            self.highlight_selected_col)
        self.colnames_table.cellChanged.connect(self.colname_changed)
        self.main_canvas.mpl_connect('resize_event',
                                     self.adjust_lims_after_resize)
        self.btn_load_image.clicked.connect(self.load_image)
        self.btn_recognize.clicked.connect(self.read_colpic)
        self.btn_find.clicked.connect(self._find_colnames)
        self.cb_find_all_cols.stateChanged.connect(
            self.enable_or_disable_btn_find)
        self.cb_ignore_data_part.stateChanged.connect(
            self.change_ignore_data_part)

    def colname_changed(self, row, column):
        """Update the column name in the :attr:`colnames_reader`

        This method is called when a cell in the :attr:`colnames_table` has
        been changed and updates the corresponding name in the
        :attr:`colnames_reader`

        Parameters
        ----------
        row: int
            The row of the cell in the :attr:`colnames_table` that changed
        column: int
            The column of the cell in the :attr:`colnames_table` that changed
        """
        self.colnames_reader._column_names[row] = self.colnames_table.item(
            row, column).text()

    def read_colpic(self):
        """Recognize the text in the :attr:`colpic`

        See Also
        --------
        straditize.colnames.ColNamesReader.recognize_text"""
        text = self.colnames_reader.recognize_text(self.colpic)
        self.colnames_table.item(self.current_col, 0).setText(text)
        self.colnames_reader._column_names[self.current_col] = text
        return text

    def load_image(self):
        """Load a high resolution image"""
        if self.btn_load_image.isChecked():
            fname = QtWidgets.QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Straditizer project',
                self.straditizer_widgets.menu_actions._start_directory,
                'Projects and images '
                '(*.nc *.nc4 *.pkl *.jpeg *.jpg *.pdf *.png *.raw *.rgba *.tif'
                ' *.tiff);;'
                'NetCDF files (*.nc *.nc4);;'
                'Pickle files (*.pkl);;'
                'All images '
                '(*.jpeg *.jpg *.pdf *.png *.raw *.rgba *.tif *.tiff);;'
                'Joint Photographic Experts Group (*.jpeg *.jpg);;'
                'Portable Document Format (*.pdf);;'
                'Portable Network Graphics (*.png);;'
                'Raw RGBA bitmap (*.raw *.rbga);;'
                'Tagged Image File Format(*.tif *.tiff);;'
                'All files (*)'
                )
            fname = fname[0]
            if fname:
                from PIL import Image
                with Image.open(fname) as _image:
                    image = Image.fromarray(np.array(_image.convert('RGBA')),
                                            'RGBA')
                self.colnames_reader.highres_image = image

        else:
            self.colnames_reader.highres_image = None
        self.refresh()

    def cancel_colpic_selection(self):
        """Stop the colpic selection in the :attr:`im_rotated`"""
        self.colnames_reader._colpics = self._colpics_save
        if self.current_col is not None:
            self.colpic = self.colnames_reader.colpics[self.current_col]
        self.btn_select_colpic.setChecked(False)
        self.toggle_colpic_selection()

    def toggle_colpic_selection(self):
        """Enable or disable the colpic selection"""
        if (not self.btn_select_colpic.isChecked() and
                self.selector is not None):
            self.remove_selector()
            self.btn_select_colpic.setText('Select column name')
            if self.current_col is not None:
                self.colnames_reader._colpics[self.current_col] = self.colpic
            if self.colpic is None and self.colpic_im is not None:
                self.colpic_im.remove()
                del self.colpic_im
                self.colpic_canvas.draw()
            self.btn_cancel_colpic_selection.setVisible(False)
            self.main_canvas.toolbar.pan()
            self._colpics_save.clear()
            self.info_label.setText(self.NAVIGATION_LABEL)
        else:
            self.create_selector()
            self.btn_select_colpic.setText('Cancel')
            self.info_label.setText(self.SELECT_LABEL)
            self.main_canvas.toolbar.pan()
            self._colpics_save = list(self.colnames_reader.colpics)
            self.cb_find_all_cols.setChecked(False)
        self.main_canvas.draw()

    def remove_selector(self):
        """Remove and disconnect the :attr:`selector`"""
        self.selector.disconnect_events()
        for a in self.selector.artists:
            try:
                a.remove()
            except ValueError:
                pass
        self.main_canvas.draw()
        del self.selector
        self.main_canvas.mpl_disconnect(self.key_press_cid)

    def reset_control(self):
        """Reset the dialog"""
        if self.is_shown:
            self.hide_plugin()
            self.btn_select_names.setChecked(False)
        self.remove_images()
        self.cb_find_all_cols.setChecked(False)
        self.btn_select_colpic.setChecked(False)
        self.btn_cancel_colpic_selection.setVisible(False)
        if self.selector is not None:
            self.remove_selector()
        self.cb_fliph.setChecked(False)
        self.cb_flipv.setChecked(False)
        self.txt_rotate.blockSignals(True)
        self.txt_rotate.setText('0')
        self.txt_rotate.blockSignals(False)

    def create_selector(self):
        """Create the :attr:`selector` to enable :attr:`colpic` selection"""
        self.selector = RectangleSelector(
            self.main_ax, self.update_image, interactive=True)
        if self.colpic_extents is not None:
            self.selector.extents = self.colpic_extents
        self.key_press_cid = self.main_canvas.mpl_connect(
            'key_press_event', self.update_image)

    def plot_colpic(self):
        """Plot the :attr:`colpic` in the :attr:`colpic_ax`"""
        try:
            self.colpic_im.remove()
        except (AttributeError, ValueError):
            pass
        self.colpic_im = self.colpic_ax.imshow(self.colpic)
        self.colpic_canvas.draw()

    def update_image(self, *args, **kwargs):
        """Update the :attr:`colpic` with the extents of the :attr:`selector`

        ``*args`` and ``**kwargs`` are ignored
        """
        self.colpic_extents = np.round(self.selector.extents).astype(int)
        x, y = self.colpic_extents.reshape((2, 2))
        x0, x1 = sorted(x)
        y0, y1 = sorted(y)
        self.colpic = self.colnames_reader._colpics[self.current_col] = \
            self.colnames_reader.get_colpic(x0, y0, x1, y1)
        self.plot_colpic()
        self.btn_select_colpic.setText('Apply')
        self.btn_cancel_colpic_selection.setVisible(True)
        self.btn_recognize.setEnabled(
            self.should_be_enabled(self.btn_recognize))

    def highlight_selected_col(self):
        """Highlight the column selected in the :attr:`colnames_tables`

        See Also
        --------
        straditize.colnames.ColNamesReader.highlight_column"""
        draw = False
        if self.rect is not None:
            self.rect.remove()
            draw = True
            del self.rect
        col = self.current_col
        if col is not None:
            reader = self.straditizer.colnames_reader
            self.rect = reader.highlight_column(col, self.main_ax)
            reader.navigate_to_col(col, self.main_ax)
            self.btn_select_colpic.setEnabled(True)
            if self.colpic_im is not None:
                self.colpic_im.remove()
                del self.colpic_im
            self.colpic = colpic = self.colnames_reader.colpics[col]
            if colpic is not None:
                self.colpic_im = self.colpic_ax.imshow(colpic)
            self.colpic_canvas.draw()
            self.btn_recognize.setEnabled(
                self.should_be_enabled(self.btn_recognize))
            draw = True
        else:
            self.btn_select_colpic.setEnabled(False)
        if draw:
            self.main_canvas.draw()
        self.enable_or_disable_btn_find()

    def enable_or_disable_btn_find(self, *args, **kwargs):
        self.btn_find.setEnabled(self.should_be_enabled(self.btn_find))

    def setup_children(self, item):
        child = QtWidgets.QTreeWidgetItem(0)
        item.addChild(child)
        self.straditizer_widgets.tree.setItemWidget(
            child, 0, self.btn_select_names)

    def should_be_enabled(self, w):
        ret = self.straditizer is not None and getattr(
            self.straditizer.data_reader, '_column_starts', None) is not None
        if ret and w is self.btn_find:
            from straditize.colnames import tesserocr
            ret = tesserocr is not None and (
                self.cb_find_all_cols.isChecked() or
                self.current_col is not None)
        elif ret and w is self.btn_recognize:
            from straditize.colnames import tesserocr
            ret = tesserocr is not None and self.colpic is not None
        return ret

    def toggle_dialog(self):
        """Close the dialog when the :attr:`btn_select_names` button is clicked
        """
        from psyplot_gui.main import mainwindow
        if not self.refreshing:
            if not self.btn_select_names.isChecked() or (
                    self.dock is not None and self.is_shown):
                self.hide_plugin()
                if self.btn_select_colpic.isChecked():
                    self.btn_select_colpic.setChecked(False)
                    self.toggle_colpic_selection()
            elif self.btn_select_names.isEnabled():
                self.straditizer_widgets.tree.itemWidget(
                    self.straditizer_widgets.col_names_item, 1).show_docs()
                self.to_dock(mainwindow, 'Straditizer column names')
                self.info_label.setText(self.NAVIGATION_LABEL)
                self.show_plugin()
                self.dock.raise_()
                self.widget(0).layout().update()
            self.refresh()

    def _maybe_check_btn_select_names(self):
        if self.dock is None:
            return
        self.btn_select_names.blockSignals(True)
        self.btn_select_names.setChecked(
            self.dock.toggleViewAction().isChecked())
        self.btn_select_names.blockSignals(False)

    def refresh(self):
        with self.refreshing:
            super().refresh()
            self.btn_select_names.setChecked(
                self.btn_select_names.isEnabled() and self.dock is not None and
                self.is_shown)
        if self.btn_select_names.isEnabled():
            names = self.straditizer.colnames_reader.column_names
            self.colnames_table.setRowCount(len(names))
            for i, name in enumerate(names):
                self.colnames_table.setItem(
                    i, 0, QtWidgets.QTableWidgetItem(name))
            self.colnames_table.setVerticalHeaderLabels(
                list(map(str, range(len(names)))))
            self.replot_figure()
            reader = self.colnames_reader
            self.txt_rotate.setText(str(reader.rotate))
            self.cb_fliph.setChecked(reader.mirror)
            self.cb_flipv.setChecked(reader.flip)
            self.cb_ignore_data_part.setChecked(reader.ignore_data_part)

            image = reader._highres_image
            if image is reader.image:
                image = None
            if image is not None:
                self.btn_load_image.setText(
                    'HR image with size {}'.format(image.size))
                self.btn_load_image.setToolTip(
                    'Remove and ignore the high resolution image')
                checked = True
            else:
                self.btn_load_image.setText('Load HR image')
                self.btn_load_image.setToolTip(
                    'Select a version of this image with a higher resolution '
                    'to improve the text recognition')
                checked = False
            self.btn_load_image.blockSignals(True)
            self.btn_load_image.setChecked(checked)
            self.btn_load_image.blockSignals(False)
            self.btn_recognize.setEnabled(
                self.should_be_enabled(self.btn_recognize))
        else:
            self.colnames_table.setRowCount(0)
            self.remove_images()

    def remove_images(self):
        """Remove the :attr:`im_rotated` and the :attr:`colpic_im`"""
        try:
            self.im_rotated.remove()
        except (AttributeError, ValueError):
            pass
        try:
            self.colpic_im.remove()
        except (AttributeError, ValueError):
            pass
        self.im_rotated = self.colpic_im = self.xc = self.yc = None

    def set_xc_yc(self):
        """Set the x- and y-center before rotating or flipping"""
        xc = np.mean(self.main_ax.get_xlim())
        yc = np.mean(self.main_ax.get_ylim())
        self.xc, self.yc = self.colnames_reader.transform_point(xc, yc, True)

    def flip(self, checked):
        """TFlip the image"""
        self.set_xc_yc()
        self.colnames_reader.flip = checked == Qt.Checked
        self.replot_figure()

    def mirror(self, checked):
        """Mirror the image"""
        self.set_xc_yc()
        self.colnames_reader.mirror = checked == Qt.Checked
        self.replot_figure()

    def change_ignore_data_part(self, checked):
        """Change :attr:`straditize.colnames.ColNamesReader.ignore_data_part`
        """
        self.colnames_reader.ignore_data_part = checked == Qt.Checked

    def rotate(self, val):
        """Rotate the image

        Parameters
        ----------
        float
            The angle for the rotation"""
        if not str(val).strip():
            return
        try:
            val = float(val)
        except (ValueError, TypeError):
            val = 0
        self.set_xc_yc()
        self.colnames_reader.rotate = val
        self.replot_figure()

    def replot_figure(self):
        """Remove and replot the :attr:`im_rotated`"""
        adjust_lims = self.im_rotated is None
        ax = self.main_ax
        if not self.is_shown:
            return
        elif self.im_rotated:
            rotated = self.straditizer.colnames_reader.rotated_image
            if np.all(self.im_rotated.get_array() == np.asarray(rotated)):
                return
            else:
                try:
                    self.im_rotated.remove()
                except ValueError:
                    pass
        else:
            rotated = self.straditizer.colnames_reader.rotated_image
        self.im_rotated = ax.imshow(rotated)
        if self.xc is not None:
            dx = np.diff(ax.get_xlim()) / 2.
            dy = np.diff(ax.get_ylim()) / 2.
            xc, yc = self.colnames_reader.transform_point(self.xc, self.yc)
            ax.set_xlim(xc - dx, xc + dx)
            ax.set_ylim(yc - dy, yc + dy)
        self.highlight_selected_col()
        self.xc = self.yc = None
        if adjust_lims:
            self.adjust_lims()

    def adjust_lims(self):
        """Adjust the limits of the :attr:`main_ax` to fill the entire figure
        """
        size = xs, ys = np.array(self.im_rotated.get_size())
        ax = self.main_ax
        figw, figh = ax.figure.get_figwidth(), ax.figure.get_figheight()
        woh = figw / figh  # width over height
        how = figh / figw  # height over width
        limits = np.array([[xs, xs * how], [xs * woh, xs],
                           [ys, ys * how], [ys * woh, ys]])
        x, y = min(filter(lambda a: (a >= size).all(), limits),
                   key=lambda a: (a - size).max())
        ax.set_xlim(0, x)
        ax.set_ylim(y, 0)
        ax.axis('off')
        ax.margins(0)
        ax.set_position([0, 0, 1, 1])

    def to_dock(self, main, title=None, position=None, *args, **kwargs):
        if position is None:
            if main.centralWidget() is not main.help_explorer:
                position = main.dockWidgetArea(main.help_explorer.dock)
            else:
                position = Qt.RightDockWidgetArea
        connect = self.dock is None
        ret = super(ColumnNamesManager, self).to_dock(
            main, title, position, *args, **kwargs)
        if connect:
            action = self.dock.toggleViewAction()
            action.triggered.connect(self.maybe_tabify)
            action.triggered.connect(self._maybe_check_btn_select_names)
        return ret

    def maybe_tabify(self):
        main = self.dock.parent()
        if self.is_shown and main.dockWidgetArea(
                main.help_explorer.dock) == main.dockWidgetArea(self.dock):
            main.tabifyDockWidget(main.help_explorer.dock, self.dock)

    def adjust_lims_after_resize(self, event):
        """Adjust the limits of the :attr:`main_ax` after resize of the figure
        """
        h = event.height
        w = event.width
        if self.fig_w is None:
            self.fig_w = w
            self.fig_h = h
            self.adjust_lims()
            return
        ax = self.main_ax
        dx = np.diff(ax.get_xlim())[0]
        dy = np.diff(ax.get_ylim())[0]
        new_dx = dx * w/self.fig_w
        new_dy = dy * h/self.fig_h
        xc = np.mean(ax.get_xlim())
        yc = np.mean(ax.get_ylim())
        ax.set_xlim(xc - new_dx/2, xc + new_dx/2)
        ax.set_ylim(yc-new_dy/2, yc+new_dy/2)
        self.fig_w = w
        self.fig_h = h

    def _find_colnames(self):
        return self.find_colnames()

    def find_colnames(self, warn=True, full_image=False, all_cols=None):
        """Find the column names automatically

        See Also
        --------
        straditize.colnames.ColNamesReader.find_colnames"""
        ys, xs = self.im_rotated.get_size()
        x0, x1 = self.main_ax.get_xlim() if not full_image else (0, xs)
        y0, y1 = sorted(self.main_ax.get_ylim()) if not full_image else (0, ys)
        x0 = max(x0, 0)
        y0 = max(y0, 0)
        x1 = min(x1, xs)
        y1 = min(y1, ys)
        reader = self.colnames_reader
        texts, images, boxes = reader.find_colnames(
            [x0, y0, x1, y1])
        # make sure we have the exact length
        reader.column_names
        reader.colpics
        all_cols = all_cols or (all_cols is None and
                                self.cb_find_all_cols.isChecked())
        if not all_cols and self.current_col not in texts:
            if self.current_col is not None:
                msg = ("Could not find a column name of column %i in the "
                       "selected image!" % self.current_col)
                if warn:
                    QtWidgets.QMessageBox.warning(
                        self.straditizer_widgets, 'Could not find column name',
                        msg)
            return msg
        elif not texts:
            msg = "Could not find any column name in the selected image!"
            if warn:
                QtWidgets.QMessageBox.warning(
                    self.straditizer_widgets, 'Could not find column name',
                    msg)
            return msg
        elif not all_cols:
            texts = {self.current_col: texts[self.current_col]}
        for col, text in texts.items():
                self.colnames_table.setItem(col, 0,
                                            QtWidgets.QTableWidgetItem(text))
                self.colnames_reader._colpics[col] = images[col]
        if self.current_col is not None:
            self.colpic = self.colnames_reader._colpics[self.current_col]
            if self.selector is not None:
                box = boxes[self.current_col]
                self.colpic_extents = np.round(box.extents).astype(int)
                self.remove_selector()
                self.create_selector()
                self.main_canvas.draw()
            self.plot_colpic()
