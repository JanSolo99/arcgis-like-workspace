"""Shows/hides ribbon action groups and native editing toolbars based on
the active layer.

Mimics ArcGIS Pro's contextual ribbon tabs (e.g. "Feature Layer" tools that
only appear when a feature layer is selected in Contents, editing tools
that only matter while editing) using only signal connections and
visibility toggles -- no new widgets.

The native toolbars' original visibility is not recorded here: Restore
brings it back wholesale via QMainWindow.restoreState() (plugin.py), which
covers every toolbar this module touches.
"""

import logging

from qgis.core import QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtWidgets import QToolBar

from .constants import QGIS_EDITING_CONTEXT_TOOLBAR_NAMES, QGIS_VECTOR_CONTEXT_TOOLBAR_NAMES
from .reversible import ConnectionTracker

logger = logging.getLogger(__name__)

#: Ribbon groups (see toolbars.ToolbarBuilder.action_groups) only relevant
#: when a vector layer is active.
VECTOR_ONLY_GROUPS = ("Edit", "Selection")
#: Ribbon groups only relevant when a raster layer is active. Empty for now
#: -- kept as an explicit, separate list (rather than "everything not
#: vector-only") so a future raster-specific group has an obvious place to
#: register without touching the show/hide logic below.
RASTER_ONLY_GROUPS = ()


class ContextualRibbon:
    """Connects iface.currentLayerChanged to toggle ribbon group visibility."""

    def __init__(self, iface, toolbars):
        self.iface = iface
        self.toolbars = toolbars
        self._connections = ConnectionTracker()
        #: editingStarted/editingStopped of the current active layer only --
        #: swapped out on every layer change, so it never accumulates.
        self._layer_connections = ConnectionTracker()
        self._connected = False

    def apply(self):
        """Idempotent connection; re-syncs visibility every call (including
        on re-apply, when the ribbon's action groups have just been rebuilt
        from scratch and would otherwise default to all-visible)."""
        if not self._connected:
            self._connections.connect(self.iface.currentLayerChanged, self._on_layer_changed)
            self._connected = True
        self._on_layer_changed(self.iface.activeLayer())

    def restore(self):
        """Safe to call even if apply() never ran.

        Must disconnect before the ribbon toolbar's widgets are scheduled
        for deletion elsewhere -- plugin.py runs features.restore_all()
        before toolbars.remove_workspace_toolbars(), which guarantees that
        ordering here.
        """
        self._connections.disconnect_all()
        self._layer_connections.disconnect_all()
        self._connected = False
        self._set_all_groups_visible(True)

    def _on_layer_changed(self, layer):
        is_vector = isinstance(layer, QgsVectorLayer)
        is_raster = isinstance(layer, QgsRasterLayer)
        self._watch_editing_state(layer if is_vector else None)
        self._sync_native_toolbars(layer)
        try:
            for label in VECTOR_ONLY_GROUPS:
                group = self.toolbars.action_groups.get(label)
                if group is not None:
                    group.set_visible(is_vector)
            for label in RASTER_ONLY_GROUPS:
                group = self.toolbars.action_groups.get(label)
                if group is not None:
                    group.set_visible(is_raster)
        except RuntimeError:
            # Underlying Qt widget already deleted -- e.g. the workspace was
            # restored between the signal firing and this handler running.
            logger.debug(
                "ArcGIS-like Workspace: ribbon group toggle skipped (widget deleted)",
                exc_info=True,
            )

    def _set_all_groups_visible(self, visible: bool):
        for group in self.toolbars.action_groups.values():
            try:
                group.set_visible(visible)
            except RuntimeError:
                # Underlying Qt widget already deleted -- safe to skip.
                logger.debug(
                    "ArcGIS-like Workspace: could not reset visibility for ribbon group '%s' (widget deleted)",
                    group.label,
                    exc_info=True,
                )

    def _watch_editing_state(self, layer):
        """Follow the active vector layer's edit mode, so the editing
        toolbars appear the moment editing starts, not on the next layer
        change."""
        self._layer_connections.disconnect_all()
        if layer is None:
            return
        try:
            self._layer_connections.connect(layer.editingStarted, self._on_editing_changed)
            self._layer_connections.connect(layer.editingStopped, self._on_editing_changed)
        except (AttributeError, RuntimeError):
            logger.debug("ArcGIS-like Workspace: could not watch the layer's editing state", exc_info=True)

    def _on_editing_changed(self):
        self._sync_native_toolbars(self.iface.activeLayer())

    def _sync_native_toolbars(self, layer):
        is_vector = isinstance(layer, QgsVectorLayer)
        try:
            is_editing = is_vector and bool(layer.isEditable())
        except RuntimeError:
            is_editing = False  # layer deleted between signal and handler
        wanted = {name: is_editing for name in QGIS_EDITING_CONTEXT_TOOLBAR_NAMES}
        wanted.update({name: is_vector for name in QGIS_VECTOR_CONTEXT_TOOLBAR_NAMES})
        try:
            for toolbar in self.toolbars.window.findChildren(QToolBar):
                visible = wanted.get(toolbar.objectName())
                if visible is not None:
                    toolbar.setVisible(visible)
        except RuntimeError:
            logger.debug("ArcGIS-like Workspace: native toolbar toggle skipped (widget deleted)", exc_info=True)
