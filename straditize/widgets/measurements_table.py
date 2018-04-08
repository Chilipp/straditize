"""A table for manipulating measurements"""
from __future__ import division
import six
import numpy as np
import pandas as pd
from itertools import chain
from psyplot_gui.compat.qtcompat import (
    QWidget, QHBoxLayout, QVBoxLayout, QtCore, QLineEdit,
    QPushButton, Qt, QMenu, QCheckBox, QTableView)
from psyplot_gui.common import DockMixin, PyErrorMessage
from psyplot_gui.dataframeeditor import DataFrameDock, FrozenTableView
from collections import defaultdict


class MultiCrossMarksModel(QtCore.QAbstractTableModel):

    _format = '%0.6g'

    @property
    def fig(self):
        return self.axes[0].figure

    def __init__(self, marks, columns, mark_factory, mark_removal, axes=None):
        super(MultiCrossMarksModel, self).__init__()
        ncols = len(columns)
        self._column_names = columns
        arr = np.array(marks).reshape((len(marks) // ncols, ncols)).tolist()
        self.marks = list(zip((l[0].y for l in arr), arr))
        if axes is None:
            self.axes = [m.ax for m in self.marks[0][1]]
        else:
            self.axes = axes
        self._new_mark = mark_factory
        self._remove_mark = mark_removal
        self._marks_moved = 0
        self._new_marks = []
        self.lines = []
        for mark in marks:
            mark.moved.connect(self.update_after_move)

    def get_cell_mark(self, row, column):
        return self.marks[row][1][column - 1]

    @property
    def iter_marks(self):
        return chain.from_iterable(t[1] for t in self.marks)

    def update_after_move(self, old_pos, mark):
        self._marks_moved += 1
        if self._marks_moved == self.columnCount() - 1:
            for i, (y, marks) in enumerate(self.marks):
                if mark in marks:
                    self.marks[i] = (mark.y, marks)
                    self.update_lines()
                    break
            self.sort_marks()
            self.reset()
            self._marks_moved = 0
            self.fig.canvas.draw_idle()

    def setData(self, index, value, role=Qt.EditRole, change_type=None):
        """Cell content change"""
        return self._set_cell_data(index.row(), index.column(), value)

    def _set_cell_data(self, row, column, value):
        value = float(value)
        if column == 0:
            old_y, marks = self.marks[row]
            for mark in marks:
                mark.ya[:] = value
                mark.set_pos((mark.xa, mark.ya))
            self.marks[row] = (value, marks)
            self.sort_marks()
        else:
            mark = self.get_cell_mark(row, column)
            xa = mark.xa[:]
            i = min(column, len(xa)) - 1
            xa[i] = float(value)
            mark.set_pos((xa, mark.ya))
        self.fig.canvas.draw()
        return True

    def get_format(self):
        """Return current format"""
        # Avoid accessing the private attribute _format from outside
        return self._format

    def set_format(self, fmt):
        """Change display format"""
        self._format = six.text_type(fmt)
        self.reset()

    def flags(self, index):
        """Set flags"""
        return Qt.ItemFlags(QtCore.QAbstractTableModel.flags(self, index) |
                            Qt.ItemIsEditable)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self._get_cell_data(index.row(), index.column())

    @property
    def df(self):
        """Get the measurements_locs"""
        vals = np.array([[m.x for m in marks[:-1]] for y, marks in self.marks])
        df = pd.DataFrame(vals, index=[y for y, marks in self.marks],
                          columns=np.arange(self.columnCount() - 2))
        return df.sort_index()

    def plot_lines(self):
        self.lines.extend(chain.from_iterable(
            ax.plot(s.values, s.index.values, c='r')
            for ax, (col, s) in zip(self.axes, self.df.items())))
        self.fig.canvas.draw_idle()

    def update_lines(self):
        for l, (col, s) in zip(self.lines, self.df.items()):
            l.set_xdata(s.values)
            l.set_ydata(s.index.values)
        self.fig.canvas.draw_idle()

    def remove_lines(self):
        for l in self.lines:
            try:
                l.remove()
            except ValueError:
                pass
        self.lines.clear()
        self.fig.canvas.draw_idle()

    def _get_cell_data(self, row, column):
            y, marks = self.marks[row]
            if column == 0:
                return self.get_format() % y
            else:
                i = min(column, len(marks)) - 1
                mark = marks[i]
                i = min(column, len(mark.xa)) - 1
                return self.get_format() % mark.xa[i]

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.marks)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.marks[0][1]) + 1

    def reset(self):
        self.beginResetModel()
        self.endResetModel()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return six.text_type('y')
            else:
                col = self._column_names[section - 1]
                try:
                    col = int(col)
                except (TypeError, ValueError):
                    return six.text_type(col)
                else:
                    return 'Column %i' % col
        elif orientation == Qt.Vertical:
            return six.text_type(section + 1)
        else:
            return None

    def _sorter(self, t):
        return (t[0], [m.x for m in t[1]])

    def sort_marks(self):
        self.marks = sorted(self.marks, key=self._sorter)

    def load_new_marks(self, mark):
        self._new_marks.append(mark)
        mark.moved.connect(self.update_after_move)
        if len(self._new_marks) == self.columnCount() - 1:
            new = (self._new_marks[0].y, self._new_marks)
            self.marks.append(new)
            self._new_marks = []
            self.sort_marks()
            idx = self.marks.index(new)
            self.beginInsertRows(QtCore.QModelIndex(), idx, idx)
            self.endInsertRows()
            self.update_lines()

    def remove_mark(self, mark):
        found = False
        for i, (y, marks) in enumerate(self.marks):
            if mark in marks:
                found = True
                break
        if found:
            for m in self.marks[i][1]:
                m.moved.disconnect(self.update_after_move)
            del self.marks[i]
            self.beginRemoveRows(QtCore.QModelIndex(), i, i)
            self.endRemoveRows()
            self.update_lines()

    def insertRow(self, irow):
        """Insert a row into the :attr:`df`

        Parameters
        ----------
        irow: int
            The row index. If `irow` is equal to the length of the
            :attr:`marks`, the rows will be appended"""
        mark = self.marks[irow][1][0]
        y = mark.y
        new = self._new_mark(mark.xa, mark.ya)
        for m in new:
            m.moved.connect(self.update_after_move)
        if irow == len(self.marks):
            self.marks.append((y, new))
        else:
            self.marks.insert(irow, (y, new))
        self.beginInsertRows(QtCore.QModelIndex(), irow, irow)
        self.endInsertRows()
        self.update_lines()

    def delRow(self, irow):
        for mark in self.marks[irow][1]:
            mark.moved.disconnect(self.update_after_move)
            try:
                self._remove_mark(mark)
            except ValueError:
                pass
        del self.marks[irow]
        self.beginRemoveRows(QtCore.QModelIndex(), irow, irow)
        self.endRemoveRows()
        self.update_lines()


