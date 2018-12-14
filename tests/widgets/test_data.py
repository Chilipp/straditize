"""Test the straditize.widgets.data module"""
import numpy as np
import pandas as pd
from itertools import chain
from straditize import binary
import os.path as osp
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt


class RemoverTest(bt.StraditizeWidgetsTestCase):
    """A test case for testing the removing of features"""

    def test_remove_yaxes(self):
        """Test the removing of yaxes

        This method removes the vertical lines in
        ``'basic_diagram_yaxes.png'`` and compares it with
        ``'basic_diagram_yaxes_removed.png'``"""
        self.init_reader('basic_diagram_yaxes.png', xlim=np.array([9., 27.]))
        self.reader.column_starts = np.array([0, 7, 15])
        self.straditizer_widgets.refresh()
        self.digitizer.txt_line_fraction.setText('30')
        self.digitizer.cb_max_lw.setChecked(False)
        self.digitizer.sp_min_lw.setValue(1)
        QTest.mouseClick(self.digitizer.btn_remove_yaxes,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary,
            self.get_fig_path('basic_diagram_yaxes_removed.png'))

    def test_remove_vlines(self):
        """Test the removing of vertical lines

        This method removes the vertical lines in
        ``'basic_diagram_vlines.png'`` and compares it with
        ``'basic_diagram_vlines_removed.png'``"""
        self.init_reader('basic_diagram_vlines.png')
        self.digitizer.cb_max_lw.setChecked(True)
        self.digitizer.sp_max_lw.setValue(2)
        self.digitizer.sp_min_lw.setValue(2)
        self.digitizer.txt_line_fraction.setText('75')
        QTest.mouseClick(self.digitizer.btn_remove_vlines,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary,
            self.get_fig_path('basic_diagram_vlines_removed.png'))

    def test_remove_xaxes(self):
        """Test the removing of x-axes

        This method removes the horizontal lines in
        ``'basic_diagram_xaxes.png'`` and compares it with
        ``'basic_diagram_xaxes_removed.png'``"""
        self.init_reader('basic_diagram_xaxes.png', ylim=np.array([10., 33.]),
                         xlim=np.array([10., 29.]))
        self.digitizer.txt_line_fraction.setText('50')
        self.digitizer.cb_max_lw.setChecked(False)
        self.digitizer.sp_min_lw.setValue(1)
        QTest.mouseClick(self.digitizer.btn_remove_xaxes,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary,
            self.get_fig_path('basic_diagram_xaxes_removed.png'))

    def test_remove_hlines(self):
        """Test the removing of horizonal lines lines

        This method removes the horizontal lines in
        ``'basic_diagram_hlines.png'`` and compares it with
        ``'basic_diagram_hlines_removed.png'``"""
        self.init_reader('basic_diagram_hlines.png')
        self.digitizer.cb_max_lw.setChecked(True)
        self.digitizer.sp_max_lw.setValue(2)
        self.digitizer.sp_min_lw.setValue(2)
        self.digitizer.txt_line_fraction.setText('90')
        QTest.mouseClick(self.digitizer.btn_remove_hlines,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary,
            self.get_fig_path('basic_diagram_hlines_removed.png'))

    def test_remove_disconnected_01_from0(self):
        """Test the removing of disconnected features

        This method removes the disconnected features in
        ``'basic_diagram_disconnected.png'`` and compares it with
        ``'basic_diagram_binary.png'``"""
        # set the distance for removing
        self.digitizer.cb_fromlast.setChecked(False)
        self.digitizer.cb_from0.setChecked(True)
        self.digitizer.txt_from0.setText('4')
        # setup the reader
        self._test_disconnected('basic_diagram_disconnected_01.png',
                                'basic_diagram_disconnected_01_ref.png')

    def test_remove_disconnected_02_from0_fromlast(self):
        """Test the removing of disconnected features

        This method removes the disconnected features in
        ``'basic_diagram_disconnected.png'`` and compares it with
        ``'basic_diagram_binary.png'``"""
        # setup the reader
        self.digitizer.cb_fromlast.setChecked(True)
        self.digitizer.cb_from0.setChecked(True)
        self.digitizer.txt_fromlast.setText('2')
        self.digitizer.txt_from0.setText('3')
        self._test_disconnected('basic_diagram_disconnected_02.png',
                                'basic_diagram_disconnected_02_ref.png')

    def test_remove_disconnected_03_fromlast(self):
        """Test the removing of disconnected features

        This method removes the disconnected features in
        ``'basic_diagram_disconnected.png'`` and compares it with
        ``'basic_diagram_binary.png'``"""
        # setup the reader
        self.digitizer.cb_fromlast.setChecked(True)
        self.digitizer.cb_from0.setChecked(False)
        self.digitizer.txt_fromlast.setText('2')
        self._test_disconnected('basic_diagram_disconnected_03.png',
                                'basic_diagram_disconnected_03_ref.png')

    def _test_disconnected(self, fname, ref):
        self.init_reader(fname)
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self.assertTrue(self.digitizer.btn_show_disconnected_parts.isEnabled())
        QTest.mouseClick(self.digitizer.btn_show_disconnected_parts,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path(ref))

    def test_remove_small_parts(self):
        """Test the removement of small features

        This test methods removes two small features in
        basic_diagram_small_features.png"""
        self.init_reader('basic_diagram_small_features.png')
        self.assertTrue(self.digitizer.btn_show_small_parts.isEnabled())
        QTest.mouseClick(self.digitizer.btn_show_small_parts, Qt.LeftButton)
        # before removing, highlight the small selections
        QTest.mouseClick(self.digitizer.btn_highlight_small_selection,
                         Qt.LeftButton)
        self.assertEqual(len(self.reader._ellipses), 2,
                         msg=self.reader._ellipses)
        # check for correct centers
        centers_drawn = sorted(e.center for e in self.reader._ellipses)
        self.assertEqual(centers_drawn, [(14.0, 18.0), (21.5, 14.5)])
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        # ellipses should be removed now
        self.assertEqual(len(self.reader._ellipses), 0,
                         msg=self.reader._ellipses)
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path('basic_diagram_binary.png'))

    def test_remove_features_at_column_ends(self):
        """Test the removement of features at the end of columns

        This test methods removes two small features in
        basic_diagram_small_features.png"""
        self.init_reader('basic_diagram_features_at_col_ends.png')
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self.assertTrue(
            self.digitizer.btn_show_parts_at_column_ends.isEnabled())
        QTest.mouseClick(self.digitizer.btn_show_parts_at_column_ends,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path(
                'basic_diagram_features_at_col_ends_removed.png'))

    def test_remove_cross_column_features(self):
        """Test the removement of features at the end of columns

        This test methods removes two small features in
        basic_diagram_small_features.png"""
        self.init_reader('basic_diagram_cross_col.png')
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self.digitizer.txt_cross_column_px.setText('3')
        self.assertTrue(
            self.digitizer.btn_show_cross_column.isEnabled())
        QTest.mouseClick(self.digitizer.btn_show_cross_column,
                         Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path(
                'basic_diagram_cross_col_removed.png'))


