"""Navigation slider module

This module defines a slider class to navigate within an axes"""
import six
from matplotlib.widgets import Slider, AxesWidget
import matplotlib.colorbar as mcbar
from matplotlib.axes import SubplotBase
from psyplot.utils import _temp_bool_prop


class VerticalSlider(AxesWidget):
    """
    A slider representing a floating point range

    For the slider to remain responsive you must maintain a
    reference to it.

    The following attributes are defined
      *ax*        : the slider :class:`matplotlib.axes.Axes` instance

      *val*       : the current slider value

      *hline*     : a :class:`matplotlib.lines.Line2D` instance
                     representing the initial value of the slider

      *poly*      : A :class:`matplotlib.patches.Polygon` instance
                     which is the slider knob

      *valfmt*    : the format string for formatting the slider text

      *label*     : a :class:`matplotlib.text.Text` instance
                     for the slider label

      *closedmin* : whether the slider is closed on the minimum

      *closedmax* : whether the slider is closed on the maximum

      *slidermin* : another slider - if not *None*, this slider must be
                     greater than *slidermin*

      *slidermax* : another slider - if not *None*, this slider must be
                     less than *slidermax*

      *dragging*  : allow for mouse dragging on slider

    Call :meth:`on_changed` to connect to the slider event
    """
    def __init__(self, ax, label, valmin, valmax, valinit=0.5, valfmt='%1.2f',
                 closedmin=True, closedmax=True, slidermin=None,
                 slidermax=None, dragging=True, **kwargs):
        """
        Create a slider from *valmin* to *valmax* in axes *ax*.

        Additional kwargs are passed on to ``self.poly`` which is the
        :class:`matplotlib.patches.Rectangle` which draws the slider
        knob.  See the :class:`matplotlib.patches.Rectangle` documentation
        valid property names (e.g., *facecolor*, *edgecolor*, *alpha*, ...).

        Parameters
        ----------
        ax : Axes
            The Axes to put the slider in

        label : str
            Slider label

        valmin : float
            The minimum value of the slider

        valmax : float
            The maximum value of the slider

        valinit : float
            The slider initial position

        label : str
            The slider label

        valfmt : str
            Used to format the slider value, fprint format string

        closedmin : bool
            Indicate whether the slider interval is closed on the bottom

        closedmax : bool
            Indicate whether the slider interval is closed on the top

        slidermin : Slider or None
            Do not allow the current slider to have a value less than
            `slidermin`

        slidermax : Slider or None
            Do not allow the current slider to have a value greater than
            `slidermax`


        dragging : bool
            if the slider can be dragged by the mouse

        Notes
        -----
        This class has been copied from https://stackoverflow.com/a/25940123 on
        May, 8th, 2018 since the :class:`matplotlib.widgets.Slider` class
        is only implemented as a horizontal slider
        """
        AxesWidget.__init__(self, ax)

        self.valmin = valmin
        self.valmax = valmax
        self.val = valinit
        self.valinit = valinit
        self.poly = ax.axhspan(valmin, valinit, 0, 1, **kwargs)

        self.hline = ax.axhline(valinit, 0, 1, color='r', lw=1)

        self.valfmt = valfmt
        ax.set_xticks([])
        ax.set_ylim((valmin, valmax))
        ax.set_yticks([])
        ax.set_navigate(False)

        self.connect_event('button_press_event', self._update)
        self.connect_event('button_release_event', self._update)
        if dragging:
            self.connect_event('motion_notify_event', self._update)
        self.label = ax.text(0.5, 1.03, label, transform=ax.transAxes,
                             verticalalignment='center',
                             horizontalalignment='center')

        self.valtext = ax.text(0.5, -0.03, valfmt % valinit,
                               transform=ax.transAxes,
                               verticalalignment='center',
                               horizontalalignment='center')

        self.cnt = 0
        self.observers = {}

        self.closedmin = closedmin
        self.closedmax = closedmax
        self.slidermin = slidermin
        self.slidermax = slidermax
        self.drag_active = False

    def _update(self, event):
        """update the slider position"""
        if self.ignore(event):
            return

        if event.button != 1:
            return

        if event.name == 'button_press_event' and event.inaxes == self.ax:
            self.drag_active = True
            event.canvas.grab_mouse(self.ax)

        if not self.drag_active:
            return

        elif ((event.name == 'button_release_event') or
              (event.name == 'button_press_event' and
               event.inaxes != self.ax)):
            self.drag_active = False
            event.canvas.release_mouse(self.ax)
            return

        val = event.ydata
        if val <= self.valmin:
            if not self.closedmin:
                return
            val = self.valmin
        elif val >= self.valmax:
            if not self.closedmax:
                return
            val = self.valmax

        if self.slidermin is not None and val <= self.slidermin.val:
            if not self.closedmin:
                return
            val = self.slidermin.val

        if self.slidermax is not None and val >= self.slidermax.val:
            if not self.closedmax:
                return
            val = self.slidermax.val

        self.set_val(val)

    def set_val(self, val):
        xy = self.poly.xy
        xy[1] = 0, val
        xy[2] = 1, val
        self.poly.xy = xy
        self.valtext.set_text(self.valfmt % val)
        if self.drawon:
            self.ax.figure.canvas.draw_idle()
        self.val = val
        if not self.eventson:
            return
        for cid, func in six.iteritems(self.observers):
            func(val)

    def on_changed(self, func):
        """
        When the slider value is changed, call *func* with the new
        slider position

        A connection id is returned which can be used to disconnect
        """
        cid = self.cnt
        self.observers[cid] = func
        self.cnt += 1
        return cid

    def disconnect(self, cid):
        """remove the observer with connection id *cid*"""
        try:
            del self.observers[cid]
        except KeyError:
            pass

    def reset(self):
        """reset the slider to the initial value if needed"""
        if (self.val != self.valinit):
            self.set_val(self.valinit)


