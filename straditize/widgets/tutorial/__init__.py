"""The tutorial of straditize

This module contains a guided tour through straditize"""
import os.path as osp
import glob
from itertools import chain
import numpy as np
from straditize.widgets import StraditizerControlBase
import straditize.cross_mark as cm
from PyQt5 import QtWidgets, QtCore, QtGui
from psyplot_gui.common import get_icon as get_psy_icon


class TutorialNavigation(QtWidgets.QWidget):
    """A widget for navigating through the tutorial. It has a button to go
    to the previous step and to go to the next step. Furthermore it has a
    progressbar implemented a `hint` button"""

    #: Signal that is emitted, when the step changes. The first integer is the
    #: old step, the second one the current step
    step_changed = QtCore.pyqtSignal(int, int)

    #: Signal that is emitted if the hint of the current step is requested
    hint_requested = QtCore.pyqtSignal(int)

    #: Signal that is emitted, if the step is skipped
    skipped = QtCore.pyqtSignal(int)

    #: The current step in the tutorial
    current_step = 0

    def __init__(self, nsteps, validate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = True
        self.nsteps = nsteps
        self.validate = validate

        self.lbl_progress = QtWidgets.QLabel()

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(1)
        self.progress_bar.setMaximum(nsteps + 1)

        self.btn_prev = QtWidgets.QPushButton('Back')
        self.btn_next = QtWidgets.QPushButton('Next')
        self.btn_skip = QtWidgets.QPushButton('Skip')
        self.btn_hint = QtWidgets.QPushButton('Hint')
        self.btn_info = QtWidgets.QToolButton()
        self.btn_info.setIcon(QtGui.QIcon(get_psy_icon('info.png')))

        self.set_current_step(0)

        # ---------------------------------------------------------------------
        # --------------------------- Layouts ---------------------------------
        # ---------------------------------------------------------------------

        layout = QtWidgets.QVBoxLayout()
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.lbl_progress)
        hbox.addStretch(0)
        hbox.addWidget(self.btn_info)
        layout.addLayout(hbox)
        layout.addWidget(self.progress_bar)

        button_box = QtWidgets.QHBoxLayout()
        button_box.addWidget(self.btn_prev)
        button_box.addStretch(0)
        button_box.addWidget(self.btn_hint)
        button_box.addWidget(self.btn_skip)
        button_box.addStretch(0)
        button_box.addWidget(self.btn_next)

        layout.addLayout(button_box)

        self.setLayout(layout)

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------
        self.btn_prev.clicked.connect(self.goto_prev_step)
        self.btn_next.clicked.connect(self.goto_next_step)
        self.btn_hint.clicked.connect(self.display_hint)
        self.btn_skip.clicked.connect(self.skip)
        self.btn_info.clicked.connect(self.show_info)

    def setEnabled(self, enable):
        for w in [self.btn_prev, self.btn_next, self.btn_skip, self.btn_info]:
            w.setEnabled(enable)
        if enable:
            self.maybe_enable_widgets()
        self.enabled = enable

    def maybe_enable_widgets(self):
        i = self.current_step
        if i == 0:
            self.btn_next.setEnabled(True)
            self.btn_skip.setEnabled(False)
            self.btn_hint.setEnabled(True)
        elif i < self.nsteps + 1:
            self.btn_next.setEnabled(True)
            self.btn_skip.setEnabled(True)
            self.btn_hint.setEnabled(True)
        else:
            self.btn_next.setEnabled(False)
            self.btn_skip.setEnabled(False)
            self.btn_hint.setEnabled(False)
        self.btn_prev.setEnabled(i > 0)

    def show_info(self):
        self.step_changed.emit(self.current_step, self.current_step)

    def display_hint(self):
        self.hint_requested.emit(self.current_step)

    def set_current_step(self, i):
        self.current_step = i
        self.progress_bar.setValue(i)
        self.btn_next.setText('Next')
        if i == 0:
            self.lbl_progress.setText('Start by clicking the %s button' % (
                self.btn_next.text()))
        elif i < self.nsteps + 1:
            self.lbl_progress.setText('Step %i/%i' % (i, self.nsteps))
        else:
            self.progress_bar.setValue(i+1)
            self.lbl_progress.setText('Done!')
            self.btn_next.setText('Done')
        self.maybe_enable_widgets()

    def goto_next_step(self):
        if self.validate(self.current_step):
            if self.current_step <= self.nsteps:
                self.set_current_step(self.current_step + 1)
                self.step_changed.emit(self.current_step - 1,
                                       self.current_step)
            else:
                self.set_current_step(self.current_step)

    def goto_prev_step(self):
        if self.current_step > 0:
            self.set_current_step(self.current_step - 1)
            self.step_changed.emit(self.current_step + 1, self.current_step)

    def skip(self):
        self.skipped.emit(self.current_step)
        self.goto_next_step()


