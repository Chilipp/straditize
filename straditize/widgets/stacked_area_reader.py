"""DataReader for stacked area plots

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
import numpy as np
import pandas as pd
from functools import partial
from straditize.binary import (
    DataReader, readers, result_overlay_color, RESULT_OVERLAY_FILL_ALPHA,
    RESULT_OVERLAY_LINE_ALPHA, RESULT_OVERLAY_LINEWIDTH)
from straditize.widgets import StraditizerControlBase, get_straditizer_widgets
import skimage.morphology as skim
from psyplot_gui.compat.qtcompat import (
    QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLabel, QVBoxLayout)
import gc


class StackedReader(DataReader, StraditizerControlBase):
    """A DataReader for stacked area plots

    This reader only works within the straditizer GUI because the digitization
    (see :meth:`digitize`) is interactive. The user has to manually distinguish
    the stacked variables."""

    #: The QTreeWidgetItem that holds the digitization widgets
    digitize_child = None

    #: A QPushButton to select the previous variable during the digitization
    #: (see :meth:`decrease_current_col`)
    btn_prev = None

    #: A QPushButton to select the next variable during the digitization
    #: (see :meth:`increase_current_col`)
    btn_next = None

    #: A QPushButton to select the features in the image for the current
    #: variable (see :meth:`select_current_column`)
    btn_edit = None

    #: A QPushButton to add a new variable to the current ones
    #: (see :meth:`select_and_add_current_column`)
    btn_add = None

    #: A QLabel to display the current column
    lbl_col = None

    strat_plot_identifier = 'stacked'

    _current_col = 0

    def digitize(self):
        """Digitize the data interactively

        This method creates a new child item for the digitize button in the
        straditizer control to manually distinguish the variables in the
        stacked diagram."""
        if getattr(self, 'straditizer_widgets', None) is None:
            self.init_straditizercontrol(get_straditizer_widgets())
        digitizer = self.straditizer_widgets.digitizer
        digitizing = digitizer.btn_digitize.isChecked()
        if digitizing and self.digitize_child is None:
            raise ValueError("Apparently another digitization is in progress!")
        elif not digitizing and self.digitize_child is None:
            if len(self.columns) == 1 or self._current_col not in self.columns:
                self._current_col = self.columns[0]
            if len(self.columns) == 1:
                super(StackedReader, self).digitize()
            # start digitization
            digitizer.btn_digitize.setCheckable(True)
            digitizer.btn_digitize.setChecked(True)
            self._init_digitize_child()
            # Disable the changing of readers
            digitizer.cb_readers.setEnabled(False)
            digitizer.tree.expandItem(digitizer.digitize_item)
            self.enable_or_disable_navigation_buttons()
            self.reset_lbl_col()
        elif not digitizing:
            # stop digitization
            digitizer.btn_digitize.setChecked(False)
            digitizer.btn_digitize.setCheckable(False)
            self._remove_digitze_child(digitizer)
            digitizer.cb_readers.setEnabled(
                digitizer.should_be_enabled(digitizer.cb_readers))
            del self.straditizer_widgets

    def _init_digitize_child(self):
        self.lbl_col = QLabel('')
        self.btn_prev = QPushButton('<')
        self.btn_next = QPushButton('>')
        self.btn_edit = QPushButton('Edit')
        self.btn_add = QPushButton('+')
        self.reset_lbl_col()
        self.btn_box = w = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(self.lbl_col)
        hbox = QHBoxLayout()
        hbox.addWidget(self.btn_prev)
        hbox.addWidget(self.btn_next)
        hbox.addWidget(self.btn_edit)
        hbox.addWidget(self.btn_add)
        vbox.addLayout(hbox)
        w.setLayout(vbox)

        self.digitize_child = QTreeWidgetItem(0)
        self.straditizer_widgets.digitizer.digitize_item.addChild(
            self.digitize_child)
        self.straditizer_widgets.digitizer.tree.setItemWidget(
            self.digitize_child, 0, w)
        self.widgets2disable = [self.btn_prev, self.btn_next,
                                self.btn_edit, self.btn_add]

        self.btn_next.clicked.connect(self.increase_current_col)
        self.btn_prev.clicked.connect(self.decrease_current_col)
        self.btn_edit.clicked.connect(self.select_current_column)
        self.btn_add.clicked.connect(self.select_and_add_current_column)

    def reset_lbl_col(self):
        """Reset the :attr:`lbl_col` to display the current column"""
        self.lbl_col.setText('Part %i of %i' % (
            self.columns.index(self._current_col) + 1, len(self.columns)))

    def increase_current_col(self):
        """Take the next column as the current column"""
        self._current_col = min(self.columns[-1], self._current_col + 1)
        self.reset_lbl_col()
        self.enable_or_disable_navigation_buttons()

    def decrease_current_col(self):
        """Take the previous column as the current column"""
        self._current_col = max(self.columns[0], self._current_col - 1)
        self.reset_lbl_col()
        self.enable_or_disable_navigation_buttons()

    def _remove_digitze_child(self, digitizer):
        digitizer.digitize_item.takeChild(
            digitizer.digitize_item.indexOfChild(
                self.digitize_child))
        digitizer.btn_digitize.setChecked(False)
        digitizer.btn_digitize.setCheckable(False)
        for btn in self.widgets2disable:
            btn.clicked.disconnect()
        del (self.digitize_child, self.btn_prev, self.btn_next, self.btn_add,
             self.btn_edit, self.lbl_col, self.btn_box)
        self.widgets2disable.clear()

    def enable_or_disable_navigation_buttons(self):
        """Enable or disable :attr:`btn_prev` and :attr:`btn_next`

        Depending on the current column, we disable the navigation buttons
        :attr:`btn_prev` and :attr:`btn_next`"""
        disable_all = self.columns is None or len(self.columns) == 1
        self.btn_prev.setEnabled(not disable_all and
                                 self._current_col != self.columns[0])
        self.btn_next.setEnabled(not disable_all and
                                 self._current_col != self.columns[-1])

    def select_and_add_current_column(self):
        """Select the features for a column and create it as a new one"""
        return self._select_current_column(True)

    def select_current_column(self):
        """Select the features of the current column"""
        return self._select_current_column()

    def _select_current_column(self, add_on_apply=False):
        image = self.to_grey_pil(self.image).astype(int) + 1
        start = self.start_of_current_col
        end = start + self.full_df[self._current_col].values
        all_end = start + self.full_df.loc[:, self._current_col:].values.sum(
            axis=1)
        x = np.meshgrid(*map(np.arange, image.shape[::-1]))[0]
        image[(x < start[:, np.newaxis]) | (x > all_end[:, np.newaxis])] = 0
        labels = skim.label(image, connectivity=2)
        self.straditizer_widgets.selection_toolbar.data_obj = self
        self.apply_button.clicked.connect(
            self.add_col if add_on_apply else self.update_col)
        self.apply_button.clicked.connect(self.update_plotted_full_df)
        self.straditizer_widgets.selection_toolbar.start_selection(
            labels, rgba=self.image_array(), remove_on_apply=False)
        self.select_all_labels()
        # set values outside the current column to 0
        self._selection_arr[(x < start[:, np.newaxis]) |
                            (x >= end[:, np.newaxis])] = -1
        self._select_img.set_array(self._selection_arr)
        self.draw_figure()

    @property
    def start_of_current_col(self):
        """The first x-pixel of the current column"""
        if self._current_col == self.columns[0]:
            start = np.zeros(self.binary.shape[:1])
        else:
            idx = self.columns.index(self._current_col)
            start = self.full_df.iloc[:, :idx].values.sum(axis=1)
        start += self.column_starts[0]
        return start

    def update_plotted_full_df(self):
        """Update the plotted full_df if it is shown

        See Also
        --------
        plot_full_df"""
        pc = self.straditizer_widgets.plot_control.table
        if pc.can_plot_full_df() and pc.get_full_df_lines():
            pc.remove_full_df_plot()
            pc.plot_full_df()

    def update_col(self):
        """Update the current column based on the selection.

        This method updates the end of the current column and adds or removes
        the changes from the columns to the right."""
        current = self._current_col
        start = self.start_of_current_col
        selected = self.selected_part
        end = (self.binary.shape[1] - selected[:, ::-1].argmax(axis=1) -
               start)
        not_selected = ~selected.any()
        end[not_selected] = 0

        diff_end = self.parent._full_df.loc[:, current] - end
        self.parent._full_df.loc[:, current] = end
        if current != self.columns[-1]:
            self.parent._full_df.loc[:, current + 1] += diff_end

    def get_binary_for_col(self, col):
        s, e = self.column_bounds[self.columns.index(col)]
        if self.parent._full_df is None:
            return self.binary[:, s:e]
        else:
            vals = self.full_df.loc[:, col].values
            ret = np.zeros((self.binary.shape[0], int(vals.max())))
            dist = np.tile(np.arange(ret.shape[1])[np.newaxis], (len(ret), 1))
            ret[dist <= vals[:, np.newaxis]] = 1
            return ret

    def add_col(self):
        """Create a column out of the current selection"""
        def increase_col_nums(df):
            df_cols = np.asarray(df.columns, dtype=int).copy()
            df_cols[df_cols >= current] += 1
            df.columns = df_cols
        current = self._current_col
        start = self.start_of_current_col
        selected = self.selected_part
        end = (self.binary.shape[1] - selected[:, ::-1].argmax(axis=1) -
               start)
        not_selected = ~selected.any()
        end[not_selected] = 0

        # ----- Update of reader column numbers -----
        for reader in self.iter_all_readers:
            for i, col in enumerate(reader.columns):
                if col >= current:
                    reader.columns[i] += 1
        self.columns.insert(self.columns.index(current + 1), current)
        self.parent._column_starts = np.insert(
            self.parent._column_starts, current, self._column_starts[current])
        if self.parent._column_ends is not None:
            self.parent._column_ends = np.insert(
                self.parent._column_ends, current,
                self.parent._column_ends[current])

        # ----- Update of column numbers in dataframes -----
        # increase column numbers in full_df
        full_df = self.parent._full_df
        increase_col_nums(full_df)
        # increase column numbers in samples
        samples = self.parent._sample_locs
        if samples is not None:
            increase_col_nums(samples)

        # ----- Update of DataFrames -----
        # update the current column in full_df and add the new one
        full_df.loc[:, current + 1] -= end
        full_df[current] = end
        full_df.sort_index(axis=1, inplace=True)
        # update the current column in samples and add the new one
        if samples is not None:
            new_samples = full_df.loc[samples.index, current]
            samples.loc[:, current + 1] -= new_samples
            samples[current] = new_samples
            samples.sort_index(axis=1, inplace=True)
        rough_locs = self.parent.rough_locs
        if rough_locs is not None:
            rough_locs[(current + 1, 'vmin')] = rough_locs[(current, 'vmin')]
            rough_locs[(current + 1, 'vmax')] = rough_locs[(current, 'vmax')]
            rough_locs.loc[:, current] = -1
            rough_locs.sort_index(inplace=True, level=0)
        self.reset_lbl_col()
        self.enable_or_disable_navigation_buttons()

    def plot_full_df(self, ax=None):
        """Plot the lines for the digitized diagram"""
        vals = self.full_df.values
        starts = self.column_starts
        self.lines = lines = []
        y = np.arange(np.shape(self.image)[0])
        ax = ax or self.ax
        if self.extent is not None:
            y += self.extent[-1]
            starts += self.extent[0]
        x = np.zeros_like(vals[:, 0]) + starts[0]
        for i in range(vals.shape[1]):
            x += vals[:, i]
            lines.extend(ax.plot(x.copy(), y, lw=2.0))

    def _plot_results_overlay_df(self, df, ax, samples=False,
                                 column_numbers=None, color_map=None):
        """Plot stacked layers as semi-transparent bands on the source image."""
        column_numbers = column_numbers or self._overlay_column_numbers(df)
        color_map = color_map or {
            col: result_overlay_color(col)
            for col in column_numbers}
        artists = {'fills': [], 'lines': []}
        y = self._overlay_ycoords(df)
        start = np.zeros(len(df), dtype=float) + self._overlay_starts(
            [column_numbers[0]])[0]

        for col_num, label in zip(column_numbers, df.columns):
            values = self._overlay_values(df.loc[:, label].values)
            color = color_map[col_num]
            artists['fills'].append(ax.fill_betweenx(
                y, start, start + values, color=color,
                alpha=RESULT_OVERLAY_FILL_ALPHA, zorder=2))
            artists['lines'].append(ax.plot(
                start + values, y, color=color,
                alpha=RESULT_OVERLAY_LINE_ALPHA,
                lw=RESULT_OVERLAY_LINEWIDTH, zorder=3)[0])
            start = start + np.nan_to_num(values, nan=0.0)
        return artists

    def plot_potential_samples(self, excluded=False, ax=None, plot_kws={},
                               *args, **kwargs):
        """Plot the ranges for potential samples"""
        vals = self.full_df.values.copy()
        starts = self.column_starts.copy()
        self.sample_ranges = lines = []
        y = np.arange(np.shape(self.image)[0])
        ax = ax or self.ax
        plot_kws = dict(plot_kws)
        plot_kws.setdefault('marker', '+')
        if self.extent is not None:
            y += self.extent[-1]
            starts = starts + self.extent[0]
        x = np.zeros(vals.shape[0]) + starts[0]
        for i, (col, arr) in enumerate(zip(self.columns, vals.T)):
            all_indices, excluded_indices = self.find_potential_samples(
                i, *args, **kwargs)
            if excluded:
                all_indices = excluded_indices
            if not all_indices:
                x += arr
                continue
            mask = np.ones(arr.size, dtype=bool)
            for imin, imax in all_indices:
                mask[imin:imax] = False
            for imin, imax in all_indices:
                lines.extend(ax.plot(
                    np.where(mask, np.nan, arr)[imin:imax] + x[imin:imax],
                    y[imin:imax], **plot_kws))
            x += arr

    def interpolate_samples(self, sample_rows):
        """Linearly interpolate the digitized stacked curves at sample rows."""
        full_df = self.full_df
        sample_rows = np.asarray(sample_rows, dtype=float)
        index = np.asarray(full_df.index, dtype=float)
        sample_index = pd.Index(sample_rows, name=full_df.index.name)
        values = np.column_stack([
            np.interp(sample_rows, index, full_df.loc[:, col].values)
            for col in full_df.columns])
        return pd.DataFrame(values, index=sample_index, columns=full_df.columns)

    def _consensus_sample_rows(self, bars):
        """Estimate a shared y-axis for stacked samples from interval votes."""
        index = np.asarray(self.full_df.index, dtype=float)
        columns = list(self.full_df.columns)
        col_map = dict(zip(columns, range(len(columns))))
        rows = np.zeros(len(bars), dtype=float)
        rough = -np.ones((len(bars), len(columns) * 2), dtype=float)
        for i, bar in enumerate(bars):
            votes = np.zeros(len(index), dtype=float)
            for col, (imin, imax) in bar.items():
                imin = max(int(imin), 0)
                imax = min(int(imax), len(index))
                rough[i, 2 * col_map[col]:2 * col_map[col] + 2] = [imin, imax]
                if imin >= imax:
                    votes[min(imin, len(votes) - 1)] += 1.0
                    continue
                votes[imin:imax] += 1.0 / max(imax - imin, 1)
            if votes.any():
                winners = np.flatnonzero(votes == votes.max())
                rows[i] = index[winners].mean()
            else:
                centers = []
                for imin, imax in bar.values():
                    imin = max(int(imin), 0)
                    imax = min(int(imax), len(index))
                    if imin >= imax:
                        centers.append(index[min(imin, len(index) - 1)])
                    else:
                        centers.append(index[imin:imax].mean())
                rows[i] = np.mean(centers) if centers else np.nan
        return rows, rough

    def _merge_consensus_occurences(self, locs):
        for col, occs in self.occurences_dict.items():
            closest = np.abs(
                locs.index.values[np.newaxis] -
                occs[:, np.newaxis]).argmin(axis=1)
            locs.loc[locs.index[closest], col] = self.occurences_value

    def find_consensus_samples(self, min_fract=None, pixel_tol=5,
                               *args, **kwargs):
        """Prototype sample finder using global y-consensus and interpolation.

        Unlike :meth:`find_samples`, this method first estimates one shared
        sample y-position per horizon and only then interpolates each stacked
        curve on that shared axis.
        """
        bars = self.unique_bars(min_fract, asdict=True, *args, **kwargs)
        full_df = self.full_df
        columns = list(full_df.columns)
        rough_columns = pd.MultiIndex.from_product([columns, ['vmin', 'vmax']])
        if not bars:
            empty_index = pd.Index([], dtype=float, name=full_df.index.name)
            return (pd.DataFrame([], index=empty_index, columns=columns),
                    pd.DataFrame([], index=empty_index, columns=rough_columns))

        rows, rough = self._consensus_sample_rows(bars)
        samples = self.interpolate_samples(rows)
        rough = pd.DataFrame(
            rough, index=pd.Index(rows, name=full_df.index.name),
            columns=rough_columns)

        not_duplicated = ~samples.index.duplicated()
        samples = samples.iloc[not_duplicated].sort_index()
        rough = rough.iloc[not_duplicated].sort_index()

        if pixel_tol is not None and len(samples):
            samples, rough = self.merge_close_samples(samples, rough, pixel_tol)
            samples = self.interpolate_samples(samples.index.values)
            rough.index = samples.index

        self._merge_consensus_occurences(samples)
        return samples, rough

    def resize_axes(self, grouper, bounds):
        """Reimplemented to do nothing"""
        xmin = bounds.min()
        xmax = bounds.max()
        grouper.plotters[0].update(xlim=(xmin, xmax))
        return


readers.setdefault('stacked area', StackedReader)