class OccurencesTest(bt.StraditizeWidgetsTestCase):
    """A test case for handling occurences"""

    def test_01_select_occurences(self):
        """Test the selection of occurences"""
        self.init_reader('basic_diagram_occurences.png')
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        QTest.mouseClick(self.digitizer.btn_select_occurences, Qt.LeftButton)
        labels = self.reader.labels
        self.reader.select_labels(np.array(
            [labels[5, 11], labels[13, 17]]))
        self.digitizer.cb_remove_occurences.setChecked(True)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        # make sure that the occurences have been removed
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path('basic_diagram_binary.png'))
        self.assertEqual(self.reader.occurences, {(10, 6), (17, 14)})

    def test_edit_occurences(self):
        self.test_01_select_occurences()
        QTest.mouseClick(self.digitizer.btn_edit_occurences, Qt.LeftButton)
        self.move_mark(self.straditizer.marks[0], by=[0, -1])
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.assertEqual(
            {c: list(v) for c, v in self.reader.occurences_dict.items()},
            {1: [5], 2: [14]})

    def test_samples(self):
        """Test whether the samples are correctly highlighted"""
        self.test_01_select_occurences()
        self.reader.digitize()
        self.digitizer.set_occurences_value('')
        self.digitizer.set_occurences_value('900')
        self.digitizer.find_samples()
        df = self.reader.sample_locs
        self.assertEqual(df.iloc[1, 1], 900)
        self.assertEqual(df.iloc[2, 2], 900)


