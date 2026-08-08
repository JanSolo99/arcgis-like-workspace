"""Adds a one-click "Toggle Labels" entry to the Contents right-click menu.

ArcGIS Pro exposes a Labeling toggle directly on a layer's Contents-pane
context menu; QGIS requires opening full Layer Properties. This wraps the
layer tree view's existing menu provider (rather than replacing it) so the
native context menu -- rename, zoom to layer, remove, properties, etc. --
is preserved, with the toggle appended at the end.
"""

import logging
from typing import Optional

from qgis.gui import QgsLayerTreeViewMenuProvider
from qgis.PyQt.QtWidgets import QAction, QMenu

logger = logging.getLogger(__name__)


class _WrappingMenuProvider(QgsLayerTreeViewMenuProvider):
    """Delegates to an existing menu provider, then appends a Labeling toggle."""

    def __init__(self, view, original_provider):
        super().__init__()
        self._view = view
        self._original_provider = original_provider

    def createContextMenu(self) -> QMenu:
        if self._original_provider is not None:
            try:
                menu = self._original_provider.createContextMenu()
            except Exception:
                logger.exception("ArcGIS-like Workspace: original layer-tree menu provider failed")
                menu = QMenu()
        else:
            menu = QMenu()

        layer = self._view.currentLayer()
        if layer is not None and hasattr(layer, "labelsEnabled") and hasattr(layer, "setLabelsEnabled"):
            menu.addSeparator()
            action = QAction("Toggle Labels", menu)
            action.setCheckable(True)
            try:
                action.setChecked(bool(layer.labelsEnabled()))
            except Exception:
                logger.debug("ArcGIS-like Workspace: could not read labelsEnabled()", exc_info=True)
            action.toggled.connect(lambda checked, target=layer: self._toggle_labels(target, checked))
            menu.addAction(action)

        return menu

    @staticmethod
    def _toggle_labels(layer, checked: bool):
        try:
            layer.setLabelsEnabled(checked)
            layer.triggerRepaint()
        except Exception:
            logger.exception("ArcGIS-like Workspace: failed to toggle labels for %r", layer)


class LayerTreeLabelingMenu:
    """Installs/removes the Labeling-toggle menu-provider wrapper, reversibly."""

    def __init__(self, iface):
        self.iface = iface
        self._original_provider = None
        # Kept as a strong reference on this (plugin-owned) instance for its
        # whole active lifetime -- Qt/PyQt does not keep the wrapper alive on
        # the C++ side, so an unreferenced Python wrapper would be garbage
        # collected out from under the layer tree view.
        self._wrapper: Optional[_WrappingMenuProvider] = None

    def apply(self):
        """Idempotent: calling apply() again before restore() is a no-op."""
        if self._wrapper is not None:
            return
        view = self.iface.layerTreeView()
        if view is None:
            return
        self._original_provider = view.menuProvider()
        self._wrapper = _WrappingMenuProvider(view, self._original_provider)
        view.setMenuProvider(self._wrapper)

    def restore(self):
        """Safe to call even if apply() never ran."""
        if self._wrapper is None:
            return
        view = self.iface.layerTreeView()
        if view is not None:
            view.setMenuProvider(self._original_provider)
        self._wrapper = None
        self._original_provider = None
