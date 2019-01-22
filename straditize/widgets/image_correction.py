"""Image correction methods

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
import numpy as np
from straditize.widgets import StraditizerControlBase
from psyplot_gui.compat.qtcompat import (
    QWidget, QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QDoubleValidator, QMessageBox)
from straditize.common import docstrings
import straditize.cross_mark as cm
from psyplot.utils import _temp_bool_prop


class ImageRotator(StraditizerControlBase, QWidget):
    """Widget to rotate the image

    This control mainly adds a QLineEdit :attr:`txt_rotate` to the
    :class:`straditize.widgets.StraditizerWidgets` to rotate the image.
    It also enables the user to specify the rotation angle using two
    connected :class:`~straditize.cross_mark.CrossMarks`. Here the user can
    decide between a horizontal alignment (:attr:`btn_rotate_horizontal`) or
    a vertical alignment (:attr:`btn_rotate_vertical`)"""

    _rotating = False
    _ha = False
    _va = False

    #: A QPushButton for horizontal alignment
    btn_rotate_horizontal = None

    #: A QPushButton for vertical alignment
    btn_rotate_vertical = None

    #: A QLineEdit to display the rotation angle
    txt_rotate = None

    @docstrings.dedent
    def __init__(self, straditizer_widgets, item=None, *args, **kwargs):
        """
        Parameters
        ----------
        %(StraditizerControlBase.init_straditizercontrol.parameters)s"""
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
        """Start the rotation (if not already started)"""
        if not self._rotating:
            self._rotating = True
            self.connect2apply(self.rotate_image)
            self.connect2cancel(self.remove_marks,
                                self.straditizer.draw_figure)
            self.straditizer_widgets.apply_button.setText('Rotate')

    def draw_figure(self):
        self.straditizer.draw_figure()

    def start_horizontal_alignment(self):
        """Start the horizontal alignment"""
        self.start_rotation()
        self._ha = True
        self._start_alignment()

    def start_vertical_alignment(self):
        """Start the vertical alignment"""
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
        """Update the :attr:`txt_rotate` from the displayed cross marks"""
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
        """The rotation angle from :attr:`txt_rotate` as a float"""
        angle = self.txt_rotate.text()
        if not angle.strip():
            return
        return float(angle.strip())

    def rotate_image(self):
        """Rotate the image based on the specified :attr:`angle`"""
        angle = self.angle
        if angle is None:
            return
        sw = self.straditizer_widgets
        answer = QMessageBox.Yes if sw.always_yes else QMessageBox.question(
            self, 'Restart project?',
            'This will close the straditizer and create new figures. '
            'Are you sure, you want to continue?')
        if answer == QMessageBox.Yes:
            image = self.straditizer.image.rotate(angle, expand=True)
            attrs = self.straditizer.attrs
            self.straditizer_widgets.close_straditizer()
            self.straditizer_widgets.menu_actions.open_straditizer(
                image, attrs=attrs)

        self._rotating = self._ha = self._va = False

    def remove_marks(self):
        """Remove the cross marks used for the rotation angle"""
        self._rotating = self._ha = self._va = False
        self.straditizer.remove_marks()
        self.straditizer_widgets.apply_button.setText('Apply')


class ImageRescaler(StraditizerControlBase, QPushButton):
    """A button to rescale the straditize image"""

    rescaling = _temp_bool_prop(
        'rescaling', "Boolean that is true if one of the axes is rescaling")

    #: A :class:`matplotlib.widgets.Slider` for specifying the size of the
    #: rescaled image
    slider = None

    #: The matplotlib image for the rescaled diagram
    im_rescale = None

    #: The matplotlib image for the original diagram
    im_orig = None

    #: The matplotlib axes for the :attr:`im_orig`
    ax_orig = None

    #: The matplotlib axes for the :attr:`im_rescale`
    ax_rescale = None

    #: The matplotlib figure for the rescaling
    fig = None

    def __init__(self, straditizer_widgets, item, *args, **kwargs):
        super(ImageRescaler, self).__init__('Rescale image')

        self.init_straditizercontrol(straditizer_widgets, item)

        self.widgets2disable = [self]

        self.clicked.connect(self.start_rescaling)

    def start_rescaling(self):
        """Create the rescaling figure"""
        self._create_rescale_figure()

    def _create_rescale_figure(self):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider
        import matplotlib.colorbar as mcbar
        self.fig, (self.ax_orig, self.ax_rescale) = plt.subplots(
            2, 1, figsize=(8, 12), gridspec_kw=dict(top=1.0, bottom=0.0))
        slider_ax, kw = mcbar.make_axes_gridspec(
            self.ax_rescale, orientation='horizontal', location='bottom')
        slider_ax.set_aspect('auto')
        slider_ax._hold = True
        self.slider = Slider(slider_ax, 'Fraction', 0, 100, valfmt='%1.3g %%')
        self.slider.set_val(100)
        self.slider.on_changed(self.rescale_plot)

        self.im_orig = self.ax_orig.imshow(self.straditizer.image)
        self.im_rescale = self.ax_rescale.imshow(self.straditizer.image)

        # connect limits
        self.ax_orig.callbacks.connect('xlim_changed',
                                       self.adjust_rescaled_limits)
        self.ax_orig.callbacks.connect('ylim_changed',
                                       self.adjust_rescaled_limits)
        self.ax_rescale.callbacks.connect('xlim_changed',
                                          self.adjust_orig_limits)
        self.ax_rescale.callbacks.connect('ylim_changed',
                                          self.adjust_orig_limits)
        self.fig.canvas.mpl_connect('resize_event', self.equalize_axes)

        self.connect2apply(self.rescale, self.close_figs)
        self.connect2cancel(self.close_figs)
        self.raise_figure()
        self.equalize_axes()

    def resize_stradi_image(self, percentage):
        """Resize the straditizer image

        Parameters
        ----------
        percentage: float
            A float between 0 and 100 specifying the target size of the
            :attr:`straditize.straditizer.Straditizer.image`

        Returns
        -------
        PIL.Image.Image
            The resized :attr:`~straditize.straditizer.Straditizer.image`
            of the current straditizer"""
        w, h = self.straditizer.image.size
        new_size = (int(round(w * percentage / 100.)),
                    int(round(h * percentage / 100.)))
        return self.straditizer.image.resize(new_size)

    def raise_figure(self):
        """Raise the figure for rescaling"""
        from psyplot_gui.main import mainwindow
        if mainwindow.figures:
            dock = self.fig.canvas.manager.window
            dock.widget().show_plugin()
            dock.raise_()

    def rescale_plot(self, percentage):
        """Replot :attr:`im_rescale` after adjustments of the :attr:`slider`"""
        self.im_rescale.remove()
        self.im_rescale = self.ax_rescale.imshow(
            self.resize_stradi_image(percentage))
        self.adjust_rescaled_limits()

    def adjust_rescaled_limits(self, *args, **kwargs):
        """Readjust :attr:`ax_rescale` after changes in :attr:`ax_orig`"""
        if self.rescaling:
            return
        with self.rescaling:
            x0, x1 = self.ax_orig.get_xlim()
            y0, y1 = self.ax_orig.get_ylim()
            fraction = self.slider.val / 100.
            self.ax_rescale.set_xlim(x0 * fraction, x1 * fraction)
            self.ax_rescale.set_ylim(y0 * fraction, y1 * fraction)
            self.draw_figure()

    def adjust_orig_limits(self, *args, **kwargs):
        """Readjust :attr:`ax_orig` after changes in :attr:`ax_rescale`"""
        if self.rescaling:
            return
        with self.rescaling:
            x0, x1 = self.ax_rescale.get_xlim()
            y0, y1 = self.ax_rescale.get_ylim()
            fraction = self.slider.val / 100.
            self.ax_orig.set_xlim(x0 / fraction, x1 / fraction)
            self.ax_orig.set_ylim(y0 / fraction, y1 / fraction)
            self.draw_figure()

    def equalize_axes(self, event=None):
        """Set both axes to the same size"""
        rescale_pos = self.ax_rescale.get_position()
        self.ax_orig.set_position((
            rescale_pos.x0, 0.55, rescale_pos.width,
            rescale_pos.height))

    def draw_figure(self):
        self.fig.canvas.draw()

    def rescale(self, ask=None):
        """Rescale and start a new straditizer

        Parameters
        ----------
        ask: bool
            Whether to ask with a QMessageBox. If None, it defaults to the
            :attr:`straditize.widgets.StraditizerWidgers.always_yes`"""
        if ask is None:
            ask = not self.straditizer_widgets.always_yes
        answer = QMessageBox.Yes if not ask else QMessageBox.question(
            self, 'Restart project?',
            'This will close the straditizer and create new figures. '
            'Are you sure, you want to continue?')
        if answer == QMessageBox.Yes:
            image = self.resize_stradi_image(self.slider.val)
            attrs = self.straditizer.attrs
            self.straditizer_widgets.close_straditizer()
            self.straditizer_widgets.menu_actions.open_straditizer(
                image, attrs=attrs)

    def close_figs(self):
        """Close the :attr:`fig`"""
        import matplotlib.pyplot as plt
        plt.close(self.fig.number)
        del self.fig, self.ax_orig, self.ax_rescale, self.im_rescale, \
            self.im_orig, self.slider

    def should_be_enabled(self, w):
        return self.straditizer is not None
