# -*- coding: utf-8 -*-
"""Module defining the base class for the gui test"""
import gc
import numpy as np
from PIL import Image
import os
import six
import tempfile
import os.path as osp
import unittest
from pandas.util.testing import assert_frame_equal


test_dir = osp.dirname(__file__)


from psyplot_gui.compat.qtcompat import QApplication, QTest, Qt
from psyplot_gui import rcParams
from psyplot import rcParams as psy_rcParams


def is_running_in_gui():
    from psyplot_gui.main import mainwindow
    return mainwindow is not None


def setup_rcparams():
    rcParams.defaultParams['console.start_channels'][0] = False
    rcParams.defaultParams['main.listen_to_port'][0] = False
    rcParams.defaultParams['help_explorer.render_docs_parallel'][0] = False
    rcParams.defaultParams['help_explorer.use_intersphinx'][0] = False
    rcParams.defaultParams['plugins.include'][0] = ['straditize.widgets']
    rcParams.defaultParams['plugins.exclude'][0] = 'all'
    rcParams.update_from_defaultParams()


running_in_gui = is_running_in_gui()


on_travis = os.environ.get('TRAVIS')


if running_in_gui:
    app = QApplication.instance()
else:
    setup_rcparams()
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)


class StraditizeWidgetsTestCase(unittest.TestCase):
    """A base class for testing the psyplot_gui module

    At the initializzation of the TestCase, a new
    :class:`psyplot_gui.main.MainWindow` widget is created which is closed at
    the end of all the tests"""

    data_xlim = np.array([10., 30.])

    data_ylim = np.array([10., 30.])

    column_starts = np.array([0, 6, 14], dtype=int)

    column_ends = np.array([6, 14, 20], dtype=int)

    @property
    def digitizer(self):
        return self.straditizer_widgets.digitizer

    @classmethod
    def setUpClass(cls):
        import psyplot_gui.main as main
        from straditize.widgets import get_straditizer_widgets
        from PyQt5.QtCore import QTimer
        if not running_in_gui:
            import psyplot_gui
            psyplot_gui.UNIT_TESTING = True
            cls.window = main.MainWindow.run(show=False)
        else:
            cls.window = main.mainwindow
            timer = QTimer(cls.window)
            timer.setSingleShot(True)
            timer.start(1000)
        cls.straditizer_widgets = get_straditizer_widgets(cls.window)
        cls.straditizer_widgets.always_yes = True
        cls.straditizer_widgets.switch_to_straditizer_layout()

    def setUp(self):
        self.created_files = set()
        self.digitizer.sp_pixel_tol.setValue(2)

    def tearDown(self):
        import matplotlib.pyplot as plt
        from straditize.straditizer import Straditizer
        from straditize.binary import DataReader
        from psyplot.data import Signal
        import psyplot.project as psy

        # potentially recreate the straditizer control
        try:
            restart = self.straditizer_widgets.apply_button.isEnabled()
        except (AttributeError, RuntimeError):
            pass
        else:
            self.straditizer_widgets.reset_control()
            if restart:
                self.tearDownClass()
                self.setUpClass()

        for obj in gc.get_objects():
            if isinstance(obj, Signal):
                obj.disconnect()
        psy.close('all')
        plt.close('all')
        for f in self.created_files:
            if osp.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

        # ------- Tracking down memory leaks ---------
        # Now we check, that the straditizers are correctly garbage collected
        gc.collect()
        straditizers = [obj for obj in gc.get_objects()
                        if isinstance(obj, Straditizer)]
#        print('Straditizers:', straditizers)
#        if len(straditizers) >= 5:
#            print(gc.get_referrers(straditizers[0]))
        self.assertLess(len(straditizers), 5,
                        msg='Straditizers have not been garbage collected!')

        # And we check, for readers
        readers = [obj for obj in gc.get_objects()
                   if isinstance(obj, DataReader)]
