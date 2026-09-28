"""A locator filter that finds QGIS geoprocessing tools by their ArcGIS
Pro names (typing "Erase" finds Difference), plus a "Find" button that
focuses QGIS's native locator bar (Ctrl+K).

QGIS's own locator already searches project layers, bookmarks and
processing algorithms by their QGIS names without a prefix (the built-in
"layertree", "bookmarks" and "processing_alg" filters), so this filter
only adds what those can't find: an Esri tool name leading to its QGIS
equivalent. An earlier version also searched layers, bookmarks and
algorithm names itself, which showed every such hit twice.
"""

import logging
from typing import List, Tuple

from qgis.core import QgsApplication, QgsLocatorFilter, QgsLocatorResult
from qgis.gui import QgsLocatorWidget
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QWidget

from .compat import qgis_enum
from .toolbars import theme_icon

logger = logging.getLogger(__name__)

# ArcGIS refugees search for the tool they know by its Esri name, not its
# QGIS Processing name -- "Erase" has no hit against "Difference" otherwise.
# Keys are lowercase ArcGIS tool names. Values are either an exact
# algorithm id ("provider:name", used where a display-name substring would
# be ambiguous -- "merge" alone matches half a dozen algorithms) or a
# substring matched against algorithm displayName()s. Curated by hand
# against docs.qgis.org's processing algorithm reference and checked
# against a QGIS 4.2 registry, not exhaustive -- extend as more
# ArcGIS-to-QGIS gaps are reported.
ESRI_TOOL_ALIASES = {
    "erase": "native:difference",
    "spatial join": "join attributes by location",
    "feature to point": "centroids",
    "add field": "add field to attributes table",
    "calculate field": "field calculator",
    "project": "reproject layer",
    "merge": "native:mergevectorlayers",
    "append": "native:mergevectorlayers",
    "intersect": "intersection",
    "dissolve": "dissolve",
    "clip": "clip",
    "buffer": "buffer",
    "union": "union",
    "select by location": "select by location",
    "select by attributes": "select by expression",
    "xy table to point": "create points layer from table",
    "table to table": "export to spreadsheet",
    "summary statistics": "statistics by categories",
    "near": "distance to nearest hub",
    "points to line": "points to path",
    "feature class to feature class": "convert format",
    "raster to polygon": "gdal:polygonize",
    "polygon to raster": "gdal:rasterize",
    "extract by mask": "clip raster by mask layer",
    "mosaic": "gdal:merge",
    "mosaic to new raster": "gdal:merge",
}


def _alias_matches(qgis_term: str, algorithm_id: str, display_name_lower: str) -> bool:
    if ":" in qgis_term:
        return algorithm_id == qgis_term
    return qgis_term in display_name_lower


def _format_esri_alias_name(esri_name: str) -> str:
    """Title-case an ESRI_TOOL_ALIASES key for display, e.g. in a result
    description. Good enough for a locator hint; not a general title-caser
    (the one acronym this plugin's alias table contains, "xy", is fixed up
    by hand rather than pulling in a full title-casing dependency).
    """
    label = esri_name.title()
    if label.startswith("Xy "):
        label = "XY " + label[3:]
    return label


class ArcGISWorkspaceLocatorFilter(QgsLocatorFilter):
    """Finds processing algorithms by their ArcGIS Pro tool names."""

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        #: (algorithm id, display name) pairs, snapshotted in prepare().
        self._algorithms: List[Tuple[str, str]] = []
        self.setUseWithoutPrefix(True)

    def name(self):
        return "arcgis_like_workspace_unified_search"

    def displayName(self):
        return "ArcGIS Tool Names"

    def priority(self):
        return qgis_enum(QgsLocatorFilter, "Medium", "Priority")

    def clone(self):
        return ArcGISWorkspaceLocatorFilter(self.iface)

    def prepare(self, string, context):
        """Snapshot the processing registry on the main thread.

        QGIS calls prepare() on the main thread and then runs
        fetchResults() on a worker thread; the registry and its algorithm
        objects are not thread-safe, so fetchResults() only reads this
        plain-Python snapshot.
        """
        try:
            self._algorithms = [
                (algorithm.id(), algorithm.displayName())
                for algorithm in QgsApplication.processingRegistry().algorithms()
            ]
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not read the processing registry")
            self._algorithms = []
        return []

    def fetchResults(self, search, context, feedback):
        if not search or len(search) < 2:
            return
        needle = search.lower()

        emitted = set()
        for esri_name, qgis_term in ESRI_TOOL_ALIASES.items():
            if needle not in esri_name:
                continue
            for algorithm_id, display_name in self._algorithms:
                if feedback.isCanceled():
                    return
                display_lower = display_name.lower()
                if algorithm_id in emitted or not _alias_matches(qgis_term, algorithm_id, display_lower):
                    continue
                if needle in display_lower:
                    # QGIS's own processing filter already lists it (e.g.
                    # "clip" -> Clip); only aliases add anything here.
                    continue
                emitted.add(algorithm_id)
                self._emit(
                    display_name,
                    f"Geoprocessing Tool (ArcGIS: {_format_esri_alias_name(esri_name)})",
                    {"type": "algorithm", "id": algorithm_id},
                )

    def _emit(self, display_string: str, description: str, user_data: dict):
        result = QgsLocatorResult()
        result.filter = self
        result.displayString = display_string
        result.description = description
        result.userData = user_data
        self.resultFetched.emit(result)

    def triggerResult(self, result):
        data = result.userData
        if isinstance(data, dict) and data.get("type") == "algorithm":
            self._trigger_algorithm(data.get("id"))

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


def find_locator_widget(window):
    """Return QGIS's native locator bar widget, or None.

    findChild(QgsLocatorWidget) returns None on QGIS 4.2 (verified): the
    widget is created by the app, so PyQt only knows it as a plain QWidget
    and the class-based lookup never matches. Find it by its Qt class
    name, then sip.cast() it to the Python class so search() is callable.
    """
    widget = window.findChild(QgsLocatorWidget)
    if widget is not None:
        return widget
    for candidate in window.findChildren(QWidget):
        if candidate.metaObject().className() == "QgsLocatorWidget":
            from qgis.PyQt import sip

            return sip.cast(candidate, QgsLocatorWidget)
    return None


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
            self._find_action = QAction(
                theme_icon("/search.svg", "SP_FileDialogContentsView"), "Find", self.iface.mainWindow()
            )
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
        # QgsGui.instance().locatorWidget() does not exist on any QGIS
        # version -- the locator widget lives on QgisApp (the main window),
        # not on the QgsGui singleton, and it's not exposed via
        # QgisInterface either. See find_locator_widget().
        try:
            widget = find_locator_widget(self.iface.mainWindow())
            if widget is not None:
                widget.search("")
            else:
                logger.warning("ArcGIS-like Workspace: could not find the native locator widget")
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not focus the native locator bar")
