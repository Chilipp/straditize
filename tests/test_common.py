"""Tests for shared helpers."""
import asyncio
import os
import subprocess
import sys
import types
import unittest
from unittest import mock
import warnings

import pandas as pd

from straditize.common import (
    configure_runtime_warning_filters,
    configure_qt_opengl,
    ensure_asyncio_event_loop,
    ensure_qt_int,
    patch_psyplot_gui_opengl,
    patch_psyplot_gui_entrypoints,
    ensure_toolbar_message_signal,
    nearest_index_position,
    nearest_index_value,
)


class CommonHelpersTest(unittest.TestCase):

    def test_nearest_index_position(self):
        index = pd.Index([0.0, 4.0, 9.0, 15.0])

        self.assertEqual(nearest_index_position(index, 10.1), 2)

    def test_nearest_index_value(self):
        index = pd.Index([0.0, 4.0, 9.0, 15.0])

        self.assertEqual(nearest_index_value(index, 13.0), 15.0)

    def test_configure_runtime_warning_filters_sets_platformdirs(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                configure_runtime_warning_filters()

        self.assertEqual(os.environ['JUPYTER_PLATFORM_DIRS'], '1')

    def test_ensure_asyncio_event_loop_sets_missing_loop(self):
        sentinel = object()

        with mock.patch.object(
                asyncio, 'get_event_loop',
                side_effect=RuntimeError('missing loop')) as get_loop, \
                mock.patch.object(
                    asyncio, 'new_event_loop',
                    return_value=sentinel) as new_event_loop, \
                mock.patch.object(asyncio, 'set_event_loop') as set_event_loop:
            self.assertIs(ensure_asyncio_event_loop(), sentinel)

        get_loop.assert_called_once_with()
        new_event_loop.assert_called_once_with()
        set_event_loop.assert_called_once_with(sentinel)

    def test_ensure_toolbar_message_signal_wraps_set_message(self):
        class Toolbar(object):
            def __init__(self):
                self.messages = []

            def set_message(self, text):
                self.messages.append(text)

        toolbar = Toolbar()
        signal = ensure_toolbar_message_signal(toolbar)
        received = []

        signal.connect(received.append)
        toolbar.set_message('hello')

        self.assertIs(signal, toolbar.message)
        self.assertEqual(toolbar.messages, ['hello'])
        self.assertEqual(received, ['hello'])

    def test_ensure_qt_int_rounds_float_sizes(self):
        self.assertEqual(ensure_qt_int(10), 10)
        self.assertEqual(ensure_qt_int(10.2), 10)
        self.assertEqual(ensure_qt_int(10.9), 11)

    def test_configure_qt_opengl_before_application_exists(self):
        fake_psyplot_gui = types.ModuleType('psyplot_gui')
        fake_psyplot_gui._set_opengl_implementation = mock.Mock()
        fake_qtcompat = types.ModuleType('psyplot_gui.compat.qtcompat')
        fake_qtcompat.QCoreApplication = mock.Mock()
        fake_qtcompat.QCoreApplication.instance.return_value = None

        with mock.patch.dict(
                sys.modules,
                {'psyplot_gui': fake_psyplot_gui,
                 'psyplot_gui.compat.qtcompat': fake_qtcompat},
                clear=False):
            self.assertTrue(configure_qt_opengl('software'))

        fake_qtcompat.QCoreApplication.instance.assert_called_once_with()
        fake_psyplot_gui._set_opengl_implementation.assert_called_once_with(
            'software')

    def test_configure_qt_opengl_skips_existing_application(self):
        fake_psyplot_gui = types.ModuleType('psyplot_gui')
        fake_psyplot_gui._set_opengl_implementation = mock.Mock()
        fake_qtcompat = types.ModuleType('psyplot_gui.compat.qtcompat')
        fake_qtcompat.QCoreApplication = mock.Mock()
        fake_qtcompat.QCoreApplication.instance.return_value = object()

        with mock.patch.dict(
                sys.modules,
                {'psyplot_gui': fake_psyplot_gui,
                 'psyplot_gui.compat.qtcompat': fake_qtcompat},
                clear=False):
            self.assertFalse(configure_qt_opengl('software'))

        fake_qtcompat.QCoreApplication.instance.assert_called_once_with()
        fake_psyplot_gui._set_opengl_implementation.assert_not_called()

    def test_patch_psyplot_gui_opengl_skips_late_configuration(self):
        fake_psyplot_gui = types.ModuleType('psyplot_gui')

        def original(option):
            return ('configured', option)

        fake_psyplot_gui._set_opengl_implementation = original
        fake_qtcompat = types.ModuleType('psyplot_gui.compat.qtcompat')
        fake_qtcompat.QCoreApplication = mock.Mock()
        fake_qtcompat.QCoreApplication.instance.return_value = object()

        with mock.patch.dict(
                sys.modules,
                {'psyplot_gui': fake_psyplot_gui,
                 'psyplot_gui.compat.qtcompat': fake_qtcompat},
                clear=False):
            self.assertTrue(patch_psyplot_gui_opengl())
            self.assertIsNone(
                fake_psyplot_gui._set_opengl_implementation('software'))

        fake_qtcompat.QCoreApplication.instance.assert_called_once_with()

    def test_patch_psyplot_gui_entrypoints_supports_select_api(self):
        class DummyEntryPoint(object):
            name = 'plugin'
            value = 'keep.module:Widget'
            group = 'psyplot_gui'
            module = 'keep.module'
            attr = 'Widget'

            def load(self):
                return object

        class DummyEntryPoints(object):
            def __init__(self, entries):
                self._entries = entries

            def select(self, **kwargs):
                if kwargs.get('group') == 'psyplot_gui':
                    return self._entries
                return []

        class DummyGuiRcParams(object):
            def __init__(self):
                self._plugins = []
                self._values = {
                    'plugins.include': ['keep.module'],
                    'plugins.exclude': [],
                }

            def __getitem__(self, key):
                return self._values[key]

            def _load_plugin_entrypoints(self):
                return iter(())

        fake_module = types.ModuleType('psyplot_gui.config.rcsetup')
        fake_module.GuiRcParams = DummyGuiRcParams

        with mock.patch.dict(
                sys.modules, {'psyplot_gui.config.rcsetup': fake_module},
                clear=False), \
                mock.patch(
                    'importlib.metadata.entry_points',
                    return_value=DummyEntryPoints([DummyEntryPoint()])):
            self.assertTrue(patch_psyplot_gui_entrypoints())
            rcparams = DummyGuiRcParams()
            plugins = list(rcparams._load_plugin_entrypoints())

        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0].module, 'keep.module')

    def test_imports_avoid_deprecation_and_syntax_warnings(self):
        env = dict(os.environ)
        env['PYTHONWARNINGS'] = 'error::DeprecationWarning,error::SyntaxWarning'
        cmd = [
            sys.executable,
            '-c',
            ('import straditize.binary; import straditize.cross_mark; '
             'import straditize.widgets.data; import straditize.widgets.menu_actions; '
             'import straditize.colnames; import straditize.__main__')
        ]
        completed = subprocess.run(
            cmd, capture_output=True, text=True, env=env, check=False)

        self.assertEqual(
            completed.returncode, 0,
            msg='stdout:\n%s\nstderr:\n%s' % (
                completed.stdout, completed.stderr))


if __name__ == '__main__':
    unittest.main()