#        print('Readers:', readers)
#        if len(readers) >= 5:
#            print(gc.get_referrers(readers[0]))
        self.assertLess(len(readers), 5,
                        msg='DataReaders have not been garbage collected!')

    @classmethod
    def tearDownClass(cls):
        if not running_in_gui:
            import psyplot_gui.main as main
            cls.window.close()
            rcParams.update_from_defaultParams()
            psy_rcParams.update_from_defaultParams()
            rcParams.disconnect()
            psy_rcParams.disconnect()
            main._set_mainwindow(None)
            del cls.window, cls.straditizer_widgets

    # ------ New test methods -------------------------------------------------

    def assertFrameEqual(self, df, df_ref, *args, **kwargs):
        """Simple wrapper around assert_frame_equal to use unittests assertion

        Parameters
        ----------
        df: pd.DataFrame
            The simulation data frame
        df_ref: pd.DataFrame
            The reference data frame"""
        try:
            assert_frame_equal(df, df_ref, *args, **kwargs)
        except (Exception, AssertionError) as e:
            self.fail(e if six.PY3 else e.message)

    def assertImageEquals(self, actual, expected, tol=5):
        """
        Compare two "image" files checking differences within a tolerance.

        The two given filenames may point to PNG files.

        Parameters
        ----------
        expected : str
            The filename of the expected image.
        actual :str
            The filename of the actual image.
        tol : float
            The tolerance (a color value difference, where 255 is the
            maximal difference).  The test fails if the average pixel
            difference is greater than this value.

        Note
        ----
        Large parts of this method are copied from the
        :func:`matplotlib.testing.compare` function. However, here we only
        accept PNG files and we do not remove the alpha channel but set the
        corresponding colors to black
        """
        if not os.path.exists(actual):
            raise Exception("Output image %s does not exist." % actual)

        if os.stat(actual).st_size == 0:
            raise Exception("Output image file %s is empty." % actual)

        if not os.path.exists(expected):
            raise IOError('Baseline image %r does not exist.' % expected)

        if not isinstance(expected, six.string_types):
            expectedImage = expected.copy()
        else:
            expectedImage = np.array(Image.open(expected))
        if not isinstance(actual, six.string_types):
            actualImage = actual.copy()
            diff_image = self.get_random_filename(suffix='.png')
        else:
            actualImage = np.array(Image.open(actual))
            diff_image = osp.splitext(actual)[0] + '-failed-diff.png'

        if actualImage.shape != expectedImage.shape:
            raise ValueError(
                "Test image %r and reference image %r have differing "
                "shapes!" % (actualImage.shape, expectedImage.shape))

        if tol <= 0.0:
            if np.array_equal(expectedImage, actualImage):
                return None

        # convert to signed integers, so that the images can be subtracted
        # without overflow
        expectedImage = expectedImage.astype(np.int16)
        actualImage = actualImage.astype(np.int16)

        if expectedImage.shape[-1] == 4:
            alpha = np.tile(~expectedImage[..., -1:].astype(bool), (1, 1, 4))
            expectedImage[alpha] = 0
            alpha = np.tile(~actualImage[..., -1:].astype(bool), (1, 1, 4))
            actualImage[alpha] = 0

        # calculate rms
        num_values = expectedImage.size
        abs_diff_image = abs(expectedImage - actualImage)
        histogram = np.bincount(abs_diff_image.ravel(), minlength=256)
        sum_of_squares = np.sum(histogram * np.arange(len(histogram)) ** 2)
        rms = np.sqrt(float(sum_of_squares) / num_values)

        if rms <= tol:
            return None

        if not isinstance(actual, six.string_types):
            actual = self.get_random_filename(suffix='.png')
            Image.fromarray(actualImage, 'RGBA').save(actual)

        if not isinstance(expected, six.string_types):
            expected = self.get_random_filename(suffix='.png')
            Image.fromarray(expectedImage, 'RGBA').save(expected)

        absDiffImage = np.abs(expectedImage - actualImage)

        # expand differences in luminance domain
        absDiffImage *= 255 * 10

        Image.fromarray(absDiffImage, 'RGBA').save(diff_image)

        results = dict(rms=rms, expected=str(expected),
                       actual=str(actual), diff=str(diff_image), tol=tol)

        template = ['Error: Image files did not match.',
                    'RMS Value: {rms}',
                    'Expected:  \n    {expected}',
                    'Actual:    \n    {actual}',
                    'Difference:\n    {diff}',
                    'Tolerance: \n    {tol}', ]
        results = '\n  '.join([line.format(**results) for line in template])
        self.fail(results)

    def assertBinaryImageEquals(self, binary, ref):
        """Compare two binary images

        Parameters
        ----------
        binary: str or np.ndarray of ndim 2
            The image to test. Either a string representing the path to an
            image, or a 2D binary image array
        ref: str or np.ndarray of ndim 2
            The reference image. Either a string representing the path to an
            image, or a 2D binary image array."""
        from straditize.binary import DataReader
        if not np.ndim(binary):
            binary = DataReader.to_binary_pil(Image.open(binary))
        if not np.ndim(ref):
            ref = DataReader.to_binary_pil(Image.open(ref))
        try:
            np.testing.assert_equal(binary, ref)
        except (Exception, AssertionError) as e:
            self.fail(e if six.PY3 else e.message)

    def assertArrayEquals(self, arr, ref, msg=''):
        try:
            np.testing.assert_equal(np.asarray(arr), np.asarray(ref))
        except (Exception, AssertionError) as e:
            self.fail(str(e if six.PY3 else e.message) + msg)

    # ------ Utitlty methods --------------------------------------------------

    def get_random_filename(self, **kwargs):
        kwargs.setdefault('prefix', 'stradi_')
        with tempfile.NamedTemporaryFile(**kwargs) as file:
            fname = file.name
        self.created_files.add(fname)
        return fname

    @property
    def straditizer(self):
        ret = self.straditizer_widgets.straditizer
        self.assertIsNotNone(ret)
        return ret

    @property
    def reader(self):
        ret = self.straditizer.data_reader
        self.assertIsNotNone(ret)
        return ret

    def get_fig_path(self, fname):
        ret = osp.join(test_dir, '..', 'test_figures', fname)
        self.assertTrue(osp.exists(ret), msg='Missing ' + ret)
        return ret

    def open_img(self, fname='basic_diagram.png'):
        fname = self.get_fig_path(fname)
        self.straditizer_widgets.menu_actions.open_straditizer(fname)
        self.assertEqual(self.straditizer.get_attr('image_file'), fname,
                         msg='Image not opened correctly!')

    def set_data_lims(self, xlim=None, ylim=None):
        x0, x1 = xlim if xlim is not None else self.data_xlim
        y0, y1 = ylim if ylim is not None else self.data_ylim
        self.assertTrue(
            self.straditizer_widgets.digitizer.btn_select_data.isEnabled())
        self.straditizer_widgets.digitizer.select_data_part(guess_lims=False)
        self.straditizer._new_mark(x0, y0)
        self.straditizer._new_mark(x1, y1)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertIsNotNone(self.straditizer.data_xlim)
        self.assertEqual(self.straditizer.data_xlim.tolist(),
                         [x0, x1])
        self.assertEqual(self.straditizer.data_ylim.tolist(),
                         [y0, y1])

    def init_reader(self, fname='basic_diagram.png', xlim=None, ylim=None):
        self.open_img(fname)
        self.set_data_lims(xlim, ylim)
        QTest.mouseClick(self.straditizer_widgets.digitizer.btn_init_reader,
                         Qt.LeftButton)
        return self.reader

    def focus_on_mark(self, mark, dx=2, dy=2):
        ax = mark.ax
        try:
            x = mark.x
        except Exception:
            pass
        else:
            xlim = ax.get_xlim()
            ax.set_xlim(min(xlim[0], x-dx), max(xlim[1], x+dx))
        try:
            y = mark.y
        except Exception:
            pass
        else:
            ylim = ax.get_ylim()
            ax.set_ylim(max(ylim[0], y+dy), min(ylim[1], y-dy))

    def move_mark(self, mark, by=None, to=None):
        if by is None and to is None:
            raise ValueError("Either `by` or `to` must be specified!")
        elif by is not None and to is not None:
            raise ValueError("Only one of `by` and `to` can be specified!")
        elif by is not None:
            to = mark.pos + np.asarray(by)
        by = np.asarray(to) - mark.pos
        ax = mark.ax
        canvas = mark.fig.canvas
        self.focus_on_mark(mark, *np.abs(by))
        x0, y0 = ax.transData.transform([mark.pos])[0]
        x1, y1 = ax.transData.transform([to])[0]
        # select the mark
        canvas.button_press_event(x0, y0, 1)
        # move the mark
        x1, y1 = ax.transData.transform([to])[0]
        canvas.motion_notify_event(x1, y1)
        # release the mark
        canvas.button_release_event(x1, y1, 1)
        self.assertEqual(list(mark.pos), list(to))

    def add_mark(self, pos, ax=None):
        """Add a new mark at the given position"""
        self.straditizer.show_full_image()
        marks = self.straditizer.marks
        n = len(marks)
        if ax is None:
            ax = marks[0].ax
            canvas = marks[0].fig.canvas
        else:
            canvas = ax.figure.canvas
        x, y = pos

        # focus on the new position
        xlim = ax.get_xlim()
        ax.set_xlim(min(xlim[0], x-2), max(xlim[1], x+2))
        ylim = ax.get_ylim()
        ax.set_ylim(max(ylim[0], y+2), min(ylim[1], y-2))

        x0, y0 = ax.transData.transform([pos])[0]
        canvas.key_press_event('shift')
        canvas.button_press_event(x0, y0, 1)
        canvas.button_release_event(x0, y0, 1)
        self.assertGreater(len(self.straditizer.marks), n,
                           msg='No new marks added!')

    def remove_mark(self, mark):
        """Add a new mark at the given position"""
        self.focus_on_mark(mark)
        marks = self.straditizer.marks
        n = len(marks)
        ax = mark.ax
        canvas = mark.fig.canvas
        x0, y0 = ax.transData.transform([mark.pos])[0]
        canvas.button_press_event(x0, y0, 3)
        self.assertLess(len(marks), n, msg='No marks removed!')