class MultiCrossMarksView(QTableView):
    """Data Frame view class"""

    _fit2selection_cid = None

    def __init__(self, marks, full_df, *args, **kwargs):
        """
        Parameters
        ----------
        %(DataFrameModel.parameters)s
        """
        QTableView.__init__(self)
        self.full_df = full_df
        model = self.init_model(marks, *args, **kwargs)
        self.setModel(model)
        self.menu = self.setup_menu()

        self.frozen_table_view = FrozenTableView(self)
        self.frozen_table_view.update_geometry()

        self.setHorizontalScrollMode(1)
        self.setVerticalScrollMode(1)

        self.horizontalHeader().sectionResized.connect(
            self.update_section_width)
        self.verticalHeader().sectionResized.connect(
            self.update_section_height)

        self.header_class = self.horizontalHeader()

    def init_model(self, marks, *args, **kwargs):
        return MultiCrossMarksModel(marks, *args, **kwargs)

    def update_section_width(self, logical_index, old_size, new_size):
        """Update the horizontal width of the frozen column when a
        change takes place in the first column of the table"""
        if logical_index == 0:
            self.frozen_table_view.setColumnWidth(0, new_size)
            self.frozen_table_view.update_geometry()

    def update_section_height(self, logical_index, old_size, new_size):
        """Update the vertical width of the frozen column when a
        change takes place on any of the rows"""
        self.frozen_table_view.setRowHeight(logical_index, new_size)

    def resizeEvent(self, event):
        """Update the frozen column dimensions.

        Updates takes place when the enclosing window of this
        table reports a dimension change
        """
        QTableView.resizeEvent(self, event)
        self.frozen_table_view.update_geometry()

    def moveCursor(self, cursor_action, modifiers):
        """Update the table position.

        Updates the position along with the frozen column
        when the cursor (selector) changes its position
        """
        current = QTableView.moveCursor(self, cursor_action, modifiers)

        col_width = (self.columnWidth(0) +
                     self.columnWidth(1))
        topleft_x = self.visualRect(current).topLeft().x()

        overflow = self.MoveLeft and current.column() > 1
        overflow = overflow and topleft_x < col_width

        if cursor_action == overflow:
            new_value = (self.horizontalScrollBar().value() +
                         topleft_x - col_width)
            self.horizontalScrollBar().setValue(new_value)
        return current

    def scrollTo(self, index, hint):
        """Scroll the table.

        It is necessary to ensure that the item at index is visible.
        The view will try to position the item according to the
        given hint. This method does not takes effect only if
        the frozen column is scrolled.
        """
        if index.column() > 1:
            QTableView.scrollTo(self, index, hint)

    def setup_menu(self):
        """Setup context menu"""
        menu = QMenu(self)
        self.insert_row_above_action = menu.addAction(
            'Insert row above', self.insert_row_above_selection)
        self.insert_row_below_action = menu.addAction(
            'Insert row below', self.insert_row_below_selection)
        menu.addSeparator()
        self.delete_selected_rows_action = menu.addAction(
            'Delete selected rows', self.delete_selected_rows)
        menu.addSeparator()
        self.fit2data_action = menu.addAction(
            'Fit selected cells to the data', self.fit2data)
        self.zoom_to_selection_action = menu.addAction(
            'Zoom to selected cells and rows', self.zoom_to_selection)
        return menu

    def insert_row_above_selection(self):
        """Insert a row above the selection"""
        self._insert_row(above=True)

    def _insert_row(self, above=True):
        rows, cols = self._selected_rows_and_cols()
        model = self.model()
        if not model.rowCount():
            model.insertRows(0, 1)
        elif not rows and not cols:
            return
        else:
            irow = min(rows) if above else (max(rows) + 1)
            model.insertRow(irow)

    def insert_row_below_selection(self):
        """Insert a row below the selection"""
        self._insert_row(above=False)

    def delete_selected_rows(self):
        rows, cols = self._selected_rows_and_cols()
        model = self.model()
        for row in sorted(set(rows), reverse=True):
            model.delRow(row)

    def fit2data(self):
        model = self.model()
        df = self.full_df
        mark = None
        for index in self.selectedIndexes():
            row = index.row()
            col = index.column()
            if col == 0:  # index column
                continue
            mark = model.get_cell_mark(row, col)
            old_pos = mark.pos
            xa = df.loc[df.index.get_loc(mark.y, method='nearest')].iloc[col-1]
            if np.isnan(xa):
                xa = 0
            mark.set_pos((xa, mark.ya))
            mark.moved.emit(old_pos, mark)
        if mark is not None:
            mark.fig.canvas.draw()

    def _selected_rows_and_cols(self):
        index_list = self.selectedIndexes()
        if not index_list:
            return [], []
        return list(zip(*[(i.row(), i.column()) for i in index_list]))

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        self.menu.popup(event.globalPos())
        event.accept()

    def zoom_to_selection(self):
        self.zoom_to_cells(*self._selected_rows_and_cols())

    def zoom_to_cells(self, rows, cols):
        model = self.model()
        xvals = defaultdict(list)
        yvals = []
        marks = {}
        mark = None
        for row, col in zip(rows, cols):
            if col == 0:  # index column
                yvals.append(model.get_cell_mark(row, 1).y)
            else:
                mark = model.get_cell_mark(row, col)
                xvals[col - 1].append(mark.x)
                yvals.append(mark.y)
                marks[col - 1] = mark
        if not yvals:
            return
        ymin = min(yvals) - 10
        ymax = max(yvals) + 10
        mark = model.get_cell_mark(0, 1)
        mark.ax.set_ylim(ymax, ymin)
        for col, x in xvals.items():
            xmin = min(x) - 10
            xmax = max(x) + 10
            mark = marks[col]
            mark.ax.set_xlim(xmin, xmax)
            mark.ax.set_ylim(ymax, ymin)
        mark.fig.canvas.draw()

    def show_all_marks(self):
        model = self.model()
        for m in chain.from_iterable(t[1] for t in model.marks):
            m.set_visible(True)
        model.marks[0][1][0].fig.canvas.draw()

    def show_selected_marks_only(self):
        model = self.model()
        # hide all marks
        for m in model.iter_marks:
            m.set_visible(False)
        # show selected marks
        rows = sorted(set(self._selected_rows_and_cols()[0]))
        for row in rows:
            for col in range(model.columnCount()):
                model.get_cell_mark(row, col).set_visible(True)
        model.fig.canvas.draw()


