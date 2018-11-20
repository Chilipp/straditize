"""Widget for handling column names"""
import numpy as np
import os
from straditize.widgets import StraditizerControlBase
from straditize.widgets.pattern_selection import EmbededMplCanvas
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

    im_rotated = None

    rect = None

    fig_w = fig_h = None

    highres_image = None

    colpic_im = colpic_extents = selector = colpic = None

    @property
    def current_col(self):
        """The currently selected column"""
        indexes = self.colnames_table.selectedIndexes()
        if len(indexes):
            return indexes[0].row()

    @property
    def colnames_reader(self):
        return self.straditizer.colnames_reader

    def __init__(self, straditizer_widgets, item=None, *args, **kwargs):
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
        self.btn_recognize.setToolTip('Use tesseract to recognize the column '
                                      'name in the given image')
        super().__init__(Qt.Horizontal)

        # centers of the image
        self.xc = self.yc = None

        self.txt_rotate = QtWidgets.QLineEdit()
        self.txt_rotate.setValidator(QtGui.QDoubleValidator(0., 90., 3))
        self.txt_rotate.setPlaceholderText('0˚..90˚')

        self.cb_fliph = QtWidgets.QCheckBox('Flip horizontally')
        self.cb_flipv = QtWidgets.QCheckBox('Flip vertically')

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
        layout.addRow(self.main_canvas)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.btn_select_colpic)
        hbox.addWidget(self.btn_cancel_colpic_selection)
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

        self.widgets2disable = [self.btn_select_names]

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

    def colname_changed(self, row, column):
        """Function that is called when a cell has been changed"""
        self.colnames_reader._column_names[row] = self.colnames_table.item(
            row, column).text()

    def read_colpic(self):
        text = self.colnames_reader.recognize_text(self.colpic)
        self.colnames_table.item(self.current_col, 0).setText(text)
        self.colnames_reader._column_names[self.current_col] = text

    def load_image(self):
        if self.btn_load_image.isChecked():
            fname = QtWidgets.QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Straditizer project',
                os.getcwd(),
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
                image = Image.open(fname)
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                self.colnames_reader.highres_image = image

        else:
            self.colnames_reader.highres_image = None
        self.refresh()

    def cancel_colpic_selection(self):
        self.colnames_reader._colpics = self._colpics_save
        if self.current_col is not None:
            self.colpic = self.colnames_reader.colpics[self.current_col]
        self.btn_select_colpic.setChecked(False)
        self.toggle_colpic_selection()

    def toggle_colpic_selection(self):
        """Enable or disable the template selection"""
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
        else:
            self.selector = RectangleSelector(
                self.main_ax, self.update_image, interactive=True)
            if self.colpic_extents is not None:
                self.selector.draw_shape(self.colpic_extents)
            self.key_press_cid = self.main_canvas.mpl_connect(
                'key_press_event', self.update_image)
            self.btn_select_colpic.setText('Cancel')
            self.main_canvas.toolbar.pan()
            self._colpics_save = list(self.colnames_reader.colpics)
        self.main_canvas.draw()

    def remove_selector(self):
        self.selector.disconnect_events()
        for a in self.selector.artists:
            try:
                a.remove()
            except ValueError:
                pass
        self.main_canvas.draw()
        del self.selector
        self.main_canvas.mpl_disconnect(self.key_press_cid)

    def update_image(self, *args, **kwargs):
        if self.colpic_im is not None:
            self.colpic_im.remove()
            del self.colpic_im

        self.colpic_extents = np.round(self.selector.extents).astype(int)
        x, y = self.colpic_extents.reshape((2, 2))
        x0, x1 = sorted(x)
        y0, y1 = sorted(y)
        self.colpic = self.colnames_reader._colpics[self.current_col] = \
            self.colnames_reader.get_colpic(x0, y0, x1, y1)
        self.colpic_im = self.colpic_ax.imshow(self.colpic)
        self.btn_select_colpic.setText('Apply')
        self.btn_cancel_colpic_selection.setVisible(True)
        self.colpic_canvas.draw()
        self.btn_recognize.setEnabled(True)

    def highlight_selected_col(self):
        if self.rect is not None:
            self.rect.remove()
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
            self.btn_recognize.setEnabled(colpic is not None)
        else:
            self.btn_select_colpic.setEnabled(False)
        self.main_canvas.draw()

    def setup_children(self, item):
        child = QtWidgets.QTreeWidgetItem(0)
        item.addChild(child)
        self.straditizer_widgets.tree.setItemWidget(
            child, 0, self.btn_select_names)

    def should_be_enabled(self, w):
        return self.straditizer is not None and getattr(
            self.straditizer.data_reader, '_column_starts', None) is not None

    def toggle_dialog(self):
        from psyplot_gui.main import mainwindow
        if not self.refreshing:
            if not self.btn_select_names.isChecked() or (
                    self.dock is not None and self.is_shown):
                self.hide_plugin()
            elif self.btn_select_names.isEnabled():
                self.straditizer_widgets.tree.itemWidget(
                    self.straditizer_widgets.col_names_item, 1).show_docs()
                self.to_dock(mainwindow, 'Straditizer column names')
                self.show_plugin()
                self.dock.raise_()
            self.refresh()

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

            image = self.colnames_reader.highres_image
            if image is not None:
                self.btn_load_image.setText(
                    'HR image with size {}'.format(image.size))
                self.btn_load_image.setToolTip(
                    'Select a version of this image with a higher resolution '
                    'to improve the text recognition')
                checked = True
            else:
                self.btn_load_image.setText('Load HR image')
                self.btn_load_image.setToolTip(
                    'Remove and ignore the high resolution image')
                checked = False
            self.btn_load_image.blockSignals(True)
            self.btn_load_image.setChecked(checked)
            self.btn_load_image.blockSignals(False)
            self.btn_recognize.setEnabled(self.colpic is not None)
        else:
            try:
                self.im_rotated.remove()
            except (AttributeError, ValueError):
                pass
            self.im_rotated = self.xc = self.yc = None


    def set_xc_yc(self):
        xc = np.mean(self.main_ax.get_xlim())
        yc = np.mean(self.main_ax.get_ylim())
        self.xc, self.yc = self.colnames_reader.transform_point(xc, yc, True)

    def flip(self, checked):
        self.set_xc_yc()
        self.colnames_reader.flip = checked == Qt.Checked
        self.replot_figure()

    def mirror(self, checked):
        self.set_xc_yc()
        self.colnames_reader.mirror = checked == Qt.Checked
        self.replot_figure()

    def rotate(self, val):
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
        ys, xs = self.im_rotated.get_size()
        ax = self.main_ax
        figw, figh = ax.figure.get_figwidth(), ax.figure.get_figheight()
        if figw < figh:
            ax.set_ylim(ys, 0)
            ax.set_xlim(0, ys * figw/figh)
        else:
            ax.set_xlim(0, xs)
            ax.set_ylim(xs*figh/figw, 0)
        ax.axis('off')
        ax.margins(0)
        ax.set_position([0, 0, 1, 1])

    def to_dock(self, main, title=None, position=None, *args, **kwargs):
        if position is None:
            position = main.dockWidgetArea(main.help_explorer.dock)
        connect = self.dock is None
        ret = super(ColumnNamesManager, self).to_dock(
            main, title, position, *args, **kwargs)
        if connect:
            self.dock.toggleViewAction().triggered.connect(self.maybe_tabify)
        return ret

    def maybe_tabify(self):
        main = self.dock.parent()
        if self.is_shown and main.dockWidgetArea(
                main.help_explorer.dock) == main.dockWidgetArea(self.dock):
            main.tabifyDockWidget(main.help_explorer.dock, self.dock)

    def adjust_lims_after_resize(self, event):
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
