"""A table for manipulating samples

This module defines the sample editors, either for editing the samples in the
straditizer image (:class:`SingleCrossMarksEditor`) or in a separate
:class:`~matplotlib.figure.Figure` (:class:`MultiCrossMarksEditor`)

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
import six
import numpy as np
import pandas as pd
from itertools import chain
from psyplot_gui.compat.qtcompat import (
    QWidget, QHBoxLayout, QVBoxLayout, QtCore, QLineEdit,
    QPushButton, Qt, QMenu, QCheckBox, QTableView)
from psyplot_gui.common import DockMixin, PyErrorMessage
from psyplot_gui.dataframeeditor import DataFrameDock, FrozenTableView
from straditize.common import docstrings
from collections import defaultdict


class MultiCrossMarksModel(QtCore.QAbstractTableModel):
    """A table model to handle multiple connected cross marks in different axes
    """

    _format = '%0.6g'

    @property
    def fig(self):
        """The figure of the cross marks"""
        return self.axes[0].figure

    @property
    def _new_mark(self):
        return self.straditizer()._new_mark

    @property
    def _remove_mark(self):
        return self.straditizer()._remove_mark

    #: A list ``[float, list]`` where the first ``float`` is the vertical
    #: position and the second ``list`` is a list of the corresponding
    #: :class:`~straditize.cross_mark.CrossMarks` instances
    marks = []

    #: A list of :class:`matplotlib.lines.Line2D` that connects the cross marks
    #: and plots a reconstruction based on them
    lines = []

    @docstrings.get_sectionsf('MultiCrossMarksModel')
    def __init__(self, marks, columns, straditizer, axes=None,
                 occurences_value=-9999):
        """
        Parameters
        ----------
        marks: list of :class:`straditize.cross_mark.CrossMarks`
            the initial marks
        columns: list of str
            the column names to use
        straditizer: straditize.straditizer.Straditizer
            The straditizer that manages the `marks`
        axes: list of :class:`matplotlib.axes.Axes`
            The matplotlib axes that contain the `marks`
        occurences_value: float
            The value that marks an occurence"""
        super(MultiCrossMarksModel, self).__init__()
        self.occurences_value = occurences_value
        self.set_marks(marks, columns)
        if axes is None:
            self.axes = [m.ax for m in self.marks[0][1]]
        else:
            self.axes = axes
        self.straditizer = straditizer
        self._marks_moved = 0
        self._new_marks = []
        self.lines = []
        for mark in marks:
            mark.moved.connect(self.update_after_move)

    def set_marks(self, marks, columns):
        """Set the :attr:`marks` attribute from the given `columns`

        Parameters
        ----------
        marks: list of :class:`straditize.cross_mark.CrossMarks`
            the initial marks
        columns: list of str
            the column names to use"""
        ncols = len(columns)
        self._column_names = columns
        arr = np.array(marks).reshape((len(marks) // ncols, ncols)).tolist()
        self.marks = list(zip((l[0].y for l in arr), arr))

    def get_cell_mark(self, row, column):
        """Get the mark for a given cell in the table

        Parameters
        ----------
        row: int
            The row of the cell
        column: int
            The column of the cell

        Returns
        -------
        straditize.cross_mark.CrossMarks
            The corresponding mark from the :attr:`marks` attribute"""
        return self.marks[row][1][column - 1]

    @property
    def iter_marks(self):
        """Iter over all marks in the :attr:`marks` attribute"""
        return chain.from_iterable(t[1] for t in self.marks)

    def update_after_move(self, old_pos, mark):
        self._marks_moved += 1
        if self._marks_moved == self.columnCount() - 1:
            for i, (y, marks) in enumerate(self.marks):
                if mark in marks:
                    self.marks[i] = (mark.y, marks)
                    if self.lines:
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
            if value == self.occurences_value:
                mark._is_occurence[i] = True
            else:
                xa[i] = value
                mark.set_pos((xa, mark.ya))
                mark._is_occurence[i] = False
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
        """Get the samples_locs"""
        vals = np.array([[m.x for m in marks[:-1]] for y, marks in self.marks])
        df = pd.DataFrame(vals, index=[y for y, marks in self.marks],
                          columns=np.arange(self.columnCount() - 2))
        return df.sort_index()

    def plot_lines(self):
        """Connect the samples through visual :attr:`lines`"""
        if not self.rowCount():
            return
        self.lines.extend(chain.from_iterable(
            ax.plot(s.values, s.index.values, c='r')
            for ax, (col, s) in zip(self.axes, self.df.items())))
        self.fig.canvas.draw_idle()

    def update_lines(self):
        """Update the :attr:`lines` or plot them

        See Also
        --------
        plot_lines"""
        if not self.lines:
            self.plot_lines()
        elif not self.rowCount():
            for l in self.lines:
                l.remove()
            self.lines.clear()
        else:
            for l, (col, s) in zip(self.lines, self.df.items()):
                l.set_xdata(s.values)
                l.set_ydata(s.index.values)
            self.fig.canvas.draw_idle()

    def remove_lines(self):
        """Remove the :attr:`lines`"""
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
                if mark._is_occurence[i]:
                    return self.get_format() % self.occurences_value
                return self.get_format() % mark.xa[i]

    def rowCount(self, index=QtCore.QModelIndex()):
        """The number of rows in the table"""
        return len(self.marks)

    def columnCount(self, index=QtCore.QModelIndex()):
        """The number of rows in the table"""
        return len(self.axes) + 1

    def reset(self):
        """Reset the model"""
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
        """Sort the marks based on there y-position"""
        self.marks = sorted(self.marks, key=self._sorter)

    def load_new_marks(self, mark):
        """Add a new mark into the table after they have been added by the user

        Parameters
        ----------
        mark: straditize.cross_mark.CrossMarks
            The added mark"""
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
        """Remove a mark from the table after it has been removed by the user

        Parameters
        ----------
        mark: straditize.cross_mark.CrossMarks
            The removed mark"""
        found = False
        for i, (y, marks) in enumerate(self.marks):
            if mark in marks:
                found = True
                break
        if found:
            for m in self.marks[i][1]:
                try:
                    m.moved.disconnect(self.update_after_move)
                except ValueError:
                    pass
            del self.marks[i]
            self.beginRemoveRows(QtCore.QModelIndex(), i, i)
            self.endRemoveRows()
            self.update_lines()

    def insertRow(self, irow, xa=None, ya=None):
        """Insert a row into the table

        Parameters
        ----------
        irow: int
            The row index. If `irow` is equal to the length of the
            :attr:`marks`, the rows will be appended"""
        if xa is None or ya is None:
            mark = self.marks[min(irow, len(self.marks) - 1)][1][0]
            new = self._new_mark(mark.xa, mark.ya)
        else:
            new = self._new_mark(xa, ya)
        y = new[0].y
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
            try:
                mark.moved.disconnect(self.update_after_move)
            except ValueError:
                pass
            try:
                self._remove_mark(mark)
            except ValueError:
                pass
        del self.marks[irow]
        self.beginRemoveRows(QtCore.QModelIndex(), irow, irow)
        self.endRemoveRows()
        self.update_lines()


class SingleCrossMarksModel(MultiCrossMarksModel):
    """A table model to handle cross marks within one single axis"""

    #: A list of tuples like ``(float, mark)`` where ``float`` is the y-pixel
    #: and ``mark`` is the corresponding
    #: :class:`straditize.cross_mark.CrossMarks` instance
    marks = []

    @docstrings.get_sectionsf('SingleCrossMarksModel')
    @docstrings.dedent
    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        %(MultiCrossMarksModel.parameters)s
        column_bounds: np.ndarray of shape ``(N, 2)``
            The column boundaries
        y0: float
            The upper extent of the data image
        """
        self._bounds = kwargs.pop('column_bounds')
        self._y0 = kwargs.pop('y0')
        super(SingleCrossMarksModel, self).__init__(*args, **kwargs)

    def set_marks(self, marks, columns):
        self._column_names = columns
        self.marks = list(zip((m.y for m in marks), marks))

    set_marks.__doc__ = MultiCrossMarksModel.set_marks.__doc__

    def get_cell_mark(self, row, column):
        ret = self.marks[row][1]
        if column > 0:
            ret._i_vline = column - 1
        return ret

    get_cell_mark.__doc__ = MultiCrossMarksModel.get_cell_mark.__doc__

    @property
    def iter_marks(self):
        """Iter over all marks in the :attr:`marks` attribute"""
        return (m for y, m in self.marks)

    def update_after_move(self, old_pos, mark):
        for i, (y, m) in enumerate(self.marks):
            if m is mark:
                self.marks[i] = (mark.y, mark)
                if self.lines:
                    self.update_lines()
                break
        self.sort_marks()
        self.reset()
        self.fig.canvas.draw_idle()

    def _set_cell_data(self, row, column, value):
        value = float(value)
        if column == 0:
            old_y, mark = self.marks[row]
            mark.ya[:] = value + self._y0
            mark.set_pos((mark.xa, mark.ya))
            self.marks[row] = (value + self._y0, mark)
            self.sort_marks()
        else:
            mark = self.get_cell_mark(row, column)
            if value == self.occurences_value:
                mark._is_occurence[column-1] = True
            else:
                xa = mark.xa[:]
                xa[column - 1] = value + self._bounds[column - 1, 0]
                mark._is_occurence[column-1] = False
                mark.set_pos((xa, mark.ya))
        self.fig.canvas.draw()
        return True

    @property
    def df(self):
        """Get the samples_locs"""
        if self.marks:
            vals = np.array([t[1].xa for t in self.marks]) - \
                self._bounds[:, :1].T
        else:
            vals = []
        df = pd.DataFrame(
            vals,
            index=np.array([y for y, mark in self.marks]) - self._y0,
            columns=np.arange(self.columnCount() - 1))
        return df.sort_index()

    def plot_lines(self):
        if not self.rowCount():
            return
        ax = self.axes[0]
        starts = self._bounds[:, 0]
        y0 = self._y0
        self.lines.extend(chain.from_iterable(
            ax.plot(starts[col] + s.values, y0 + s.index.values, c='r')
            for col, s in self.df.items()))
        self.fig.canvas.draw_idle()

    plot_lines.__doc__ = MultiCrossMarksModel.plot_lines.__doc__

    def update_lines(self):
        if not self.lines:
            self.plot_lines()
        elif not self.rowCount():
            for l in self.lines:
                l.remove()
            self.lines.clear()
        else:
            starts = self._bounds[:, 0]
            y0 = self._y0
            for l, (col, s) in zip(self.lines, self.df.items()):
                l.set_xdata(starts[col] + s.values)
                l.set_ydata(y0 + s.index.values)
            self.fig.canvas.draw_idle()

    update_lines.__doc__ = MultiCrossMarksModel.update_lines.__doc__

    def _get_cell_data(self, row, column):
            y, mark = self.marks[row]
            if column == 0:
                return self.get_format() % (y - self._y0)
            else:
                if mark._is_occurence[column - 1]:
                    return self.get_format() % self.occurences_value
                return self.get_format() % (mark.xa[column - 1] -
                                            self._bounds[column - 1][0])

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self._column_names) + 1

    def _sorter(self, t):
        return (t[0], list(t[1].xa - self._bounds[:, 0]))

    def load_new_marks(self, mark):
        new = [mark.y, mark]
        self.marks.append(new)
        self.sort_marks()
        idx = self.marks.index(new)
        self.beginInsertRows(QtCore.QModelIndex(), idx, idx)
        self.endInsertRows()
        mark.moved.connect(self.update_after_move)
        self.update_lines()

    def remove_mark(self, mark):
        found = False
        for i, (y, m) in enumerate(self.marks):
            if m is mark:
                found = True
                break
        if found:
            try:
                mark.moved.disconnect(self.update_after_move)
            except ValueError:
                pass
            del self.marks[i]
            self.beginRemoveRows(QtCore.QModelIndex(), i, i)
            self.endRemoveRows()
            self.update_lines()

    def insertRow(self, irow, xa=None, ya=None):
        """Insert a row into the table

        Parameters
        ----------
        irow: int
            The row index. If `irow` is equal to the length of the
            :attr:`marks`, the rows will be appended"""
        if xa is None or ya is None:
            mark = self.marks[min(irow, len(self.marks) - 1)][1]
            new = self._new_mark(mark.xa[0], mark.ya[0])[0]
        else:
            new = self._new_mark(xa + self._bounds[:, 0], ya + self._y0)[0]
            new.set_pos((xa + self._bounds[:, 0], ya + self._y0))
        y = new.y
        new.moved.connect(self.update_after_move)
        if irow == len(self.marks):
            self.marks.append((y, new))
        else:
            self.marks.insert(irow, (y, new))
        self.beginInsertRows(QtCore.QModelIndex(), irow, irow)
        self.endInsertRows()
        self.update_lines()

    def delRow(self, irow):
        mark = self.marks[irow][1]
        try:
            mark.moved.disconnect(self.update_after_move)
        except ValueError:
            pass
        try:
            self._remove_mark(mark)
        except ValueError:
            pass
        del self.marks[irow]
        self.beginRemoveRows(QtCore.QModelIndex(), irow, irow)
        self.endRemoveRows()
        self.update_lines()


