# -*- coding: utf-8 -*-
"""The tutorial of straditize

This module contains a guided tour to get started with straditize

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
import os
import os.path as osp
import shutil
import glob
from itertools import chain
import numpy as np
from straditize.widgets import StraditizerControlBase, get_icon, get_doc_file
import straditize.cross_mark as cm
from PyQt5 import QtWidgets, QtCore, QtGui
from psyplot_gui.common import get_icon as get_psy_icon, DockMixin
from psyplot_gui.help_explorer import UrlHelp
import pandas as pd


class TutorialDocs(UrlHelp, DockMixin):
    """A documentation viewer for the tutorial docs

    This viewer is accessible through the :attr:`Tutorial.tutorial_docs`
    attribute and shows the :attr:`~TutorialPage.src_file` for the
    tutorial :attr:`~Tutorial.pages`"""

    dock_position = QtCore.Qt.RightDockWidgetArea

    title = 'Straditize tutorial'

    def __init__(self, *args, **kwargs):
        from psyplot_gui.main import mainwindow
        super().__init__(*args, **kwargs)
        self.bt_connect_console.setChecked(False)
        self.bt_lock.setChecked(False)
        self._orig_bt_url_lock = self.bt_url_lock
        self.bt_url_lock = mainwindow.help_explorer.viewers[
            'HTML help'].bt_url_lock
        self._orig_bt_url_lock.setVisible(False)
        self.bt_connect_console.setVisible(False)
        self.bt_lock.setVisible(False)
        self.bt_url_menus.setVisible(False)


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
        """
        Parameters
        ----------
        nsteps: int
            The total number of steps in the :class:`Tutorial`
        validate: callable
            A callable that takes the :attr:`current_step` as an argument and
            returns a :class:`bool` whether the current step is valid and
            finished, or not
        """
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
        """Enable or disable the navigation buttons

        Parameters
        ----------
        enable: bool
            Whether to enable or disable the buttons"""
        for w in [self.btn_prev, self.btn_next, self.btn_skip, self.btn_info]:
            w.setEnabled(enable)
        if enable:
            self.maybe_enable_widgets()
        self.enabled = enable

    def maybe_enable_widgets(self):
        """Enable the buttons based on the :attr:`current_step`"""
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
        """Trigger the :attr:`step_changed` signal with the current step"""
        self.step_changed.emit(self.current_step, self.current_step)

    def display_hint(self):
        """Trigger the :attr:`hint_requested` signal with the current step"""
        self.hint_requested.emit(self.current_step)

    def set_current_step(self, i):
        """Change the :attr:`current_step`

        Parameters
        ----------
        i: int
            The :attr:`current_step` to switch to"""
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
        """Increase the :attr:`current_step` by one"""
        if self.validate(self.current_step):
            if self.current_step <= self.nsteps:
                self.set_current_step(self.current_step + 1)
                self.step_changed.emit(self.current_step - 1,
                                       self.current_step)
            else:
                self.set_current_step(self.current_step)

    def goto_prev_step(self):
        """Decrease the :attr:`current_step` by one"""
        if self.current_step > 0:
            self.set_current_step(self.current_step - 1)
            self.step_changed.emit(self.current_step + 1, self.current_step)

    def skip(self):
        """Skip the :attr:`current_step` and emit the :attr:`skipped` signal
        """
        self.skipped.emit(self.current_step)
        self.goto_next_step()


class TutorialPage(object):
    """A base class for the tutorial pages

    Subclasses show implement the :meth:`show_hint` method and the
    :meth:`is_finished` property"""

    #: The source directory for the docs
    src_dir = osp.join(osp.dirname(__file__), 'beginner')

    #: The basename of the stratigraphic diagram image for this tutorial
    src_base = 'beginner-tutorial.png'

    #: The complete path to the of the stratigraphic diagram image for this
    #: tutorial
    src_file = osp.join(src_dir, src_base)

    #: str. The tooltip that has been shown. This attribute is mainly for
    #: testing purposes
    _last_tooltip_shown = None

    def __init__(self, filename, tutorial):
        """
        Parameters
        ----------
        filename: str
            The basename (without ending) of the RST file corresponding to this
            tutorial page
        tutorial: Tutorial
            The tutorial instance"""
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
        try:
            self.tutorial.tutorial_docs.bt_lock.setChecked(lock)
        except AttributeError:
            pass

    def show(self):
        """Show the page and browse the :attr:`filename` in the tutorial docs
        """
        try:
            self.lock_viewer(False)
            self.tutorial.tutorial_docs.browse(self.filename)
            self.lock_viewer(True)
        except AttributeError:
            with open(osp.join(self.src_dir, self.filename + '.rst')) as f:
                rst = f.read()
            self.tutorial.tutorial_docs.show_rst(rst, self.filename)

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
        self._last_tooltip_shown = tooltip
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
        self._last_tooltip_shown = tooltip
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
        """The current page of the tutorial (corresponding to the
        :attr:`TutorialNavigation.current_step`)"""
        return self.pages[self.navigation.current_step]

    @property
    def load_image_step(self):
        """The number of the page that loads the diagram image (i.e. the index
        of the :class:`LoadImage` instance in the :attr:`pages` attribute"""
        return next(
            (i for i, p in enumerate(self.pages) if isinstance(p, LoadImage)),
            1)

    #: A list of the :class:`TutorialPages` for this tutorial
    pages = []

    #: A :class:`TutorialDocs` to display the RST-files of the tutorial
    tutorial_docs = None

    #: A :class:`TutorialNavigation` to navigate through the tutorial
    navigation = None

    def __init__(self, straditizer_widgets):
        from psyplot_gui.main import mainwindow
        self.init_straditizercontrol(straditizer_widgets)
        self.tutorial = self

        self.central_widget_key = mainwindow.central_widget_key

        self.tutorial_docs = TutorialDocs()

        self.docs_key = ':'.join(
            [__name__, self.__class__.__name__, 'tutorial'])
        mainwindow.plugins[self.docs_key] = self.tutorial_docs
        self.tutorial_docs.to_dock(mainwindow)
        mainwindow.set_central_widget(self.tutorial_docs)

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
            The paths of the remaining tutorial files"""
        files = glob.glob(osp.join(self.src_dir, '*.rst')) + \
            glob.glob(osp.join(self.src_dir, '*.png')) + \
            glob.glob(get_doc_file('*.rst')) + \
            glob.glob(get_psy_icon('*.png')) + \
            glob.glob(get_doc_file('*.png')) + \
            glob.glob(get_icon('*.png'))
        intro = files.pop(next(
            i for i, f in enumerate(files)
            if osp.basename(f).endswith('-tutorial-intro.rst')))
        return intro, files

    def show(self):
        """Show the documentation of the tutorial"""
        intro, files = self.get_doc_files()
        self.filename = osp.splitext(osp.basename(intro))[0]
        with open(intro) as f:
            rst = f.read()
        name = osp.splitext(osp.basename(intro))[0]
        self.lock_viewer(False)
        self.tutorial_docs.show_rst(rst, name, files=files)

    def setup_tutorial_pages(self):
        """Setup the :attr:`pages` attribute and initialize the tutorial pages
        """
        self.pages = [
            self,
            ControlIntro('beginner-tutorial-control', self),
            LoadImage('beginner-tutorial-load-image', self),
            TutorialPage('beginner-tutorial-plot-navigation', self),
            SelectDataPart('beginner-tutorial-select-data', self),
            CreateReader('beginner-tutorial-create-reader', self),
            SeparateColumns('beginner-tutorial-column-starts', self),
            CleanImagePage('beginner-tutorial-clean-image', self),
            DigitizePage('beginner-tutorial-digitize', self),
            SamplesPage('beginner-tutorial-samples', self),
            TranslateYAxis('beginner-tutorial-yaxis-translation', self),
            TranslateXAxis('beginner-tutorial-xaxis-translation', self),
            ColumnNames('beginner-tutorial-column-names', self),
            FinishPage('beginner-tutorial-finish', self),
            ]

    def refresh(self):
        stradi = self._get_tutorial_stradi()
        enable = stradi is None or self.straditizer is stradi
        self.navigation.setEnabled(enable)
        for page in self.pages[1:]:
            page.refresh()
        if (stradi is None and
                self.navigation.current_step > self.load_image_step):
            self.navigation.set_current_step(self.load_image_step)

    def _get_tutorial_stradi(self):
        """Get the straditizer for this tutorial

        Returns
        -------
        straditize.straditizer.Straditizer
            The straditizer for this tutorial or None if it is closed"""
        src_file = self.src_base
        get_attr = self.straditizer_widgets.get_attr
        for stradi in self.straditizer_widgets._straditizers:
            if (get_attr(stradi, 'image_file') and
                    osp.basename(get_attr(stradi, 'image_file')) == src_file):
                return stradi

    def close(self):
        """Close the tutorial and remove the widgets"""
        stradi = self._get_tutorial_stradi()
        if stradi is not None:
            self.straditizer_widgets._close_stradi(stradi)
        if hasattr(self, 'navigation'):
            self.straditizer_widgets.layout().removeWidget(self.navigation)
            del self.straditizer_widgets.tutorial
            for p in self.pages:
                del p.tutorial, p.straditizer_widgets
            self.pages.clear()
            del self.pages
            self.navigation.close()
            self.tutorial_docs.close()
            self.tutorial_docs.remove_plugin()
            del self.navigation
            del self.tutorial_docs

    def goto_page(self, old, new):
        """Go to another page

        Parameters
        ----------
        old: int
            The index of the old page in the :attr:`pages` attribute that is
            subject to be deactivated (see :meth:`TutorialPage.deactivate`)
        new: int
            The index of the new page in the :attr:`pages` attribute that is
            subject to be activated (see :meth:`TutorialPage.activate`)

        See Also
        --------
        TutorialPage.activate
        TutorialPage.deactivate"""
        self.pages[old].deactivate()
        page = self.pages[new]
        page.show()
        page.activate()

    def skip_page(self, i):
        """Skip a tutorial page

        Parameters
        ----------
        i: int
            The index of the page in the :attr:`pages` attribute

        See Also
        --------
        TutorialPage.skip"""
        self.pages[i].skip()

    def display_hint(self, i):
        """Display the hint for a tutorial page

        Parameters
        ----------
        i: int
            The index of the page in the :attr:`pages` attribute

        See Also
        --------
        TutorialPage.hint"""
        stradi = self._get_tutorial_stradi()
        if stradi is None and i > self.load_image_step:
            self.navigation.set_current_step(self.load_image_step)
        elif stradi is not self.straditizer:
            self.show_tooltip_at_widget(
                "Select the straditizer for the <i>%s</i> diagram" % (
                    self.src_base), self.straditizer_widgets.stradi_combo)
        else:
            self.pages[i].hint()

    def validate_page(self, i, silent=False):
        """Validate a tutorial page

        Parameters
        ----------
        i: int
            The index of the page in the :attr:`pages` attribute
        silent: bool
            If True, and the page is not yet finished (see
            :attr:`TutorialPage.is_finished`), the hint is displayed

        Returns
        -------
        bool
            True, if the page :attr:`~TutorialPage.is_finished`"""
        ret = self.pages[i].is_finished
        if not silent and not ret:
            self.navigation.display_hint()
        return ret


class ControlIntro(TutorialPage):
    """Tutorial page for the control"""

    def activate(self):
        dest = osp.join(self.tutorial.tutorial_docs.build_dir,
                        '_static', 'straditizer-control.png')
        if not osp.exists(osp.dirname(dest)):
            os.makedirs(osp.dirname(dest))
        shutil.copyfile(
            osp.join(self.src_dir, 'straditizer-control.png'), dest)


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
        get_attr = self.straditizer_widgets.get_attr
        return stradi is not None and (
            get_attr(stradi, 'image_file') and osp.basename(
                get_attr(stradi, 'image_file')) == self.src_base)

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
    ref_lims = np.array([[258, 1803], [375, 1666]])

    #: Valid ranges for xmin and xmax
    valid_xlims = np.array([[221, 263], [1730, 1922]])

    #: Valid ranges for ymin and ymax
    valid_ylims = np.array([[346, 403], [1648, 1701]])

    #: true if the data box should be removed at the end
    remove_data_box = True

    marks = []

    @property
    def is_finished(self):
        stradi = self.tutorial.straditizer
        refx, refy = self.ref_lims
        if stradi.data_xlim is None:
            return False
        if not self.validate_corners():
            return False
        if (self.remove_data_box and
                getattr(stradi, 'data_box', None) is not None):
            return False
        return True

    def validate_corners(self):
        stradi = self.tutorial.straditizer
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
        if self.straditizer_widgets.cancel_button.isEnabled():
            self.straditizer_widgets.cancel_button.click()
        stradi.data_xlim, stradi.data_ylim = self.ref_lims
        self.clicked_correct_button()
        if getattr(stradi, 'data_box', None) is not None:
            stradi.remove_data_box()
            stradi.draw_figure()
        self.straditizer_widgets.refresh()

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
        pc_item = sw.plot_control_item
        pc = sw.plot_control
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
            if not self.validate_corners():
                self.show_tooltip_at_widget(
                    "You did not select the correct diagram corners. Click "
                    "the <i>%s</i> button to modify your "
                    "selection or the <i>Skip</i> button to proceed with the "
                    "next step" % btn.text(), sw.digitizer.btn_select_data)
            elif (self.remove_data_box and
                  getattr(stradi, 'data_box', None) is not None):
                if not pc_item.isExpanded():
                    sw.tree.scrollToItem(pc_item)
                    self.show_tooltip_at_widget(
                        "Expand the <i>%s</i> item by clicking on the arrow "
                        "to it's left" % pc_item.text(0),
                        sw.tree.itemWidget(pc_item, 1))
                else:
                    row = list(pc.table.get_artists_funcs).index(
                        'Diagram part')
                    sw.tree.scrollToItem(sw.marker_control_item)
                    self.show_tooltip_at_widget(
                        "Click the cross to remove the red rectangle",
                        pc.table.cellWidget(row, 1))

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
            sw = self.straditizer_widgets
            btn = sw.digitizer.btn_init_reader
            sw.tree.scrollToItem(sw.digitizer_item)
            self.show_tooltip_at_widget(
                "Click <i>%s</i> to initialize the reader for the diagram" % (
                    btn.text()), btn)
        else:
            super().hint()


class SeparateColumns(TutorialPage):
    """The page for separating the columns"""

    ncols = 4

    @property
    def is_finished(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        return (reader._column_starts is not None and
                len(reader._column_starts) == self.ncols)

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
        elif starts is not None and len(starts) != self.ncols:
            if self.is_selecting:
                self.show_tooltip_in_plot(
                    "There are 28 columns in the diagram. Select all or "
                    "cancel and hit the <i>Reset</i> button",
                    stradi.data_xlim.mean(), stradi.data_ylim.mean())
            else:
                self.show_tooltip_at_widget(
                    "The diagram has 28 columns, not %i. Hit the <i>%s</i> "
                    "button or modify the column starts." % (
                        len(starts), sw.digitizer.btn_reset_columns.text()),
                    sw.digitizer.btn_reset_columns)
        elif self.is_selecting:  # currently creating marks
            self.show_tooltip_at_widget(
                "Done! Click the <i>Apply</i> button",
                sw.apply_button)
        elif starts is not None:
            super().hint()


class ColumnNames(TutorialPage):
    """The page for recognizing column names"""

    select_names_button_clicked = False

    #: The column names in the diagram
    column_names = [
        'Pinus', 'Juniperus', 'Quercus ilex-type', 'Chenopodiaceae']

    @property
    def is_finished(self):
        sw = self.straditizer_widgets
        reader = sw.straditizer.colnames_reader
        return (
            reader.column_names == self.column_names and
            not sw.colnames_manager.btn_select_names.isChecked())

    def skip(self):
        self.straditizer_widgets.straditizer.colnames_reader.column_names = \
            self.column_names
        btn = self.straditizer_widgets.colnames_manager.btn_select_names
        if btn.isChecked():
            btn.click()

    def activate(self):
        sw = self.straditizer_widgets
        sw.colnames_manager.btn_select_names.clicked.connect(
            self.clicked_select_names_button)

    def deactivate(self):
        sw = self.straditizer_widgets
        sw.colnames_manager.btn_select_names.clicked.disconnect(
            self.clicked_select_names_button)

    def clicked_select_names_button(self):
        self.select_names_button_clicked = True

    def hint(self):
        reader = self.straditizer_widgets.straditizer.colnames_reader
        sw = self.straditizer_widgets
        btn = sw.colnames_manager.btn_select_names
        rc = sw.col_names_item
        is_finished = self.is_finished
        if not is_finished and (not self.select_names_button_clicked or
                                not sw.colnames_manager.is_shown):
            sw.tree.scrollToItem(rc)
            if not rc.isExpanded():
                self.show_tooltip_at_widget(
                    "Expand the <i>%s</i> item by clicking on the arrow to "
                    "it's left" % rc.text(0), sw.tree.itemWidget(rc, 1))
            else:
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button" % btn.text(), btn)
        elif not is_finished:
            ncols = len(reader.column_bounds)
            if reader.column_names == list(map(str, range(ncols))):
                self.hint_for_start_editing()
            elif reader.column_names != self.column_names:
                i, (curr, ref) = next(
                    t for t in enumerate(zip(reader.column_names,
                                             self.column_names))
                    if t[1][0] != t[1][1])
                self.hint_for_wrong_name(i, curr, ref)
            elif btn.isChecked():
                sw.tree.scrollToItem(rc)
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to finish" % btn.text(), btn)
        else:
            super().hint()

    def hint_for_start_editing(self):
        from straditize.colnames import tesserocr
        if tesserocr is not None:
            btn = self.straditizer_widgets.colnames_manager.btn_find
            ocr = ' or click the <i>%s</i> button' % btn.text()
        else:
            ocr = ''
        self.show_tooltip_at_widget(
            'Edit the column names in the table%s. You can zoom into '
            'the plot on the left using the `right` mouse button and '
            'navigate using the `left` mouse button' % ocr,
            self.straditizer_widgets.colnames_manager.colnames_table)

    def hint_for_wrong_name(self, col, curr, ref):
        """Display a hint if a name is not correctly set"""
        manager = self.straditizer_widgets.colnames_manager
        if manager.current_col != col:
            self.show_tooltip_at_widget(
                "Column name of the %s column (column %i) is not correct "
                "(%r != %r)!<br><br>"
                "Select the column in the table and enter the correct "
                "name or click the 'skip' button" % (ref, col, curr, ref),
                manager.colnames_table)
        else:
            self.show_tooltip_at_widget(
                "Enter the correct name (%r)" % ref, manager.colnames_table)


class CleanImagePage(TutorialPage):
    """Tutorial page to clean the diagram part"""

    btn_remove_yaxes_clicked = btn_remove_xaxes_clicked = False

    def skip(self):
        stradi = self.straditizer_widgets.straditizer
        reader = stradi.data_reader
        reader.recognize_yaxes(remove=True)
        reader.binary[:, 1797 - int(stradi.data_xlim[0]):] = 0
        reader.recognize_xaxes(remove=True)
        stradi.draw_figure()
        self.clicked_btn_remove_xaxes()
        self.clicked_btn_remove_yaxes()
        self.straditizer_widgets.refresh()

    @property
    def is_finished(self):
        stradi = self.straditizer_widgets.straditizer
        reader = stradi.data_reader
        if not len(reader.vline_locs) or not len(reader.hline_locs):
            return False
        elif (stradi.data_xlim[1] > 1797 and
              reader.binary[:, 1799 - stradi.data_xlim[0]].any()):
            return False
        return True

    def activate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_remove_yaxes.clicked.connect(
            self.clicked_btn_remove_yaxes)
        sw.digitizer.btn_remove_xaxes.clicked.connect(
            self.clicked_btn_remove_xaxes)

    def deactivate(self):
        sw = self.straditizer_widgets
        sw.digitizer.btn_remove_yaxes.clicked.disconnect(
            self.clicked_btn_remove_yaxes)
        sw.digitizer.btn_remove_xaxes.clicked.disconnect(
            self.clicked_btn_remove_xaxes)

    def clicked_btn_remove_yaxes(self):
        self.btn_remove_yaxes_clicked = True

    def clicked_btn_remove_xaxes(self):
        self.btn_remove_xaxes_clicked = True

    def icon_to_bytes(self, icon):
        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.WriteOnly)
        if isinstance(icon, str):
            icon = QtGui.QIcon(get_icon(icon))
        pixmap = icon.pixmap(10, 10)
        pixmap.save(buffer, "PNG", quality=100)
        image = bytes(buffer.data().toBase64()).decode()
        return '<img src="data:image/png;base64,{}">'.format(image)

    def hint(self):
        sw = self.straditizer_widgets
        stradi = sw.straditizer
        reader = stradi.data_reader
        btn_x = sw.digitizer.btn_remove_xaxes
        btn_y = sw.digitizer.btn_remove_yaxes
        rc = sw.digitizer.remove_child
        rlc = sw.digitizer.remove_line_child
        if not len(reader.vline_locs) or not len(reader.hline_locs):
            if not rc.isExpanded():
                sw.tree.scrollToItem(rc)
                self.show_tooltip_at_widget(
                    "Expand the <i>%s</i> item by clicking on the arrow to "
                    "it's left" % rc.text(0), sw.tree.itemWidget(rc, 1))
            elif (not self.btn_remove_xaxes_clicked and
                  not self.btn_remove_yaxes_clicked and self.is_selecting):
                self.show_tooltip_at_widget(
                    "Wrong button clicked! Click cancel and use the "
                    "<i>%s</i> button." % btn_y.text(), sw.cancel_button)
            elif self.is_selecting:
                self.show_tooltip_at_widget(
                    "Done! Click the <i>Remove</i> button", sw.apply_button)
            elif not self.btn_remove_yaxes_clicked:
                sw.tree.scrollToItem(rlc)
                self.show_tooltip_at_widget(
                    ("Click the <i>%s</i> button to select the"
                     " y-axes") % btn_y.text(), btn_y)
            elif not self.btn_remove_xaxes_clicked:
                sw.tree.scrollToItem(rlc)
                self.show_tooltip_at_widget(
                    ("Click the <i>%s</i> button to select the"
                     " x-axes") % btn_x.text(), btn_x)
        elif not self.is_finished:
            if self.is_selecting and sw.apply_button.text() != 'Remove':
                self.show_tooltip_at_widget(
                    "Wrong button clicked! Click cancel and use the "
                    "selection toolbar.", sw.selection_toolbar)
            elif not self.is_selecting:
                if sw.selection_toolbar.wand_type != 'cols':
                    wand_icon = sw.selection_toolbar.wand_action.icon()
                    self.show_tooltip_at_widget(
                        "Select the %s (column selection) mode in the %s "
                        "menu" % (self.icon_to_bytes('col_select.png'),
                                  self.icon_to_bytes(wand_icon)),
                        sw.selection_toolbar)
                elif not sw.selection_toolbar.wand_action.isChecked():
                    self.show_tooltip_at_widget(
                        "Enable the %s selection" % (
                            self.icon_to_bytes('col-select.png'), ),
                        sw.selection_toolbar)
                elif sw.selection_toolbar.remove_select_action.isChecked():
                    self.show_tooltip_at_widget(
                        "Enable the %s or %s selection mode" % (
                            self.icon_to_bytes('new_selection.png'),
                            self.icon_to_bytes('add_select.png')),
                        sw.selection_toolbar)
                else:
                    self.show_tooltip_in_plot(
                        "Drag a rectangle around the most right line",
                        1799, int(np.mean(stradi.ax.get_ylim())))
            elif not reader.selected_part[
                    :, 1799 - stradi.data_xlim[0]].any():
                self.show_tooltip_in_plot(
                    "Drag a rectangle around the most right line",
                    1799, int(np.mean(stradi.ax.get_ylim())))
            else:
                self.show_tooltip_at_widget(
                    "Click the <i>Remove</i> button to remove the line",
                    sw.apply_button)
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
            self.straditizer_widgets.tree.scrollToItem(
                self.straditizer_widgets.digitizer.digitize_item)
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
        self.straditizer_widgets.refresh()

    def hint(self):
        reader = self.straditizer_widgets.straditizer.data_reader
        sw = self.straditizer_widgets
        esc = sw.digitizer.edit_samples_child
        btn_find = sw.digitizer.btn_find_samples
        btn_edit = sw.digitizer.btn_edit_samples
        if not esc.isExpanded():
            sw.tree.scrollToItem(esc)
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % esc.text(0), sw.tree.itemWidget(esc, 1))
        elif reader._sample_locs is None or not len(reader._sample_locs):
            sw.tree.scrollToItem(esc.child(0))
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to automatically find the "
                "samples." % btn_find.text(), btn_find)
        elif not self.correct_button_clicked:
            sw.tree.scrollToItem(esc.child(2))
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
        self.straditizer_widgets.straditizer.yaxis_data = np.array([150, 450])
        self.straditizer_widgets.straditizer._yaxis_px_orig = \
            np.array([378, 1663])
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
            sw.tree.scrollToItem(item)
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % item.text(0), sw.tree.itemWidget(item, 1))
        elif not self.correct_button_clicked:
            if self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and use the "
                        "<i>%s</i> button." % btn.text(), sw.cancel_button)
            else:
                sw.tree.scrollToItem(item.child(1))
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to start." % btn.text(), btn)
        elif len(marks) < 2:
            self.show_tooltip_in_plot(
                "<pre>Shift+Leftclick</pre> on a point on the vertical axis "
                "to enter %s y-value" % (
                    "another" if len(marks) else "the corresponding"),
                260, np.mean(sw.straditizer.ax.get_ylim()))
        elif len(marks) == 2:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to stop the editing." % (
                    sw.apply_button.text()), sw.apply_button)


