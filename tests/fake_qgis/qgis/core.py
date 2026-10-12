"""Fake qgis.core -- just the symbols core/*.py imports from it.

Documented contracts encoded here (verified against
https://qgis.org/pyqgis/master/ -- see tests/conftest.py and this
package's own docstring for the general approach):

* QgsTaskManager.taskAdded emits an int task id, and task(id) returns the
  QgsTask or None if it isn't registered -- see _FakeTaskManager below.
  Confirmed via https://qgis.org/pyqgis/master/core/QgsTaskManager.html:
  `taskAdded(taskId: int)` / `task(id: int) -> QgsTask | None`.
"""

import copy
from typing import Any, Dict, Optional

from .PyQt.QtCore import FakeSignal


class Qgis:
    """Flat message-level attributes (qgis_message_level() in compat.py
    checks these first) plus the nested enum groups settings_toggles.py's
    qgis_enum_candidates() calls resolve via (Qgis, "SnappingType.Vertex")
    etc."""

    Info = "Info"
    Warning = "Warning"
    Critical = "Critical"

    class SnappingType:
        Vertex = 1
        Segment = 2

    class MapToolUnit:
        Pixels = 1

    class LayerType:
        Vector = "Vector"


class QgsSnappingConfig:
    """Legacy flat-attribute fallback candidates for the snapping-type
    flags (see settings_toggles._SNAPPING_*_CANDIDATES) -- Qgis.SnappingType
    resolves first in practice, these exist only so the fallback branch of
    qgis_enum_candidates() has something real to resolve if ever exercised.
    """

    VertexFlag = 1
    SegmentFlag = 2

    def __init__(self):
        self._enabled = False
        self._tolerance = None
        self._units = None
        self._type_flag = None
        #: Stands in for the per-layer settings the real config carries,
        #: which change whenever layers are added -- not something Apply
        #: touches.
        self._individual_layer_settings = {}

    def set_layer_settings(self, layer_id, settings):
        self._individual_layer_settings[layer_id] = settings

    def setEnabled(self, enabled: bool):
        self._enabled = enabled

    def enabled(self) -> bool:
        return self._enabled

    def setTolerance(self, tolerance):
        self._tolerance = tolerance

    def tolerance(self):
        return self._tolerance

    def setUnits(self, units):
        self._units = units

    def units(self):
        return self._units

    def setTypeFlag(self, flag):
        self._type_flag = flag

    def typeFlag(self):
        return self._type_flag

    def __eq__(self, other):
        if not isinstance(other, QgsSnappingConfig):
            return NotImplemented
        return (
            self._enabled == other._enabled
            and self._tolerance == other._tolerance
            and self._units == other._units
            and self._type_flag == other._type_flag
            and self._individual_layer_settings == other._individual_layer_settings
        )

    def __repr__(self):
        return (
            f"QgsSnappingConfig(enabled={self._enabled!r}, tolerance={self._tolerance!r}, "
            f"units={self._units!r}, type_flag={self._type_flag!r})"
        )


class QgsTolerance:
    class UnitType:
        Pixels = 1


class _FakeBookmarkManager:
    def __init__(self):
        self._bookmarks = []

    def bookmarks(self):
        return list(self._bookmarks)


class QgsProject:
    """Singleton, like the real QgsProject.instance(). snappingConfig()
    returns an independent copy each call -- QgsSnappingConfig is a C++
    value type there, and settings_toggles._apply_snapping_defaults()
    relies on exactly that value-semantics (it reads the "original" once,
    then reads a *second*, separately-mutable copy to hand to
    setTypeFlag()/setSnappingConfig()) -- see that method's body."""

    _instance: Optional["QgsProject"] = None

    def __init__(self):
        self._snapping_config = QgsSnappingConfig()
        self._layers: Dict[str, Any] = {}
        self._bookmark_manager = _FakeBookmarkManager()
        self._dirty = False
        #: Emitted by the real QgsProject on New/Open/Close (clear()).
        self.cleared = FakeSignal()

    def isDirty(self) -> bool:
        return self._dirty

    def setDirty(self, dirty: bool = True):
        self._dirty = dirty

    def clear(self):
        """Test helper mirroring QgsProject.clear(): fresh state, then cleared."""
        self._snapping_config = QgsSnappingConfig()
        self._dirty = False
        self.cleared.emit()

    @classmethod
    def instance(cls) -> "QgsProject":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def snappingConfig(self) -> QgsSnappingConfig:
        return copy.deepcopy(self._snapping_config)

    def setSnappingConfig(self, config: QgsSnappingConfig):
        # Real QgsProject marks itself dirty when the config changes.
        if config != self._snapping_config:
            self._dirty = True
        self._snapping_config = copy.deepcopy(config)

    def mapLayers(self) -> Dict[str, Any]:
        return dict(self._layers)

    def mapLayer(self, layer_id):
        return self._layers.get(layer_id)

    def bookmarkManager(self) -> _FakeBookmarkManager:
        return self._bookmark_manager