class NavigationSliderMixin(object):

    @property
    def limits(self):
        return NotImplemented("Must be implemented by subclasses!")

    def set_src_lims(self, vmin, vmax):
        raise NotImplementedError("Must be implemented by subclasses!")

    adjusting_limits = _temp_bool_prop(
        'adjusting_limits',
        "Boolean that is True, when the limits are adjusted")

    def init_navigation_slider(self, ax, orientation='horizontal',
                               sax=None):
        self.ax_src = ax

        if sax is None:
            if isinstance(ax, SubplotBase):
                sax, kw = mcbar.make_axes_gridspec(ax, orientation=orientation)
            else:
                sax, kw = mcbar.make_axes(ax, orientation=orientation)
            sax.set_aspect('auto')
            sax._hold = True

        label = 'x' if orientation == 'horizontal' else 'y'
        lims = sorted(self.limits)
        mean = sum(lims) / 2
        return ((sax, label, lims[0], lims[1]),
                dict(valinit=mean, valfmt='%1.2g'))

    def adjust_limits(self, val):
        if self.adjusting_limits:
            return
        with self.adjusting_limits:
            lims = self.limits
            diff = (lims[1] - lims[0]) / 2
            self.set_src_lims(val - diff, val + diff)
            self.ax_src.figure.canvas.draw_idle()

    def connect_to_src(self):
        self.on_changed(self.adjust_limits)

    def set_val_from_limits(self, ax):
        self.set_val(sum(self.limits) / 2)


class HorizontalNavigationSlider(NavigationSliderMixin, Slider):

    @property
    def limits(self):
        return self.ax_src.get_xlim()

    def set_src_lims(self, vmin, vmax):
        self.ax_src.set_xlim(vmin, vmax)

    def __init__(self, ax, sax=None):
        args, kwargs = self.init_navigation_slider(ax, 'horizontal', sax)
        super().__init__(*args, **kwargs)
        self.connect_to_src()

    def connect_to_src(self):
        super().connect_to_src()
        self.ax_src.callbacks.connect('xlim_changed', self.set_val_from_limits)


class VerticalNavigationSlider(NavigationSliderMixin, VerticalSlider):

    @property
    def limits(self):
        return self.ax_src.get_ylim()

    def set_src_lims(self, vmin, vmax):
        self.ax_src.set_ylim(vmin, vmax)

    def __init__(self, ax, sax=None):
        args, kwargs = self.init_navigation_slider(ax, 'vertical', sax)
        super().__init__(*args, **kwargs)
        self.connect_to_src()

    def connect_to_src(self):
        super().connect_to_src()
        self.ax_src.callbacks.connect('ylim_changed', self.set_val_from_limits)
