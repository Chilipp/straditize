"""Test module for :mod:`straditize.widgets.image_correction"""
import _base_testing as bt
import unittest
from psyplot_gui.compat.qtcompat import QTest, Qt


class ImageRotatorTest(bt.StraditizeWidgetsTestCase):
    """Test case for the
    :class:`straditize.widgets.image_correction.ImageRotator` class"""

    @property
    def rotator(self):
        return self.straditizer_widgets.image_rotator

    def test_horizontal_rotation(self):
        self.open_img()
        self.straditizer.draw_figure()
        self.rotator.start_horizontal_alignment()
        self.add_mark((10, 10), ax=self.straditizer.ax)
        self.add_mark((10, 30))
        angle = self.rotator.angle
        self.assertEqual(angle, -90)
        rotated = self.straditizer.image.rotate(angle, expand=True)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertArrayEquals(self.straditizer.image, rotated)

    def test_vertical_rotation(self):
        self.open_img()
        self.straditizer.draw_figure()
        self.rotator.start_vertical_alignment()
        self.add_mark((10, 10), ax=self.straditizer.ax)
        self.add_mark((30, 10))
        angle = self.rotator.angle
        self.assertEqual(angle, 90)
        rotated = self.straditizer.image.rotate(angle, expand=True)
        QTest.mouseClick(self.straditizer_widgets.apply_button,
                         Qt.LeftButton)
        self.assertArrayEquals(self.straditizer.image, rotated)


if __name__ == '__main__':
    unittest.main()
