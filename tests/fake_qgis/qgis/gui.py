"""Fake qgis.gui -- QgsGui (for its shortcutsManager() singleton accessor)
and QgsLocatorWidget (an empty stand-in only ever used via findChild()).

QgsGui.shortcutsManager() returns whatever QgsGui._manager currently is --
tests set it directly (`QgsGui._manager = FakeShortcutsManager(...)`) to
control the manager's behavior per-test. See test_shortcuts.py.
"""

from typing import Optional


class QgsLocatorWidget:
    """Empty stand-in -- locator_filter.py only ever does
    `mainWindow().findChild(QgsLocatorWidget)`, never instantiates one."""


class QgsGui:
    """Real QgsGui.shortcutsManager() returns the QGIS-wide
    QgsShortcutsManager singleton (verified against
    https://qgis.org/pyqgis/master/gui/QgsGui.html). `_manager` is settable
    per-test rather than a hardcoded singleton so each test can install its
    own FakeShortcutsManager (or leave it None to exercise the "no manager
    available" path, if ever added)."""

    _manager: Optional[object] = None

    @classmethod
    def shortcutsManager(cls):
        return cls._manager
