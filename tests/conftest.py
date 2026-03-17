"""Configuration module for running tests with pytest

We use a methodology inspired by
https://nvbn.github.io/2017/02/02/pytest-leaking/
to show huw many MB are leaked from each test."""
import os
from psutil import Process
from collections import namedtuple
from itertools import groupby
from matplotlib.backend_bases import FigureCanvasBase, KeyEvent, MouseEvent

# import skimage now to avoid
# ImportError: dlopen: cannot load any more object with static TLS
from skimage.feature import match_template


_proc = Process(os.getpid())


def _install_canvas_event_shims():
    """Restore test helper event methods removed from newer matplotlib."""
    if not hasattr(FigureCanvasBase, 'button_press_event'):
        def button_press_event(self, x, y, button=1, dblclick=False,
                               guiEvent=None):
            event = MouseEvent(
                'button_press_event', self, x, y, button=button,
                dblclick=dblclick, guiEvent=guiEvent)
            self.callbacks.process('button_press_event', event)
            return event

        FigureCanvasBase.button_press_event = button_press_event

    if not hasattr(FigureCanvasBase, 'button_release_event'):
        def button_release_event(self, x, y, button=1, guiEvent=None):
            event = MouseEvent(
                'button_release_event', self, x, y, button=button,
                guiEvent=guiEvent)
            self.callbacks.process('button_release_event', event)
            return event

        FigureCanvasBase.button_release_event = button_release_event

    if not hasattr(FigureCanvasBase, 'motion_notify_event'):
        def motion_notify_event(self, x, y, guiEvent=None):
            event = MouseEvent('motion_notify_event', self, x, y,
                               guiEvent=guiEvent)
            self.callbacks.process('motion_notify_event', event)
            return event

        FigureCanvasBase.motion_notify_event = motion_notify_event

    if not hasattr(FigureCanvasBase, 'key_press_event'):
        def key_press_event(self, key, guiEvent=None):
            event = KeyEvent('key_press_event', self, key, guiEvent=guiEvent)
            self.callbacks.process('key_press_event', event)
            return event

        FigureCanvasBase.key_press_event = key_press_event


_install_canvas_event_shims()


def get_consumed_ram():
    return _proc.memory_info().rss


def pytest_addoption(parser):
    group = parser.getgroup("straditize", "straditize specific options")
    group.addoption('--nrandom',
                    help='Set the number of generated random samples',
                    default=2, type=int)
    group.addoption('--leak-threshold', help="Threshold for leak report",
                    default=20, type=int)
    group.addoption(
        '--sort-leaks', help="Sort the leaking report in ascending order",
        action='store_true')


def pytest_configure(config):
    import test_binary
    global LEAK_LIMIT, SORT_LEAKS
    test_binary.DataReaderTest.nsamples = config.getoption('nrandom')
    LEAK_LIMIT = config.getoption('leak_threshold') * 1024 * 1024
    SORT_LEAKS = config.getoption('sort_leaks')


START = 'START'
END = 'END'
ConsumedRamLogEntry = namedtuple('ConsumedRamLogEntry',
                                 ('nodeid', 'on', 'consumed_ram'))
consumed_ram_log = []


def pytest_runtest_setup(item):
    log_entry = ConsumedRamLogEntry(item.nodeid, START, get_consumed_ram())
    consumed_ram_log.append(log_entry)


def pytest_runtest_teardown(item):
    log_entry = ConsumedRamLogEntry(item.nodeid, END, get_consumed_ram())
    consumed_ram_log.append(log_entry)


# display leaks greater than 20 MB
LEAK_LIMIT = 20 * 1024 * 1024

SORT_LEAKS = False


def pytest_terminal_summary(terminalreporter):
    grouped = groupby(consumed_ram_log, lambda entry: entry.nodeid)
    leaks = []
    for nodeid, (start_entry, end_entry) in grouped:
        leaked = end_entry.consumed_ram - start_entry.consumed_ram
        if leaked > LEAK_LIMIT:
            leaks.append((leaked // 1024 // 1024, nodeid,
                          end_entry.consumed_ram // 1024 // 1024))
    if SORT_LEAKS:
        leaks.sort()
    for t in leaks:
        terminalreporter.write(
            'LEAKED %s MB in %s. Total: %s MB\n' % t)