class MultiCrossMarksView(QTableView):
    """A table view set up by cross marks from multiple axes

    The model for this table is the :class:`MultiCrossMarksModel`"""

    _fit2selection_cid = None

    docstrings.delete_params('MultiCrossMarksModel.parameters', 'marks')

    #: The :class:`pandas.DataFrame` representing the full digitized data
    #: from the :attr:`straditize.binary.DataReader.full_df` data frame
    full_df = None

    @docstrings.dedent
    def __init__(self, marks, full_df, *args, **kwargs):
        """
        Parameters
        ----------
        marks: list of :class:`straditize.cross_mark.CrossMarks`
            the initial marks
        full_df: pandas.DataFrame
            The data fame of the full digitized data
        %(MultiCrossMarksModel.parameters.no_marks)s
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

    @docstrings.with_indent(8)
    def init_model(self, marks, *args, **kwargs):
        """Initialize the table :class:`MultiCrossMarksModel`

        Parameters
        ----------
        %(MultiCrossMarksModel.parameters)s"""
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
            model.insertRow(0, xa=self.full_df.iloc[0],
                            ya=self.full_df.index[0])
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
        """Fit the selected cells to the :attr:`full_df`"""
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
        """Zoom to the selected cells in the plot"""
        self.zoom_to_cells(*self._selected_rows_and_cols())

    def zoom_to_cells(self, rows, cols):
        """Zoom to specific cells in the plot

        Parameters
        ----------
        rows: list of int
            The row indices of the cells
        cols: list of int
            The column indicies of the cells"""
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
            mark = marks[col]
            xmax = float(self.full_df.iloc[:, col].max())
            mark.ax.set_xlim(0, xmax)
            mark.ax.set_ylim(ymax, ymin)
        mark.fig.canvas.draw()

    def show_all_marks(self):
        """Show all marks

        See Also
        --------
        show_selected_marks_only"""
        model = self.model()
        for m in model.iter_marks:
            m.set_visible(True)
        model.fig.canvas.draw()

    def show_selected_marks_only(self):
        """Show only the marks selected in the table

        See Also
        --------
        show_all_marks"""
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


class SingleCrossMarksView(MultiCrossMarksView):
    """A table for visualizing marks from a single axes"""

    def init_model(self, marks, *args, **kwargs):
        """Initialize the table :class:`SingleCrossMarksModel`

        Parameters
        ----------
        %(SingleCrossMarksModel.parameters)s"""
        return SingleCrossMarksModel(marks, *args, **kwargs)

    def fit2data(self):
        model = self.model()
        df = self.full_df
        mark = None
        y0 = model._y0
        starts = model._bounds[:, 0]
        for index in self.selectedIndexes():
            row = index.row()
            col = index.column()
            if col == 0:  # index column
                continue
            mark = model.get_cell_mark(row, col)
            xa = mark.xa
            old_pos = mark.pos
            x = df.loc[
                df.index.get_loc(mark.y - y0, method='nearest')].iloc[col-1]
            if np.isnan(x):
                x = 0
            xa[col - 1] = x + starts[col - 1]
            mark.set_pos((xa, mark.ya))
            mark.moved.emit(old_pos, mark)
        if mark is not None:
            mark.fig.canvas.draw()

    fit2data.__doc__ = MultiCrossMarksView.fit2data.__doc__

    def zoom_to_cells(self, rows, cols):
        model = self.model()
        rows = list(rows)
        cols = list(cols)
        if not model.rowCount() or not len(cols) or not len(rows):
            return
        y = model.df.iloc[rows].index + model._y0
        cols = np.unique(cols) - 1
        xmin = model._bounds[:, 0][cols].min()
        xmax = model._bounds[:, 1][cols].max()
        ax = model.axes[0]
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(y.max() + 10, y.min() - 10)
        model.fig.canvas.draw()

    zoom_to_cells.__doc__ = MultiCrossMarksView.zoom_to_cells.__doc__


class MultiCrossMarksEditor(DockMixin, QWidget):
    """An editor for cross marks in multiple axes"""

    #: The QDockWidget for the :class:`DataFrameEditor`
    dock_cls = DataFrameDock

    #: A :class:`weakref` to the
    #: :attr:`~straditize.widgets.StraditizerWidgets.straditizer`
    straditizer = None

    def __init__(self, straditizer, axes=None, *args, **kwargs):
        """
        Parameters
        ----------
        straditizer: weakref.ref
            The reference to the straditizer
        axes: matplotlib.axes.Axes
            The matplotlib axes corresponding to the marks
        """
        super(MultiCrossMarksEditor, self).__init__(*args, **kwargs)
        self.straditizer = straditizer
        straditizer = straditizer()
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
        self.btn_save.setToolTip('Save the samples and continue editing')

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
        self.btn_save.clicked.connect(self.save_samples)
        straditizer.mark_added.connect(self.table.model().load_new_marks)
        straditizer.mark_removed.connect(self.table.model().remove_mark)
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
        """Create the :class:`MultiCrossMarksView` of the editor

        Parameters
        ----------
        axes: list of :class:`matplotlib.axes.Axes`
            The matplotlib axes for the marks"""
        stradi = self.straditizer()
        reader = stradi.data_reader
        df = getattr(stradi, '_plotted_full_df', reader._full_df).copy()
        df.columns = [
            str(i) if str(i) == colname else '%s (%i)' % (colname, i)
            for i, colname in enumerate(stradi.colnames_reader.column_names +
                                        ['nextrema'])]
        return MultiCrossMarksView(stradi.marks, df, df.columns,
                                   self.straditizer, axes=axes,
                                   occurences_value=reader.occurences_value)

    def save_samples(self):
        """Save the samples to the :attr:`straditizer` without removing them"""
        self.straditizer().update_samples_sep(remove=False)

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
            if main.centralWidget() is not main.help_explorer:
                position = main.dockWidgetArea(main.help_explorer.dock)
            else:
                position = Qt.RightDockWidgetArea
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


class SingleCrossMarksEditor(MultiCrossMarksEditor):
    """The editor for cross marks on a single axes"""

    def create_view(self, axes=None):
        """Create the :class:`SingleCrossMarksView` of the editor

        Parameters
        ----------
        axes: list of :class:`matplotlib.axes.Axes`
            The matplotlib axes for the marks"""
        stradi = self.straditizer()
        reader = stradi.data_reader
        axes = [reader.ax]
        df = getattr(stradi, '_plotted_full_df', reader._full_df).copy()
        df.columns = [
            str(i) if str(i) == colname else '%s (%i)' % (colname, i)
            for i, colname in enumerate(stradi.colnames_reader.column_names)]
        x0 = min(stradi.data_xlim)
        return SingleCrossMarksView(
            stradi.marks, df, df.columns, self.straditizer, axes=axes,
            column_bounds=x0 + reader.all_column_bounds,
            y0=min(stradi.data_ylim),
            occurences_value=reader.occurences_value)

    def save_samples(self):
        self.straditizer().update_samples(remove=False)

    def _fit2selection(self, event):
        model = self.table.model()
        if (not event.inaxes or event.button != 1 or
                model.fig.canvas.manager.toolbar.mode != ''):
            return
        y = int(np.round(event.ydata)) - model._y0
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
            x = data[col - 1]
            if np.isnan(x):
                x = 0
            xa = mark.xa
            xa[col - 1] = model._bounds[col - 1, 0] + x
            mark.set_pos((xa, mark.ya))
            mark.moved.emit(old_pos, mark)
        if mark is not None:
            mark.fig.canvas.draw()