class TutorialPage(object):
    """A base class for the tutorial pages

    Subclasses show implement the :meth:`show_hint` method and the
    :meth:`is_finished` property"""

    src_dir = osp.join(osp.dirname(__file__), 'docs')

    src_base = 'straditize-tutorial.png'

    src_file = osp.join(src_dir, src_base)

    def __init__(self, filename, tutorial):
        self.filename = filename
        self.tutorial = tutorial
        self.straditizer_widgets = self.tutorial.straditizer_widgets

    def show_hint(self):
        """Show a hint to the user"""
        pass

    def activate(self):
        """Method that is called, when the page is activated"""
        pass

    def deactivate(self):
        """Method that is called, when the page is deactivated"""
        pass

    def hint(self):
        """A method that should display a hint to the user"""
        btn = self.tutorial.navigation.btn_next
        self.show_tooltip_at_widget(
            "Click the %r button for the next step" % btn.text(), btn)

    def skip(self):
        """Skip the steps in this page"""
        pass

    def refresh(self):
        pass

    @property
    def is_finished(self):
        """Boolean that is True, if the steps are all finished"""
        return True

    def lock_viewer(self, lock):
        """Set or unset the url lock of the HTML viewer"""
        from psyplot_gui.main import mainwindow
        try:
            mainwindow.help_explorer.viewer.bt_lock.setChecked(lock)
        except AttributeError:
            pass

    def show(self):
        from psyplot_gui.main import mainwindow
        try:
            self.lock_viewer(False)
            mainwindow.help_explorer.viewer.browse(self.filename)
            self.lock_viewer(True)
        except AttributeError:
            with open(osp.join(self.src_dir, self.filename + '.rst')) as f:
                rst = f.read()
            mainwindow.help_explorer.show_rst(rst, self.filename)

    def show_tooltip_at_widget(self, tooltip, widget, timeout=20000):
        """Show a tooltip close to a widget

        Parameters
        ----------
        tooltip: str
            The tooltip to display
        widget: QWidget
            The widget that should be close to the tooltip
        timeout: int
            The time that the tool tip shall be displayed, in milliseconds"""
        QtWidgets.QToolTip.showText(
            widget.parent().mapToGlobal(widget.pos()), tooltip, widget,
            self.straditizer_widgets.rect(), timeout)

    def show_tooltip_in_plot(self, tooltip, x, y, timeout=20000,
                             transform=None):
        """Show a tooltip in the matplotlib figure at the given coordinates

        Parameters
        ----------
        tooltip: str
            The tooltip to display
        x: float
            The x-coordinate of where to display the tooltip
        y: float
            The y-coordinate of where to display the tooltip
        timeout: int
            The time that the tool tip shall be displayed, in milliseconds
        transform: matplotlib transformation
            The matplotlib transformation to use. If None, the
            :attr:`self.stradi.ax.transData` transformation is used and
            `x` and `y` are expected to be in data coordinates"""
        stradi = self.straditizer_widgets.straditizer
        fig = stradi.ax.figure
        canvas = fig.canvas
        # only implemented for PyQt backend
        if not isinstance(canvas, QtWidgets.QWidget):
            return
        if transform is None:
            transform = stradi.ax.transData
            ax = stradi.ax
            xl = sorted(ax.get_xlim())
            yl = sorted(ax.get_ylim())
            if xl[0] > x or xl[1] < x:
                x = np.mean(xl)
            if yl[0] > y or yl[1] < y:
                y = np.mean(yl)
        x, y = fig.transFigure.inverted().transform(
            transform.transform([x, y]))
        size = canvas.size()
        height = size.height()
        width = size.width()
        point = canvas.mapToGlobal(
            QtCore.QPointF(x * width, height - y * height).toPoint())
        QtWidgets.QToolTip.showText(
            point, tooltip, canvas, canvas.rect(), timeout)

    @property
    def is_selecting(self):
        """True if the user clicked the btn_select_data button"""
        return self.straditizer_widgets.apply_button.isEnabled()