class DigitizerTest(bt.StraditizeWidgetsTestCase):
    """A TestCase for testing general features of the digitizer control"""

    def test_column_starts(self):
        """Test the recognition of column starts"""
        self.init_reader()
        self.assertTrue(self.digitizer.btn_column_starts.isEnabled())
        QTest.mouseClick(self.digitizer.btn_column_starts, Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertEqual(list(self.reader.column_starts),
                         list(self.column_starts))
        self.assertEqual(list(self.reader.column_ends),
                         list(self.column_ends))

    def test_column_ends(self):
        """Test the modification of column ends"""
        self.test_column_starts()
        self.assertTrue(self.digitizer.btn_column_ends.isEnabled())
        QTest.mouseClick(self.digitizer.btn_column_ends, Qt.LeftButton)
        self.assertTrue(bool(self.straditizer.marks),
                        msg='No crossmarks created!')
        # move the second mark by one pixel
        mark = self.straditizer.marks[1]
        mark.set_pos((mark.x + 1, mark.pos[1]))
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        ref_cols = list(self.column_ends)
        ref_cols[1] += 1
        self.assertEqual(list(self.reader.column_ends),
                         ref_cols)

    def test_digitize(self):
        """Test the digitization of the full data"""
        self.test_column_starts()
        self.assertTrue(self.digitizer.btn_digitize.isEnabled())
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)
        full_df = self.reader.full_df
        self.assertIsNotNone(full_df)
        # load the reference DataFrame
        ref = pd.read_csv(self.get_fig_path(osp.join('data', 'full_data.csv')),
                          index_col=0, dtype=float)
        self.assertEqual(list(map(str, full_df.columns)),
                         list(map(str, ref.columns)))
        ref.columns = full_df.columns
        self.assertFrameEqual(full_df, ref, check_index_type=False)

    def test_load_samples(self):
        """Test loading samples from a file"""
        self.test_digitize()
        fname = self.get_fig_path(osp.join('data', 'data.csv'))
        ref = pd.read_csv(fname, index_col=0, dtype=float)
        ref.index = ref.index.astype(int)
        ref.columns = ref.columns.astype(int)
        self.digitizer.load_samples(fname)
        self.assertFrameEqual(ref, self.reader.sample_locs,
                              check_names=False)

    def test_plot_results(self):
        """Test the plotting of the results"""
        sw = self.straditizer_widgets
        self.assertFalse(sw.plot_control.results_plot.cb_final.isEnabled())
        self.test_load_samples()
        sp, groupers = sw.plot_control.results_plot.plot_results()
        self.assertEqual(
            len(sp), len(self.straditizer.data_reader._full_df.columns))


