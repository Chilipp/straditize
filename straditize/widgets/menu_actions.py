"""The main control widget for a straditizer
"""
import os
import os.path as osp
import pandas as pd
from itertools import chain
import datetime as dt
import six
from straditize.widgets import StraditizerControlBase
from psyplot_gui.compat.qtcompat import (
    with_qt5, QFileDialog, QMenu, QKeySequence, QDialog, QDialogButtonBox,
    QLineEdit, QToolButton, QIcon, QCheckBox, QHBoxLayout, QVBoxLayout, QLabel,
    QDesktopWidget)
from psyplot_gui.common import get_icon
import numpy as np
from PIL import Image

straditizer = None


class ExportDfDialog(QDialog):

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
        meta = self.stradi.valid_attrs.copy(True)
        meta.loc['exported'] = str(dt.datetime.now())
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
                self.df.to_csv(f)
        self.accept()

    @classmethod
    def export_df(cls, parent, df, straditizer, fname=None, exec_=True):
        """Open a dialog for exporting a DataFrame"""
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

    save_actions = data_actions = text_actions = []

    window_layout_action = None

    @property
    def all_actions(self):
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

        # image buttons
        self.export_images_menu = menu = QMenu('Straditizer image(s)')
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

        self.window_layout_action = main.window_layouts_menu.addAction(
            'Straditizer layout',
            self.straditizer_widgets.switch_to_straditizer_layout)

        self.save_actions = [self.export_full_image_action,
                             self.save_straditizer_action]
        self.data_actions = [self.export_data_image_action,
                             self.export_full_action,
                             self.export_final_action]
        self.text_actions = [self.export_text_image_action]

        self.widgets2disable = [self.load_stradi_action,
                                self.load_clipboard_action]

    def setup_shortcuts(self, main):
        """Setup the shortcuts when switched to the straditizer layout"""
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

    def open_straditizer(self, fname=None, *args, **kwargs):
        from straditize.straditizer import Straditizer
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getOpenFileName(
                self.straditizer_widgets, 'Straditizer project', os.getcwd(),
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
        if not fname:
            return
        elif fname.endswith('.nc') or fname.endswith('.nc4'):
            import xarray as xr
            ds = xr.open_dataset(fname)
            stradi = Straditizer.from_dataset(ds.load())
            stradi.set_attr('project_file', fname)
            ds.close()
        elif fname.endswith('.pkl'):
            stradi = Straditizer.load(fname, *args, **kwargs)
            stradi.set_attr('project_file', fname)
        else:
            from PIL import Image
            image = Image.open(fname)
            stradi = Straditizer(image, *args, **kwargs)
            stradi.set_attr('image_file', fname)
        self.finish_loading(stradi)

    def finish_loading(self, stradi):
        self.straditizer = stradi
        stradi.show_full_image()
        self.set_stradi_in_console()
        self.stack_zoom_window()
        self.straditizer_widgets.refresh()

    def stack_zoom_window(self):
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
        from PIL import ImageGrab
        from straditize.straditizer import Straditizer
        image = ImageGrab.grabclipboard()
        if np.shape(image)[-1] == 3:
            image.putalpha(255)
        stradi = Straditizer(image)
        return self.finish_loading(stradi)

    def save_straditizer(self):
        try:
            fname = self.straditizer.attrs.loc['project_file', 0]
        except KeyError:
            fname = None
        return self.save_straditizer_as(fname)

    def save_straditizer_as(self, fname=None):
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getSaveFileName(
                self.straditizer_widgets, 'Straditizer file destination',
                os.getcwd(),
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
            ds.to_netcdf(fname)

    def save_text_image(self, fname=None):
        self._save_image(self.straditizer.text_reader.image, fname)

    def save_full_image(self, fname=None):
        self._save_image(self.straditizer.image, fname)

    def save_data_image(self, fname=None):
        arr = np.tile(self.straditizer.data_reader.binary[:, :, np.newaxis],
                      (1, 1, 4))
        arr[..., 3] *= 255
        arr[..., :3] = 0
        image = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        self._save_image(image, fname)

    def set_stradi_in_console(self):
        from psyplot_gui.main import mainwindow
        global straditizer
        straditizer = self.straditizer
        if mainwindow is not None:
            mainwindow.console.kernel_manager.kernel.shell.run_code(
                'from %s import straditizer as stradi' % __name__)
        straditizer = None

    def _save_image(self, image, fname=None):
        if fname is None or not isinstance(fname, six.string_types):
            fname = QFileDialog.getSaveFileName(
                self.straditizer_widgets, 'Straditizer file destination',
                os.getcwd(),
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
        if not fname:
            return
        image.save(fname)

    def _export_df(self, df, fname=None):
        ExportDfDialog.export_df(self.straditizer_widgets, df,
                                 self.straditizer, fname)

    def export_final(self, fname=None):
        try:
            df = self.straditizer.final_df
        except Exception as e:
            self.straditizer_widgets.error_msg.showTraceback(
                e.message if six.PY2 else str(e))
        else:
            self._export_df(df, fname)

    def export_full(self, fname=None):
        self._export_df(self.straditizer.full_df, fname)

    def refresh(self):
        stradi = self.straditizer
        if stradi is None:
            for w in self.all_actions:
                w.setEnabled(False)
        else:
            if stradi.data_reader is None:
                for w in self.data_actions:
                    w.setEnabled(False)
            else:
                reader = stradi.data_reader
                self.export_data_image_action.setEnabled(True)
                self.export_full_action.setEnabled(reader.full_df is not None)
                self.export_final_action.setEnabled(reader.full_df is not None)
            for w in self.text_actions:
                w.setEnabled(stradi.text_reader is not None)
            for w in self.save_actions:
                w.setEnabled(True)
