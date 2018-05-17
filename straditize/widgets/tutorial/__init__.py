"""The tutorial of straditize

This module contains a guided tour through straditize"""
import os.path as osp
import glob
from straditize.widgets import StraditizerControlBase
from PyQt5 import QtWidgets, QtCore


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
        self.nsteps = nsteps
        self.validate = validate

        self.lbl_progress = QtWidgets.QLabel()

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(1)
        self.progress_bar.setMaximum(nsteps + 1)

        self.btn_prev = QtWidgets.QPushButton('Back')
        self.btn_next = QtWidgets.QPushButton('Check')
        self.btn_skip = QtWidgets.QPushButton('Skip')
        self.btn_hint = QtWidgets.QPushButton('Hint')

        self.set_current_step(0)

        # ---------------------------------------------------------------------
        # --------------------------- Layouts ---------------------------------
        # ---------------------------------------------------------------------

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.lbl_progress)
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

    def display_hint(self):
        self.hint_requested.emit(self.current_step)

    def set_current_step(self, i):
        self.current_step = i
        self.progress_bar.setValue(i)
        if i == 0:
            self.lbl_progress.setText('Start by clicking the > button')
            self.btn_next.setText('>')
            self.btn_next.setEnabled(True)
            self.btn_skip.setEnabled(False)
        elif i < self.nsteps + 1:
            self.lbl_progress.setText('Step %i/%i' % (i, self.nsteps))
            self.btn_next.setEnabled(True)
            self.btn_skip.setEnabled(True)
            if not self.validate(i, silent=True):
                self.btn_next.setText('Check')
            else:
                self.btn_next.setText('>')
        else:
            self.progress_bar.setValue(i+1)
            self.lbl_progress.setText('Done!')
            self.btn_next.setText('Done')
            self.btn_next.setEnabled(False)
            self.btn_skip.setEnabled(False)
        self.btn_prev.setEnabled(i > 0)

    def goto_next_step(self):
        if self.btn_next.text() == '>':
            if self.current_step <= self.nsteps:
                self.btn_next.setText('Check and proceed')
                self.set_current_step(self.current_step + 1)
                self.step_changed.emit(self.current_step - 1,
                                       self.current_step)
            else:
                self.set_current_step(self.current_step)
        elif self.validate(self.current_step):
            self.btn_next.setText('>')

    def goto_prev_step(self):
        if self.current_step > 0:
            self.set_current_step(self.current_step - 1)
            self.step_changed.emit(self.current_step + 1, self.current_step)

    def skip(self):
        self.skipped.emit(self.current_step)
        self.btn_next.setText('>')
        self.goto_next_step()


class TutorialPage(object):
    """A base class for the tutorial pages

    Subclasses show implement the :meth:`show_hint` method and the
    :meth:`is_finished` property"""

    src_dir = osp.join(osp.dirname(__file__), 'docs')

    def __init__(self, filename, tutorial):
        self.filename = filename
        self.tutorial = tutorial

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

    @property
    def is_finished(self):
        """Boolean that is True, if the steps are all finished"""
        return True

    def show(self):
        from psyplot_gui.main import mainwindow
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
            widget.rect(), timeout)

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
        canvas = self.stradi.ax.figure.canvas
        # only implemented for PyQt backend
        if not isinstance(canvas, QtWidgets):
            return
        if transform is None:
            transform = self.straditizer.ax.transData
        x, y = transform.transform([x, y])[0]
        point = canvas.parent().mapToGlobal(
            QtCore.QPointF(x, canvas.size().height() - y).toPoint())
        QtWidgets.QToolTip.showText(
            point, tooltip, canvas, canvas.rect(), timeout)


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
        mainwindow.help_explorer.show_rst(rst, name, files=files)

    def setup_tutorial_pages(self):
        self.pages = [
            self,
            LoadImage('straditize_tutorial_load_image', self),
            TutorialPage('straditize_tutorial_finish', self),
            ]

    def close(self):
        """Close the tutorial and remove the widgets"""
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
        self.pages[i].hint()

    def validate_page(self, i, silent=False):
        ret = self.pages[i].is_finished
        if not silent and not ret:
            self.navigation.display_hint()
        return ret


class LoadImage(TutorialPage):
    """TutorialPage for loading the straditizer image"""

    def activate(self):
        sw = self.tutorial.straditizer_widgets
        sw.menu_actions._dirname_to_use = self.src_dir

    def deactivate(self):
        self.tutorial.straditizer_widgets.menu_actions._dirname_to_use = None

    @property
    def is_finished(self):
        return self.tutorial.straditizer is not None

    def hint(self):
        if self.is_finished:
            super().hint()
        else:
            self.show_tooltip_at_widget(
                'Click here to load the image',
                self.tutorial.straditizer_widgets.btn_open_stradi)

    def skip(self):
        self.tutorial.straditizer_widgets.menu_actions.open_straditizer(
            osp.join(self.src_dir, 'straditize-tutorial.png'))