class Tutorial(StraditizerControlBase, TutorialPage):
    """A tutorial for digitizing an area diagram"""

    @property
    def current_page(self):
        return self.pages[self.navigation.current_step]

    def __init__(self, straditizer_widgets):
        self.init_straditizercontrol(straditizer_widgets)
        self.tutorial = self

        self.setup_tutorial_pages()

        self.navigation = TutorialNavigation(len(self.pages) - 2,
                                             self.validate_page)
        layout = straditizer_widgets.layout()
        layout.insertWidget(layout.count() - 1, self.navigation)
        self.navigation.step_changed.connect(self.goto_page)
        self.navigation.hint_requested.connect(self.display_hint)
        self.navigation.skipped.connect(self.skip_page)
        self.show()

    def get_doc_files(self):
        """Get the rst files for the tutorial

        Returns
        -------
        str
            The path to the tutorial introduction file
        list of str
            The paths of the remaining tutorialpdc files"""
        files = glob.glob(osp.join(self.src_dir, '*.rst')) + \
            glob.glob(osp.join(self.src_dir, '*.png'))
        intro = files.pop(next(
            i for i, f in enumerate(files)
            if osp.basename(f) == 'straditize_tutorial_intro.rst'))
        return intro, files

    def show(self):
        """Show the documentation of the tutorial"""
        from psyplot_gui.main import mainwindow
        intro, files = self.get_doc_files()
        self.filename = osp.splitext(osp.basename(intro))[0]
        mainwindow.help_explorer.set_viewer('HTML help')
        with open(intro) as f:
            rst = f.read()
        name = osp.splitext(osp.basename(intro))[0]
        self.lock_viewer(False)
        mainwindow.help_explorer.show_rst(rst, name, files=files)

    def setup_tutorial_pages(self):
        self.pages = [
            self,
            LoadImage('straditize_tutorial_load_image', self),
            SelectDataPart('straditize_tutorial_select_data', self),
            CreateReader('straditize_tutorial_create_reader', self),
            SeparateColumns('straditize_tutorial_column_starts', self),
            RemoveLines('straditize_tutorial_remove_lines', self),
            DigitizePage('straditize_tutorial_digitize', self),
            SamplesPage('straditize_tutorial_samples', self),
            TranslateYAxis('straditize_tutorial_yaxis_translation', self),
            TranslateXAxis('straditize_tutorial_xaxis_translation', self),
            EditMeta('straditize_tutorial_meta', self),
            FinishPage('straditize_tutorial_finish', self),
            ]

    def refresh(self):
        stradi = self._get_tutorial_stradi()
        enable = stradi is None or self.straditizer is stradi
        self.navigation.setEnabled(enable)
        for page in self.pages[1:]:
            page.refresh()
        if stradi is None and self.navigation.current_step > 1:
            self.navigation.set_current_step(1)

    def _get_tutorial_stradi(self):
        src_file = self.src_base
        get_attr = self.straditizer_widgets.get_attr
        for stradi in self.straditizer_widgets._straditizers:
            if osp.basename(get_attr(stradi, 'image_file')) == src_file:
                return stradi

    def close(self):
        """Close the tutorial and remove the widgets"""
        stradi = self._get_tutorial_stradi()
        if stradi is not None:
            self.straditizer_widgets._close_stradi(stradi)
        if hasattr(self, 'navigation'):
            self.straditizer_widgets.layout().removeWidget(self.navigation)
            self.navigation.close()
            del self.navigation
            del self.straditizer_widgets.tutorial
            del self.straditizer_widgets
            del self.pages

    def goto_page(self, old, new):
        self.pages[old].deactivate()
        page = self.pages[new]
        page.show()
        page.activate()

    def skip_page(self, i):
        self.pages[i].skip()

    def display_hint(self, i):
        stradi = self._get_tutorial_stradi()
        if stradi is None and i > 1:
            self.navigation.set_current_step(1)
        elif stradi is not self.straditizer:
            self.show_tooltip_at_widget(
                "Select the straditizer for the <i>%s</i> diagram" % (
                    self.src_base), self.straditizer_widgets.stradi_combo)
        else:
            self.pages[i].hint()

    def validate_page(self, i, silent=False):
        ret = self.pages[i].is_finished
        if not silent and not ret:
            self.navigation.display_hint()
        return ret


