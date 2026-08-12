"""Adds a "Toggle Labels" entry (and a few other common actions) to the
Contents right-click menu.

CRASH-FIX / LIFETIME NOTE (read before touching this file): the previous
version of this module captured QGIS's native menu provider via
`view.menuProvider()`, installed a wrapper via `view.setMenuProvider()`,
and tried to "give the native one back" on Restore by calling
`setMenuProvider()` again with the captured reference.

That is unsafe and was the cause of a real QGIS crash. QGIS's own docs
for `setMenuProvider()` state it "Takes ownership of the instance" -- the
view stores the provider in a `std::unique_ptr`, and *every* call deletes
whatever provider was installed before. So:

  1. The very first setMenuProvider() call (in the old apply()) deleted
     QGIS's native provider. The captured "original" reference was
     already dangling from that point on.
  2. Restore() then passed that dangling pointer back into
     setMenuProvider(). This doesn't crash immediately -- reset() just
     stores the pointer -- but it corrupts the view's internal state.
  3. The *next* setMenuProvider() call (the second Apply) deletes
     whatever is "currently" installed as part of replacing it -- which
     was that dangling pointer. Deleting an already-deleted object is a
     double-free, which is exactly the kind of bug that crashes the
     whole process instead of raising a catchable Python exception.
     Apply -> Restore -> Apply again -> crash.

Because of this, this module NEVER attempts to preserve, delegate to, or
restore the native provider. It installs its own self-contained provider
(built from QgsLayerTreeViewDefaultActions, QGIS's supported helper for
exactly this) at most ONCE for the life of the QGIS session, and only
ever toggles an `active` flag afterward -- apply()/restore() never call
setMenuProvider() again. The unavoidable tradeoff: once installed, the
Contents right-click menu shows this plugin's reconstructed set of
common actions (zoom, rename, remove, feature count, and -- only while
"active" -- Toggle Labels and Layer Properties) instead of QGIS's exact
native menu, for the rest of that QGIS session, even after Restore --
there is no API to get the original back.
"""

import logging

from qgis.gui import QgsLayerTreeViewDefaultActions, QgsLayerTreeViewMenuProvider
from qgis.PyQt.QtWidgets import QAction, QMenu

logger = logging.getLogger(__name__)


class _SelfContainedMenuProvider(QgsLayerTreeViewMenuProvider):
    """Builds the Contents context menu from scratch every time.

    Never wraps or delegates to a previously-installed provider -- see
    module docstring. `active` gates only the extra ArcGIS-like entries
    (Toggle Labels, Layer Properties); the common actions below remain
    available even after Restore, since there is no way back to the
    original native menu once this provider has been installed.
    """

    def __init__(self, iface, view):
        super().__init__()
        self.iface = iface
        self._view = view
        self.active = False

    def createContextMenu(self) -> QMenu:
        menu = QMenu()
        layer = self._view.currentLayer()

        try:
            actions = QgsLayerTreeViewDefaultActions(self._view)
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not create QgsLayerTreeViewDefaultActions")
            actions = None

        if actions is not None:
            if layer is not None:
                self._add_action(menu, lambda: actions.actionZoomToLayers(self.iface.mapCanvas(), menu))
            self._add_action(menu, lambda: actions.actionRenameGroupOrLayer(menu))
            self._add_action(menu, lambda: actions.actionRemoveGroupOrLayer(menu))
            if layer is not None:
                self._add_action(menu, lambda: actions.actionShowFeatureCount(menu))

        if not self.active:
            return menu

        if layer is not None and hasattr(layer, "labelsEnabled") and hasattr(layer, "setLabelsEnabled"):
            menu.addSeparator()
            label_action = QAction("Toggle Labels", menu)
            label_action.setCheckable(True)
            try:
                label_action.setChecked(bool(layer.labelsEnabled()))
            except Exception:
                logger.debug("ArcGIS-like Workspace: could not read labelsEnabled()", exc_info=True)
            label_action.toggled.connect(lambda checked, target=layer: self._toggle_labels(target, checked))
            menu.addAction(label_action)

        if layer is not None:
            properties_action = QAction("Layer Properties...", menu)
            properties_action.triggered.connect(lambda checked=False, target=layer: self._show_properties(target))
            menu.addAction(properties_action)

        return menu

    @staticmethod
    def _add_action(menu: QMenu, factory):
        """Best-effort: adds the QAction *factory()* returns, skipping
        quietly (and logging) if the call raises or returns None."""
        try:
            action = factory()
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not build a default layer-tree action")
            return
        if action is not None:
            menu.addAction(action)

    def _show_properties(self, layer):
        try:
            self.iface.showLayerProperties(layer)
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not open layer properties for %r", layer)

    @staticmethod
    def _toggle_labels(layer, checked: bool):
        try:
            layer.setLabelsEnabled(checked)
            layer.triggerRepaint()
        except Exception:
            logger.exception("ArcGIS-like Workspace: failed to toggle labels for %r", layer)


class LayerTreeLabelingMenu:
    """Installs the self-contained menu provider (at most once) and
    toggles its `active` flag on apply()/restore() -- see module
    docstring for why setMenuProvider() is never called more than once.
    """

    def __init__(self, iface):
        self.iface = iface
        self._provider = None

    def apply(self):
        """Idempotent, and safe to call repeatedly across apply/restore
        cycles -- only the first call ever installs a provider."""
        self._ensure_installed()
        if self._provider is not None:
            self._provider.active = True

    def restore(self):
        """Safe to call even if apply() never ran. Does NOT uninstall the
        provider (that would require the same unsafe setMenuProvider()
        round-trip that caused the crash this module fixes) -- just
        turns off the extra ArcGIS-like menu entries."""
        if self._provider is not None:
            self._provider.active = False

    def _ensure_installed(self):
        if self._provider is not None:
            return
        view = self.iface.layerTreeView()
        if view is None:
            return
        self._provider = _SelfContainedMenuProvider(self.iface, view)
        view.setMenuProvider(self._provider)
