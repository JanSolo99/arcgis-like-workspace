"""A unified locator filter searching layers, geoprocessing tools, and
bookmarks in one query -- closer to ArcGIS Pro's single search box than
having to know which of QGIS's several built-in locator filters to use.
QGIS's native locator bar (Ctrl+K) already supports this extension point;
this filter is purely additive alongside the existing built-in ones.
"""

import logging

from qgis.core import QgsApplication, QgsLocatorFilter, QgsLocatorResult, QgsProject
from qgis.gui import QgsGui
from qgis.PyQt.QtWidgets import QAction, QDockWidget

from .compat import qgis_enum
from .toolbars import standard_icon

logger = logging.getLogger(__name__)


class ArcGISWorkspaceLocatorFilter(QgsLocatorFilter):
    """Searches project layers, processing algorithms, and bookmarks."""

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.setUseWithoutPrefix(True)

    def name(self):
        return "arcgis_like_workspace_unified_search"

    def displayName(self):
        return "Layers, Tools & Bookmarks"

    def priority(self):
        return qgis_enum(QgsLocatorFilter, "Medium", "Priority")

    def clone(self):
        return ArcGISWorkspaceLocatorFilter(self.iface)

    def fetchResults(self, search, context, feedback):
        if not search or len(search) < 2:
            return
        needle = search.lower()

        try:
            for layer_id, layer in QgsProject.instance().mapLayers().items():
                if feedback.isCanceled():
                    return
                if needle in layer.name().lower():
                    self._emit(layer.name(), "Layer", {"type": "layer", "id": layer_id})
        except Exception:
            logger.exception("ArcGIS-like Workspace: locator layer search failed")

        try:
            for algorithm in QgsApplication.processingRegistry().algorithms():
                if feedback.isCanceled():
                    return
                if needle in algorithm.displayName().lower():
                    self._emit(
                        algorithm.displayName(),
                        "Geoprocessing Tool",
                        {"type": "algorithm", "id": algorithm.id()},
                    )
        except Exception:
            logger.exception("ArcGIS-like Workspace: locator algorithm search failed")

        try:
            for bookmark in QgsProject.instance().bookmarkManager().bookmarks():
                if feedback.isCanceled():
                    return
                if needle in bookmark.name().lower():
                    self._emit(bookmark.name(), "Bookmark", {"type": "bookmark", "id": bookmark.id()})
        except Exception:
            logger.exception("ArcGIS-like Workspace: locator bookmark search failed")

    def _emit(self, display_string: str, description: str, user_data: dict):
        result = QgsLocatorResult()
        result.filter = self
        result.displayString = display_string
        result.description = description
        result.userData = user_data
        self.resultFetched.emit(result)

    def triggerResult(self, result):
        data = result.userData
        result_type = data.get("type") if isinstance(data, dict) else None
        if result_type == "layer":
            self._trigger_layer(data.get("id"))
        elif result_type == "algorithm":
            self._trigger_algorithm(data.get("id"))
        elif result_type == "bookmark":
            self._trigger_bookmark(data.get("id"))

    def _trigger_layer(self, layer_id):
        layer = QgsProject.instance().mapLayer(layer_id)
        if layer is None:
            return
        try:
            self.iface.setActiveLayer(layer)
            canvas = self.iface.mapCanvas()
            canvas.setExtent(layer.extent())
            canvas.refresh()
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not activate layer from locator result")

    def _trigger_algorithm(self, algorithm_id):
        try:
            import processing

            processing.execAlgorithmDialog(algorithm_id)
            return
        except Exception:
            logger.exception(
                "ArcGIS-like Workspace: could not open algorithm dialog for '%s', "
                "falling back to the Processing Toolbox panel",
                algorithm_id,
            )
        try:
            for dock in self.iface.mainWindow().findChildren(QDockWidget):
                haystack = f"{dock.objectName()} {dock.windowTitle()}".lower()
                if "processing" in haystack:
                    dock.setVisible(True)
                    dock.raise_()
                    return
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not fall back to the Processing Toolbox panel")

    def _trigger_bookmark(self, bookmark_id):
        try:
            for bookmark in QgsProject.instance().bookmarkManager().bookmarks():
                if bookmark.id() == bookmark_id:
                    canvas = self.iface.mapCanvas()
                    canvas.setReferencedExtent(bookmark.extent())
                    canvas.refresh()
                    return
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not zoom to bookmark from locator result")


class LocatorFeature:
    """Registers/deregisters the unified locator filter, reversibly.

    Also adds an optional "Find" button to the tab toolbar that focuses
    QGIS's native locator bar -- switchers otherwise tend to miss that it
    exists at all (default shortcut Ctrl+K, bottom-left of the window).
    """

    def __init__(self, iface, toolbars):
        self.iface = iface
        self.toolbars = toolbars
        self._filter = None
        self._find_action = None

    def apply(self):
        if self._filter is None:
            self._filter = ArcGISWorkspaceLocatorFilter(self.iface)
            try:
                self.iface.registerLocatorFilter(self._filter)
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not register locator filter")
                self._filter = None

        if self._find_action is None:
            self._find_action = QAction(standard_icon("SP_FileDialogContentsView"), "Find", self.iface.mainWindow())
            self._find_action.triggered.connect(self._focus_locator)

        self._attach_find_action()

    def restore(self):
        if self._filter is not None:
            try:
                self.iface.deregisterLocatorFilter(self._filter)
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not deregister locator filter")
            self._filter = None

        if self._find_action is not None:
            if self.toolbars.tab_toolbar is not None:
                self.toolbars.tab_toolbar.removeAction(self._find_action)
            # Parented to iface.mainWindow() (long-lived), not to anything
            # this plugin destroys on restore -- unlike the notifications
            # dock's toggle action (owned/deleted by its QDockWidget), this
            # one needs an explicit deleteLater() or it would be orphaned
            # with a live signal connection for the rest of the QGIS session.
            self._find_action.deleteLater()
        self._find_action = None

    def _attach_find_action(self):
        toolbar = self.toolbars.tab_toolbar
        if self._find_action is None or toolbar is None:
            return
        if self._find_action not in toolbar.actions():
            toolbar.addAction(self._find_action)

    def _focus_locator(self):
        try:
            QgsGui.instance().locatorWidget().search("")
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not focus the native locator bar")