class LoadImage(TutorialPage):
    """TutorialPage for loading the straditizer image"""

    def activate(self):
        sw = self.straditizer_widgets
        sw.menu_actions._dirname_to_use = self.src_dir

    def deactivate(self):
        self.straditizer_widgets.menu_actions._dirname_to_use = None

    @property
    def is_finished(self):
        stradi = self.tutorial.straditizer
        return stradi is not None and (
            osp.basename(
                self.straditizer_widgets.get_attr(stradi, 'image_file')) ==
            self.src_base)

    def hint(self):
        if self.is_finished:
            super().hint()
        else:
            self.show_tooltip_at_widget(
                'Click here to load the <i>%s</i> image' % self.src_base,
                self.straditizer_widgets.btn_open_stradi)

    def skip(self):
        self.straditizer_widgets.menu_actions.open_straditizer(self.src_file)


class SelectDataPart(TutorialPage):
    """TutorialPage for selecting the data part"""

    #: The reference x- and y- limits
    ref_lims = np.array([[315, 1946], [511, 1311]])

    #: Valid ranges for xmin and xmax
    valid_xlims = np.array([[310, 319], [1928, 1960]])

    #: Valid ranges for ymin and ymax
    valid_ylims = np.array([[508, 513], [1307, 1312]])

    marks = []

    @property
    def is_finished(self):
        stradi = self.tutorial.straditizer
        refx, refy = self.ref_lims
        if stradi.data_xlim is None:
            return False
        for val, lim in zip(chain(stradi.data_xlim, stradi.data_ylim),
                            chain(self.valid_xlims, self.valid_ylims)):
            if not lim.searchsorted(val) == 1:
                return False
        return True

    def activate(self):
        self.straditizer_widgets.digitizer.btn_select_data.clicked.connect(
            self.clicked_correct_button)

    def deactivate(self):
        self.straditizer_widgets.digitizer.btn_select_data.clicked.disconnect(
            self.clicked_correct_button)

    correct_button_clicked = False

    def clicked_correct_button(self):
        self.correct_button_clicked = True

    def display_reference_marks(self):
        stradi = self.straditizer_widgets.straditizer
        p1, p2 = zip(*self.ref_lims)
        try:  # interrupt the current timer
            self.timer.stop()
        except AttributeError:
            pass
        else:
            for t in self.timer.callbacks:
                t[0]()
        self.marks = marks = [
            cm.CrossMarks(p1, ax=stradi.ax, selectable=[], c='r', alpha=0.5),
            cm.CrossMarks(p2, ax=stradi.ax, selectable=[], c='r', alpha=0.5)]
        stradi.draw_figure()
        self.timer = timer = stradi.ax.figure.canvas.new_timer(10000)
        timer.single_shot = True
        timer.add_callback(marks[0].remove)
        timer.add_callback(marks[1].remove)
        timer.add_callback(marks.clear)
        timer.add_callback(stradi.draw_figure)
        timer.add_callback(timer.stop)
        timer.add_callback(lambda: delattr(self, 'timer'))
        timer.start()

    def skip(self):
        stradi = self.straditizer_widgets.straditizer
        stradi.data_xlim, stradi.data_ylim = self.ref_lims
        self.straditizer_widgets.refresh()
        self.clicked_correct_button()

    def is_valid_x(self, x):
        return np.array([self.valid_xlims[0].searchsorted(x) == 1,
                         self.valid_xlims[1].searchsorted(x) == 1])

    def is_valid_y(self, y):
        return np.array([self.valid_ylims[0].searchsorted(y) == 1,
                         self.valid_ylims[1].searchsorted(y) == 1])

    def check_mark(self, mark):
        valid = self.is_valid_x(mark.x)
        if any(valid):
            valid = self.is_valid_y(mark.y)
        if not any(valid):
            self.show_tooltip_in_plot(
                "<pre>Leftclick</pre> the mark and drag it to one of "
                "the diagram corners. e.g. x=%i, y=%i. Make sure, you exclude "
                "the x- and y-axes but include the diagram.\n\n"
                "One could also remove them later in the digitization, but it "
                "is easier to exlude them now." % tuple(
                    self.ref_lims[:, 0]), *mark.pos)
        return any(valid)

    def hint(self):
        sw = self.straditizer_widgets
        stradi = sw.straditizer
        refx, refy = self.ref_lims
        xlim = stradi.data_xlim
        ylim = stradi.data_ylim
        btn = sw.digitizer.btn_select_data
        if xlim is None and (
                not self.correct_button_clicked or not self.is_selecting):
            if self.is_selecting:
                self.show_tooltip_at_widget(
                    "Wrong button clicked! Click cancel and use the "
                    "<i>%s</i> button." % btn.text(), sw.cancel_button)
            else:
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to start" % btn.text(),
                    sw.digitizer.btn_select_data)
        elif self.is_selecting:  # currently creating marks
            marks = stradi.marks
            if not len(marks):
                self.show_tooltip_in_plot(
                    "<pre>Shift+leftclick</pre> on one of the corners in the "
                    "diagram to create a mark", refx[0], refy[0])
            elif len(marks) == 1:
                mark = marks[0]
                if self.check_mark(mark):
                    # display the tooltip in the other corner
                    self.show_tooltip_in_plot(
                        "<pre>Shift+leftclick</pre> on the other corners in "
                        "the diagram to create a mark", *self.ref_lims[
                            np.c_[~self.is_valid_x(mark.x),
                                  ~self.is_valid_y(mark.y)].T])
            elif len(marks) == 2:
                if self.check_mark(marks[0]) and self.check_mark(marks[1]):
                    xlim = np.unique(np.ceil([m.x for m in marks]))
                    ylim = np.unique(np.ceil([m.y for m in marks]))
                    if len(xlim) == 1 or len(ylim) == 1:
                        self.show_tooltip_in_plot(
                            "<pre>Leftclick</pre> the marks and drag them "
                            "close to the diagram corners. e.g. x=%i, y=%i "
                            "and x=%i, y=%i" % (refx[0], refy[0], refx[1],
                                                refy[1]),
                            *marks[1].pos)
                    else:
                        self.show_tooltip_at_widget(
                            "Done! Click the <i>Apply</i> button",
                            sw.apply_button)
                        return
            self.display_reference_marks()
        elif xlim is not None:
            if not self.is_finished:
                self.show_tooltip_at_widget(
                    "You did not select the correct diagram corners. Click "
                    "the <i>%s</i> button to modify your "
                    "selection or the <i>Skip</i> button to proceed with the "
                    "next step" % btn.text(), sw.digitizer.btn_select_data)
            else:
                super().hint()


