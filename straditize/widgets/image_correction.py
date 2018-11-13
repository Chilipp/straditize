"""Image correction methods
"""
import numpy as np
from straditize.widgets import StraditizerControlBase
from psyplot_gui.compat.qtcompat import (
    QWidget, QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QDoubleValidator)
import straditize.cross_mark as cm


class ImageRotator(StraditizerControlBase, QWidget):
    """Object to rotate the image"""

    _rotating = False
    _ha = False
    _va = False

    def __init__(self, straditizer_widgets, item, *args, **kwargs):
        super(ImageRotator, self).__init__(*args, **kwargs)
        self.txt_rotate = QLineEdit()
        self.txt_rotate.setValidator(QDoubleValidator())

        self.btn_rotate_horizontal = QPushButton('Horizontal alignment')
        self.btn_rotate_horizontal.setToolTip(
            'Mark two points that should be on the same horizontal level '
            'and rotate the picture to achieve this.')

        self.btn_rotate_vertical = QPushButton('Vertical alignment')
        self.btn_rotate_vertical.setToolTip(
            'Mark two points that should be on the same vertical level '
            'and rotate the picture to achieve this.')

        self.init_straditizercontrol(straditizer_widgets, item)

        # ---------------------------------------------------------------------
        # --------------------------- Layouts ---------------------------------
        # ---------------------------------------------------------------------

        layout = QVBoxLayout()

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel('Rotate:'))
        hbox.addWidget(self.txt_rotate)
        layout.addLayout(hbox)

        layout.addWidget(self.btn_rotate_horizontal)
        layout.addWidget(self.btn_rotate_vertical)

        self.setLayout(layout)

        # ---------------------------------------------------------------------
        # --------------------------- Connections -----------------------------
        # ---------------------------------------------------------------------

        self.txt_rotate.textChanged.connect(self.start_rotation)
        self.btn_rotate_horizontal.clicked.connect(
            self.start_horizontal_alignment)
        self.btn_rotate_vertical.clicked.connect(
            self.start_vertical_alignment)

        self.widgets2disable = [self.txt_rotate, self.btn_rotate_horizontal,
                                self.btn_rotate_vertical]

    def should_be_enabled(self, w):
        if not self._rotating:
            return self.straditizer is not None
        elif w is self.txt_rotate:
            return True
        return False

    def start_rotation(self):
        if not self._rotating:
            self._rotating = True
            self.connect2apply(self.rotate_image, self.remove_marks,
                               self.straditizer.draw_figure)
            self.connect2cancel(self.remove_marks,
                                self.straditizer.draw_figure)
            self.straditizer_widgets.apply_button.setText('Rotate')

    def start_horizontal_alignment(self):
        self.start_rotation()
        self._ha = True
        self._start_alignment()

    def start_vertical_alignment(self):
        self.start_rotation()
        self._va = True
        self._start_alignment()

    def _start_alignment(self):
        def new_mark(pos):
            if len(self.straditizer.marks) == 2:
                return
            mark = cm.CrossMarks(pos, ax=stradi.ax, c='b')
            if self.straditizer.marks:
                marks = [mark] + self.straditizer.marks
                mark.connect_marks(marks, visible=True)
                self.update_txt_rotate(marks=marks)
            mark.moved.connect(self.update_txt_rotate)
            return [mark]

        stradi = self.straditizer
        stradi.marks = []

        stradi.mark_cids.add(stradi.fig.canvas.mpl_connect(
            'button_press_event', stradi._add_mark_event(new_mark)))
        stradi.mark_cids.add(stradi.fig.canvas.mpl_connect(
            'button_press_event', stradi._remove_mark_event))

    def update_txt_rotate(self, *args, marks=[], **kwargs):
        stradi = self.straditizer
        marks = marks or stradi.marks
        if len(marks) != 2:
            return
        x0, y0 = marks[0].pos
        x1, y1 = marks[1].pos
        dx = x0 - x1
        dy = y0 - y1

        if self._ha:
            angle = np.arctan(dy / dx) if dx else np.sign(dy) * np.pi / 2.
            self.txt_rotate.setText('%1.3g' % np.rad2deg(angle))
        elif self._va:
            angle = np.arctan(dx / dy) if dy else np.sign(dx) * np.pi / 2.
            self.txt_rotate.setText('%1.3g' % -np.rad2deg(angle))

    def enable_or_disable_widgets(self, b):
        super(ImageRotator, self).enable_or_disable_widgets(b)
        if self._rotating:
            self.txt_rotate.setEnabled(self.should_be_enabled(self.txt_rotate))

    @property
    def angle(self):
        angle = self.txt_rotate.text()
        if not angle.strip():
            return
        return float(angle.strip())

    def rotate_image(self):
        angle = self.angle
        if angle is None:
            return
        self.straditizer.image = self.straditizer.image.rotate(angle)
        self.straditizer.plot_im.set_array(np.asarray(self.straditizer.image))

    def remove_marks(self):
        self._rotating = self._ha = self._va = False
        self.straditizer.remove_marks()
        self.straditizer_widgets.apply_button.setText('Apply')