class _FakeMessageLog:
    def __init__(self):
        self.messageReceived = FakeSignal()

    def logMessage(self, message: str, tag: str = "", level=None):
        self.messageReceived.emit(message, tag, level)


class _FakeTaskManager:
    """Encodes QgsTaskManager's documented contract -- see module
    docstring. `add_task()`/`forget()` are test helpers (not part of the
    real API) standing in for QGIS actually running a background task."""

    def __init__(self):
        self.taskAdded = FakeSignal()
        self._tasks: Dict[int, Any] = {}
        self._next_id = 1

    def add_task(self, task) -> int:
        task_id = self._next_id
        self._next_id += 1
        self._tasks[task_id] = task
        self.taskAdded.emit(task_id)
        return task_id

    def task(self, task_id: int):
        """QgsTaskManager.task(id) -> QgsTask | None."""
        return self._tasks.get(task_id)

    def forget(self, task_id: int):
        """Test helper: simulates QgsTaskManager releasing a finished/
        terminated task, the way it does in real QGIS once a task
        completes."""
        self._tasks.pop(task_id, None)


class FakeAlgorithm:
    def __init__(self, algorithm_id: str, display_name: str):
        self._id = algorithm_id
        self._display_name = display_name

    def id(self) -> str:
        return self._id

    def displayName(self) -> str:
        return self._display_name


class _FakeProcessingRegistry:
    def __init__(self):
        self._algorithms = []

    def algorithms(self):
        return list(self._algorithms)


class QgsApplication:
    """Class-level (not instance-level) singletons, mirroring the real
    QgsApplication.messageLog()/taskManager() app-wide singletons. Reset
    between tests by the `reset_qgis_fakes` autouse fixture in conftest.py
    so state can't leak across tests."""

    _message_log = _FakeMessageLog()
    _task_manager = _FakeTaskManager()
    _processing_registry = _FakeProcessingRegistry()

    @classmethod
    def messageLog(cls) -> _FakeMessageLog:
        return cls._message_log

    @classmethod
    def taskManager(cls) -> _FakeTaskManager:
        return cls._task_manager

    @classmethod
    def processingRegistry(cls) -> _FakeProcessingRegistry:
        return cls._processing_registry

    @staticmethod
    def getThemeIcon(name: str):
        from .PyQt.QtGui import QIcon

        return QIcon(name)


def reset_singletons():
    """Test-only helper: give QgsApplication/QgsProject fresh state.
    Called from conftest.py's autouse `reset_qgis_fakes` fixture before
    every test."""
    QgsApplication._message_log = _FakeMessageLog()
    QgsApplication._task_manager = _FakeTaskManager()
    QgsApplication._processing_registry = _FakeProcessingRegistry()
    QgsProject._instance = None


class QgsRasterLayer:
    """Empty stand-in -- only used via isinstance() in contextual_ribbon.py."""


class QgsVectorLayer:
    """Stand-in for the bits contextual_ribbon.py touches: isinstance(),
    isEditable() and the editingStarted/editingStopped signals."""

    def __init__(self):
        self._editable = False
        self.editingStarted = FakeSignal()
        self.editingStopped = FakeSignal()

    def isEditable(self) -> bool:
        return self._editable

    def startEditing(self):
        """Test helper standing in for toggling edit mode."""
        self._editable = True
        self.editingStarted.emit()

    def stopEditing(self):
        self._editable = False
        self.editingStopped.emit()


class QgsLocatorResult:
    def __init__(self):
        self.filter = None
        self.displayString = ""
        self.description = ""
        self.userData = None


class QgsLocatorFilter:
    """Base class stand-in for locator_filter.ArcGISWorkspaceLocatorFilter."""

    def __init__(self):
        self.resultFetched = FakeSignal()

    def setUseWithoutPrefix(self, value: bool):
        self._use_without_prefix = value
