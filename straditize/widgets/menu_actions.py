"""The main control widget for a straditizer

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
import os
import os.path as osp
import weakref
import pandas as pd
from itertools import chain
import datetime as dt
import six
from straditize.widgets import StraditizerControlBase
from straditize.common import rgba2rgb, docstrings
from psyplot_gui.compat.qtcompat import (
    with_qt5, QFileDialog, QMenu, QKeySequence, QDialog, QDialogButtonBox,
    QLineEdit, QToolButton, QIcon, QCheckBox, QHBoxLayout, QVBoxLayout, QLabel,
    QDesktopWidget, QTreeWidgetItem, Qt, QMessageBox)
from PyQt5 import QtWidgets
from psyplot_gui.common import get_icon
import numpy as np
from PIL import Image

straditizer = None


# axes that are being updated currently
_updating = []


class ExportDfDialog(QDialog):
    """A QDialog to export a :class:`pandas.DataFrame` to Excel or CSV"""

    @docstrings.get_sectionsf('ExportDfDialog')
    def __init__(self, df, straditizer, fname=None, *args, **kwargs):
        """
        Parameters
        ----------
        df: pandas.DataFrame
            The DataFrame to be exported
        straditizer: straditize.straditizer.Straditizer
            The source straditizer
        fname: str
            The file name to export to
        """
        super().__init__(*args, **kwargs)
        self.df = df
        self.stradi = straditizer
        self.txt_fname = QLineEdit()
        self.bt_open_file = QToolButton()
        self.bt_open_file.setIcon(QIcon(get_icon('run_arrow.png')))
        self.bt_open_file.setToolTip('Select the export file on your drive')

        self.cb_include_meta = QCheckBox('Include meta data')
        self.cb_include_meta.setChecked(True)

        self.bbox = bbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                            QDialogButtonBox.Cancel)

        # ---------------------------------------------------------------------
        # --------------------------- Layouts ---------------------------------
        # ---------------------------------------------------------------------
        vbox = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Export to:'))
        hbox.addWidget(self.txt_fname)
        hbox.addWidget(self.bt_open_file)
        vbox.addLayout(hbox)

        vbox.addWidget(self.cb_include_meta)

        vbox.addWidget(bbox)
        self.setLayout(vbox)

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------
        bbox.accepted.connect(self._export)
        bbox.rejected.connect(self.reject)
        self.bt_open_file.clicked.connect(self.get_open_file_name)

        if fname is not None:
            self.txt_fname.setText(fname)
            self._export()

    def get_open_file_name(self):
        """Ask the user for a filename for saving the data frame"""
        def check_current():
            dirname = osp.dirname(current)
            if osp.exists(dirname) and osp.isdir(dirname):
                return dirname
        current = self.txt_fname.text().strip()
        start = None
        if current:
            start = check_current()
        if start is None:
            for attr in 'project_file', 'image_file':
                try:
                    current = self.stradi.get_attr(attr)
                except KeyError:
                    pass
                else:
                    start = check_current()
                    if start is not None:
                        break
        if start is None:
            start = os.getcwd()
        fname = QFileDialog.getSaveFileName(
            self, 'DataFrame file destination', start,
            'Excel files (*.xlsx *.xls);;'
            'csv files (*.csv);;'
            'All files (*)'
            )
        if with_qt5:  # the filter is passed as well
            fname = fname[0]
        if not fname:
            return
        self.txt_fname.setText(fname)

    def _export(self):
        fname = self.txt_fname.text()
        ending = osp.splitext(fname)[1]
        self.stradi.set_attr('exported', str(dt.datetime.now()))
        meta = self.stradi.valid_attrs
        if ending in ['.xls', '.xlsx']:
            with pd.ExcelWriter(fname) as writer:
                self.df.to_excel(writer, 'Data')
                if self.cb_include_meta.isChecked() and len(meta):
                    meta.to_excel(writer, 'Metadata', header=False)
        else:
            with open(fname, 'w') as f:
                if self.cb_include_meta.isChecked():
                    for t in meta.iloc[:, 0].items():
                        f.write('# %s: %s\n' % t)
            self.df.to_csv(fname, mode='a')
        self.accept()

    def cancel(self):
        del self.stradi, self.df
        super().cancel()

    def accept(self):
        del self.stradi, self.df
        super().accept()

    @classmethod
    @docstrings.dedent
    def export_df(cls, parent, df, straditizer, fname=None, exec_=True):
        """Open a dialog for exporting a DataFrame

        Parameters
        ----------
        parent: QWidget
            The parent widget
        %(ExportDfDialog.parameters)s"""
        dialog = cls(df, straditizer, fname, parent=parent)
        if fname is None:
            available_width = QDesktopWidget().availableGeometry().width() / 3.
            width = dialog.sizeHint().width()
            height = dialog.sizeHint().height()
            # The plot creator window should cover at least one third of the
            # screen
            dialog.resize(max(available_width, width), height)
            if exec_:
                dialog.exec_()
            else:
                return dialog


class StraditizerMenuActions(StraditizerControlBase):
    """An object to control the main functionality of a Straditizer

    This object is creates menu actions to load the straditizer"""

    #: The QActions to save the straditizer, straditizer image, etc.
    save_actions = []

    #: The QActions to save the exported DataFrames and data images
    data_actions = []

    #: The QActions to save the column names images
    text_actions = []

    #: The action to
    #: :meth:`~straditize.widgets.StraditizerWidgets.switch_to_straditizer_layout`
    window_layout_action = None

    #: The path to a directory from where to open a straditizer. Is set in the
    #: tutorial
    _dirname_to_use = None

    @property
    def all_actions(self):
        """:attr:`save_actions`, :attr:`data_actions` and :attr:`text_actions`
        """
        return chain(self.save_actions, self.data_actions, self.text_actions)

    def __init__(self, straditizer_widgets):
        self.init_straditizercontrol(straditizer_widgets)

    def setup_menu_actions(self, main):
        """Create the actions for the file menu

        Parameters
        ----------
        main: psyplot_gui.main.MainWindow
            The mainwindow whose menubar shall be adapted"""
        # load buttons
        self.open_menu = menu = QMenu('Open straditizer')
        main.open_project_menu.addMenu(self.open_menu)

        self.load_stradi_action = self._add_action(
            menu, 'Project or image', self.open_straditizer,
            tooltip='Reload a digitization project or load a picture')

        self.load_clipboard_action = self._add_action(
            menu, 'From clipboard', self.from_clipboard,
            tooltip='Load a picture from the clipboard')

        # save and export data buttons
        self.save_straditizer_action = self._add_action(
            main.save_project_menu, 'Save straditizer', self.save_straditizer,
            tooltip='Save the digitization project')

        self.save_straditizer_as_action = self._add_action(
            main.save_project_as_menu, 'Save straditizer as',
            self.save_straditizer_as,
            tooltip='Save the digitization project to a different file')

        self.export_data_menu = menu = QMenu('Straditizer data')
        main.export_project_menu.addMenu(menu)

        self.export_full_action = self._add_action(
            menu, 'Full data', self.export_full,
            tooltip='Export the full digitized data')

        self.export_final_action = self._add_action(
            menu, 'Samples', self.export_final,
            tooltip='Export the data at the sample locations')

        # close menu
        self.close_straditizer_action = self._add_action(
            main.close_project_menu, 'Close straditizer',
            self.straditizer_widgets.close_straditizer,
            tooltip='Close the current straditize project')

        self.close_all_straditizer_action = self._add_action(
            main.close_project_menu, 'Close all straditizers',
            self.straditizer_widgets.close_all_straditizers,
            tooltip='Close all open straditize projects')

        # export image buttons
        self.export_images_menu = menu = QMenu('Straditizer image(s)')
        menu.setToolTipsVisible(True)
        main.export_project_menu.addMenu(menu)

        self.export_full_image_action = self._add_action(
            menu, 'Full image', self.save_full_image,
            tooltip='Save the full image to a file')

        self.export_data_image_action = self._add_action(
            menu, 'Save data image', self.save_data_image,
            tooltip='Save the binary image that represents the data part')

        self.export_text_image_action = self._add_action(
            menu, 'Save text image', self.save_text_image,
            tooltip='Save the image part with the rotated column descriptions')

        # import image buttons
        self.import_images_menu = menu = QMenu('Import straditizer image(s)')
        menu.setToolTipsVisible(True)

        self.import_full_image_action = self._add_action(
            menu, 'Full image', self.import_full_image,
            tooltip='Import the diagram into the current project')

        self.import_data_image_action = self._add_action(
            menu, 'Data image', self.import_data_image,
            tooltip='Import the data part image')

        self.import_binary_image_action = self._add_action(
            menu, 'Binary data image', self.import_binary_image,
            tooltip='Import the binary image for the data part')

        self.import_text_image_action = self._add_action(
            menu, 'Text image', self.import_text_image,
            tooltip='Import the image for the column names')

        self.window_layout_action = main.window_layouts_menu.addAction(
            'Straditizer layout',
            self.straditizer_widgets.switch_to_straditizer_layout)

        self.save_actions = [self.export_full_image_action,
                             self.save_straditizer_action,
                             self.import_full_image_action]
        self.data_actions = [self.export_data_image_action,
                             self.export_full_action,
                             self.export_final_action,
                             self.import_binary_image_action,
                             self.import_data_image_action]
        self.text_actions = [self.export_text_image_action,
                             self.import_text_image_action]

        self.widgets2disable = [self.load_stradi_action,
                                self.load_clipboard_action]

        self.refresh()

    def setup_shortcuts(self, main):
        """Setup the shortcuts when switched to the straditizer layout

        Parameters
        ----------
        main: psyplot_gui.main.MainWindow
            The psyplot mainwindow"""
        main.register_shortcut(self.save_straditizer_action, QKeySequence.Save)
        main.register_shortcut(self.save_straditizer_as_action,
                               QKeySequence.SaveAs)
        main.register_shortcut(self.close_straditizer_action,
                               QKeySequence.Close)
        main.register_shortcut(
            self.close_all_straditizer_action,
            QKeySequence('Ctrl+Shift+W', QKeySequence.NativeText))

        main.register_shortcut(
            self.export_final_action, QKeySequence(
                'Ctrl+E', QKeySequence.NativeText))
        main.register_shortcut(
            self.export_full_action, QKeySequence(
                'Ctrl+Shift+E', QKeySequence.NativeText))
        main.register_shortcut(self.load_stradi_action,
                               [QKeySequence.Open, QKeySequence.New])

    def _add_action(self, menu, *args, **kwargs):
        tooltip = kwargs.pop('tooltip', None)
        a = menu.addAction(*args, **kwargs)
        if tooltip:
            a.setToolTip(tooltip)
        return a

    @property
    def _start_directory(self):
        def check_current():
            dirname = osp.dirname(current)
            if osp.exists(dirname) and osp.isdir(dirname):
                return dirname
        if self.straditizer is not None:
            current = None
            for attr in 'project_file', 'image_file':
                try:
                    current = self.straditizer.get_attr(attr)
                except KeyError:
                    pass
                else:
                    start = check_current()
                    if start is not None:
                        break
            if current:
                return osp.splitext(current)[0]
        return os.getcwd()

    @docstrings.get_sectionsf('StraditizerMenuActions._open_image')
    def _open_image(self, fname=None):
        """Open an image file

        Parameters
        ----------
        fname: :class:`str`, :class:`PIL.Image.Image` or ``None``
            The path of the image file or the :class:`PIL.Image.Image`. If
            None, a QFileDialog is opened to request the file from the user.

        Returns
        -------
        PIL.Image.Image
            The image file or None if the operation has been cancelled by the
            user"""
        if fname is None or (not isinstance(fname, six.string_types) and
                             np.ndim(fname) < 2):
            fname = QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Stratigraphic diagram',
                self._dirname_to_use or self._start_directory,
                'All images '
                '(*.jpeg *.jpg *.pdf *.png *.raw *.rgba *.tif *.tiff);;'
                'Joint Photographic Experts Group (*.jpeg *.jpg);;'
                'Portable Document Format (*.pdf);;'
                'Portable Network Graphics (*.png);;'
                'Tagged Image File Format(*.tif *.tiff);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not np.ndim(fname) and not fname:
            return
        elif np.ndim(fname) >= 2:
            return fname
        else:
            from PIL import Image
            with Image.open(fname) as _image:
                return Image.fromarray(np.array(_image.convert('RGBA')))

    @docstrings.with_indent(8)
    def import_full_image(self, fname=None):
        """Import the straditizer image from an external file

        This method imports the
        :attr:`straditize.straditizer.Straditizer.image` from an external
        file and sets it to the current straditizer.

        Parameters
        ----------
        %(StraditizerMenuActions._open_image.parameters)s"""
        image = self._open_image(fname)
        if image is not None:
            if self.straditizer is None:
                self.open_straditizer(image)
            else:
                self.straditizer.reset_image(image)

    @docstrings.with_indent(8)
    def import_data_image(self, fname=None):
        """Import the data reader image from an external file

        This method imports the
        :attr:`straditize.binary.DataReader.image` from an external
        file and sets it to the current
        :attr:`~straditize.straditizer.Straditizer.data_reader`.

        Parameters
        ----------
        %(StraditizerMenuActions._open_image.parameters)s

        See Also
        --------
        import_binary_image: To import the binary file"""
        image = self._open_image(fname)
        if image is not None:
            self.straditizer.data_reader.reset_image(image)

    @docstrings.with_indent(8)
    def import_binary_image(self, fname=None):
        """Import the binary data reader image from an external file

        This method imports the
        :attr:`straditize.binary.DataReader.binary` from an external
        file and sets it to the current
        :attr:`~straditize.straditizer.Straditizer.data_reader`.

        Parameters
        ----------
        %(StraditizerMenuActions._open_image.parameters)s"""
        image = self._open_image(fname)
        if image is not None:
            self.straditizer.data_reader.reset_image(image, binary=True)

    @docstrings.with_indent(8)
    def import_text_image(self, fname):
        """Import the column names reader image from an external file

        This method imports the
        :attr:`straditize.colnames.ColNamesReader.highres_image` from an
        external file and sets it to the current
        :attr:`~straditize.straditizer.Straditizer.colnames_reader`.

        Parameters
        ----------
        %(StraditizerMenuActions._open_image.parameters)s"""
        image = self._open_image(fname)
        if image is not None:
            self.straditizer.colnames_reader.highres_image = image

    def open_straditizer(self, fname=None, *args, **kwargs):
        """Open a straditizer from an image or project file

        Parameters
        ----------
        fname: :class:`str`, :class:`PIL.Image.Image` or ``None``
            The path to the file to import. If None, a QFileDialog is opened
            and the user is asked for a file name. The action then depends on
            the ending of ``fname``:

            ``'.nc'`` or ``'.nc4'``
                we expect a netCDF file and open it with
                :func:`xarray.open_dataset` and load the straditizer with the
                :meth:`straditize.straditizer.Straditizer.from_dataset`
                constructor
            ``'.pkl'``
                We expect a pickle file and load the straditizer with
                :func:`pickle.load`
            any other ending
                We expect an image file and use the :func:`PIL.Image.open`
                function

            At the end, the loading is finished with the :meth:`finish_loading`
            method"""
        from straditize.straditizer import Straditizer
        if fname is None or (not isinstance(fname, six.string_types) and
                             np.ndim(fname) < 2):
            fname = QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Straditizer project',
                self._dirname_to_use or self._start_directory,
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
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not np.ndim(fname) and not fname:
            return
        elif np.ndim(fname) >= 2:
            stradi = Straditizer(fname, *args, **kwargs)
        elif fname.endswith('.nc') or fname.endswith('.nc4'):
            import xarray as xr
            ds = xr.open_dataset(fname)
            stradi = Straditizer.from_dataset(ds.load(), *args, **kwargs)
            stradi.set_attr('project_file', fname)
            ds.close()
            stradi.set_attr('loaded', str(dt.datetime.now()))
        elif fname.endswith('.pkl'):
            stradi = Straditizer.load(fname, *args, **kwargs)
            stradi.set_attr('project_file', fname)
            stradi.set_attr('loaded', str(dt.datetime.now()))
        else:
            from PIL import Image
            with Image.open(fname) as _image:
                image = Image.fromarray(np.array(_image.convert('RGBA')),
                                        'RGBA')
            w, h = image.size
            im_size = w * h
            if im_size > 20e6:
                recom_frac = 17403188.0 / im_size
                answer = (
                    QMessageBox.Yes
                    if self.straditizer_widgets.always_yes else
                    QMessageBox.question(
                        self.straditizer_widgets, "Large straditizer image",
                        "This is a rather large image with %1.0f pixels. "
                        "Shall I reduce it to %1.0f%% of it's size for a "
                        "better interactive experience?<br>"
                        "If not, you can rescale it via<br><br>"
                        "Transform source image &rarr; Rescale image" % (
                            im_size, 100. * recom_frac)))
                if answer == QMessageBox.Yes:
                    image = image.resize((int(round(w * recom_frac)),
                                          int(round(h * recom_frac))))

            stradi = Straditizer(image, *args, **kwargs)
            stradi.set_attr('image_file', fname)
        self.finish_loading(stradi)
        self._dirname_to_use = None

    def finish_loading(self, stradi):
        """Finish the opening of a straditizer

        This method sets the
        :attr:`straditizer.widgets.StraditizerWidgets.straditizer`, shows the
        straditizer image, creates the navigation sliders and sets the
        straditizer in the console

        Parameters
        ----------
        stradi: straditize.straditizer.Straditizer
            The straditizer that just has been opened"""
        self.straditizer = stradi
        stradi.show_full_image()
        self.create_sliders(stradi)
        self.set_stradi_in_console()
        self.stack_zoom_window()
        self.straditizer_widgets.refresh()

    def create_sliders(self, stradi):
        """Create sliders to navigate in the given axes

        Parameters
        ----------
        stradi: straditize.straditizer.Straditizer
            The straditizer that just has been opened"""
        ax = stradi.ax
        try:
            manager = ax.figure.canvas.manager
            dock = manager.window
            fig_widget = manager.parent_widget
        except AttributeError:
            return
        from psyplot_gui.backend import FigureWidget
        import matplotlib.colors as mcol
        xs, ys = stradi.image.size
        fc = ax.figure.get_facecolor()
        rgb = tuple(np.round(np.array(mcol.to_rgb(fc)) * 255).astype(int))

        slh = QtWidgets.QSlider(Qt.Horizontal)
        slv = QtWidgets.QSlider(Qt.Vertical)

        slh.setStyleSheet("background-color:rgb{};".format(rgb))
        slv.setStyleSheet("background-color:rgb{};".format(rgb))

        slh.setMaximum(xs)
        slv.setMaximum(ys)
        slv.setInvertedAppearance(True)
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()

        vbox.setSpacing(0)
        hbox.setSpacing(0)

        hbox.addWidget(fig_widget)
        hbox.addWidget(slv)
        vbox.addLayout(hbox)
        vbox.addWidget(slh)

        w = FigureWidget()
        w.dock = dock
        w.setLayout(vbox)
        dock.setWidget(w)

        ax.callbacks.connect('xlim_changed', self.update_x_navigation_sliders)
        ax.callbacks.connect('ylim_changed', self.update_y_navigation_sliders)
        self.update_x_navigation_sliders(ax)
        self.update_y_navigation_sliders(ax)
        ref = weakref.ref(ax)
        slh.valueChanged.connect(self.set_ax_xlim(ref))
        slv.valueChanged.connect(self.set_ax_ylim(ref))

    @staticmethod
    def set_ax_xlim(ax_ref):
        """Define a function to update xlim from a given centered value

        Parameters
        ----------
        ax_ref: matplotlib.axes.Axes
            The axes whose x-limits to update when the returned function is
            called

        Returns
        -------
        callable
            The function that can be called with a `val` to set the x-center
            of the `ax_ref`"""
        def update(val):
            ax = ax_ref()
            if ax in _updating or ax is None:
                return

            _updating.append(ax)
            lims = ax.get_xlim()
            diff = (lims[1] - lims[0]) / 2
            ax.set_xlim(val - diff, val + diff)
            ax.figure.canvas.draw_idle()
            _updating.remove(ax)
        return update

    @staticmethod
    def set_ax_ylim(ax_ref):
        """Define a function to update ylim from a given centered value

        Parameters
        ----------
        ax_ref: matplotlib.axes.Axes
            The axes whose y-limits to update when the returned function is
            called

        Returns
        -------
        callable
            The function that can be called with a `val` to set the y-center
            of the `ax_ref`"""
        def update(val):
            ax = ax_ref()
            if ax in _updating or ax is None:
                return

            _updating.append(ax)
            lims = ax.get_ylim()
            diff = (lims[1] - lims[0]) / 2
            ax.set_ylim(val - diff, val + diff)
            ax.figure.canvas.draw_idle()
            _updating.remove(ax)
        return update

    @staticmethod
    def update_x_navigation_sliders(ax):
        """Update the horizontal navigation slider for the given `ax``

        Set the horizontal slider of the straditizer figure depending on the
        x-limits of it's corresponding axes

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The :attr:`straditize.straditizer.Straditizer.ax` attribute of a
            straditizer
        """
        w = ax.figure.canvas.manager.window.widget()
        slh = w.layout().itemAt(1).widget()

        xc = np.mean(ax.get_xlim())

        slh.setValue(max(0, min(slh.maximum(), int(round(xc)))))

    @staticmethod
    def update_y_navigation_sliders(ax):
        """Update the vertical navigation slider for the given `ax``

        Set the vertical slider of the straditizer figure depending on the
        y-limits of it's corresponding axes

        Parameters
        ----------
        ax: matplotlib.axes.Axes
            The :attr:`straditize.straditizer.Straditizer.ax` attribute of a
            straditizer
        """
        w = ax.figure.canvas.manager.window.widget()
        slv = w.layout().itemAt(0).itemAt(1).widget()

        yc = np.mean(ax.get_ylim())
        slv.setValue(max(0, min(slv.maximum(), int(round(yc)))))

    def stack_zoom_window(self):
        """Stack the magnifier image above the help explorer"""
        from psyplot_gui.main import mainwindow
        if mainwindow.figures:
            found = False
            for stradi in self.straditizer_widgets._straditizers:
                if stradi is not self.straditizer and stradi.magni:
                    ref_dock = stradi.magni.ax.figure.canvas.manager.window
                    found = True
                    break
            if not found:
                ref_dock = mainwindow.help_explorer.dock
            dock = self.straditizer.magni.ax.figure.canvas.manager.window
            pos = mainwindow.dockWidgetArea(ref_dock)
            mainwindow.addDockWidget(pos, dock)
            if not found:
                mainwindow.addDockWidget(pos, ref_dock)
            else:
                mainwindow.tabifyDockWidget(ref_dock, dock)
                # show the zoom figure
                dock.widget().show_plugin()
                dock.raise_()
            mainwindow.figures.insert(-1, mainwindow.figures.pop(-1))
            # show the straditizer figure
            mainwindow.figures[-1].widget().show_plugin()
            mainwindow.figures[-1].raise_()

    def from_clipboard(self):
        """Open a straditizer from an Image in the clipboard

        This method uses the :func:`PIL.ImageGrab.grabclipboard` function to
        open a new straditizer from the clipboard."""
        from PIL import ImageGrab
        from straditize.straditizer import Straditizer
        image = ImageGrab.grabclipboard()
        if np.shape(image)[-1] == 3:
            image.putalpha(255)
        stradi = Straditizer(image)
        return self.finish_loading(stradi)

    def save_straditizer(self):
        """Save the straditizer to a file"""
        try:
            fname = self.straditizer.attrs.loc['project_file', 0]
        except KeyError:
            fname = None
        return self.save_straditizer_as(fname)

    def save_straditizer_as(self, fname=None):
        """Save the straditizer to a file

        Parameters
        ----------
        fname: str or ``None``
            If None, a QFileDialog is opened and the user has to provide a
            filename. The final action then depends on the ending of the
            chose file:

            ``'.pkl'``
                We save the straditizer with :meth:`pickle.dump`
            else
                We use the
                :meth:`straditize.straditizer.Straditizer.to_dataset` method
                and save the resulting dataset using the
                :meth:`xarray.Dataset.to_netcdf` method"""
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getSaveFileName(
                self.straditizer_widgets, 'Straditizer file destination',
                self._start_directory,
                ('NetCDF files (*.nc *.nc4);;Pickle files (*.pkl);;'
                 'All files (*)')
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not fname:
            return
        ending = os.path.splitext(fname)[1]
        self.straditizer.set_attr('saved', str(dt.datetime.now()))
        self.straditizer.set_attr('project_file', fname)
        if ending == '.pkl':
            self.straditizer.save(fname)
        else:
            ds = self.straditizer.to_dataset()
            # -- Compression with a level of 4. Requires netcdf4 engine
            comp = dict(zlib=True, complevel=4)
            encoding = {var: comp for var in ds.data_vars}

            ds.to_netcdf(fname, encoding=encoding, engine='netcdf4')

    @docstrings.get_sectionsf('StraditizerMenuActions._save_image')
    def _save_image(self, image, fname=None):
        """Save an image to a file

        Parameters
        ----------
        image: PIL.Image.Image
            The image to save
        fname: str or None
            The path of the target filename where to save the `image`. If None,
            A QFileDialog is opened and we ask the user for a filename"""
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getSaveFileName(
                self.straditizer_widgets, 'Straditizer file destination',
                self._start_directory,
                'All images '
                '(*.png *.jpeg *.jpg *.pdf *.tif *.tiff);;'
                'Joint Photographic Experts Group (*.jpeg *.jpg);;'
                'Portable Document Format (*.pdf);;'
                'Portable Network Graphics (*.png);;'
                'Tagged Image File Format(*.tif *.tiff);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if not fname:
            return
        ext = osp.splitext(fname)[1]
        if ext.lower() in ['.jpg', '.jpeg', '.pdf'] and image.mode == 'RGBA':
            image = rgba2rgb(image)
        image.save(fname)

    docstrings.keep_params('StraditizerMenuActions._save_image.parameters',
                           'fname')

    @docstrings.with_indent(8)
    def save_text_image(self, fname=None):
        """Save the image of the colnames reader

        Save the :attr:`straditize.colnames.ColNamesReader.image` of the
        current :attr:`~straditize.straditizer.Straditizer.colnames_reader`

        Parameters
        ----------
        %(StraditizerMenuActions._save_image.parameters.fname)s
        """
        reader = self.straditizer.colnames_reader
        self._save_image(reader.highres_image, fname)

    def save_full_image(self, fname=None):
        """Save the image of the straditizer

        Save the :attr:`straditize.straditizer.Straditizer.image` of the
        current :attr:`~straditize.widgets.StraditizerWidgets.straditizer`

        Parameters
        ----------
        %(StraditizerMenuActions._save_image.parameters.fname)s
        """
        self._save_image(self.straditizer.image, fname)

    def save_data_image(self, fname=None):
        """Save the binary image of the data reader

        Save the :attr:`straditize.binary.DataReader.binary` of the
        current :attr:`~straditize.straditizer.Straditizer.data_reader`

        Parameters
        ----------
        %(StraditizerMenuActions._save_image.parameters.fname)s
        """
        arr = np.tile(self.straditizer.data_reader.binary[:, :, np.newaxis],
                      (1, 1, 4))
        arr[..., 3] *= 255
        arr[..., :3] = 0
        image = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        self._save_image(image, fname)

    def set_stradi_in_console(self):
        """Set the straditizer in the console of the GUI mainwindow

        This sets the current
        :attr:`~straditize.widgets.StraditizerWidgets.straditizer` in psyplots
        :attr:`~psyplot_gui.main.MainWindow.console` as the ``stradi`` variable
        """
        from psyplot_gui.main import mainwindow
        global straditizer
        straditizer = self.straditizer
        if mainwindow is not None:
            mainwindow.console.run_command_in_shell(
                'from %s import straditizer as stradi' % __name__)
        straditizer = None

    @docstrings.get_sectionsf('StraditizerMenuActions._export_df')
    def _export_df(self, df, fname=None):
        """Export a data frame to a file

        This method opens an :class:`ExportDfDialog` to save a data frame

        Parameters
        ----------
        df: pandas.DataFrame
            The dataframe to save
        fname: str or None
            The path of the target filename where to save the `df`
            (see the :meth:`ExportDialog.export_df`)"""
        ExportDfDialog.export_df(self.straditizer_widgets, df,
                                 self.straditizer, fname)

    docstrings.keep_params('StraditizerMenuActions._export_df.parameters',
                           'fname')

    @docstrings.with_indent(8)
    def export_final(self, fname=None):
        """Export the final results

        This method exports the
        :attr:`straditize.straditizer.Straditizer.final_df` of the current
        :attr:`~straditize.widgets.StraditizerWidgets.straditizer`

        Parameters
        ----------
        %(StraditizerMenuActions._export_df.parameters.fname)s"""
        try:
            df = self.straditizer.final_df
        except Exception as e:
            self.straditizer_widgets.error_msg.showTraceback(
                e.message if six.PY2 else str(e))
        else:
            self._export_df(df, fname)

    @docstrings.with_indent(8)
    def export_full(self, fname=None):
        """Export the full digitized data

        This method exports the
        :attr:`straditize.straditizer.Straditizer.full_df` of the current
        :attr:`~straditize.widgets.StraditizerWidgets.straditizer`

        Parameters
        ----------
        %(StraditizerMenuActions._export_df.parameters.fname)s"""
        self._export_df(self.straditizer.full_df, fname)

    def refresh(self):
        stradi = self.straditizer
        import_stradi_action = getattr(self, 'import_full_image_action', None)
        if stradi is None:
            for w in filter(lambda w: w is not import_stradi_action,
                            self.all_actions):
                w.setEnabled(False)
        else:
            if stradi.data_reader is None:
                for w in self.data_actions:
                    w.setEnabled(False)
            else:
                reader = stradi.data_reader
                self.export_data_image_action.setEnabled(True)
                self.import_binary_image_action.setEnabled(True)
                self.import_data_image_action.setEnabled(True)
                self.export_full_action.setEnabled(reader.full_df is not None)
                self.export_final_action.setEnabled(reader.full_df is not None)
            for w in self.text_actions:
                w.setEnabled(stradi.colnames_reader is not None)
            for w in self.save_actions:
                w.setEnabled(True)

    def setup_children(self, item):
        tree = self.straditizer_widgets.tree

        # import menu
        import_child = QTreeWidgetItem(0)
        item.addChild(import_child)
        self.btn_import = QToolButton()
        self.btn_import.setText('Import images')
        self.btn_import.setMenu(self.import_images_menu)
        self.btn_import.setPopupMode(QToolButton.InstantPopup)
        tree.setItemWidget(import_child, 0, self.btn_import)

        # export menu
        export_child = QTreeWidgetItem(0)
        item.addChild(export_child)
        self.btn_export = QToolButton()
        self.btn_export.setText('Export images')
        self.btn_export.setMenu(self.export_images_menu)
        self.btn_export.setPopupMode(QToolButton.InstantPopup)
        tree.setItemWidget(export_child, 0, self.btn_export)
