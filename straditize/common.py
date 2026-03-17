# -*- coding: utf-8 -*-
"""Module of commonly use python objects

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
import asyncio
import logging
import os
import warnings
from functools import wraps

from docrep import DocstringProcessor

docstrings = DocstringProcessor()


def configure_runtime_warning_filters():
    """Silence narrow third-party deprecations that straditize cannot fix."""
    os.environ.setdefault('JUPYTER_PLATFORM_DIRS', '1')
    warnings.filterwarnings(
        'ignore',
        message='Jupyter is migrating its paths to use standard platformdirs.*',
        category=DeprecationWarning,
        module=r'jupyter_client\.connect')
    warnings.filterwarnings(
        'ignore',
        message='zmq\\.eventloop\\.ioloop is deprecated in pyzmq 17.*',
        category=DeprecationWarning)


def rgba2rgb(image, color=(255, 255, 255)):
    """Alpha composite an RGBA Image with a specified color.

    Source: http://stackoverflow.com/a/9459208/284318

    Parameters
    ----------
    image: PIL.Image
        The PIL RGBA Image object
    color: tuple
        The rgb color for the background

    Returns
    -------
    PIL.Image
        The rgb image
    """
    from PIL import Image
    image.load()  # needed for split()
    background = Image.new('RGB', image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background


def nearest_index_position(index, value):
    """Return the integer position of the nearest numeric index entry."""
    if not len(index):
        raise KeyError(value)
    position = index.get_indexer([value], method='nearest')[0]
    if position < 0:
        raise KeyError(value)
    return int(position)


def nearest_index_value(index, value):
    """Return the nearest numeric value from a pandas-like index."""
    return index[nearest_index_position(index, value)]


def ensure_qt_int(value):
    """Convert float-like Qt size arguments to integers."""
    return int(round(value))


def patch_psyplot_gui_opengl():
    """Avoid late OpenGL configuration warnings from psyplot-gui startup."""
    try:
        import psyplot_gui
        from psyplot_gui.compat.qtcompat import QCoreApplication
    except ImportError:
        return False

    original = psyplot_gui._set_opengl_implementation
    if getattr(original, '_straditize_patched', False):
        return True

    @wraps(original)
    def wrapped(*args, **kwargs):
        if QCoreApplication.instance() is not None:
            return None
        return original(*args, **kwargs)

    wrapped._straditize_patched = True
    psyplot_gui._set_opengl_implementation = wrapped
    return True


def configure_qt_opengl(opengl_implementation=None):
    """Configure psyplot-gui OpenGL before QApplication creation."""
    try:
        import psyplot_gui
        from psyplot_gui.compat.qtcompat import QCoreApplication
    except ImportError:
        return False

    patch_psyplot_gui_opengl()
    if QCoreApplication.instance() is not None:
        return False
    psyplot_gui._set_opengl_implementation(opengl_implementation)
    return True


def ensure_asyncio_event_loop():
    """Return a usable event loop for GUI startup on modern Python versions.

    Python 3.14 no longer creates a default event loop implicitly for the
    main thread, but psyplot-gui still expects ``asyncio.get_event_loop()``
    to succeed during console initialization.
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


class _ToolbarMessageSignal(object):
    """Small signal-like adapter for modern matplotlib toolbars."""

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, text):
        for callback in list(self._callbacks):
            callback(text)


class _ToolbarMessageDescriptor(object):
    """Descriptor that recreates the removed toolbar ``message`` signal."""

    def __get__(self, toolbar, owner):
        if toolbar is None:
            return self
        return ensure_toolbar_message_signal(toolbar)


def ensure_toolbar_message_signal(toolbar):
    """Provide a ``message.connect(...)`` API for newer Qt toolbars.

    Matplotlib 3.10 dropped the ``NavigationToolbar2QT.message`` signal that
    older psyplot-gui releases still connect to. Newer toolbars only expose a
    ``set_message`` method, so we mirror that into a tiny signal adapter.
    """
    if toolbar is None:
        return None
    signal = getattr(toolbar, '_straditize_message_signal', None)
    if signal is not None:
        return signal
    descriptor = getattr(type(toolbar), 'message', None)
    if (descriptor is not None and
            not isinstance(descriptor, _ToolbarMessageDescriptor)):
        return toolbar.message
    if not hasattr(toolbar, 'set_message'):
        return None

    signal = _ToolbarMessageSignal()
    original = toolbar.set_message

    @wraps(original)
    def wrapped(text):
        ret = original(text)
        signal.emit(text)
        return ret

    toolbar.set_message = wrapped
    toolbar._straditize_message_signal = signal
    toolbar.message = signal
    return signal


