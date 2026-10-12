"""Dock widget rearrangement: Contents (left); Catalog, Geoprocessing,
Symbology, and Identify Results (right, tabbed); Log Messages (bottom,
hidden by default). All native QGIS docks -- nothing custom-built."""

import logging
from typing import List, Optional

from qgis.PyQt.QtWidgets import QDockWidget

from .compat import BOTTOM_DOCK_WIDGET_AREA, LEFT_DOCK_WIDGET_AREA, RIGHT_DOCK_WIDGET_AREA

logger = logging.getLogger(__name__)

#: Lookup specs for the native docks this plugin arranges: exact object
#: names first (stable across QGIS 3.28-4.x and, unlike titles, across UI
#: languages -- read off a QGIS 4.2 session), then title/object-name
#: substrings as a fallback for builds that name them differently.
#: "IdentifyResultsDock" is QGIS's name for the lazily-created Identify
#: Results dock, which may not exist yet at Apply time.
CONTENTS_DOCK = (["Layers"], ["layers", "layer tree", "legend", "toc"], ["styling", "style", "symbology"])
CATALOG_DOCK = (["Browser"], ["browser"], ["browser2", "(2)"])
GEOPROCESSING_DOCK = (["ProcessingToolbox"], ["processing"], [])
SYMBOLOGY_DOCK = (["LayerStyling"], ["styling", "style", "symbology"], [])
IDENTIFY_RESULTS_DOCK = (["IdentifyResultsDock"], ["identify results"], [])
LOG_MESSAGES_DOCK = (["MessageLog"], ["log messages"], [])


class DockArranger:
    """Rearranges and renames native QGIS dock widgets, reversibly."""

    def __init__(self, window):
        self.window = window
        self.renamed_docks: dict = {}

    def arrange(self):
        """Rearrange dock widgets: Contents on the left; Catalog, Geoprocessing,
        Symbology, and Identify Results stacked on the right; Log Messages at
        the bottom (kept hidden -- it also feeds the Notifications dock)."""
        contents = self.find_named_dock(CONTENTS_DOCK)
        catalog = self.find_named_dock(CATALOG_DOCK)
        geoprocessing = self.find_named_dock(GEOPROCESSING_DOCK)
        symbology = self.find_named_dock(SYMBOLOGY_DOCK)
        # Promoted in place of a custom Attributes pane -- QGIS's native
        # Identify Results dock is a ready-made, selection/click-driven
        # feature inspector with zero edit-buffer-conflict risk.
        identify_results = self.find_named_dock(IDENTIFY_RESULTS_DOCK)

        if contents is not None:
            self.rename_dock(contents, "Contents")
            self._move_dock(contents, LEFT_DOCK_WIDGET_AREA)
            contents.setVisible(True)

        right_anchor = None
        for dock, title in [
            (catalog, "Catalog"),
            (geoprocessing, "Geoprocessing"),
            (symbology, "Symbology"),
            (identify_results, "Identify Results"),
        ]:
            if dock is None:
                continue
            self.rename_dock(dock, title)
            self._move_dock(dock, RIGHT_DOCK_WIDGET_AREA)
            dock.setVisible(True)

            if right_anchor is None:
                right_anchor = dock
            else:
                self.window.tabifyDockWidget(right_anchor, dock)

        if right_anchor is not None:
            right_anchor.raise_()

        log_messages = self.find_named_dock(LOG_MESSAGES_DOCK)
        if log_messages is not None:
            self.rename_dock(log_messages, "Log Messages")
            self._move_dock(log_messages, BOTTOM_DOCK_WIDGET_AREA)
            log_messages.setVisible(False)

    def _move_dock(self, dock: QDockWidget, area):
        """Reposition *dock* into *area*, reliably.

        QMainWindow.addDockWidget() alone can fail to cleanly detach a
        dock that's currently tabbed with another one (which Browser is,
        by default, tabbed with Layers) -- the widget can stay visually
        in its old spot until some later, unrelated layout change nudges
        Qt into actually redoing the tab group. Explicitly removing it
        first forces a clean re-parent into the target area on the very
        first call, instead of needing a second Apply to "catch up".
        Order also matters here: position before show, not the reverse --
        moving an already-visible dock risks a render-in-old-spot flash
        that setVisible(True)-then-move does not reliably avoid.
        """
        self.window.removeDockWidget(dock)
        self.window.addDockWidget(area, dock)

    def find_named_dock(self, spec) -> Optional[QDockWidget]:
        """Look up a dock by one of the *_DOCK specs above."""
        object_names, tokens, exclude = spec
        return self.find_dock(tokens, exclude=exclude, object_names=object_names)

    def find_dock(
        self,
        tokens: List[str],
        exclude: Optional[List[str]] = None,
        object_names: Optional[List[str]] = None,
    ) -> Optional[QDockWidget]:
        """Return the dock whose object name is exactly one of *object_names*
        or, failing that, the first whose name/title matches any *tokens*
        but none of *exclude*."""
        exclude = exclude or []
        docks = self.window.findChildren(QDockWidget)

        for name in object_names or []:
            for dock in docks:
                if dock.objectName() == name:
                    return dock

        for dock in docks:
            haystack = f"{dock.objectName()} {dock.windowTitle()}".lower()
            if any(token in haystack for token in exclude):
                continue
            if any(token in haystack for token in tokens):
                return dock

        return None

    def rename_dock(self, dock: QDockWidget, title: str):
        """Rename *dock* to *title*, saving the original title for later restore."""
        key = dock.objectName() or str(id(dock))
        if key not in self.renamed_docks:
            self.renamed_docks[key] = (dock, dock.windowTitle())
        dock.setWindowTitle(title)

    def restore_titles(self):
        """Restore original dock widget titles.

        Each dock is a native QGIS widget this plugin doesn't own the
        lifetime of -- e.g. the Processing dock disappears if that plugin
        gets disabled mid-session -- so the underlying C++ object can be
        gone by the time Restore runs. setWindowTitle() on a deleted dock
        raises RuntimeError; guard per-dock so one dead dock can't abort
        the loop and strand the rest un-restored. renamed_docks is cleared
        in `finally` regardless, otherwise a single bad entry would keep
        failing (or keep getting skipped) on every subsequent Restore.
        """
        try:
            for dock, title in self.renamed_docks.values():
                try:
                    dock.setWindowTitle(title)
                except RuntimeError:
                    logger.debug("ArcGIS-like Workspace: dock already deleted, skipping title restore")
        finally:
            self.renamed_docks = {}