class ChildReaderFrameworkTest(bt.StraditizeWidgetsTestCase):
    """Test the column specific reader framework"""

    def test_init_child_reader(self, init=True):
        """Test initializing a child reader"""
        if init:
            self.init_reader()
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        cols = list(self.reader.columns)

        # select a column
        self.digitizer.enable_col_selection_for_new_reader()
        ax = self.straditizer.ax
        x = self.reader.column_starts[1] + self.data_xlim[0] + 1
        y = np.mean(self.data_ylim)
        x, y = ax.transData.transform([[x, y]])[0]
        ax.figure.canvas.button_press_event(x, y, 1)

        # create the new reader
        self.digitizer.new_reader_for_selection(self.reader.__class__)
        QTest.mouseClick(self.straditizer_widgets.cancel_button, Qt.LeftButton)

        self.assertEqual(len(self.reader.children), 1)
        self.assertEqual(list(self.reader.columns), sorted(set(cols) - {1}))
        self.assertEqual(list(self.reader.children[0].columns), [1])

    def test_change_child_reader(self, init=True):
        """Test changing the reader"""
        if init:
            self.test_init_child_reader()
        current = self.reader
        new = self.reader.children[0]
        self.digitizer.cb_readers.setCurrentIndex(1)
        self.assertIs(new, self.reader)
        self.assertIs(current, self.reader.children[0])

    def test_digitize_child_reader(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()

        ref_df = self.reader.full_df

        # plot the full_df and save it
        self.reader.plot_full_df(c='r')  # plot the data with  red lines
        fname_ref = self.get_random_filename(suffix='.png')
        self.reader.ax.figure.savefig(fname_ref)
        for l in self.reader.lines:
            l.remove()
        self.reader.lines.clear()

        # plot the potential samples
        self.reader.plot_potential_samples(plot_kws=dict(c='r'))
        fname_meas_ref = self.get_random_filename(suffix='.png')
        self.reader.ax.figure.savefig(fname_meas_ref)
        for l in self.reader.sample_ranges:
            l.remove()
        self.reader.sample_ranges.clear()

        self.reader._full_df = None

        self.test_init_child_reader(init=False)
        self.reader.digitize()
        self.reader.plot_full_df(c='r')

        self.test_change_child_reader(init=False)
        self.reader.digitize()
        self.reader.plot_full_df(c='r')

        fname = self.get_random_filename(suffix='.png')
        self.reader.ax.figure.savefig(fname)

        self.assertFrameEqual(self.reader._full_df, ref_df)
        self.assertImageEquals(fname, fname_ref)

        for l in chain.from_iterable(
                reader.lines for reader in self.reader.iter_all_readers):
            l.remove()
        for reader in self.reader.iter_all_readers:
            reader.lines.clear()
            reader.plot_potential_samples(plot_kws=dict(c='r'))
        fname = self.get_random_filename(suffix='.png')
        self.reader.ax.figure.savefig(fname)
        self.assertImageEquals(fname, fname_meas_ref)

    def test_child_reader_samples(self):
        """Test editing samples"""
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.reader.digitize()
        ref = self.reader._get_sample_locs()
        # reset the reader
        self.digitizer.init_reader()
        self.test_init_child_reader(init=False)
        self.reader.digitize()
        self.test_change_child_reader(init=False)
        self.reader.digitize()

        # compare the samples
        QTest.mouseClick(self.digitizer.btn_find_samples, Qt.LeftButton)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        self.assertFrameEqual(
            self.reader._get_sample_locs(), ref)


class ExaggeratedTest(bt.StraditizeWidgetsTestCase):
    """A test case for the exaggerated reader"""

    def test_init_exaggerated(self):
        self.init_reader('basic_diagram_exaggerated.png')
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self.digitizer.txt_exag_factor.setText('2')
        # add the exaggeration reader
        QTest.mouseClick(self.digitizer.btn_new_exaggeration, Qt.LeftButton)

    def test_select_exaggerations(self):
        """Test selecting the exaggerations"""
        self.test_init_exaggerated()
        orig = self.reader.binary.copy()
        # select the exaggeration parts
        QTest.mouseClick(self.digitizer.btn_select_exaggerations,
                         Qt.LeftButton)
        tb = self.straditizer_widgets.selection_toolbar
        tb.set_color_wand_mode()
        tb.cb_whole_fig.setChecked(True)
        tb.wand_action.setChecked(True)
        tb.toggle_selection()
        slx, sly = tb.get_xy_slice(15, 25, 15, 25)
        tb.select_rect(slx, sly)
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        # test the exaggerations
        exag = self.reader.exaggerated_reader.binary
        exag_sum = exag.sum()
        self.assertGreater(exag_sum, 0)
        self.assertArrayEquals(orig, self.reader.binary + exag)
        self.assertBinaryImageEquals(
            self.reader.binary, self.get_fig_path('basic_diagram_binary.png'))

    def test_digitize_exaggerations(self):
        # get the original data
        self.init_reader()
        self.reader.column_starts = self.column_starts
        orig = self.reader.digitize(inplace=False)
        # start new from scratch
        self.tearDown()
        self.setUp()

        # use the exaggerations
        self.test_select_exaggerations()
        self.digitizer.txt_exag_absolute.setText('3')
        self.assertFalse(self.digitizer.btn_digitize_exag.isEnabled())
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)
        self.assertTrue(self.digitizer.btn_digitize_exag.isEnabled())
        # digitize the exaggerations
        df, mask = self.reader.digitize_exaggerated(
            absolute=3, return_mask=True, inplace=False)
        self.assertFrameEqual(df, orig)
        self.assertArrayEquals(
            mask.values,
            orig.values.astype(bool) & (orig.values < 3))
        QTest.mouseClick(self.digitizer.btn_digitize_exag, Qt.LeftButton)
        self.assertFrameEqual(self.reader.full_df, orig)