def patch_psyplot_gui_asyncio():
    """Patch psyplot-gui's console startup for Python 3.14+ on Windows.

    psyplot-gui resets the Windows asyncio policy during console startup.
    On Python 3.14 that policy switch leaves the main thread without a current
    loop, so the subsequent ``asyncio.gather(...)`` call fails immediately.
    """
    try:
        import psyplot_gui.console as console
    except ImportError:
        return False

    original = console.init_asyncio_patch
    if getattr(original, '_straditize_patched', False):
        return True

    @wraps(original)
    def wrapped(*args, **kwargs):
        ret = original(*args, **kwargs)
        ensure_asyncio_event_loop()
        return ret

    wrapped._straditize_patched = True
    console.init_asyncio_patch = wrapped
    return True


def patch_psyplot_gui_backend():
    """Patch psyplot-gui's Qt backend for Matplotlib 3.10 toolbars."""
    try:
        import psyplot_gui.backend as backend
    except ImportError:
        return False

    try:
        toolbar_cls = backend.FigureManagerQT._toolbar2_class
    except AttributeError:
        return False
    if hasattr(toolbar_cls, 'message'):
        return True

    toolbar_cls.message = _ToolbarMessageDescriptor()
    return True


def patch_psyplot_gui_common():
    """Patch psyplot-gui widgets that still pass float sizes to Qt."""
    try:
        from psyplot_gui.common import PyErrorMessage
    except ImportError:
        return False

    original = PyErrorMessage.resize
    if getattr(original, '_straditize_patched', False):
        return True

    @wraps(original)
    def wrapped(self, *args):
        if len(args) == 2:
            return original(
                self, ensure_qt_int(args[0]), ensure_qt_int(args[1]))
        return original(self, *args)

    wrapped._straditize_patched = True
    PyErrorMessage.resize = wrapped
    return True


def patch_psyplot_gui_entrypoints():
    """Use importlib.metadata entry points for modern psyplot-gui sessions."""
    try:
        from importlib import metadata
        from psyplot_gui.config.rcsetup import GuiRcParams
    except ImportError:
        return False

    original = GuiRcParams._load_plugin_entrypoints
    if getattr(original, '_straditize_patched', False):
        return True

    class _CompatEntryPoint(object):
        def __init__(self, entry_point):
            self._entry_point = entry_point
            self.name = entry_point.name
            self.value = entry_point.value
            self.group = entry_point.group
            self.module = entry_point.module
            self.module_name = entry_point.module
            self.attrs = (
                [] if entry_point.attr is None else entry_point.attr.split('.'))

        def load(self):
            return self._entry_point.load()

        def __str__(self):
            return str(self._entry_point)

    @wraps(original)
    def wrapped(self):
        inc = self["plugins.include"]
        exc = self["plugins.exclude"]
        logger = logging.getLogger('psyplot_gui.config.rcsetup')
        self._plugins = self._plugins or []
        raw_eps = metadata.entry_points()
        if hasattr(raw_eps, 'select'):
            raw_eps = raw_eps.select(group='psyplot_gui')
        elif isinstance(raw_eps, dict):
            raw_eps = raw_eps.get('psyplot_gui', [])
        else:
            raw_eps = [ep for ep in raw_eps
                       if getattr(ep, 'group', None) == 'psyplot_gui']
        for raw_ep in raw_eps:
            ep = _CompatEntryPoint(raw_ep)
            plugin_name = "%s:%s:%s" % (
                ep.module, ":".join(ep.attrs), ep.name)
            include_user = None
            if inc:
                include_user = (
                    ep.module in inc
                    or ep.name in inc
                    or "%s:%s" % (ep.module, ":".join(ep.attrs)) in inc
                )
            if include_user is None and exc == 'all':
                include_user = False
            elif include_user is None:
                include_user = not (
                    ep.module in exc
                    or ep.name in exc
                    or "%s:%s" % (ep.module, ":".join(ep.attrs)) in exc
                )
            if not include_user:
                logger.debug(
                    "Skipping plugin %s: Excluded by user", plugin_name)
            else:
                logger.debug("Loading plugin %s", plugin_name)
                self._plugins.append(str(ep))
                yield ep

    wrapped._straditize_patched = True
    GuiRcParams._load_plugin_entrypoints = wrapped
    return True
