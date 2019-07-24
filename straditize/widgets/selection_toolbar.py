"""Module for the selection toolbar

This module defines the selection toolbar that is added to the
:class:`psyplot_gui.main.MainWindow` for selecting features in the
stratigraphic diagram and the data reader image.

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
from itertools import chain
import six
import numpy as np
from straditize.widgets import get_icon, StraditizerControlBase, InfoButton
from psyplot_gui.compat.qtcompat import (
    QIcon, QtCore, QComboBox, QToolBar, with_qt5, QMenu, Qt, QLabel,
    QCheckBox)
from matplotlib.backend_tools import cursors
import matplotlib.widgets as mwid
import matplotlib.path as mplp

if with_qt5:
    from PyQt5.QtWidgets import QActionGroup, QSlider
else:
    from PyQt4.QtGui import QActionGroup, QSlider


class PointOrRectangleSelector(mwid.RectangleSelector):
    """RectangleSelector that allows to select points

    This class reimplements the :class:`matplotlib.widgets.RectangleSelector`
    to select points"""

    def press(self, *args, **kwargs):
        ret = super(PointOrRectangleSelector, self).press(*args, **kwargs)
        if self.eventpress is not None:
            x = self.eventpress.xdata
            y = self.eventpress.ydata
            self.extents = x, x, y, y
        return ret


class SelectionToolbar(QToolBar, StraditizerControlBase):
    """A toolbar for selecting features in the straditizer and data image

    The current data object is set in the :attr:`combo` and can be accessed
    through the :attr:`data_obj` attribute. It's either the straditizer or the
    data_reader that is accessed"""

    _idPress = None

    _idRelease = None

    #: A signal that is emitted when something is selected
    selected = QtCore.pyqtSignal()

    set_cursor_id = None

    reset_cursor_id = None

    #: The QCombobox that defines the data object to be used
    combo = None

    @property
    def ax(self):
        """The :class:`matplotlib.axes.Axes` of the :attr:`data_obj`"""
        return self.data_obj.ax

    @property
    def data(self):
        """The np.ndarray of the :attr:`data_obj` image"""
        text = self.combo.currentText()
        if text == 'Reader':
            return self.straditizer.data_reader.binary
        elif text == 'Reader - Greyscale':
            return self.straditizer.data_reader.to_grey_pil(
                self.straditizer.data_reader.image)
        else:
            from straditize.binary import DataReader
            return DataReader.to_grey_pil(self.straditizer.image)

    @property
    def data_obj(self):
        """The data object as set in the :attr:`combo`.

        Either a :class:`~straditize.straditizer.Straditizer` or a
        :class:`straditize.binary.DataReader` instance. """
        text = self.combo.currentText()
        if text in ['Reader', 'Reader - Greyscale']:
            return self.straditizer.data_reader
        else:
            return self.straditizer

    @data_obj.setter
    def data_obj(self, value):
        """The data object as set in the :attr:`combo`.

        Either a :class:`~straditize.straditizer.Straditizer` or a
        :class:`straditize.binary.DataReader` instance. """
        if self.straditizer is None:
            return
        if isinstance(value, six.string_types):
            possible_values = {
                self.combo.itemText(i) for i in range(self.combo.count())}
            if value not in possible_values:
                raise ValueError(
                    'Do not understand %r! Please use one of %r' % (
                        value, possible_values))
            else:
                self.combo.setCurrentText(value)
        else:
            if value is self.straditizer:
                self.combo.setCurrentText('Straditizer')
            elif value and value is self.straditizer.data_reader:
                self.combo.setCurrentText('Reader')
            else:
                raise ValueError('Do not understand %r! Please either use '
                                 'the Straditizer or DataReader instance!' % (
                                     value, ))

    @property
    def fig(self):
        """The :class:`~matplotlib.figure.Figure` of the :attr:`data_obj`"""
        try:
            return self.ax.figure
        except AttributeError:
            return None

    @property
    def canvas(self):
        """The canvas of the :attr:`data_obj`"""
        try:
            return self.fig.canvas
        except AttributeError:
            return None

    @property
    def toolbar(self):
        """The toolbar of the :attr:`canvas`"""
        return self.canvas.toolbar

    @property
    def select_action(self):
        """The rectangle selection tool"""
        return self._actions['select']

    @property
    def wand_action(self):
        """The wand selection tool"""
        return self._actions['wand_select']

    @property
    def new_select_action(self):
        """The action to make new selection with one of the selection tools"""
        return self._type_actions['new_select']

    @property
    def add_select_action(self):
        """The action to add to the current selection with the selection tools
        """
        return self._type_actions['add_select']

    @property
    def remove_select_action(self):
        """
        An action to remove from the current selection with the selection tools
        """
        return self._type_actions['remove_select']

    @property
    def select_all_action(self):
        """An action to select all features in the :attr:`data`"""
        return self._actions['select_all']

    @property
    def expand_select_action(self):
        """An action to expand the current selection to the full feature"""
        return self._actions['expand_select']

    @property
    def invert_select_action(self):
        """An action to invert the current selection"""
        return self._actions['invert_select']

    @property
    def clear_select_action(self):
        """An action to clear the current selection"""
        return self._actions['clear_select']

    @property
    def select_right_action(self):
        """An action to select everything in the data column to the right"""
        return self._actions['select_right']

    @property
    def select_pattern_action(self):
        """An action to start a pattern selection"""
        return self._actions['select_pattern']

    @property
    def widgets2disable(self):
        if not self._actions:
            return []
        elif self._selecting:
            return [self.combo]
        else:
            return list(chain([self.combo],
                              self._actions.values(),
                              self._appearance_actions.values()))

    @property
    def labels(self):
        """The labeled data that is displayed"""
        if self.data_obj._selection_arr is not None:
            return self.data_obj._selection_arr
        text = self.combo.currentText()
        if text == 'Reader':
            return self.straditizer.data_reader.labels.copy()
        elif text == 'Reader - Greyscale':
            return self.straditizer.data_reader.color_labels()
        else:
            return self.straditizer.get_labels()

    @property
    def rect_callbacks(self):
        """The functions to call after the rectangle selection.

        If not set manually, it is the :meth:`select_rect` method. Note that
        this is cleared at every call of the :meth:`end_selection`.

        Callables in this list must accept two arguments ``(slx, sly)``:
        the first one is the x-slice, and the second one the y-slice. They both
        correspond to the :attr:`data` attribute."""
        return self._rect_callbacks or [self.select_rect]

    @rect_callbacks.setter
    def rect_callbacks(self, value):
        """The functions to call after the rectangle selection.

        If not set manually, it is the :meth:`select_rect` method. Note that
        this is cleared at every call of the :meth:`end_selection`.

        Callables in this list must accept two arguments ``(slx, sly)``:
        the first one is the x-slice, and the second one the y-slice. They both
        correspond to the :attr:`data` attribute."""
        self._rect_callbacks = value

    @property
    def poly_callbacks(self):
        """The functions to call after the polygon selection

        If not set manually, it is the :meth:`select_poly` method. Note that
        this is cleared at every call of the :meth:`end_selection`.

        Callables in this list must accept one argument, a ``np.ndarray``
        of shape ``(N, 2)``. This array defines the ``N`` x- and y-coordinates
        of the points of the polygon"""
        return self._poly_callbacks or [self.select_poly]

    @poly_callbacks.setter
    def poly_callbacks(self, value):
        """The functions to call after the polygon selection.

        If not set manually, it is the :meth:`poly_callbacks` method. Note that
        this is cleared at every call of the :meth:`end_selection`.

        Callables in this list must accept one argument, a ``np.ndarray``
        of shape ``(N, 2)``. This array defines the ``N`` x- and y-coordinates
        of the points of the polygon"""
        self._poly_callbacks = value

    #: A :class:`PointOrRectangleSelector` to select features in the image
    selector = None

    _pattern_selection = None

    def __init__(self, straditizer_widgets, *args, **kwargs):
        super(SelectionToolbar, self).__init__(*args, **kwargs)
        self._actions = {}
        self._wand_actions = {}
        self._pattern_actions = {}
        self._select_actions = {}
        self._appearance_actions = {}
        # Boolean that is True if we are in a selection process
        self._selecting = False
        self.init_straditizercontrol(straditizer_widgets)
        self._ids_select = []
        self._rect_callbacks = []
        self._poly_callbacks = []
        self._selection_mode = None
        self._lastCursor = None
        self.create_actions()
        self._changed_selection = False
        self._connected = []
        self._action_clicked = None
        self.wand_type = 'labels'
        self.select_type = 'rect'
        self.pattern_type = 'binary'
        self.auto_expand = False

    def create_actions(self):
        """Define the actions for the toolbar and set everything up"""
        # Reader toolbar
        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.addWidget(self.combo)

        select_group = QActionGroup(self)

        # select action
        self._actions['select'] = a = self.addAction(
            QIcon(get_icon('select.png')), 'select', self.toggle_selection)
        a.setToolTip('Select pixels within a rectangle')
        a.setCheckable(True)
        select_group.addAction(a)

        # select menu
        select_menu = QMenu(self)
        self._select_actions['rect_select'] = menu_a = select_menu.addAction(
            QIcon(get_icon('select.png')), 'rectangle',
            self.set_rect_select_mode)
        menu_a.setToolTip('Select a rectangle')
        a.setToolTip(menu_a.toolTip())

        self._select_actions['poly_select'] = menu_a = select_menu.addAction(
            QIcon(get_icon('poly_select.png')), 'polygon',
            self.set_poly_select_mode)
        menu_a.setToolTip('Select a rectangle')
        a.setToolTip(menu_a.toolTip())

        a.setMenu(select_menu)

        # wand_select action
        self._actions['wand_select'] = a = self.addAction(
            QIcon(get_icon('wand_select.png')), 'select',
            self.toggle_selection)
        a.setCheckable(True)
        select_group.addAction(a)

        # wand menu
        tool_menu = QMenu(self)
        self._wand_actions['wand_select'] = menu_a = tool_menu.addAction(
            QIcon(get_icon('wand_select.png')), 'wand',
            self.set_label_wand_mode)
        menu_a.setToolTip('Select labels within a rectangle')
        a.setToolTip(menu_a.toolTip())

        self._wand_actions['color_select'] = menu_a = tool_menu.addAction(
            QIcon(get_icon('color_select.png')), 'color wand',
            self.set_color_wand_mode)
        menu_a.setToolTip('Select colors')

        self._wand_actions['row_select'] = menu_a = tool_menu.addAction(
            QIcon(get_icon('row_select.png')), 'row selection',
            self.set_row_wand_mode)
        menu_a.setToolTip('Select pixel rows')

        self._wand_actions['col_select'] = menu_a = tool_menu.addAction(
            QIcon(get_icon('col_select.png')), 'column selection',
            self.set_col_wand_mode)
        menu_a.setToolTip('Select pixel columns')

        a.setMenu(tool_menu)

        # color_wand widgets
        self.distance_slider = slider = QSlider(Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(255)
        slider.setValue(30)
        slider.setSingleStep(1)

        self.lbl_slider = QLabel('30')
        slider.valueChanged.connect(lambda i: self.lbl_slider.setText(str(i)))
        slider.setMaximumWidth(self.combo.sizeHint().width())

        self.cb_whole_fig = QCheckBox('Whole plot')
        self.cb_whole_fig.setToolTip('Select the colors on the entire plot')

        self.cb_use_alpha = QCheckBox('Use alpha')
        self.cb_use_alpha.setToolTip('Use the alpha channel, i.e. the '
                                     'transparency of the RGBA image.')

        self.color_wand_actions = [
                self.addWidget(slider), self.addWidget(self.lbl_slider),
                self.addWidget(self.cb_whole_fig),
                self.addWidget(self.cb_use_alpha)]

        self.set_label_wand_mode()

        self.addSeparator()
        type_group = QActionGroup(self)

        self._type_actions = {}

        # new selection action
        self._type_actions['new_select'] = a = self.addAction(
            QIcon(get_icon('new_selection.png')), 'Create a new selection')
        a.setToolTip('Select pixels within a rectangle and ignore the current '
                     'selection')
        a.setCheckable(True)
        type_group.addAction(a)

        # add to selection action
        self._type_actions['add_select'] = a = self.addAction(
            QIcon(get_icon('add_select.png')), 'Add to selection')
        a.setToolTip('Select pixels within a rectangle and add them to the '
                     'current selection')
        a.setCheckable(True)
        type_group.addAction(a)

        # remove action
        self._type_actions['remove_select'] = a = self.addAction(
            QIcon(get_icon('remove_select.png')), 'Remove from selection')
        a.setToolTip('Select pixels within a rectangle and remove them from '
                     'the current selection')
        a.setCheckable(True)
        type_group.addAction(a)

        # info button
        self.addSeparator()
        self.info_button = InfoButton(self, 'selection_toolbar.rst')
        self.addWidget(self.info_button)

        # selection appearence options
        self.addSeparator()
        self.sl_alpha = slider = QSlider(Qt.Horizontal)
        self._appearance_actions['alpha'] = self.addWidget(slider)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(100)
        slider.setSingleStep(1)

        self.lbl_alpha_slider = QLabel('100 %')
        slider.valueChanged.connect(
            lambda i: self.lbl_alpha_slider.setText(str(i) + ' %'))
        slider.valueChanged.connect(self.update_alpha)
        slider.setMaximumWidth(self.combo.sizeHint().width())

        # Select all and invert selection buttons
        self.addSeparator()
        self._actions['select_all'] = a = self.addAction(
            QIcon(get_icon('select_all.png')), 'all', self.select_all)
        a.setToolTip('Select all labels')

        self._actions['expand_select'] = a = self.addAction(
            QIcon(get_icon('expand_select.png')), 'expand',
            self.expand_selection)
        a.setToolTip('Expand the selected areas to select the entire feature')

        self._actions['invert_select'] = a = self.addAction(
            QIcon(get_icon('invert_select.png')), 'invert',
            self.invert_selection)
        a.setToolTip('Invert selection')

        self._actions['clear_select'] = a = self.addAction(
            QIcon(get_icon('clear_select.png')), 'clear',
            self.clear_selection)
        a.setToolTip('Clear selection')

        self._actions['select_right'] = a = self.addAction(
            QIcon(get_icon('select_right.png')), 'right',
            self.select_everything_to_the_right)
        a.setToolTip('Select everything to the right of each column')

        self._actions['select_pattern'] = a = self.addAction(
            QIcon(get_icon('pattern.png')), 'pattern',
            self.start_pattern_selection)
        a.setCheckable(True)
        a.setToolTip(
            'Select a binary pattern/hatch within the current selection')

        # wand menu
        pattern_menu = QMenu(self)
        self._pattern_actions['binary'] = menu_a = pattern_menu.addAction(
            QIcon(get_icon('pattern.png')), 'Binary',
            self.set_binary_pattern_mode)
        menu_a.setToolTip(
            'Select a binary pattern/hatch within the current selection')
        a.setToolTip(menu_a.toolTip())

        self._pattern_actions['grey'] = menu_a = pattern_menu.addAction(
            QIcon(get_icon('pattern_grey.png')), 'Greyscale',
            self.set_grey_pattern_mode)
        menu_a.setToolTip(
            'Select a pattern/hatch within the current selection based on '
            'grey scale colors')

        a.setMenu(pattern_menu)

        self.new_select_action.setChecked(True)
        for a in self._type_actions.values():
            a.toggled.connect(self.add_or_remove_pattern)

        self.refresh()

    def should_be_enabled(self, w):
        if self.straditizer is None:
            return False
        elif (self._actions and
              w in [self.remove_select_action, self.invert_select_action,
                    self.clear_select_action, self.expand_select_action,
                    self.select_right_action] and
              not self._selecting):
            return False
        elif w in self._appearance_actions.values() and not self._selecting:
            return False
        elif (self.combo and not self.combo.currentText().startswith('Reader')
              and w is self.select_right_action):
            return False
        return True

    def disable_actions(self):
        if self._changed_selection:
            return
        for a in self._actions.values():
            if a.isChecked():
                a.setChecked(False)
                self.toggle_selection()
            else:
                a.setChecked(False)

    def select_all(self):
        """Select all features in the image

        See Also
        --------
        straditize.label_selection.LabelSelection.select_all_labels"""
        obj = self.data_obj
        if obj._selection_arr is None:
            rgba = obj.image_array() if hasattr(obj, 'image_array') else None
            self.start_selection(self.labels, rgba=rgba)
        obj.select_all_labels()
        self.canvas.draw()

    def invert_selection(self):
        """Invert the current selection"""
        obj = self.data_obj
        if obj._selection_arr is None:
            rgba = obj.image_array() if hasattr(obj, 'image_array') else None
            self.start_selection(self.labels, rgba=rgba)
        if (obj._selection_arr != obj._orig_selection_arr).any():
            selection = obj.selected_part

            # clear the current selection
            obj._selection_arr[:] = np.where(
                obj._selection_arr.astype(bool) & (~selection),
                obj._orig_selection_arr.max() + 1, obj._orig_selection_arr)
            obj._select_img.set_array(obj._selection_arr)
            obj.unselect_all_labels()
        else:
            obj.select_all_other_labels()
        self.canvas.draw()

    def clear_selection(self):
        """Clear the current selection"""
        obj = self.data_obj
        if obj._selection_arr is None:
            return
        obj._selection_arr[:] = obj._orig_selection_arr.copy()
        obj._select_img.set_array(obj._selection_arr)
        obj.unselect_all_labels()
        self.canvas.draw()

    def expand_selection(self):
        """Expand the selected areas to select the full labels"""
        obj = self.data_obj
        if obj._selection_arr is None:
            return
        arr = obj._orig_selection_arr.copy()
        selected_labels = np.unique(arr[obj.selected_part])
        obj._selection_arr = arr
        obj._select_img.set_array(arr)
        obj.unselect_all_labels()
        obj.select_labels(selected_labels)
        self.canvas.draw()

    def update_alpha(self, i):
        """Set the transparency of the selection image

        Parameters
        ----------
        i: int
            The transparency between 0 and 100"""
        self.data_obj._select_img.set_alpha(i / 100.)
        self.data_obj._update_magni_img()
        self.canvas.draw()

    def select_everything_to_the_right(self):
        """Selects everything to the right of the current selection"""
        reader = self.data_obj
        if reader._selection_arr is None:
            return
        bounds = reader.column_bounds
        selection = reader.selected_part
        new_select = np.zeros_like(selection)
        for start, end in bounds:
            can_be_selected = reader._selection_arr[:, start:end].astype(bool)
            end = start + can_be_selected.shape[1]
            last_in_row = selection[:, start:end].argmax(axis=-1).reshape(
                (-1, 1))
            dist2start = np.tile(np.arange(end - start)[np.newaxis],
                                 (len(selection), 1))
            can_be_selected[dist2start <= last_in_row] = False
            can_be_selected[~np.tile(last_in_row.astype(bool),
                                     (1, end - start))] = False
            new_select[:, start:end] = can_be_selected
        max_label = reader._orig_selection_arr.max()
        reader._selection_arr[new_select] = max_label + 1
        reader._select_img.set_array(reader._selection_arr)
        reader._update_magni_img()
        self.canvas.draw()

    def start_pattern_selection(self):
        """Open the pattern selection dialog

        This method will enable the pattern selection by starting a
        :class:`straditize.widgets.pattern_selection.PatternSelectionWidget`"""
        from straditize.widgets.pattern_selection import PatternSelectionWidget
        if self.select_pattern_action.isChecked():
            from straditize.binary import DataReader
            from psyplot_gui.main import mainwindow
            obj = self.data_obj
            if obj._selection_arr is None:
                if hasattr(obj, 'image_array'):
                    rgba = obj.image_array()
                else:
                    rgba = None
                self.start_selection(self.labels, rgba=rgba)
                self.select_all()
            if not obj.selected_part.any():
                self.select_pattern_action.setChecked(False)
                raise ValueError(
                    "No data in the image is selected. Please select the "
                    "coarse region in which the pattern should be searched.")
            if self.pattern_type == 'binary':
                arr = DataReader.to_binary_pil(obj.image)
            else:
                arr = DataReader.to_grey_pil(obj.image)
            self._pattern_selection = w = PatternSelectionWidget(
                arr, obj)
            w.to_dock(mainwindow, 'Pattern selection')
            w.btn_close.clicked.connect(self.uncheck_pattern_selection)
            w.btn_cancel.clicked.connect(self.uncheck_pattern_selection)
            self.disable_actions()
            pattern_action = self.select_pattern_action
            for a in self._actions.values():
                a.setEnabled(False)
            pattern_action.setEnabled(True)
            pattern_action.setChecked(True)
            w.show_plugin()
            w.maybe_tabify()
            w.raise_()
        elif self._pattern_selection is not None:
            self._pattern_selection.cancel()
            self.uncheck_pattern_selection()
            del self._pattern_selection

    def uncheck_pattern_selection(self):
        """Disable the pattern selection"""
        self.select_pattern_action.setChecked(False)
        del self._pattern_selection
        for a in self._actions.values():
            a.setEnabled(self.should_be_enabled(a))

    def add_or_remove_pattern(self):
        """Enable the removing or adding of the pattern selection"""
        if getattr(self, '_pattern_selection', None) is None:
            return
        current = self._pattern_selection.remove_selection
        new = self.remove_select_action.isChecked()
        if new is not current:
            self._pattern_selection.remove_selection = new
            if self._pattern_selection.btn_select.isChecked():
                self._pattern_selection.modify_selection(
                    self._pattern_selection.sl_thresh.value())

    def set_rect_select_mode(self):
        """Set the current wand tool to the color wand"""
        self.select_type = 'rect'
        self.select_action.setIcon(QIcon(get_icon('select.png')))
        self._action_clicked = None
        self.toggle_selection()

    def set_poly_select_mode(self):
        """Set the current wand tool to the color wand"""
        self.select_type = 'poly'
        self.select_action.setIcon(QIcon(get_icon('poly_select.png')))
        self._action_clicked = None
        self.toggle_selection()

    def set_label_wand_mode(self):
        """Set the current wand tool to the color wand"""
        self.wand_type = 'labels'
        self.wand_action.setIcon(QIcon(get_icon('wand_select.png')))
        for a in self.color_wand_actions:
            a.setVisible(False)
        self._action_clicked = None
        self.toggle_selection()

    def set_color_wand_mode(self):
        """Set the current wand tool to the color wand"""
        self.wand_type = 'color'
        self.wand_action.setIcon(QIcon(get_icon('color_select.png')))
        for a in self.color_wand_actions:
            a.setVisible(True)
        self._action_clicked = None
        self.toggle_selection()

    def set_row_wand_mode(self):
        """Set the current wand tool to the color wand"""
        self.wand_type = 'rows'
        self.wand_action.setIcon(QIcon(get_icon('row_select.png')))
        for a in self.color_wand_actions:
            a.setVisible(False)
        self._action_clicked = None
        self.toggle_selection()

    def set_col_wand_mode(self):
        """Set the current wand tool to the color wand"""
        self.wand_type = 'cols'
        self.wand_action.setIcon(QIcon(get_icon('col_select.png')))
        for a in self.color_wand_actions:
            a.setVisible(False)
        self._action_clicked = None
        self.toggle_selection()

    def set_binary_pattern_mode(self):
        """Set the current pattern mode to the binary pattern"""
        self.pattern_type = 'binary'
        self.select_pattern_action.setIcon(QIcon(get_icon('pattern.png')))

    def set_grey_pattern_mode(self):
        """Set the current pattern mode to the binary pattern"""
        self.pattern_type = 'grey'
        self.select_pattern_action.setIcon(QIcon(get_icon('pattern_grey.png')))

    def disconnect(self):
        if self.set_cursor_id is not None:
            if self.canvas is None:
                self.canvas.mpl_disconnect(self.set_cursor_id)
                self.canvas.mpl_disconnect(self.reset_cursor_id)
            self.set_cursor_id = None
            self.reset_cursor_id = None

        if self.selector is not None:
            self.selector.disconnect_events()
            self.selector = None

    def toggle_selection(self):
        """Activate selection mode"""
        if self.canvas is None:
            return
        self.disconnect()

        key = next((key for key, a in self._actions.items() if a.isChecked()),
                   None)
        if key is None or key == self._action_clicked:
            self._action_clicked = None
            if key is not None:
                self._actions[key].setChecked(False)
        else:
            if self.wand_action.isChecked() and self.wand_type == 'color':
                self.selector = PointOrRectangleSelector(
                    self.ax, self.on_rect_select, rectprops=dict(fc='none'),
                    lineprops=dict(c='none'), useblit=True)
            elif self.select_action.isChecked() and self.select_type == 'poly':
                self.selector = mwid.LassoSelector(
                    self.ax, self.on_poly_select)
            else:
                self.selector = PointOrRectangleSelector(
                    self.ax, self.on_rect_select, useblit=True)
            self.set_cursor_id = self.canvas.mpl_connect(
                'axes_enter_event', self._on_axes_enter)
            self.reset_cursor_id = self.canvas.mpl_connect(
                'axes_leave_event', self._on_axes_leave)
            self._action_clicked = next(key for key, a in self._actions.items()
                                        if a.isChecked())

        self.toolbar.set_message(self.toolbar.mode)

    def enable_or_disable_widgets(self, b):
        super(SelectionToolbar, self).enable_or_disable_widgets(b)
        if not b:
            for w in [self.clear_select_action, self.invert_select_action,
                      self.expand_select_action]:
                w.setEnabled(self.should_be_enabled(w))
        if self._actions and not self.select_action.isEnabled():
            for a in self._actions.values():
                if a.isChecked():
                    a.setChecked(False)
                    self.toggle_selection()

    def refresh(self):
        super(SelectionToolbar, self).refresh()
        combo = self.combo
        if self.straditizer is None:
            combo.clear()
        else:
            if not combo.count():
                combo.addItem('Straditizer')
            if self.straditizer.data_reader is not None:
                if not any(combo.itemText(i) == 'Reader'
                           for i in range(combo.count())):
                    combo.addItem('Reader')
                    combo.addItem('Reader - Greyscale')
            else:
                for i in range(combo.count()):
                    if combo.itemText(i).startswith('Reader'):
                        combo.removeItem(i)

    def _on_axes_enter(self, event):
        ax = self.ax
        if ax is None:
            return
        if (event.inaxes is ax and self.toolbar._active == '' and
                self.selector is not None):
            if self._lastCursor != cursors.SELECT_REGION:
                self.toolbar.set_cursor(cursors.SELECT_REGION)
                self._lastCursor = cursors.SELECT_REGION

    def _on_axes_leave(self, event):
        ax = self.ax
        if ax is None:
            return
        if (event.inaxes is ax and self.toolbar._active == '' and
                self.selector is not None):
            if self._lastCursor != cursors.POINTER:
                self.toolbar.set_cursor(cursors.POINTER)
                self._lastCursor = cursors.POINTER

    def end_selection(self):
        """Finish the selection and disconnect everything"""
        if getattr(self, '_pattern_selection', None) is not None:
            self._pattern_selection.remove_plugin()
            del self._pattern_selection
        self._selecting = False
        self._action_clicked = None
        self.toggle_selection()
        self.auto_expand = False
        self._labels = None
        self._rect_callbacks.clear()
        self._poly_callbacks.clear()
        self._wand_actions['color_select'].setEnabled(True)

    def get_xy_slice(self, lastx, lasty, x, y):
        """Transform x- and y-coordinates to :class:`slice` objects

        Parameters
        ----------
        lastx: int
            The initial x-coordinate
        lasty: int
            The initial y-coordinate
        x: int
            The final x-coordinate
        y: int
            The final y-coordinate

        Returns
        -------
        slice
            The ``slice(lastx, x)``
        slice
            The ``slice(lasty, y)``"""
        all_x = np.floor(np.sort([lastx, x])).astype(int)
        all_y = np.floor(np.sort([lasty, y])).astype(int)
        extent = getattr(self.data_obj, 'extent', None)
        if extent is not None:
            all_x -= np.ceil(extent[0]).astype(int)
            all_y -= np.ceil(min(extent[2:])).astype(int)
        if self.wand_action.isChecked() and self.wand_type == 'color':
            all_x[0] = all_x[1]
            all_y[0] = all_y[1]
        all_x[all_x < 0] = 0
        all_y[all_y < 0] = 0
        all_x[1] += 1
        all_y[1] += 1
        return slice(*all_x), slice(*all_y)

    def on_rect_select(self, e0, e1):
        """Call the :attr:`rect_callbacks` after a rectangle selection

        Parameters
        ----------
        e0: matplotlib.backend_bases.Event
            The initial event
        e1: matplotlib.backend_bases.Event
            The final event"""
        slx, sly = self.get_xy_slice(e0.xdata, e0.ydata, e1.xdata, e1.ydata)
        for func in self.rect_callbacks:
            func(slx, sly)

    def select_rect(self, slx, sly):
        """Select the data defined by a rectangle

        Parameters
        ----------
        slx: slice
            The x-slice of the rectangle
        sly: slice
            The y-slice of the rectangle

        See Also
        --------
        rect_callbacks"""
        obj = self.data_obj
        if obj._selection_arr is None:
            arr = self.labels
            rgba = obj.image_array() if hasattr(obj, 'image_array') else None
            self.start_selection(arr, rgba=rgba)
        expand = False
        if self.select_action.isChecked():
            arr = self._select_rectangle(slx, sly)
            expand = True
        elif self.wand_type == 'labels':
            arr = self._select_labels(slx, sly)
        elif self.wand_type == 'rows':
            arr = self._select_rows(slx, sly)
        elif self.wand_type == 'cols':
            arr = self._select_cols(slx, sly)
        else:
            arr = self._select_colors(slx, sly)
            expand = True
        if arr is not None:
            obj._selection_arr = arr
            obj._select_img.set_array(arr)
            obj._update_magni_img()
            if expand and self.auto_expand:
                self.expand_selection()
            else:
                self.canvas.draw()

    def on_poly_select(self, points):
        """Call the :attr:`poly_callbacks` after a polygon selection

        Parameters
        ----------
        e0: matplotlib.backend_bases.Event
            The initial event
        e1: matplotlib.backend_bases.Event
            The final event"""
        for func in self.poly_callbacks:
            func(points)

    def select_poly(self, points):
        """Select the data defined by a polygon

        Parameters
        ----------
        points: np.ndarray of shape (N, 2)
            The x- and y-coordinates of the vertices of the polygon

        See Also
        --------
        poly_callbacks"""
        obj = self.data_obj
        if obj._selection_arr is None:
            rgba = obj.image_array() if hasattr(obj, 'image_array') else None
            self.start_selection(self.labels, rgba=rgba)
        arr = self.labels
        mpath = mplp.Path(points)
        x = np.arange(obj._selection_arr.shape[1], dtype=int)
        y = np.arange(obj._selection_arr.shape[0], dtype=int)
        extent = getattr(obj, 'extent', None)
        if extent is not None:
            x += np.ceil(extent[0]).astype(int)
            y += np.ceil(min(extent[2:])).astype(int)
        pointsx, pointsy = np.array(points).T
        x0, x1 = x.searchsorted([pointsx.min(), pointsx.max()])
        y0, y1 = y.searchsorted([pointsy.min(), pointsy.max()])
        X, Y = np.meshgrid(x[x0:x1], y[y0:y1])
        points = np.array((X.flatten(), Y.flatten())).T
        mask = np.zeros_like(obj._selection_arr, dtype=bool)
        mask[y0:y1, x0:x1] = (
            mpath.contains_points(points).reshape(X.shape) &
            obj._selection_arr[y0:y1, x0:x1].astype(bool))
        if self.remove_select_action.isChecked():
            arr[mask] = -1
        else:
            if self.new_select_action.isChecked():
                arr = obj._orig_selection_arr.copy()
                obj._select_img.set_cmap(obj._select_cmap)
                obj._select_img.set_norm(obj._select_norm)
            arr[mask] = arr.max() + 1
        obj._selection_arr = arr
        obj._select_img.set_array(arr)
        obj._update_magni_img()
        if self.auto_expand:
            self.expand_selection()
        else:
            self.canvas.draw()

    def _select_rectangle(self, slx, sly):
        """Select a rectangle within the array"""
        obj = self.data_obj
        arr = self.labels
        data_mask = obj._selection_arr.astype(bool)
        if self.remove_select_action.isChecked():
            arr[sly, slx][data_mask[sly, slx]] = -1
        else:
            if self.new_select_action.isChecked():
                arr = obj._orig_selection_arr.copy()
                obj._select_img.set_cmap(obj._select_cmap)
                obj._select_img.set_norm(obj._select_norm)
            arr[sly, slx][data_mask[sly, slx]] = arr.max() + 1
        return arr

    def _select_labels(self, slx, sly):
        """Select the unique labels in the array"""
        obj = self.data_obj
        arr = self.labels
        data_mask = obj._selection_arr.astype(bool)
        current_selected = obj.selected_labels
        new_selected = np.unique(
            arr[sly, slx][data_mask[sly, slx]])
        valid_labels = np.unique(
            obj._orig_selection_arr[sly, slx][data_mask[sly, slx]])
        valid_labels = valid_labels[valid_labels > 0]
        if not len(valid_labels):
            return
        if new_selected[0] == -1 or new_selected[-1] > obj._select_nlabels:
            mask = np.isin(obj._orig_selection_arr, valid_labels)
            current_selected = np.unique(
                np.r_[current_selected,
                      obj._orig_selection_arr[sly, slx][
                          arr[sly, slx] > obj._select_nlabels]])
            arr[mask] = obj._orig_selection_arr[mask]
        curr = set(current_selected)
        valid = set(valid_labels)
        if self.remove_select_action.isChecked():
            new = curr - valid
        elif self.add_select_action.isChecked():
            new = curr | valid
        else:
            new = valid
            arr = obj._orig_selection_arr.copy()
        obj.select_labels(np.array(sorted(new)))
        return arr

    def _select_rows(self, slx, sly):
        """Select the pixel rows defined by `sly`

        Parameters
        ----------
        slx: slice
            The x-slice (is ignored)
        sly: slice
            The y-slice defining the rows to select"""
        obj = self.data_obj
        arr = self.labels
        rows = np.arange(arr.shape[0])[sly]
        if self.remove_select_action.isChecked():
            arr[rows, :] = np.where(arr[rows, :], -1, 0)
        else:
            if self.new_select_action.isChecked():
                arr = obj._orig_selection_arr.copy()
                obj._select_img.set_cmap(obj._select_cmap)
                obj._select_img.set_norm(obj._select_norm)
            arr[rows, :] = np.where(arr[rows, :], arr.max() + 1, 0)
        return arr

    def _select_cols(self, slx, sly):
        """Select the pixel columns defined by `slx`

        Parameters
        ----------
        slx: slice
            The x-slice defining the columns to select
        sly: slice
            The y-slice (is ignored)"""
        obj = self.data_obj
        arr = self.labels
        cols = np.arange(arr.shape[1])[slx]
        if self.remove_select_action.isChecked():
            arr[:, cols] = np.where(arr[:, cols], -1, 0)
        else:
            if self.new_select_action.isChecked():
                arr = obj._orig_selection_arr.copy()
                obj._select_img.set_cmap(obj._select_cmap)
                obj._select_img.set_norm(obj._select_norm)
            arr[:, cols] = np.where(arr[:, cols], arr.max() + 1, 0)
        return arr

    def _select_colors(self, slx, sly):
        """Select the array based on the colors"""
        if self.cb_use_alpha.isChecked():
            rgba = self._rgba
            n = 4
        else:
            rgba = self._rgba[..., :-1]
            n = 3
        rgba = rgba.astype(int)
        # get the unique colors
        colors = list(
            map(np.array, set(map(tuple, rgba[sly, slx].reshape((-1, n))))))
        obj = self.data_obj
        arr = self.labels
        mask = np.zeros_like(arr, dtype=bool)
        max_dist = self.distance_slider.value()
        data_mask = obj._selection_arr.astype(bool)
        for c in colors:
            mask[np.all(np.abs(rgba - c.reshape((1, 1, -1))) <= max_dist,
                        axis=-1)] = True
        if not self.cb_whole_fig.isChecked():
            import skimage.morphology as skim
            all_labels = skim.label(mask, 8, return_num=False)
            selected_labels = np.unique(all_labels[sly, slx])
            mask[~np.isin(all_labels, selected_labels)] = False
        if self.remove_select_action.isChecked():
            arr[mask & data_mask] = -1
        else:
            if self.new_select_action.isChecked():
                arr = obj._orig_selection_arr.copy()
                obj._select_img.set_cmap(obj._select_cmap)
                obj._select_img.set_norm(obj._select_norm)
            arr[mask & data_mask] = arr.max() + 1
        return arr

    def _remove_selected_labels(self):
        self.data_obj.remove_selected_labels(disable=True)

    def _disable_selection(self):
        return self.data_obj.disable_label_selection()

    def start_selection(self, arr=None, rgba=None,
                        rect_callbacks=None, poly_callbacks=None,
                        apply_funcs=(), cancel_funcs=(), remove_on_apply=True):
        """Start the selection in the current :attr:`data_obj`

        Parameters
        ----------
        arr: np.ndarray
            The labeled selection array that is used. If specified, the
            :meth:`~straditize.label_selection.enable_label_selection` method
            is called of the :attr:`data_obj` with the given `arr`. If this
            parameter is ``None``, then we expect that this method has already
            been called
        rgba: np.ndarray
            The RGBA image that shall be used for the color selection
            (see the :meth:`set_color_wand_mode`)
        rect_callbacks: list
            A list of callbacks that shall be called after a rectangle
            selection has been made by the user (see :attr:`rect_callbacks`)
        poly_callbacks: list
            A list of callbacks that shall be called after a polygon
            selection has been made by the user (see :attr:`poly_callbacks`)
        apply_funcs: list
            A list of callables that shall be connected to the
            :attr:`~straditize.widgets.StraditizerWidgets.apply_button`
        cancel_funcs: list
            A list of callables that shall be connected to the
            :attr:`~straditize.widgets.StraditizerWidgets.cancel_button`
        remove_on_apply: bool
            If True and the
            :attr:`~straditize.widgets.StraditizerWidgets.apply_button` is
            clicked, the selected labels will be removed."""
        obj = self.data_obj
        if arr is not None:
            obj.enable_label_selection(
                arr, arr.max(), set_picker=False,
                zorder=obj.plot_im.zorder + 0.1,
                extent=obj.plot_im.get_extent())
        self._selecting = True
        self._rgba = rgba
        if rgba is None:
            self.set_label_wand_mode()
            self._wand_actions['color_select'].setEnabled(False)
        else:
            self._wand_actions['color_select'].setEnabled(True)
        self.connect2apply(
            (self._remove_selected_labels if remove_on_apply else
             self._disable_selection),
            obj.remove_small_selection_ellipses, obj.draw_figure,
            self.end_selection, *apply_funcs)
        self.connect2cancel(self._disable_selection,
                            obj.remove_small_selection_ellipses,
                            obj.draw_figure,
                            self.end_selection, *cancel_funcs)
        if self.should_be_enabled(self._appearance_actions['alpha']):
            self.update_alpha(self.sl_alpha.value())
        for w in chain(self._actions.values(),
                       self._appearance_actions.values()):
            w.setEnabled(self.should_be_enabled(w))
        if remove_on_apply:
            self.straditizer_widgets.apply_button.setText('Remove')
        if rect_callbacks is not None:
            self._rect_callbacks = rect_callbacks[:]
        if poly_callbacks is not None:
            self._poly_callbacks = poly_callbacks[:]
        del obj