class MultiCrossMarksEditor(DockMixin, QWidget):
    """An editor for multiple cross marks at the same y-location"""

    dock_cls = DataFrameDock

    def __init__(self, straditizer, axes=None, *args, **kwargs):
        super(MultiCrossMarksEditor, self).__init__(*args, **kwargs)
        self.straditizer = straditizer
        self.error_msg = PyErrorMessage(self)

        #: Plot the reconstructed data
        self.cb_plot_lines = QCheckBox('Plot reconstruction')
        self.cb_plot_lines.setChecked(True)

        # A Checkbox to automatically zoom to the selection
        self.cb_zoom_to_selection = QCheckBox('Zoom to selection')

        # A Checkbox to automaticall hide the other marks
        self.cb_selection_only = QCheckBox('Selection only')

        # A Checkbox to automatically fit the selected cells to the selected
        # data
        self.cb_fit2selection = QCheckBox(
            'Fit selected cells to selected data')
        self.cb_fit2selection.setToolTip(
            'If checked, select cells from the table and click on one of the '
            'plots to update the table with the data at the selected position.'
            )

        # The table to display the DataFrame
        self.table = self.create_view(axes=axes)

        # format line edit
        self.format_editor = QLineEdit()
        self.format_editor.setText(self.table.model()._format)

        # format update button
        self.btn_change_format = QPushButton('Update')
        self.btn_change_format.setEnabled(False)

        self.btn_save = QPushButton('Save')
        self.btn_save.setToolTip('Save the measurements and continue editing')

        # ---------------------------------------------------------------------
        # ------------------------ layout --------------------------------
        # ---------------------------------------------------------------------
        vbox = QVBoxLayout()
        self.top_hbox = hbox = QHBoxLayout()
        hbox.addWidget(self.cb_zoom_to_selection)
        hbox.addWidget(self.cb_selection_only)
        hbox.addWidget(self.cb_fit2selection)
        hbox.addWidget(self.cb_plot_lines)
        hbox.addStretch(0)
        vbox.addLayout(hbox)
        vbox.addWidget(self.table)
        self.bottom_hbox = hbox = QHBoxLayout()
        hbox.addWidget(self.format_editor)
        hbox.addWidget(self.btn_change_format)
        hbox.addStretch(0)
        hbox.addWidget(self.btn_save)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        # ---------------------------------------------------------------------
        # ------------------------ Connections --------------------------------
        # ---------------------------------------------------------------------
        self.format_editor.textChanged.connect(self.toggle_fmt_button)
        self.btn_change_format.clicked.connect(self.update_format)
        self.btn_save.clicked.connect(self.save_measurements)
        self.straditizer.mark_added.connect(self.table.model().load_new_marks)
        self.straditizer.mark_removed.connect(self.table.model().remove_mark)
        self.table.selectionModel().selectionChanged.connect(
            self.maybe_zoom_to_selection)
        self.table.frozen_table_view.selectionModel().selectionChanged.connect(
            self.maybe_zoom_to_selection)
        self.table.selectionModel().selectionChanged.connect(
            self.maybe_show_selection_only)
        self.table.frozen_table_view.selectionModel().selectionChanged.connect(
            self.maybe_show_selection_only)

        self.cb_zoom_to_selection.stateChanged.connect(
            self.toggle_cb_zoom_to_selection)
        self.cb_selection_only.stateChanged.connect(
            self.toggle_cb_selection_only)
        self.cb_fit2selection.stateChanged.connect(self.toggle_fit2selection)
        self.cb_plot_lines.stateChanged.connect(self.toggle_plot_lines)

        self.toggle_plot_lines()

    def create_view(self, axes=None):
        stradi = self.straditizer
        df = getattr(stradi, '_plotted_full_df', stradi.data_reader.full_df)
        return MultiCrossMarksView(stradi.marks, df, df.columns,
                                   stradi._new_mark, stradi._remove_mark,
                                   axes=axes)

    def save_measurements(self):
        self.straditizer.update_measurements_sep(remove=False)

    def maybe_zoom_to_selection(self):
        if self.cb_zoom_to_selection.isChecked():
            self.table.zoom_to_selection()

    def maybe_show_selection_only(self):
        if self.cb_selection_only.isChecked():
            self.table.show_selected_marks_only()

    def toggle_cb_zoom_to_selection(self):
        if self.cb_zoom_to_selection.isChecked():
            self.table.zoom_to_selection()

    def toggle_cb_selection_only(self):
        if self.cb_selection_only.isChecked():
            self.table.show_selected_marks_only()
        else:
            self.table.show_all_marks()

    def toggle_fit2selection(self):
        """Enable the fitting so selected digitized data"""
        model = self.table.model()
        fig = model.fig
        if self.cb_fit2selection.isChecked():
            self._fit2selection_cid = fig.canvas.mpl_connect(
                'button_press_event', self._fit2selection)
        elif self._fit2selection_cid is not None:
            fig.canvas.mpl_disconnect(self._fit2selection_cid)
            del self._fit2selection_cid

    def _fit2selection(self, event):
        model = self.table.model()
        if (not event.inaxes or event.button != 1 or
                model.fig.canvas.manager.toolbar.mode != ''):
            return
        y = int(np.round(event.ydata))
        data = self.table.full_df.loc[y]
        indexes = list(self.table.selectedIndexes())
        mark = None
        for index in indexes:
            row = index.row()
            col = index.column()
            if col == 0:  # index column
                continue
            mark = model.get_cell_mark(row, col)
            old_pos = mark.pos
            xa = data[col - 1]
            if np.isnan(xa):
                xa = 0
            mark.set_pos((xa, mark.ya))
            mark.moved.emit(old_pos, mark)
        if mark is not None:
            mark.fig.canvas.draw()

    def toggle_fmt_button(self, text):
        try:
            text % 1.1
        except (TypeError, ValueError):
            self.btn_change_format.setEnabled(False)
        else:
            self.btn_change_format.setEnabled(
                text.strip() != self.table.model()._format)

    def toggle_plot_lines(self):
        model = self.table.model()
        if self.cb_plot_lines.isChecked():
            model.plot_lines()
        else:
            model.remove_lines()

    def update_format(self):
        """Update the format of the table"""
        self.table.model().set_format(self.format_editor.text().strip())

    def to_dock(self, main, title=None, position=None, docktype='df', *args,
                **kwargs):
        if position is None:
            position = main.dockWidgetArea(main.help_explorer.dock)
        connect = self.dock is None
        ret = super(MultiCrossMarksEditor, self).to_dock(
            main, title, position, docktype=docktype, *args, **kwargs)
        if connect:
            self.dock.toggleViewAction().triggered.connect(self.maybe_tabify)
        return ret

    def maybe_tabify(self):
        main = self.dock.parent()
        if self.is_shown and main.dockWidgetArea(
                main.help_explorer.dock) == main.dockWidgetArea(self.dock):
            main.tabifyDockWidget(main.help_explorer.dock, self.dock)
