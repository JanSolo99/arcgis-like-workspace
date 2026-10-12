"""Tests for core/contextual_ribbon.py's native-toolbar visibility: the
Digitizing and Snapping toolbars follow the active vector layer's edit
mode, and Labeling follows "is a vector layer active"."""

from arcgis_like_workspace.core.contextual_ribbon import ContextualRibbon
from arcgis_like_workspace.core.toolbars import ToolbarBuilder
from qgis.core import QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import FakeSignal
from qgis.PyQt.QtWidgets import QToolBar

from tests.helpers import FakeMainWindow


class _Iface:
    def __init__(self):
        self.currentLayerChanged = FakeSignal()
        self._active = None

    def activeLayer(self):
        return self._active

    def set_active(self, layer):
        self._active = layer
        self.currentLayerChanged.emit(layer)


def _setup():
    window = FakeMainWindow()
    toolbars = {}
    for name in ("mDigitizeToolBar", "mSnappingToolBar", "mLabelToolBar", "mFileToolBar"):
        toolbar = QToolBar(name)
        toolbar.setObjectName(name)
        toolbars[name] = toolbar
    window.toolbar_rows = [list(toolbars.values())]
    iface = _Iface()
    ribbon = ContextualRibbon(iface, ToolbarBuilder(iface, window))
    return iface, ribbon, toolbars


def _visible(toolbars):
    return {name: toolbar.isVisible() for name, toolbar in toolbars.items()}


def test_no_active_layer_hides_every_contextual_toolbar_only():
    iface, ribbon, toolbars = _setup()

    ribbon.apply()

    assert _visible(toolbars) == {
        "mDigitizeToolBar": False,
        "mSnappingToolBar": False,
        "mLabelToolBar": False,
        "mFileToolBar": True,  # not contextual -- untouched
    }


def test_editing_toolbars_follow_the_active_layers_edit_mode():
    iface, ribbon, toolbars = _setup()
    ribbon.apply()
    layer = QgsVectorLayer()

    iface.set_active(layer)
    assert _visible(toolbars)["mLabelToolBar"] is True
    assert _visible(toolbars)["mDigitizeToolBar"] is False

    layer.startEditing()
    assert _visible(toolbars)["mDigitizeToolBar"] is True
    assert _visible(toolbars)["mSnappingToolBar"] is True

    layer.stopEditing()
    assert _visible(toolbars)["mDigitizeToolBar"] is False


def test_switching_layers_stops_watching_the_previous_one():
    iface, ribbon, toolbars = _setup()
    ribbon.apply()
    first = QgsVectorLayer()
    iface.set_active(first)

    iface.set_active(QgsRasterLayer())
    first.startEditing()  # no longer the active layer

    assert first.editingStarted.slots == []
    assert _visible(toolbars)["mDigitizeToolBar"] is False
    assert _visible(toolbars)["mLabelToolBar"] is False


def test_restore_disconnects_everything():
    iface, ribbon, toolbars = _setup()
    ribbon.apply()
    layer = QgsVectorLayer()
    iface.set_active(layer)

    ribbon.restore()

    assert iface.currentLayerChanged.slots == []
    assert layer.editingStarted.slots == [] and layer.editingStopped.slots == []
