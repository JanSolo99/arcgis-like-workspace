"""Shared test doubles used across the test_*.py modules.

These are plugin-test-specific fixtures/fakes (a fake QgisInterface, a fake
QgsShortcutsManager, a fake background task) -- distinct from tests/fake_qgis,
which stands in for the third-party 'qgis' package itself. Everything here
is plain Python, built on top of tests/fake_qgis's Qt/QGIS stand-ins.
"""

from typing import Callable, Dict, Optional

from qgis.PyQt.QtWidgets import QAction


class FakeIface:
    """Stand-in for QgisInterface, covering only what core/*.py calls.

    *actions* maps an iface method name (e.g. "actionDeleteSelected") to
    the QAction instance that method should return when called -- mirrors
    real QgisInterface, where iface.actionDeleteSelected() is itself a
    zero-arg callable returning a QAction. A name absent from *actions*
    raises AttributeError from __getattr__, which is exactly what lets
    toolbars.native_action()'s `getattr(iface, name, None)` degrade to
    None for actions this fake wasn't given -- the same "not available on
    this QGIS build/profile" path native_action() defends against for
    real QGIS.
    """

    def __init__(self, actions: Optional[Dict[str, QAction]] = None, main_window=None):
        self._actions = dict(actions or {})
        self._main_window = main_window

    def __getattr__(self, name):
        if name in self._actions:
            action = self._actions[name]
            return lambda: action
        raise AttributeError(name)

    def mainWindow(self):
        return self._main_window


class FakeShortcutsManager:
    """Stand-in for QgsShortcutsManager, encoding its documented contract:
    setKeySequence(action, sequence) only accepts *sequence* as a str --
    passing anything else (e.g. a QKeySequence) raises TypeError at the
    sip boundary in real PyQGIS. Verified against
    https://qgis.org/pyqgis/master/gui/QgsShortcutsManager.html:
    `setKeySequence(action: Optional[QAction], sequence: Optional[str]) -> bool`.

    This is the contract that made shortcuts.py's remap feature inert
    before the fix (passing a QKeySequence instead of the plain string):
    a strict fake is the whole point -- a permissive fake would let that
    exact bug pass silently.
    """

    def __init__(self):
        #: action -> default sequence string, set up per-test via
        #: set_default().
        self._defaults: Dict[QAction, str] = {}
        #: Every action registered as "known" to this manager, for
        #: listActions()/collision checks.
        self._actions: list = []
        #: Actions whose next setKeySequence() call(s) should return False
        #: (QGIS "declined" the change) rather than applying it.
        self._decline: set = set()
        #: Recorded (action, sequence) pairs for every setKeySequence()
        #: call, in order -- lets tests assert exactly what was attempted.
        self.set_calls: list = []

    def set_default(self, action: QAction, sequence: str):
        self._defaults[action] = sequence
        if action not in self._actions:
            self._actions.append(action)
        action.setShortcut(sequence)

    def register_action(self, action: QAction, sequence: str):
        """Register another action already bound to *sequence*, for
        collision-guard tests -- doesn't touch its "default"."""
        if action not in self._actions:
            self._actions.append(action)
        action.setShortcut(sequence)

    def decline_next(self, action: QAction):
        """Make setKeySequence() calls for *action* return False instead
        of applying, simulating QGIS declining the change, until
        stop_declining() is called."""
        self._decline.add(action)

    def stop_declining(self, action: QAction):
        """Undo decline_next() -- the next setKeySequence() call for
        *action* applies normally again."""
        self._decline.discard(action)

    def defaultKeySequence(self, action: QAction) -> str:
        return self._defaults.get(action, "")

    def listActions(self):
        return list(self._actions)

    def setKeySequence(self, action: QAction, sequence) -> bool:
        if not isinstance(sequence, str):
            raise TypeError(
                "setKeySequence(self, action: Optional[QAction], sequence: Optional[str]): "
                f"argument 2 has unexpected type '{type(sequence).__name__}'"
            )
        self.set_calls.append((action, sequence))
        if action in self._decline:
            return False
        action.setShortcut(sequence)
        return True


class FakeTask:
    """Stand-in for QgsTask -- just description()/taskCompleted/taskTerminated,
    the only surface notifications.py touches."""

    def __init__(self, description: str = "task"):
        from qgis.PyQt.QtCore import FakeSignal

        self._description = description
        self.taskCompleted = FakeSignal()
        self.taskTerminated = FakeSignal()

    def description(self) -> str:
        return self._description


class FakeMainWindow:
    """Minimal stand-in for iface.mainWindow() -- a QMainWindow-shaped
    object with just the dock/toolbar bookkeeping DockArranger/ToolbarBuilder
    /NotificationsDock touch."""

    def __init__(self):
        self._docks = []
        self._stylesheet = ""

    def findChildren(self, cls):
        return [dock for dock in self._docks if isinstance(dock, cls)]

    def addDockWidget(self, area, dock):
        if dock not in self._docks:
            self._docks.append(dock)

    def removeDockWidget(self, dock):
        if dock in self._docks:
            self._docks.remove(dock)

    def tabifyDockWidget(self, first, second):
        pass

    def styleSheet(self) -> str:
        return self._stylesheet

    def setStyleSheet(self, stylesheet: str):
        self._stylesheet = stylesheet


def make_action(text: str = "") -> QAction:
    """Convenience: build a bare QAction the way core/*.py itself does
    (icon-less, text-only) for tests that just need "some QAction"."""
    return QAction(text, None)


def key_fn(prefix: str) -> Callable[[str], str]:
    """Mirrors ArcGISLikeWorkspacePlugin._key() (core/plugin.py) --
    SettingsToggles is constructed with exactly this kind of key_fn."""

    def _key(name: str) -> str:
        return f"{prefix}/{name}"

    return _key
