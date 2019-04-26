"""A wdiget to select patterns in the image

The :class:`PatternSelectionWidget` is used by the
:class:`straditize.widget.selection_toolbar.SelectionToolbar` to select
patterns in the straditizer image

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
from __future__ import division
import numpy as np
import datetime as dt
from itertools import product
from psyplot_gui.common import DockMixin
from psyplot_gui.compat.qtcompat import (
    QWidget, Qt, with_qt5, QLabel, QHBoxLayout,
    QVBoxLayout, QPushButton, QGridLayout)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.widgets import RectangleSelector
from matplotlib.figure import Figure

if with_qt5:
    from PyQt5.QtWidgets import (
        QSizePolicy, QSlider, QGroupBox, QFormLayout, QProgressDialog)
else:
    from PyQt4.QtGui import (
        QSizePolicy, QSlider, QGroupBox, QFormLayout, QProgressDialog)


class EmbededMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, *args, **kwargs):
        fig = Figure(*args, **kwargs)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class PatternSelectionWidget(QWidget, DockMixin):
    """A wdiget to select patterns in the image

    This widget consist of an :class:`EmbededMplCanvas` to display the template
    for the pattern and uses the :func:`skimage.feature.match_template`
    function to identify it in the :attr:`arr`

    See Also
    --------
    straditize.widget.selection_toolbar.SelectionToolbar.start_pattern_selection
    """

    #: The template to look for in the :attr:`arr`
    template = None

    #: The selector to select the template in the original image
    selector = None

    #: The extents of the :attr:`template` in the original image
    template_extents = None

    #: The matplotlib artist of the :attr:`template` in the
    #: :attr:`template_fig`
    template_im = None

    #: The :class:`EmbededMplCanvas` to display the :attr:`template`
    template_fig = None

    axes = None

    #: A QSlider to set the threshold for the template correlation
    sl_thresh = None

    _corr_plot = None

    key_press_cid = None

    def __init__(self, arr, data_obj, remove_selection=False, *args, **kwargs):
        """
        Parameters
        ----------
        arr: np.ndarray of shape ``(Ny, Nx)``
            The labeled selection array
        data_obj: straditize.label_selection.LabelSelection
            The data object whose image shall be selected
        remove_selection: bool
            If True, remove the selection on apply
        """
        super(PatternSelectionWidget, self).__init__(*args, **kwargs)
        self.arr = arr
        self.data_obj = data_obj
        self.remove_selection = remove_selection
        self.template = None

        # the figure to show the template
        self.template_fig = EmbededMplCanvas()
        # the button to select the template
        self.btn_select_template = QPushButton('Select a template')
        self.btn_select_template.setCheckable(True)
        # the checkbox to allow fractions of the template
        self.fraction_box = QGroupBox('Template fractions')
        self.fraction_box.setCheckable(True)
        self.fraction_box.setChecked(False)
        self.fraction_box.setEnabled(False)
        self.sl_fraction = QSlider(Qt.Horizontal)
        self.lbl_fraction = QLabel('0.75')
        self.sl_fraction.setValue(75)
        # the slider to select the increments of the fractions
        self.sl_increments = QSlider(Qt.Horizontal)
        self.sl_increments.setValue(3)
        self.sl_increments.setMinimum(1)
        self.lbl_increments = QLabel('3')
        # the button to perform the correlation
        self.btn_correlate = QPushButton('Find template')
        self.btn_correlate.setEnabled(False)
        # the button to plot the correlation
        self.btn_plot_corr = QPushButton('Plot correlation')
        self.btn_plot_corr.setCheckable(True)
        self.btn_plot_corr.setEnabled(False)
        # slider for subselection
        self.btn_select = QPushButton('Select pattern')
        self.sl_thresh = QSlider(Qt.Horizontal)
        self.lbl_thresh = QLabel('0.5')

        self.btn_select.setCheckable(True)
        self.btn_select.setEnabled(False)
        self.sl_thresh.setValue(75)
        self.sl_thresh.setVisible(False)
        self.lbl_thresh.setVisible(False)

        # cancel and close button
        self.btn_cancel = QPushButton('Cancel')
        self.btn_close = QPushButton('Apply')
        self.btn_close.setEnabled(False)

        vbox = QVBoxLayout()

        vbox.addWidget(self.template_fig)
        hbox = QHBoxLayout()
        hbox.addStretch(0)
        hbox.addWidget(self.btn_select_template)
        vbox.addLayout(hbox)

        fraction_layout = QGridLayout()
        fraction_layout.addWidget(QLabel('Fraction'), 0, 0)
        fraction_layout.addWidget(self.sl_fraction, 0, 1)
        fraction_layout.addWidget(self.lbl_fraction, 0, 2)
        fraction_layout.addWidget(QLabel('Increments'), 1, 0)
        fraction_layout.addWidget(self.sl_increments, 1, 1)
        fraction_layout.addWidget(self.lbl_increments, 1, 2)

        self.fraction_box.setLayout(fraction_layout)

        vbox.addWidget(self.fraction_box)
        vbox.addWidget(self.btn_correlate)
        vbox.addWidget(self.btn_plot_corr)
        vbox.addWidget(self.btn_select)
        thresh_box = QHBoxLayout()
        thresh_box.addWidget(self.sl_thresh)
        thresh_box.addWidget(self.lbl_thresh)
        vbox.addLayout(thresh_box)

        hbox = QHBoxLayout()
        hbox.addWidget(self.btn_cancel)
        hbox.addWidget(self.btn_close)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        self.btn_select_template.clicked.connect(
            self.toggle_template_selection)
        self.sl_fraction.valueChanged.connect(
            lambda i: self.lbl_fraction.setText(str(i / 100.)))
        self.sl_increments.valueChanged.connect(
            lambda i: self.lbl_increments.setText(str(i)))
        self.btn_correlate.clicked.connect(self.start_correlation)
        self.btn_plot_corr.clicked.connect(self.toggle_correlation_plot)
        self.sl_thresh.valueChanged.connect(
            lambda i: self.lbl_thresh.setText(str((i - 50) / 50.)))
        self.sl_thresh.valueChanged.connect(self.modify_selection)
        self.btn_select.clicked.connect(
            self.toggle_selection)

        self.btn_cancel.clicked.connect(self.cancel)
        self.btn_close.clicked.connect(self.remove_plugin)

    def toggle_template_selection(self):
        """Enable or disable the template selection"""
        if (not self.btn_select_template.isChecked() and
                self.selector is not None):
            self.selector.set_active(False)
            for a in self.selector.artists:
                a.set_visible(False)
            self.btn_select_template.setText('Select a template')
        elif self.selector is not None and self.template_im is not None:
            self.selector.set_active(True)
            for a in self.selector.artists:
                a.set_visible(True)
            self.btn_select_template.setText('Apply')
        else:
            self.selector = RectangleSelector(
                self.data_obj.ax, self.update_image, interactive=True)
            if self.template_extents is not None:
                self.selector.draw_shape(self.template_extents)
            self.key_press_cid = self.data_obj.ax.figure.canvas.mpl_connect(
                'key_press_event', self.update_image)
            self.btn_select_template.setText('Cancel')
        self.data_obj.draw_figure()
        if self.template is not None:
            self.fraction_box.setEnabled(True)
            self.sl_increments.setMaximum(min(self.template.shape[:2]))
            self.btn_correlate.setEnabled(True)

    def update_image(self, *args, **kwargs):
        """Update the template image based on the :attr:`selector` extents"""
        if self.template_im is not None:
            self.template_im.remove()
            del self.template_im
        elif self.axes is None:
            self.axes = self.template_fig.figure.add_subplot(111)
            self.template_fig.figure.subplots_adjust(bottom=0.3)
        if not self.selector.artists[0].get_visible():
            self.template_extents = None
            self.template = None
            self.btn_select_template.setText('Cancel')
        else:
            self.template_extents = np.round(self.selector.extents).astype(int)
            x, y = self.template_extents.reshape((2, 2))
            if getattr(self.data_obj, 'extent', None) is not None:
                extent = self.data_obj.extent
                x -= int(min(extent[:2]))
                y -= int(min(extent[2:]))
            slx = slice(*sorted(x))
            sly = slice(*sorted(y))
            self.template = template = self.arr[sly, slx]
            if template.ndim == 3:
                self.template_im = self.axes.imshow(template)
            else:
                self.template_im = self.axes.imshow(template, cmap='binary')
            self.btn_select_template.setText('Apply')
        self.template_fig.draw()

    def start_correlation(self):
        """Look for the correlations of template and source"""
        if self.fraction_box.isChecked():
            self._fraction = self.sl_fraction.value() / 100.
            increments = self.sl_increments.value()
        else:
            self._fraction = 0
            increments = 1
        corr = self.correlate_template(
            self.arr, self.template, self._fraction, increments)
        if corr is not None:
            self._correlation = corr
        enable = self._correlation is not None
        self.btn_plot_corr.setEnabled(enable)
        self.btn_select.setEnabled(enable)

    def toggle_selection(self):
        """Modifiy the selection (or not) based on the template correlation"""
        obj = self.data_obj
        if self.btn_select.isChecked():
            self._orig_selection_arr = obj._selection_arr.copy()
            self._selected_labels = obj.selected_labels
            self._select_cmap = obj._select_cmap
            self._select_norm = obj._select_norm
            self.btn_select.setText('Reset')
            self.btn_close.setEnabled(True)
            obj.unselect_all_labels()
            self.sl_thresh.setVisible(True)
            self.lbl_thresh.setVisible(True)
            self.modify_selection(self.sl_thresh.value())
        else:
            if obj._selection_arr is not None:
                obj._selection_arr[:] = self._orig_selection_arr
                obj._select_img.set_array(self._orig_selection_arr)
                obj.select_labels(self._selected_labels)
                obj._update_magni_img()
            del self._orig_selection_arr, self._selected_labels
            self.btn_select.setText('Select pattern')
            self.btn_close.setEnabled(False)
            self.sl_thresh.setVisible(False)
            self.lbl_thresh.setVisible(False)
            obj.draw_figure()

    def modify_selection(self, i):
        """Modify the selection based on the correlation threshold

        Parameters
        ----------
        i: int
            An integer between 0 and 100, the value of the :attr:`sl_thresh`
            slider"""
        if not self.btn_select.isChecked():
            return
        obj = self.data_obj
        val = (i - 50.) / 50.
        # select the values above 50
        if not self.remove_selection:
            # clear the selection
            obj._selection_arr[:] = obj._orig_selection_arr.copy()
            select_val = obj._selection_arr.max() + 1
            obj._selection_arr[self._correlation >= val] = select_val
        else:
            obj._selection_arr[:] = self._orig_selection_arr.copy()
            obj._selection_arr[self._correlation >= val] = -1
        obj._select_img.set_array(obj._selection_arr)
        obj._update_magni_img()
        obj.draw_figure()

    def correlate_template(self, arr, template, fraction=False, increment=1,
                           report=True):
        """Correlate a template with the `arr`

        This method uses the :func:`skimage.feature.match_template` function
        to find the given `template` in the source array `arr`.

        Parameters
        ----------
        arr: np.ndarray of shape ``(Ny,Nx)``
            The labeled selection array (see :attr:`arr`), the source of the
            given `template`
        template: np.ndarray of shape ``(nx, ny)``
            The template from ``arr`` that shall be searched
        fraction: float
            If not null, we will look through the given fraction of the
            template to look for partial matches as well
        increment: int
            The increment of the loop with the `fraction`.
        report: bool
            If True and `fraction` is not null, a QProgressDialog is opened
            to inform the user about the progress"""
        from skimage.feature import match_template
        mask = self.data_obj.selected_part
        x = mask.any(axis=0)
        if not x.any():
            raise ValueError("No data selected!")
        y = mask.any(axis=1)
        xmin = x.argmax()
        xmax = len(x) - x[::-1].argmax()
        ymin = y.argmax()
        ymax = len(y) - y[::-1].argmax()
        if arr.ndim == 3:
            mask = np.tile(mask[..., np.newaxis], (1, 1, arr.shape[-1]))
        src = np.where(mask[ymin:ymax, xmin:xmax],
                       arr[ymin:ymax, xmin:xmax], 0)
        sny, snx = src.shape
        if not fraction:
            corr = match_template(src, template)
            full_shape = np.array(corr.shape)
        else:  # loop through the template to allow partial hatches
            shp = np.array(template.shape, dtype=int)[:2]
            ny, nx = shp
            fshp = np.round(fraction * shp).astype(int)
            fny, fnx = fshp
            it = list(product(
                range(0, fny, increment), range(0, fnx, increment)))
            ntot = len(it)
            full_shape = fshp - shp + src.shape
            corr = np.zeros(full_shape, dtype=float)
            if report:
                txt = 'Searching template...'
                dialog = QProgressDialog(txt, 'Cancel',
                                         0, ntot)
                dialog.setWindowModality(Qt.WindowModal)
                t0 = dt.datetime.now()
            for k, (i, j) in enumerate(it):
                if report:
                    dialog.setValue(k)
                    if k and not k % 10:
                        passed = (dt.datetime.now() - t0).total_seconds()
                        dialog.setLabelText(
                            txt + ' %1.0f seconds remaning' % (
                                (passed * (ntot / k - 1.))))
                if report and dialog.wasCanceled():
                    return
                else:
                    y_end, x_start = fshp - (i, j) - 1
                    sly = slice(y_end, full_shape[0])
                    slx = slice(0, -x_start or full_shape[1])
                    corr[sly, slx] = np.maximum(
                        corr[sly, slx],
                        match_template(src, template[:-i or ny, j:]))
        ret = np.zeros_like(arr, dtype=corr.dtype)
        dny, dnx = src.shape - full_shape
        for i, j in product(range(dny + 1), range(dnx + 1)):
            ret[ymin + i:ymax - dny + i, xmin + j:xmax - dnx + j] = np.maximum(
                ret[ymin + i:ymax - dny + i, xmin + j:xmax - dnx + j], corr)
        return np.where(mask, ret, 0)

    def toggle_correlation_plot(self):
        """Toggle the correlation plot between :attr:`template` and :attr:`arr`
        """
        obj = self.data_obj
        if self._corr_plot is None:
            self._corr_plot = obj.ax.imshow(
                self._correlation, extent=obj._select_img.get_extent(),
                zorder=obj._select_img.zorder + 0.1)
            self._corr_cbar = obj.ax.figure.colorbar(
                self._corr_plot, orientation='vertical')
            self._corr_cbar.set_label('Correlation')
        else:
            for a in [self._corr_cbar, self._corr_plot]:
                try:
                    a.remove()
                except ValueError:
                    pass
            del self._corr_plot, self._corr_cbar
        obj.draw_figure()

    def to_dock(self, main, title=None, position=None, docktype='df', *args,
                **kwargs):
        if position is None:
            position = main.dockWidgetArea(main.help_explorer.dock)
        connect = self.dock is None
        ret = super(PatternSelectionWidget, self).to_dock(
            main, title, position, docktype=docktype, *args, **kwargs)
        if connect:
            self.dock.toggleViewAction().triggered.connect(self.maybe_tabify)
        return ret

    def maybe_tabify(self):
        main = self.dock.parent()
        if self.is_shown and main.dockWidgetArea(
                main.help_explorer.dock) == main.dockWidgetArea(self.dock):
            main.tabifyDockWidget(main.help_explorer.dock, self.dock)

    def cancel(self):
        if self.btn_select.isChecked():
            self.btn_select.setChecked(False)
            self.toggle_selection()
        self.remove_plugin()

    def remove_plugin(self):
        from psyplot_gui.main import mainwindow
        if self.selector is not None:
            self.selector.disconnect_events()
            for a in self.selector.artists:
                try:
                    a.remove()
                except ValueError:
                    pass
            self.data_obj.draw_figure()
            del self.selector
        if self._corr_plot is not None:
            self.toggle_correlation_plot()
        if self.key_press_cid is not None:
            self.data_obj.ax.figure.canvas.mpl_disconnect(self.key_press_cid)
        try:
            self.template_im.remove()
        except (AttributeError, ValueError):
            pass
        try:
            self.template_fig.delaxes(self.axes)
        except (AttributeError, ValueError, RuntimeError):
            pass
        try:
            self.template_fig.close()
        except (AttributeError, RuntimeError):
            pass
        for attr in ['data_obj', 'arr', 'template', 'key_press_cid',
                     '_orig_selection_arr', '_selected_labels', '_select_cmap',
                     '_select_norm', '_correlation', 'axes', 'template_fig',
                     'template_im']:
            try:
                delattr(self, attr)
            except AttributeError:
                pass
        try:
            super().remove_plugin()
        except RuntimeError:  # already removed
            pass
        if self.dock is not None:
            try:
                mainwindow.dockwidgets.remove(self.dock)
            except (ValueError, AttributeError):
                pass
            del self.dock