class BarReaderTest(bt.StraditizeWidgetsTestCase):
    """A test case for the BarReader"""

    def init_reader(self, fname='bar_diagram.png', *args, **kwargs):
        """Reimplemented to make sure, we intiailize a bar diagram"""
        self.digitizer.cb_reader_type.setCurrentText('bars')
        super(BarReaderTest, self).init_reader(fname, *args, **kwargs)
        self.assertIsInstance(self.reader, binary.BarDataReader)

    @property
    def ref_bars(self):
        """A 2D array, where each row represents the location of one bar"""
        return np.loadtxt(
            self.get_fig_path(osp.join('data', 'bar_locations.dat')),
            dtype=int)

    def test_init_reader(self):
        self.init_reader()

    def test_digitize(self):
        self.init_reader()
        self.reader.column_starts = self.column_starts
        self.straditizer_widgets.refresh()
        self.digitizer.txt_tolerance.setText('1')
        QTest.mouseClick(self.digitizer.btn_digitize, Qt.LeftButton)
        # check that the bars are read correctly
        for col in range(len(self.column_starts)):
            self.assertLessEqual(
                set(chain.from_iterable(self.reader._all_indices[col])),
                set(np.unique(self.ref_bars)))

    def test_split_bars(self):
        """Test the splitting of too long bars"""
        def split(child):
            indices = list(map(int, child.text(0).split(', ')))
            self.assertEqual(len(indices), np.diff(ref_bars[0]) * 2)
            last = next(i for i in indices if (ref_bars[:, -1] == i).any())
            y = self.data_ylim[0] + last
            start = reader.all_column_starts[tree._col]
            x = start + self.data_xlim[0] + reader.full_df.loc[last, tree._col]
            x, y = reader.ax.transData.transform([[x, y]])[0]
            reader.ax.figure.canvas.button_press_event(x, y, 1)
            return x, y

        def revert_split(child):
            indices = list(map(int, child.text(0).split(',')))
            last = indices[-1]
            y= self.data_ylim[0] + last + 1
            start = reader.all_column_starts[tree._col]
            x = start + self.data_xlim[0] + reader.full_df.loc[last, tree._col]
            x, y = reader.ax.transData.transform([[x, y]])[0]
            reader.ax.figure.canvas.button_press_event(x, y, 3)
            return x, y
        self.assertTrue(self.digitizer.bar_split_child.isHidden())
        self.test_digitize()
        # make sure that there is something to split
        self.assertTrue(any(self.reader._splitted.values()))
        self.assertFalse(self.digitizer.bar_split_child.isHidden())

        ref_bars = self.ref_bars
        reader = self.reader
        tree = self.digitizer.tree_bar_split
        used_cols = set()

        # split the first item bars
        item = tree.topLevelItem(0).child(0)
        self.assertIsNotNone(item)
        tree.start_splitting(item)
        used_cols.add(tree._col)
        self.assertEqual(item.childCount(), 2)  # 2 suggestions
        revert_split(item.child(0))
        self.assertEqual(item.childCount(), 0)
        x, y = split(item)
        self.assertEqual(item.childCount(), 2)

        # now revert the split
        reader.ax.figure.canvas.button_press_event(x, y, 3)
        self.assertEqual(item.childCount(), 0)

        # split again
        split(item)
        x, y = split(item)
        self.assertEqual(item.childCount(), 2)

        # go to the next bar
        tree.go_to_next_bar()
        used_cols.add(tree._col)
        item = tree.topLevelItem(1).child(0)
        revert_split(item.child(0))
        self.assertEqual(item.childCount(), 0)
        split(item)
        self.assertEqual(item.childCount(), 2)

        # perform the split
        ref_bars = set(map(tuple, ref_bars))
        orig_lens = list(map(len, reader._all_indices))
        QTest.mouseClick(self.straditizer_widgets.apply_button, Qt.LeftButton)
        # test whether we splitted all
        self.assertFalse(any(reader._splitted.values()))
        for col, indices in enumerate(reader._all_indices):
            indices = list(map(tuple, indices))
            # check that the length increased
            if col in used_cols:
                self.assertGreater(len(indices), orig_lens[col])
            else:
                self.assertEqual(len(indices), orig_lens[col])
            # check for uniqueness of bars
            self.assertEqual(len(set(indices)), len(indices))
            # check that the bars are valid
            self.assertLessEqual(set(indices), ref_bars)


if __name__ == '__main__':
    unittest.main()
