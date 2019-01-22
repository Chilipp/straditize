"""Progress widget for the straditization

The ProgressWidget defined here is a ListWidget to show the current state
of the stradititization.

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
import os.path as osp
import datetime as dt
from PyQt5 import QtWidgets, QtGui, QtCore
import numpy as np
import pandas as pd
from psyplot_gui.common import get_icon as get_psy_icon
from straditize.widgets import StraditizerControlBase, get_doc_file, doc_files
from collections import OrderedDict
from straditize.widgets.data import get_reader_name, int_list2str


ALL_TASKS = 'all'
DONE = 'done'
NOTYET = 'not yet ready'
TASK_TODO = 'todo'


icons = {DONE: get_psy_icon('valid.png'),
         NOTYET: get_psy_icon('warning.png'),
         TASK_TODO: get_psy_icon('invalid.png'),
         }


class ProgressTask(QtWidgets.QListWidgetItem):
    """The base class for an item that should be shown in the ProgressWidget"""

    @property
    def is_finished(self):
        """A property that is True, when the task is finished"""
        return True

    @property
    def try_finished(self):
        """Same as :attr:`is_finished` but catches every exception"""
        try:
            return self.is_finished
        except Exception:
            pass

    @property
    def done_by_user(self):
        """boolean that is True, when the task is marked as done by the user"""
        stradi = self.straditizer
        return stradi is not None and self.name in stradi._done_tasks

    @done_by_user.setter
    def done_by_user(self, value):
        stradi = self.straditizer
        if stradi is not None:
            if value:
                stradi._done_tasks.add(self.name)
            else:
                stradi._done_tasks.difference_update({self.name})

    #: Boolean that is True if the task is ready to be solved
    is_ready = True

    @property
    def done(self):
        """True if :attr:`is_finished` or :attr:`done_by_user`"""
        return self.done_by_user or (
            self.is_ready and all(t.done for t in self.dependencies_tasks) and
            self.try_finished)

    #: The name of the task
    name = ''

    #: The summary of the task that is shown in the progress widget
    summary = ''

    #: The tooltip of the item
    task_tooltip = ''

    #: The tooltip when the straditizer is done. If None, the
    #: :attr:`task_tooltip` is used
    done_tooltip = None

    #: List of :attr:`name` attributes that this task is depending on
    dependencies = []

    #: rst file that should be displayed on double click. The filename shuould
    #: be without .rst ending.
    rst_file = None

    @property
    def dependencies_tasks(self):
        list_widget = self.listWidget()
        dependencies = self.dependencies
        return [item for item in map(list_widget.item,
                                     range(list_widget.count()))
                if item.name in dependencies]

    @property
    def progress_widget(self):
        """The progress widget that shows this task"""
        return self.listWidget().parent()

    @property
    def straditizer(self):
        """The straditizer of the GUI"""
        return self.progress_widget.straditizer

    @property
    def data_reader(self):
        """The data reader of the straditizer"""
        return self.straditizer.data_reader

    @property
    def colnames_reader(self):
        """The column names reader of the straditizer"""
        return self.straditizer.colnames_reader

    @property
    def state(self):
        """The state of the task"""
        if self.done:
            return DONE
        elif not self.is_ready or not all(
                task.done for task in self.dependencies_tasks):
            return NOTYET
        else:
            return TASK_TODO

    def refresh(self):
        pw = self.progress_widget
        state = self.state
        icon = icons[state]
        visible = pw.visible_tasks in ['all', state]
        self.setIcon(QtGui.QIcon(icon))
        self.setHidden(not visible)
        if self.done:
            try:
                tt = self.done_tooltip
            except Exception:
                tt = ''
            if tt is None:
                tt = self.task_tooltip
        else:
            tt = self.task_tooltip
        self.setToolTip(tt)

    def __init__(self, parent):
        """
        Parameters
        ----------
        parent: QListWidget
            The list that holds this item
        """
        super().__init__(self.summary, parent)


class InitStraditizerTask(ProgressTask):
    """The task to initialize a straditizer"""

    name = 'init_stradi'

    summary = 'Load an image or project'

    task_tooltip = 'Load a straditizer image or project to get started'

    rst_file = 'load_image'

    @property
    def done_tooltip(self):
        try:
            image = self.straditizer.get_attr('image_file')
        except KeyError:
            return "Loaded diagram"
        else:
            return "Loaded " + (osp.basename(image) if image else "diagram")

    @property
    def is_finished(self):
        return self.straditizer is not None


class DataLimitsTask(ProgressTask):
    """The task to check the data limits"""

    name = 'datalim'

    summary = 'Limits of the diagram'

    task_tooltip = ('Specify the corners for the data part of the diagram by '
                    'clicking the <i>Select data part</i> button')

    rst_file = 'select_data_part'

    dependencies = ['init_stradi']

    @property
    def done_tooltip(self):
        stradi = self.straditizer
        return "Data limits are set to x={} and y={}".format(
            tuple(stradi.data_xlim), tuple(stradi.data_ylim))

    @property
    def is_finished(self):
        return self.straditizer.data_xlim is not None


class DataReaderTask(ProgressTask):
    """A task for initializing the reader"""

    name = 'init_reader'

    summary = 'Initialize the diagram reader'

    task_tooltip = ('Choose the appropriate reader type and click the '
                    '<i>Convert image</i> button')

    rst_file = 'select_reader'

    dependencies = ['datalim']

    @property
    def is_finished(self):
        return self.straditizer.data_reader is not None

    @property
    def done_tooltip(self):
        reader = self.straditizer.data_reader
        return "Initialized <i>%s</i> reader" % (get_reader_name(reader) or '')


class ColumnsTask(ProgressTask):
    """A task to separate columns"""

    name = 'columns'

    summary = 'Separate the columns'

    task_tooltip = ('Separate the columns (subdiagrams) of the stratigraphic '
                    'diagram')

    rst_file = 'select_column_starts'

    dependencies = ['init_reader']

    @property
    def is_finished(self):
        return self.data_reader._column_starts is not None

    @property
    def done_tooltip(self):
        ncols = len(self.data_reader._column_starts)
        return 'Marked %i columns' % ncols


class RemoveArtifactsTask(ProgressTask):
    """Task to clean the binary image"""

    name = 'remove_artifacts'

    summary = 'Clean the diagram image'

    task_tooltip = ('Remove all artifacts in the diagram part that do not '
                    'represent data. Mark this task as done when you are '
                    'finished.')

    rst_file = 'removing_features'

    dependencies = ['columns']

    @property
    def is_finished(self):
        return (self.data_reader._full_df is not None and
                len(self.data_reader._full_df))

    @property
    def done_tooltip(self):
        if self.try_finished:
            return 'The data has been digitized'


class RemoveLinesTask(RemoveArtifactsTask):
    """Task to remove y-axes, x-axes, horizontal and vertical lines"""

    name = 'remove_lines'

    summary = 'Remove y-, x-axes and other lines'

    task_tooltip = ('In order to clean the diagram part, remove all vertical '
                    'and horizontal lines in the reader image. Mark this task '
                    'as done when you are finished.')

    rst_file = 'remove_lines'

    dependencies = ['columns']

    @property
    def is_finished(self):
        return (len(self.data_reader.vline_locs) and
                len(self.data_reader.hline_locs)) or super().is_finished

    @property
    def done_tooltip(self):
        if (len(self.data_reader.vline_locs) and
                len(self.data_reader.hline_locs)):
            return '%i vertical and %i horizontal lines have been removed' % (
                len(self.data_reader.vline_locs),
                len(self.data_reader.hline_locs))
        else:
            return super().done_tooltip


class OccurencesTask(ProgressTask):
    """Task to handle occurences"""

    name = 'occurences'

    summary = 'Select occurence markers'

    task_tooltip = ('Pollen diagrams often have markers for low taxon '
                    'percentages to show their occurence. Mark this task as '
                    'done if your diagram does not have them.')

    rst_file = 'occurences'

    dependencies = ['columns']

    @property
    def is_finished(self):
        return bool(self.data_reader.occurences)

    @property
    def done_tooltip(self):
        return "Marked %i occurences" % len(self.data_reader.occurences)


class SelectExaggerationsTask(ProgressTask):
    """Task to handle exaggerations"""

    name = 'exag'

    summary = 'Select exagerations'

    task_tooltip = ('Pollen diagrams often display an exaggerated value of '
                    'of the taxon percentage. You can select these '
                    'exaggerations using the <i>Exaggerations</i> menu. '
                    'Mark this task as done if your diagram does not have '
                    'them.')

    rst_file = 'exaggerations'

    dependencies = ['columns']

    @property
    def is_finished(self):
        return self.data_reader.exaggerated_reader is not None

    @property
    def done_tooltip(self):
        return "Created exaggerations reader"


class DigitizeTask(ProgressTask):
    """Task to digitize the data"""

    name = 'digitize'

    summary = 'Digitize the diagram'

    task_tooltip = 'Click the `Digitize` button to digitize the diagram'

    rst_file = 'digitize'

    dependencies = ['remove_artifacts', 'remove_lines']

    @property
    def is_finished(self):
        return (self.data_reader._full_df is not None and
                len(self.data_reader._full_df))

    @property
    def done_tooltip(self):
        if self.try_finished:
            return 'The data has been digitized'


class SamplesTask(ProgressTask):
    """Task to edit and find samples"""

    name = 'samples'

    summary = 'Find and edit the samples'

    rst_file = 'samples'

    task_tooltip = 'Find and edit the samples using the `Edit samples` menu'

    dependencies = ['digitize']

    @property
    def is_finished(self):
        locs = self.data_reader._sample_locs
        return locs is not None and len(locs)

    @property
    def done_tooltip(self):
        return 'Found %i samples' % len(self.data_reader._sample_locs)


class YTranslationTask(ProgressTask):
    """Task to specify the y-axis conversion from pixel to data units"""

    name = 'yaxis_trans'

    summary = "Transform the y-axis"

    rst_file = 'yaxis_translation'

    task_tooltip = "Transform the y-axis from pixel to data units"

    dependencies = ['init_reader']

    @property
    def is_finished(self):
        return self.straditizer._yaxis_px_orig is not None

    @property
    def done_tooltip(self):
        px2data = self.straditizer.px2data_y
        return "Transforming 1 pixel to %1.4g data units" % (
            np.diff(px2data(np.array([0, 1])))[0])


class XTranslationTask(ProgressTask):
    """Task to specify the x-axes conversion from pixel to data units"""

    name = 'xaxes_trans'

    summary = 'Transform the x-axes'

    rst_file = 'xaxis_translation'

    dependencies = ['columns']

    @property
    def task_tooltip(self):
        try:
            finished = self.is_finished
        except AttributeError:
            return "Transform the x-axes from pixel to data units"
        else:
            if finished:
                return self.done_tooltip
            elif self.data_reader._column_starts is None:
                return "Transform the x-axes from pixel to data units"
            else:
                reader = self.data_reader
                columns = [r.columns for r in reader.iter_all_readers
                           if r._xaxis_px_orig is None and
                           not r.is_exaggerated]
                return ("Transform the x-axes from pixel to data units for "
                        "columns<ul>%s</ul>" % (
                            ''.join('<li>%s</li>' % int_list2str(cols)
                                    for cols in columns)))

    @property
    def is_finished(self):
        return (self.data_reader._column_starts is not None and
                all(reader._xaxis_px_orig is not None
                    for reader in self.data_reader.iter_all_readers))

    @property
    def done_tooltip(self):
        reader = self.data_reader
        readers = filter(lambda r: not r.is_exaggerated,
                         reader.iter_all_readers)
        ret = "Transforming 1 pixel to<ul>"
        for reader in readers:
            s = reader.column_starts[0]
            px2data = reader.px2data_x
            ret += "<li>%1.4g data units for columns %s</li>" % (
                np.diff(px2data(np.array([s, s+1])))[0],
                int_list2str(reader.columns))
        return ret + "</ul>"


class ColumnNamesTask(ProgressTask):
    """Task to specify the column names"""

    name = 'column_names'

    summary = 'Specify the column names'

    task_tooltip = ('Click the <i>Edit column names</i> button to insert the '
                    'names for each column/variable in the diagram')

    rst_file = 'column_names'

    dependencies = ['columns']

    @property
    def is_finished(self):
        return self.colnames_reader.column_names != list(map(
            str, range(len(self.data_reader.all_column_starts))))

    @property
    def done_tooltip(self):
        return "The column names are " + ', '.join(
            self.colnames_reader.column_names)


class ExportTask(ProgressTask):
    """Task to export the final results"""

    name = 'export'

    summary = 'Export the final data'

    task_tooltip = 'Export the final data'

    rst_file = 'export'

    dependencies = ['samples']

    @property
    def is_finished(self):
        return self.straditizer.get_attr('exported') is not None

    @property
    def done_tooltip(self):
        return "Exported to {}".format(self.straditizer.get_attr('exported'))


class SaveProjectTask(ProgressTask):
    """Task to remember saving the project"""

    name = 'save_project'

    summary = 'Save the straditizer'

    dependencies = ['init_stradi']

    rst_file = 'save_and_load'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refresh_timer = QtCore.QTimer(self.progress_widget)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(60000)
        self.tooltip_timer = QtCore.QTimer(self.progress_widget)
        self.tooltip_timer.timeout.connect(self.refresh_tooltip)
        self.tooltip_timer.start(5000)

    def refresh_tooltip(self):
        self.setToolTip(self.task_tooltip)

    @property
    def is_finished(self):
        """True if the project was saved less than 5 minutes ago"""
        try:
            loaded = self.straditizer.get_attr('loaded')
        except (KeyError, AttributeError):
            pass
        else:
            if (dt.datetime.now() - pd.to_datetime(loaded)).seconds < 300:
                return True
        saved = self.straditizer.get_attr('saved')
        td = dt.datetime.now() - pd.to_datetime(saved)
        return td.seconds < 300

    @property
    def task_tooltip(self):
        try:
            saved = self.straditizer.get_attr('saved')
        except KeyError:
            return "The Project has never been saved!"
        except AttributeError:
            return "No project is open to save"
        else:
            try:
                loaded = self.straditizer.get_attr('loaded')
            except (KeyError, AttributeError):
                pass
            else:
                if saved < loaded:
                    return 'The project has not been saved in this session'
            td = dt.datetime.now() - pd.to_datetime(saved)
            return 'Last saved %i minutes and %i seconds ago' % (
                (td.seconds // 60) % 60, td.seconds % 60)

    def tooltip(self):
        return self.task_tooltip


class ProgressWidget(QtWidgets.QWidget, StraditizerControlBase):
    """A widget to show the progress of the straditization"""

    #: A QListWidget to display the :class:`ProgressTask` instances
    progress_list = None

    #: A QComboBox to select which tasks to display (todo, done, not yet ready
    #: or all tasks)
    combo_display = None

    #: A QLabel to display the tooltip of the selected task
    info_label = None

    def __init__(self, straditizer_widgets, item):
        super().__init__()
        self.init_straditizercontrol(straditizer_widgets, item)

        self.combo_display = QtWidgets.QComboBox()
        self.combo_display.setEditable(False)

        for state in [TASK_TODO, DONE, NOTYET]:
            self.combo_display.addItem(QtGui.QIcon(icons[state]), state)
        self.combo_display.addItem(ALL_TASKS)

        self.progress_list = QtWidgets.QListWidget()
        self.info_label = QtWidgets.QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet('border: 1px solid black')

        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(self.combo_display)
        vbox.addWidget(self.progress_list)
        vbox.addWidget(self.info_label)
        self.setLayout(vbox)

        self.populate_list()
        self.setup_menu()
        self.refresh()
        self.combo_display.currentIndexChanged.connect(self.refresh)
        self.progress_list.itemDoubleClicked.connect(self.show_rst)
        self.progress_list.currentItemChanged.connect(self.show_rst)
        self.progress_list.currentItemChanged.connect(self.update_info_label)

    def update_info_label(self, item, old=None):
        """Update the :attr:`info_label` from a :class:`ProgressTask`

        Parameters
        ----------
        item: ProgressTask
            The selected task whose tooltip the :attr:`info_label` shall
            display
        old: ProgressTask
            The old task that has been selected previously (this parameter is
            ignored)"""
        tt = item.toolTip()
        self.info_label.setText(tt)
        self.info_label.setVisible(bool(tt.strip()) and not item.isHidden())

    def show_rst(self, item, old=None):
        """Show the documentation corresponding to a :class:`ProgressTask

        Parameters
        ----------
        item: ProgressTask
            The task to display it's :attr:`rst_file` in the
            :attr:`psyplot_gui.main.MainWindow.help_explorer`
        old: ProgressTask
            The old task that has been selected previously (this parameter is
            ignored)"""
        from psyplot_gui.main import mainwindow
        if item.rst_file:
            try:
                mainwindow.help_explorer.viewer.browse(item.rst_file)
                self.progress_list.setFocus()
            except AttributeError:
                with open(get_doc_file(item.rst_file + '.rst')) as f:
                    doc = f.read()
                mainwindow.help_explorer.show_rst(
                    doc, item.rst_file,
                    files=list(set(doc_files) - {item.rst_file}))

    def setup_menu(self):
        """Set up the context menu"""
        self.menu = menu = QtWidgets.QMenu(self)
        self._done_action = menu.addAction(
            'Mark as done', self.toggle_done_by_user)
        menu.addAction('Show docs', lambda: self.show_rst(
            self.progress_list.selectedItems()[0]))

    def toggle_done_by_user(self):
        item = self.progress_list.selectedItems()[0]
        current = item.done_by_user
        item.done_by_user = not current
        self.refresh()

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        items = self.progress_list.selectedItems()
        if items:
            action = self._done_action
            action.setEnabled(self.straditizer is not None)
            item = items[0]
            finished = item.try_finished
            if item.done_by_user and not finished:
                action.setText('Mark as undone')
            elif not finished:
                action.setText('Mark as done')
            else:
                action.setEnabled(False)
            self.menu.popup(event.globalPos())
            event.accept()

    def populate_list(self):
        """Populate the :attr:`progress_list`

        This method adds instances of the :class:`ProgressTask` class (or it's
        subclasses) to the the :attr:`progress_list`"""
        pl = self.progress_list
        pl.addItem(InitStraditizerTask(pl))
        pl.addItem(DataLimitsTask(pl))
        pl.addItem(DataReaderTask(pl))
        pl.addItem(ColumnsTask(pl))
        pl.addItem(RemoveArtifactsTask(pl))
        pl.addItem(RemoveLinesTask(pl))
        pl.addItem(SelectExaggerationsTask(pl))
        pl.addItem(DigitizeTask(pl))
        pl.addItem(SamplesTask(pl))
        pl.addItem(YTranslationTask(pl))
        pl.addItem(XTranslationTask(pl))
        pl.addItem(ColumnNamesTask(pl))
        pl.addItem(ExportTask(pl))
        pl.addItem(SaveProjectTask(pl))

    def refresh(self):
        progress_list = self.progress_list

        states = OrderedDict([(TASK_TODO, 0), (DONE, 0), (NOTYET, 0),
                              (ALL_TASKS, progress_list.count())])
        self.visible_tasks = list(states.keys())[
            self.combo_display.currentIndex()]

        for item in map(progress_list.item, range(progress_list.count())):
            item.refresh()
            states[item.state] += 1

        for i, (state, count) in enumerate(states.items()):
            self.combo_display.setItemText(
                i, '%i task%s %s' % (count, 's' if count > 1 else '', state))
        self.combo_display.setItemText(
            3, 'all %i tasks' % progress_list.count())
        if not self.progress_list.selectedItems():
            self.info_label.setVisible(False)
        else:
            self.update_info_label(self.progress_list.selectedItems()[0])
