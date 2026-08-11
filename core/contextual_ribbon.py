"""Shows/hides ribbon action groups based on the active layer's type.

Mimics ArcGIS Pro's contextual ribbon tabs (e.g. "Feature Layer" tools that
only appear when a feature layer is selected in Contents) using only a
signal connection and visibility toggles -- no new widgets.
"""

import logging

from qgis.core import QgsRasterLayer, QgsVectorLayer

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
        self._connected = False
        self._set_all_groups_visible(True)

    def _on_layer_changed(self, layer):
        is_vector = isinstance(layer, QgsVectorLayer)
        is_raster = isinstance(layer, QgsRasterLayer)
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
