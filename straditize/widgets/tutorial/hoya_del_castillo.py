# -*- coding: utf-8 -*-
"""The tutorial of straditize

This module contains an advanced guided tour through straditize

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
import os.path as osp
import numpy as np
from PyQt5 import QtWidgets
from straditize.widgets.tutorial.beginner import (
    Tutorial, TutorialPage as TutorialPageBase, LoadImage as LoadImageBase,
    FinishPage, SelectDataPart as SelectDataPartBase, CreateReader,
    SeparateColumns as SeparateColumnsBase, ColumnNames as ColumnNamesBase,
    DigitizePage, SamplesPage)
import pandas as pd


class TutorialPage(TutorialPageBase):

    src_dir = osp.join(osp.dirname(__file__), 'hoya-del-castillo')

    src_base = 'hoya-del-castillo.png'

    src_file = osp.join(src_dir, src_base)


class HoyaDelCastilloTutorial(Tutorial):
    """A tutorial for digitizing an area diagram"""

    src_dir = osp.join(osp.dirname(__file__), 'hoya-del-castillo')

    src_base = 'hoya-del-castillo.png'

    src_file = osp.join(src_dir, src_base)

    def setup_tutorial_pages(self):
        from straditize.colnames import tesserocr
        self.pages = [
            self,
            LoadImage('hoya-del-castillo-tutorial-load-image', self),
            SelectDataPart('hoya-del-castillo-tutorial-select-data', self),
            CreateReader('hoya-del-castillo-tutorial-create-reader', self),
            SeparateColumns('hoya-del-castillo-tutorial-column-starts', self),
            (ColumnNames('hoya-del-castillo-tutorial-column-names', self)
             if tesserocr is None else
             ColumnNamesOCR('hoya-del-castillo-tutorial-column-names-ocr',
                            self)),
            RemoveLines('hoya-del-castillo-tutorial-remove-lines', self),
            DigitizePage('hoya-del-castillo-tutorial-digitize', self),
            SamplesPage('hoya-del-castillo-tutorial-samples', self),
            TranslateYAxis('hoya-del-castillo-tutorial-yaxis-translation',
                           self),
            TranslateXAxis('hoya-del-castillo-tutorial-xaxis-translation',
                           self),
            EditMeta('hoya-del-castillo-tutorial-meta', self),
            FinishPage('hoya-del-castillo-tutorial-finish', self),
            ]

    def show(self):
        """Show the documentation of the tutorial"""
        from straditize.colnames import tesserocr
        intro, files = self.get_doc_files()
        self.filename = osp.splitext(osp.basename(intro))[0]
        with open(intro) as f:
            rst = f.read()
        if tesserocr is not None:
            rst = rst.replace('straditize-tutorial-column-names-ocr',
                              'straditize-tutorial-column-names')
        name = osp.splitext(osp.basename(intro))[0]
        self.lock_viewer(False)
        self.tutorial_docs.show_rst(rst, name, files=files)


class LoadImage(LoadImageBase, TutorialPage):
    pass


class SelectDataPart(SelectDataPartBase):
    """TutorialPage for selecting the data part"""

    #: The reference x- and y- limits
    ref_lims = np.array([[315, 1946], [511, 1311]])

    #: Valid ranges for xmin and xmax
    valid_xlims = np.array([[310, 319], [1928, 1960]])

    #: Valid ranges for ymin and ymax
    valid_ylims = np.array([[508, 513], [1307, 1312]])

    remove_data_box = False


class SeparateColumns(SeparateColumnsBase):
    """The page for separating the columns"""

    ncols = 28


class ColumnNames(ColumnNamesBase):
    """The page for recognizing column names"""

    select_names_button_clicked = False

    column_names = [
        'Charcoal', 'Pinus', 'Juniperus', 'Quercus ilex-type',
        'Quercus suber-type', 'Olea', 'Betula', 'Corylus', 'Carpinus-type',
        'Ericaceae', 'Ephedra distachya-type', 'Ephedra fragilis',
        'Mentha-type', 'Anthemis-type', 'Artemisia', 'Caryophyllaceae',
        'Chenopodiaceae', 'Cruciferae', 'Filipendula', 'Gramineae <40um',
        'Gramineae >40<50um', 'Gramineae >50<60um', 'Gramineae >60um',
        'Liguliﬂorae', 'Plantago coronopus', 'Pteridium', 'Filicales',
        'Pollen Concentration']


class ColumnNamesOCR(ColumnNames):
    """Tutorial page for column names with tesserocr support"""

    colpic_extents = [(1051, 1127, 573, 588),
                      (1176, 1225, 704, 719),
                      (1338, 1422, 866, 884),
                      (1437, 1584, 964, 982),
                      (1490, 1655, 1016, 1034),
                      (1511, 1550, 1038, 1052),
                      (1533, 1587, 1061, 1075),
                      (1557, 1621, 1083, 1102),
                      (1580, 1699, 1105, 1123),
                      (1600, 1686, 1123, 1138),
                      (1623, 1828, 1151, 1169),
                      (1646, 1783, 1173, 1192),
                      (1665, 1779, 1195, 1215),
                      (1689, 1811, 1218, 1237),
                      (1711, 1793, 1240, 1254),
                      (1766, 1909, 1288, 1306),
                      (1788, 1934, 1310, 1328),
                      (1841, 1929, 1363, 1378),
                      (1862, 1957, 1390, 1407),
                      (1885, 2045, 1407, 1422),
                      (1922, 2116, 1444, 1459),
                      (1945, 2138, 1467, 1482),
                      (1968, 2128, 1490, 1505),
                      (1990, 2083, 1512, 1531),
                      (2012, 2186, 1540, 1559),
                      (2035, 2117, 1563, 1577),
                      (2056, 2126, 1584, 1599),
                      (2080, 2259, 1601, 1616)
                      ]

    colpic_sizes = [(270, 88), (189, 88), (307, 109), (494, 109), (550, 109),
                    (159, 85), (204, 85), (249, 112), (363, 60), (264, 48),
                    (655, 109), (411, 57), (336, 69), (424, 116), (286, 85),
                    (487, 112), (493, 109), (309, 88), (297, 51), (523, 88),
                    (624, 89), (624, 89), (525, 89), (333, 112), (574, 109),
                    (289, 88), (254, 88), (581, 89)]

    def hint_for_start_editing(self):
        reader = self.straditizer_widgets.straditizer.colnames_reader
        sw = self.straditizer_widgets
        if reader._highres_image is None:
            self.show_tooltip_at_widget(
                "Click the %r button and load the image file "
                "<i>hoya-del-castillo-colnames.png</i>" % (
                    sw.colnames_manager.btn_load_image.text(), ),
                sw.colnames_manager.btn_load_image)
        elif not sw.colnames_manager.cb_find_all_cols.isChecked():
            self.show_tooltip_at_widget(
                "Check the 'all columns' checkbox",
                sw.colnames_manager.cb_find_all_cols)
        else:
            self.show_tooltip_at_widget(
                "Click the %r button to automatically find the "
                "column names." % sw.colnames_manager.btn_find.text(),
                sw.colnames_manager.btn_find)

    def hint_for_wrong_name(self, col, curr, ref):

        def same_size():
            from difflib import get_close_matches
            size = manager.colpic.size
            return (bool(get_close_matches(curr, [ref])) and
                    np.abs(np.array(size) -
                           np.array(self.colpic_sizes[col])).max() < 10)

        def overlaps():
            x0, x1, y0, y1 = manager.selector.extents
            ref_extents = self.colpic_extents[col]
            i1 = pd.Interval(*ref_extents[:2])
            i2 = pd.Interval(*ref_extents[2:])
            return x0 in i1 or x1 in i1 or y0 in i2 or y1 in i2

        def isclose():
            sel_extents = np.array(manager.selector.extents)
            ref_extents = np.array(self.colpic_extents[col])
            return np.abs(ref_extents - sel_extents).max() < 15

        manager = self.straditizer_widgets.colnames_manager
        if manager.current_col != col:
            self.show_tooltip_at_widget(
                "Column name of the %s column (column %i) is not correct "
                "(%r != %r)!<br><br>"
                "Select the column in the table to edit the name" % (
                    ref, col, curr, ref),
                manager.colnames_table)
        elif same_size():
            self.show_tooltip_at_widget(
                "Column name %r is close. Just set the correct name (%r) in "
                "the table or click 'skip'." % (curr, ref),
                manager.colnames_table)
        elif not manager.btn_select_colpic.isChecked():
            self.show_tooltip_at_widget(
                "Click the %r button to select/modify the image for the "
                "column name" % manager.btn_select_colpic.text(),
                manager.btn_select_colpic)
        elif not overlaps():
            self.show_tooltip_at_widget(
                "Click the %r button to automatically find the column name "
                "end enable it for editing." % manager.btn_find.text(),
                manager.btn_find)
        elif isclose():
            self.show_tooltip_at_widget(
                "Click the %r button or enter the correct name (%r) in the "
                "table" % (manager.btn_recognize.text(), ref),
                manager.colnames_table)
        else:
            self.show_tooltip_at_widget(
                "Edit the shape of the image and click the %r button or "
                "set the correct name (%r) directly in the table." % (
                    manager.btn_recognize.text(), ref),
                manager.btn_recognize)


class RemoveLines(TutorialPage):
    """Tutorial page for removing horizontal and vertical lines"""

    @property
    def is_finished(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        return len(reader.hline_locs) and len(reader.vline_locs)

    def skip(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        if not len(reader.hline_locs):
            reader.recognize_hlines(0.75, min_lw=1, remove=True)
        if not len(reader.vline_locs):
            reader.recognize_vlines(0.3, min_lw=1, max_lw=2, remove=True)
        reader.draw_figure()
        self.clicked_hlines_button()
        self.clicked_vlines_button()
        self.straditizer_widgets.refresh()

    def activate(self):
        self.straditizer_widgets.digitizer.btn_remove_hlines.clicked.connect(
            self.clicked_hlines_button)
        self.straditizer_widgets.digitizer.btn_remove_vlines.clicked.connect(
            self.clicked_vlines_button)

    def deactivate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_remove_hlines.clicked.disconnect(
            self.clicked_hlines_button)
        sw.digitizer.btn_remove_vlines.clicked.disconnect(
            self.clicked_vlines_button)

    hlines_button_clicked = False
    vlines_button_clicked = False

    def clicked_hlines_button(self):
        self.hlines_button_clicked = True

    def clicked_vlines_button(self):
        self.vlines_button_clicked = True

    def hint(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        sw = self.straditizer_widgets
        btn_h = sw.digitizer.btn_remove_hlines
        btn_v = sw.digitizer.btn_remove_vlines
        rc = sw.digitizer.remove_child
        rlc = sw.digitizer.remove_line_child
        lf = float(sw.digitizer.txt_line_fraction.text().strip() or 0)
        if not rc.isExpanded():
            sw.tree.scrollToItem(rc)
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % rc.text(0), sw.tree.itemWidget(rc, 1))
        elif not rlc.isExpanded():
            sw.tree.scrollToItem(rlc)
            self.show_tooltip_at_widget(
                "Expand the <i>remove lines</i> item by clicking on the arrow "
                "to it's left", sw.tree.itemWidget(rlc, 1))
        elif not len(reader.hline_locs):
            if not self.hlines_button_clicked:
                if self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and use the "
                        "<i>%s</i> button." % btn_h.text(), sw.cancel_button)
                elif sw.digitizer.sp_min_lw.value() != 1:
                    self.show_tooltip_at_widget(
                        "Set the minimum line width to 1",
                        sw.digitizer.sp_min_lw)
                else:
                    self.show_tooltip_at_widget(
                        ("Click the <i>%s</i> button to select the"
                         " lines") % btn_h.text(), btn_h)
            else:
                self.show_tooltip_at_widget(
                    "Done! Click the <i>Remove</i> button", sw.apply_button)
        elif not len(reader.vline_locs):
            if not self.vlines_button_clicked:
                if self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and use the "
                        "<i>%s</i> button." % btn_v.text(), sw.cancel_button)
                elif sw.digitizer.sp_min_lw.value() != 1:
                    self.show_tooltip_at_widget(
                        "Set the minimum line width to 1",
                        sw.digitizer.sp_min_lw)
                elif not sw.digitizer.sp_max_lw.isEnabled():
                    self.show_tooltip_at_widget(
                        "Enable the maximum linewidth",
                        sw.digitizer.cb_max_lw)
                elif sw.digitizer.sp_max_lw.value() != 2:
                    self.show_tooltip_at_widget(
                        "Set the maximum line width to 2",
                        sw.digitizer.sp_max_lw)
                elif lf > 30:
                    self.show_tooltip_at_widget(
                        "Set the minimum line fraction to 30%",
                        sw.digitizer.txt_line_fraction)
                else:
                    self.show_tooltip_at_widget(
                        ("Click the <i>%s</i> button to select the"
                         " lines") % btn_v.text(), btn_v)
            else:
                self.show_tooltip_at_widget(
                    "Done! Click the <i>Remove</i> button", sw.apply_button)
        else:
            super().hint()


class TranslateYAxis(TutorialPage):
    """The tutorial page for translating the y-axis"""

    @property
    def is_finished(self):
        return self.straditizer_widgets.straditizer.yaxis_data is not None

    def skip(self):
        self.clicked_correct_button()
        self.straditizer_widgets.straditizer.yaxis_data = np.array([300, 350])
        self.straditizer_widgets.straditizer._yaxis_px_orig = \
            np.array([910, 1045])
        self.straditizer_widgets.refresh()

    def activate(self):
        btn = self.straditizer_widgets.axes_translations.btn_marks_for_y
        btn.clicked.connect(self.clicked_correct_button)

    def deactivate(self):
        btn = self.straditizer_widgets.axes_translations.btn_marks_for_y
        btn.clicked.disconnect(self.clicked_correct_button)

    correct_button_clicked = False

    def clicked_correct_button(self):
        self.correct_button_clicked = True

    def hint(self):
        sw = self.straditizer_widgets
        item = sw.axes_translations_item
        btn = sw.axes_translations.btn_marks_for_y
        marks = sw.straditizer.marks or []
        if self.is_finished:
            super().hint()
        elif not self.is_selecting and not item.isExpanded():
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % item.text(0), sw.tree.itemWidget(item, 1))
        elif not self.correct_button_clicked:
            if self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and use the "
                        "<i>%s</i> button." % btn.text(), sw.cancel_button)
            else:
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to start." % btn.text(), btn)
        elif len(marks) < 2:
            self.show_tooltip_in_plot(
                "<pre>Shift+Leftclick</pre> on a point on the vertical axis "
                "to enter %s y-value" % (
                    "another" if len(marks) else "the corresponding"),
                300, 384)
        elif len(marks) == 2:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to stop the editing." % (
                    sw.apply_button.text()), sw.apply_button)


class TranslateXAxis(TutorialPage):
    """The tutorial page for translating the x-axes"""

    @property
    def is_finished(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        if len(reader.children) < 2:
            return False
        for r in reader.iter_all_readers:
            if r.xaxis_data is None:
                return False
        return True

    def skip(self):
        from straditize.binary import readers
        self.clicked_add_reader_button()
        self.clicked_translations_button()
        reader = self.straditizer_widgets.straditizer.data_reader
        self.straditizer_widgets.refresh()

        # charcoal
        reader = reader.get_reader_for_col(0)
        if len(reader.columns) > 1:
            reader = reader.new_child_for_cols([0], readers['area'])
        reader._xaxis_px_orig = np.array([321, 427])
        reader.xaxis_data = np.array([0., 100.])

        # pollen concentration
        reader = reader.get_reader_for_col(27)
        if len(reader.columns) > 1:
            reader = reader.new_child_for_cols([27], readers['line'])
        reader._xaxis_px_orig = np.array([1776, 1855])
        reader.xaxis_data = np.array([0., 30000.])

        # pollen taxa
        reader = reader.get_reader_for_col(1)
        reader._xaxis_px_orig = np.array([499, 583])
        reader.xaxis_data = np.array([0., 40.])
        self.straditizer_widgets.refresh()

    def refresh(self):
        stradi = self.straditizer_widgets.straditizer
        self.xaxis_translations_button_clicked = (
            stradi is not None and stradi.data_reader is not None and
            stradi.data_reader.xaxis_data is not None)

    def activate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_new_child_reader.clicked.connect(
            self.clicked_add_reader_button)
        sw.axes_translations.btn_marks_for_x.clicked.connect(
            self.clicked_translations_button)

    def deactivate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_new_child_reader.clicked.disconnect(
            self.clicked_add_reader_button)
        sw.axes_translations.btn_marks_for_x.clicked.disconnect(
            self.clicked_translations_button)

    add_reader_button_clicked = []

    xaxis_translations_button_clicked = False

    def clicked_add_reader_button(self):
        self.add_reader_button_clicked = \
            list(self.straditizer_widgets.straditizer.data_reader.columns)
        self.xaxis_translations_button_clicked = False

    def clicked_translations_button(self):
        self.xaxis_translations_button_clicked = True

    def hint_for_col(self, col):
        sw = self.straditizer_widgets
        ax_item = sw.axes_translations_item
        reader_item = sw.digitizer.current_reader_item
        btn_x = sw.axes_translations.btn_marks_for_x
        btn_add = sw.digitizer.btn_new_child_reader
        marks = sw.straditizer.marks or []
        stradi = sw.straditizer
        current = stradi.data_reader
        reader = current.get_reader_for_col(col)
        if col in [0, 27] and len(reader.columns) > 1:
            # no child reader has yet been created
            if not self.is_selecting and not reader_item.isExpanded():
                self.show_tooltip_at_widget(
                    "Expand the <i>%s</i> item by clicking on the arrow to "
                    "it's left" % reader_item.text(0),
                    sw.tree.itemWidget(reader_item, 1))
            elif reader is not current:
                if (self.is_selecting and
                        col not in self.add_reader_button_clicked):
                    self.show_tooltip_at_widget(
                        "Wrong reader selected! Click cancel and use the "
                        "reader for column %i." % col, sw.cancel_button)
                elif self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and initialize "
                        "a new reader for column %i by clicking the "
                        "<i>%s</i> button." % (col, btn_add.text()),
                        sw.cancel_button)
                else:
                    self.show_tooltip_at_widget(
                        "Select the reader for column %i" % col,
                        sw.digitizer.cb_readers)
            else:  # (re-)start the child reader initialization
                if self.is_selecting:
                    if col not in self.add_reader_button_clicked:
                        self.show_tooltip_at_widget(
                            "Wrong button clicked! Click cancel and initialize"
                            " a new reader for column %i by clicking the "
                            "<i>%s</i> button." % (col, btn_add.text()),
                            sw.cancel_button)
                    else:
                        cols = sorted(reader._selected_cols)
                        if cols == [col]:
                            self.show_tooltip_at_widget(
                                "Click the <i>%s</i> button to continue." % (
                                    sw.apply_button.text()), sw.apply_button)
                        elif not cols:
                            self.show_tooltip_in_plot(
                                "Select column %i by clicking on the plot" % (
                                    col, ),
                                reader.all_column_bounds[col].mean(),
                                stradi.data_ylim.mean())
                        else:  # wrong column selected
                            self.show_tooltip_in_plot(
                                "Wrong column selected! Deselect the current "
                                "column and select column %i." % col,
                                reader.all_column_bounds[col].mean(),
                                stradi.data_ylim.mean())
                else:
                    self.show_tooltip_at_widget(
                        "Click the <i>%s</i> button to select a column for "
                        "the new reader" % btn_add.text(), btn_add)
        elif reader._xaxis_px_orig is None:
            if reader is not current:
                self.show_tooltip_at_widget(
                    "Select the reader for column %i" % col,
                    sw.digitizer.cb_readers)
            elif not self.is_selecting and not ax_item.isExpanded():
                self.show_tooltip_at_widget(
                    "Expand the <i>%s</i> item by clicking on the arrow to "
                    "it's left" % ax_item.text(0),
                    sw.tree.itemWidget(ax_item, 1))
            elif not self.xaxis_translations_button_clicked:
                if self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and use the "
                        "<i>%s</i> button." % btn_x.text(), sw.cancel_button)
                else:
                    self.show_tooltip_at_widget(
                        "Click the <i>%s</i> button to start." % btn_x.text(),
                        btn_x)
            elif len(marks) < 2:
                x = reader.all_column_bounds[col].mean()
                self.show_tooltip_in_plot(
                    "<pre>Shift+Leftclick</pre> on a point on the horizontal "
                    "axis to enter %s x-value" % (
                        "another" if len(marks) else "the corresponding"),
                    x, stradi.data_ylim[1])
            elif len(marks) == 2:
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to stop the editing." % (
                        sw.apply_button.text()), sw.apply_button)
        else:
            return True

    def hint(self):
        if self.is_finished:
            super().hint()
        else:
            for col in [0, 27, 1]:
                if not self.hint_for_col(col):
                    break


class EditMeta(TutorialPage):
    """Tutorial page for editing the meta attributes"""

    @property
    def is_finished(self):
        return self.straditizer_widgets.straditizer.attrs.iloc[:11, 0].any()

    def skip(self):
        for attr, val in zip(
                ['sitename', 'Archive', 'Country', 'Restricted',
                 'Y-axis name', 'Lon', 'Lat', 'Reference', 'DOI'],
                ['Hoya del Castillo', 'Pollen', 'Spain', 'No', 'Depth (cm)',
                 '-0.5', '41.25',
                 ('Davis, Basil A. S., and A. C. Stevenson. "The 8.2ka Event '
                  'and Early-Mid Holocene Forests, Fires and Flooding in the '
                  'Central Ebro Desert, NE Spain." Quat. Sci. Rev. , vol. 26, '
                  'no. 13-14, 2007, pp. 1695-712'),
                 '10.1016/j.quascirev.2007.04.007']):
            self.straditizer_widgets.straditizer.set_attr(attr, val)

    def hint(self):
        from psyplot_gui.main import mainwindow
        df = self.straditizer_widgets.straditizer.attrs
        btn = self.straditizer_widgets.attrs_button
        editor = next((editor for editor in mainwindow.dataframeeditors
                       if editor.table.model().df is df), None)
        if editor is None:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to edit the meta data" % (
                    btn.text()), btn)
        elif not self.is_finished:
            # Check if the editor is visible
            if editor.visibleRegion().isEmpty():
                dock = next(
                    (d for d in mainwindow.tabifiedDockWidgets(editor.dock)
                     if not d.visibleRegion().isEmpty()), None)
                tooltip = "Click the %s tab to see the attributes" % (
                    editor.title)
                if dock is None:
                    self.show_tooltip_at_widget(
                        tooltip, self.straditizer_widgets)
                else:
                    point = dock.pos()
                    point.setY(point.y() + dock.size().height())
                    point.setX(point.x() + int(dock.size().width() / 2))
                    QtWidgets.QToolTip.showText(
                        dock.parent().mapToGlobal(point), tooltip, dock,
                        dock.rect(), 10000)
            else:
                self.show_tooltip_at_widget(
                    "Add some meta information in the first column",
                    editor.table)
        else:
            super().hint()
