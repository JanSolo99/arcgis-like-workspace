"""Fake qgis.PyQt.QtCore -- just the symbols core/*.py imports from it.

No real Qt event loop, no C++ objects, no sip. Good enough to exercise the
plugin's pure-Python control flow (the reversibility contracts, the
key-sequence guards, the QSettings-key bookkeeping) without PyQt installed.
"""

from typing import Any, Callable, List


class FakeSignal:
    """Minimal connect/disconnect/emit stand-in for a Qt signal.

    Real PyQt signals are bound per-instance (each QObject instance owns
    its own connection list); this mirrors that by being a plain instance
    attribute wherever it's used (e.g. `self.taskAdded = FakeSignal()` in
    FakeTaskManager.__init__), never a shared class-level signal.

    `slots` is exposed as a public list (unlike real PyQt, which has no
    Python-visible connection list) so tests can introspect exactly what a
    connect() call closed over -- see tests/test_notifications.py, which
    inspects a connected lambda's __closure__ to verify it captured a
    plain string description rather than the QgsTask object itself.
    """

    def __init__(self):
        self.slots: List[Callable] = []

    def connect(self, slot: Callable):
        self.slots.append(slot)

    def disconnect(self, slot: Callable = None):
        if slot is None:
            if not self.slots:
                raise TypeError("disconnect() failed: signal has no connections")
            self.slots = []
            return
        try:
            self.slots.remove(slot)
        except ValueError:
            # Matches real PyQt/sip: disconnecting a slot that isn't
            # connected raises TypeError -- ConnectionTracker.disconnect_all()
            # (core/reversible.py) relies on exactly this to safely ignore
            # an already-disconnected connection.
            raise TypeError("disconnect() failed: slot is not connected")

    def emit(self, *args, **kwargs):
        for slot in list(self.slots):
            slot(*args, **kwargs)


class _ToolButtonStyle:
    ToolButtonTextUnderIcon = "ToolButtonTextUnderIcon"
    ToolButtonTextBesideIcon = "ToolButtonTextBesideIcon"


class _ToolBarArea:
    TopToolBarArea = "TopToolBarArea"


class _DockWidgetArea:
    BottomDockWidgetArea = "BottomDockWidgetArea"
    LeftDockWidgetArea = "LeftDockWidgetArea"
    RightDockWidgetArea = "RightDockWidgetArea"


class Qt:
    """Flat legacy-style attributes -- compat.qt_enum() looks these up via
    getattr(Qt, legacy_name, None) first, so a flat spelling here is all
    that's exercised; the nested ToolButtonStyle/ToolBarArea/DockWidgetArea
    groups are kept alongside only so widget_enum()'s Qt6-style nested
    fallback path also has something to resolve if ever exercised."""

    ToolButtonTextUnderIcon = _ToolButtonStyle.ToolButtonTextUnderIcon
    ToolButtonTextBesideIcon = _ToolButtonStyle.ToolButtonTextBesideIcon
    TopToolBarArea = _ToolBarArea.TopToolBarArea
    BottomDockWidgetArea = _DockWidgetArea.BottomDockWidgetArea
    LeftDockWidgetArea = _DockWidgetArea.LeftDockWidgetArea
    RightDockWidgetArea = _DockWidgetArea.RightDockWidgetArea

    ToolButtonStyle = _ToolButtonStyle
    ToolBarArea = _ToolBarArea
    DockWidgetArea = _DockWidgetArea


class QSize:
    def __init__(self, width: int = 0, height: int = 0):
        self._width = width
        self._height = height

    def width(self):
        return self._width

    def height(self):
        return self._height


class QSettings:
    """Dict-backed fake of QSettings, covering the operations core/*.py
    actually performs: setValue/value/contains/remove, plus childKeys()
    for completeness.

    Values are stored as the plain Python objects passed to setValue() --
    no ini/registry round-trip through strings like the real backends, so
    `type=` in value() is applied via a plain constructor call rather than
    QSettings' variant-conversion machinery. Good enough for this plugin's
    usage (bool flags and opaque blobs saved with saveState()/saveGeometry()
    and handed straight back to restoreState()/restoreGeometry()).

    remove(key) mirrors real QSettings' documented "removes the setting
    key and any sub-settings of key" behavior: it deletes `key` itself
    *and* every stored key that starts with f"{key}/" -- e.g.
    remove("arcgis_like_workspace") wipes
    "arcgis_like_workspace/hasSavedState",
    "arcgis_like_workspace/dockAttributeTableOriginal", etc. in one call.
    This is the "prefix-wipe" plugin.py.restore_layout() relies on.
    """

    def __init__(self):
        self._data = {}

    def setValue(self, key: str, value: Any):
        self._data[key] = value

    def value(self, key: str, defaultValue: Any = None, type: Any = None):
        if key not in self._data:
            return defaultValue
        stored = self._data[key]
        if type is not None:
            try:
                return type(stored)
            except Exception:
                return stored
        return stored

    def contains(self, key: str) -> bool:
        return key in self._data

    def remove(self, key: str):
        prefix = f"{key}/"
        for existing_key in list(self._data.keys()):
            if existing_key == key or existing_key.startswith(prefix):
                del self._data[existing_key]

    def childKeys(self, group: str = ""):
        """Simplified: returns the first path segment of every stored key
        under *group* (default: no group -- keys with no "/" at all).
        core/*.py never calls this; kept only so the fake's documented
        contract (childKeys semantics) is complete and testable on its own
        if a future feature needs it."""
        prefix = f"{group}/" if group else ""
        seen = []
        for existing_key in self._data:
            if group and not existing_key.startswith(prefix):
                continue
            remainder = existing_key[len(prefix):] if group else existing_key
            if "/" in remainder:
                continue
            if remainder not in seen:
                seen.append(remainder)
        return seen


class QTimer:
    """Only singleShot() is used (plugin.py's fallback startup path), and
    only as a fallback branch this test suite doesn't exercise -- kept as
    a no-op-by-default stand-in so importing plugin.py doesn't fail."""

    @staticmethod
    def singleShot(msec: int, slot: Callable):
        pass