class CreateReader(TutorialPage):
    """The page for creating the reader"""

    @property
    def is_finished(self):
        return self.straditizer_widgets.straditizer.data_reader is not None

    def skip(self):
        self.straditizer_widgets.straditizer.init_reader('area')
        self.straditizer_widgets.refresh()

    def hint(self):
        if not self.is_finished:
            btn = self.straditizer_widgets.digitizer.btn_init_reader
            self.show_tooltip_at_widget(
                "Click <i>%s</i> to initialize the reader for the diagram" % (
                    btn.text()), btn)
        else:
            super().hint()


class SeparateColumns(TutorialPage):
    """The page for separating the columns"""

    @property
    def is_finished(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        return (reader._column_starts is not None and
                len(reader._column_starts) == 28)

    def skip(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        reader.reset_column_starts()
        reader._get_column_starts()
        self.straditizer_widgets.refresh()
        self.clicked_correct_button()

    def activate(self):
        self.straditizer_widgets.digitizer.btn_column_starts.clicked.connect(
            self.clicked_correct_button)

    def deactivate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_column_starts.clicked.disconnect(
            self.clicked_correct_button)

    correct_button_clicked = False

    def clicked_correct_button(self):
        self.correct_button_clicked = True

    def hint(self):
        sw = self.straditizer_widgets
        stradi = sw.straditizer
        reader = stradi.data_reader
        btn = sw.digitizer.btn_column_starts
        starts = reader._column_starts
        if starts is None and (
                not self.correct_button_clicked or not self.is_selecting):
            if self.is_selecting:
                self.show_tooltip_at_widget(
                    "Wrong button clicked! Click cancel and use the "
                    "<i>%s</i> button." % btn.text(), sw.cancel_button)
            else:
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to start" % btn.text(), btn)
        elif starts is not None and len(starts) != 28:
            if self.is_selecting:
                self.show_tooltip_in_plot(
                    "There are 28 columns in the diagram. Select all or "
                    "cancel and hit the <i>Reset</i> button",
                    stradi.data_xlim.mean(), stradi.data_ylim.mean())
            else:
                self.show_tooltip_at_widget(
                    "The diagram has 28 columns, not %i. Hit the <i>Reset</i> "
                    "button or modify the column starts.",
                    sw.digitizer.btn_reset_columns)
        elif self.is_selecting:  # currently creating marks
            self.show_tooltip_at_widget(
                "Done! Click the <i>Apply</i> button",
                sw.apply_button)
        elif starts is not None:
            super().hint()


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
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % rc.text(0), sw.tree.itemWidget(rc, 1))
        elif not rlc.isExpanded():
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


class DigitizePage(TutorialPage):
    """The page for digitizing the diagram"""

    @property
    def is_finished(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        return reader._full_df is not None

    def hint(self):
        btn = self.straditizer_widgets.digitizer.btn_digitize
        if not self.is_finished:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button" % btn.text(), btn)
        else:
            super().hint()

    def skip(self):
        self.straditizer_widgets.straditizer.data_reader.digitize()
        self.straditizer_widgets.refresh()


class SamplesPage(TutorialPage):
    """The page for finding and editing the samples"""

    @property
    def is_finished(self):
        return self.correct_button_clicked and not self.is_selecting

    def activate(self):
        self.straditizer_widgets.digitizer.btn_edit_samples.clicked.connect(
            self.clicked_correct_button)

    def deactivate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_edit_samples.clicked.disconnect(
            self.clicked_correct_button)

    correct_button_clicked = False

    def clicked_correct_button(self):
        self.correct_button_clicked = True

    def skip(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        reader.reset_samples()
        reader.add_samples(*reader.find_samples(max_len=8, pixel_tol=5))
        self.clicked_correct_button()

    def hint(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        sw = self.straditizer_widgets
        esc = sw.digitizer.edit_samples_child
        btn_find = sw.digitizer.btn_find_samples
        btn_edit = sw.digitizer.btn_edit_samples
        if not esc.isExpanded():
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % esc.text(0), sw.tree.itemWidget(esc, 1))
        elif reader._sample_locs is None:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to automatically find the "
                "samples." % btn_find.text(), btn_find)
        elif not self.correct_button_clicked:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to visualize and edit the "
                "samples." % btn_edit.text(), btn_edit)
        elif self.is_selecting:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> or <i>%s</i> button to stop the "
                "editing." % (sw.apply_button.text(), sw.cancel_button.text()),
                sw.apply_button)
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
                "<pre>Shift+Leftclick</pre> on a point on the vertical axes "
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
        self.clicked_add_reader_button()
        self.clicked_translations_button()
        reader = self.straditizer_widgets.straditizer.data_reader

        # charcoal
        reader = reader.get_reader_for_col(0)
        if len(reader.columns) > 1:
            reader = reader.new_child_for_cols([0], reader.__class__)
        reader._xaxis_px_orig = np.array([321, 427])
        reader.xaxis_data = np.array([0., 100.])

        # pollen concentration
        reader = reader.get_reader_for_col(27)
        if len(reader.columns) > 1:
            reader = reader.new_child_for_cols([27], reader.__class__)
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
            else:
                if self.is_selecting:
                    cols = sorted(reader._selected_cols)
                    if cols == [col]:
                        self.show_tooltip_at_widget(
                            "Click the <i>%s</i> button to continue." % (
                                sw.apply_button.text()), sw.apply_button)
                    elif not cols:
                        self.show_tooltip_in_plot(
                            "Select column %i by clicking on the plot" % col,
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
                ['sitename', 'Archive', 'Country', 'Restricted'],
                ['Hoya del Castillo', 'Pollen', 'Spain', 'No']):
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
        elif not self.is_finished():
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


class FinishPage(TutorialPage):
    """The last page of the tutorial"""

    def show(self):
        """Reimplemented to release the help explorer lock"""
        super().show()
        self.lock_viewer(False)