class TranslateXAxis(TutorialPage):
    """The tutorial page for translating the y-axis"""

    @property
    def is_finished(self):
        return self.straditizer_widgets.straditizer.data_reader.xaxis_data is \
            not None

    def skip(self):
        self.clicked_correct_button()
        self.straditizer_widgets.straditizer.data_reader.xaxis_data = \
            np.array([0, 70])
        self.straditizer_widgets.straditizer.data_reader._xaxis_px_orig = \
            np.array([258, 700])
        self.straditizer_widgets.refresh()

    def activate(self):
        btn = self.straditizer_widgets.axes_translations.btn_marks_for_x
        btn.clicked.connect(self.clicked_correct_button)

    def deactivate(self):
        btn = self.straditizer_widgets.axes_translations.btn_marks_for_x
        btn.clicked.disconnect(self.clicked_correct_button)

    correct_button_clicked = False

    def clicked_correct_button(self):
        self.correct_button_clicked = True

    def hint(self):
        sw = self.straditizer_widgets
        item = sw.axes_translations_item
        btn = sw.axes_translations.btn_marks_for_x
        marks = sw.straditizer.marks or []
        if self.is_finished:
            super().hint()
        elif not self.is_selecting and not item.isExpanded():
            sw.tree.scrollToItem(item)
            self.show_tooltip_at_widget(
                "Expand the <i>%s</i> item by clicking on the arrow to it's "
                "left" % item.text(0), sw.tree.itemWidget(item, 1))
        elif not self.correct_button_clicked:
            if self.is_selecting:
                    self.show_tooltip_at_widget(
                        "Wrong button clicked! Click cancel and use the "
                        "<i>%s</i> button." % btn.text(), sw.cancel_button)
            else:
                sw.tree.scrollToItem(item.child(0))
                self.show_tooltip_at_widget(
                    "Click the <i>%s</i> button to start." % btn.text(), btn)
        elif len(marks) < 2:
            self.show_tooltip_in_plot(
                "<pre>Shift+Leftclick</pre> on a point on the horizontal axis "
                "to enter %s x-value" % (
                    "another" if len(marks) else "the corresponding"),
                np.mean(sw.straditizer.ax.get_xlim()), 1662)
        elif len(marks) == 2:
            self.show_tooltip_at_widget(
                "Click the <i>%s</i> button to stop the editing." % (
                    sw.apply_button.text()), sw.apply_button)


class FinishPage(TutorialPage):
    """The last page of the tutorial"""

    def show(self):
        """Reimplemented to release the help explorer lock"""
        super().show()
        self.lock_viewer(False)
