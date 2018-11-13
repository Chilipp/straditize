"""Module for translating the x- and y-axes from pixel into data coordinates
"""
from straditize.widgets import StraditizerControlBase
from psyplot_gui.compat.qtcompat import QPushButton, QTreeWidgetItem
from functools import partial


class AxesTranslations(StraditizerControlBase):
    """The control for translating x- and y-axes

    This object creates two buttons for translating x- and y-axes from pixel
    to data coordinates"""

    @property
    def tree(self):
        return self.straditizer_widgets.tree

    def __init__(self, straditizer_widgets, item):
        self.btn_marks_for_y = QPushButton('Insert Y-axis values')
        self.btn_marks_for_x = QPushButton('Insert X-axis values')

        self.btn_marks_for_y.clicked.connect(self.marks_for_y)
        self.btn_marks_for_x.clicked.connect(partial(self.marks_for_x, True))

        self.widgets2disable = [self.btn_marks_for_x, self.btn_marks_for_y]

        self.init_straditizercontrol(straditizer_widgets, item)

    def setup_children(self, item):
        self.add_info_button(item, 'axes_translations.rst')
        child = QTreeWidgetItem(0)
        item.addChild(child)
        self.tree.setItemWidget(child, 0, self.btn_marks_for_x)
        self.add_info_button(child, 'xaxis_translation.rst',
                             connections=[self.btn_marks_for_x])
        child = QTreeWidgetItem(0)
        item.addChild(child)
        self.tree.setItemWidget(child, 0, self.btn_marks_for_y)
        self.add_info_button(child, 'yaxis_translation.rst',
                             connections=[self.btn_marks_for_y])

    def marks_for_y(self):
        """Create (or enable) the marks for the y-axis translation"""
        self.straditizer.marks_for_y_values()
        self.straditizer.draw_figure()
        self.connect2apply(self.straditizer.update_yvalues,
                           self.straditizer.draw_figure,
                           self.straditizer_widgets.refresh)
        self.connect2cancel(self.straditizer.remove_marks,
                            self.straditizer.draw_figure)

    def marks_for_x(self, at_col_start=True):
        """Create (or enable) the marks for the x-axis translation"""
        self.straditizer.marks_for_x_values(at_col_start)
        self.straditizer.draw_figure()
        self.connect2apply(self.straditizer.update_xvalues,
                           self.straditizer.draw_figure,
                           self.straditizer_widgets.refresh)
        self.connect2cancel(self.straditizer.remove_marks,
                            self.straditizer.draw_figure)

    def should_be_enabled(self, w):
        if self.straditizer is None:
            return False
        elif (w is self.btn_marks_for_x and
              (self.straditizer.data_reader is None or
               self.straditizer.data_reader._column_starts is None)):
            return False
        return True
