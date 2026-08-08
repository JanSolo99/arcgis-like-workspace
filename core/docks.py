"""Dock widget rearrangement: Contents (left); Catalog, Geoprocessing,
Symbology, and Identify Results (right, tabbed); Log Messages (bottom,
hidden by default). All native QGIS docks -- nothing custom-built."""

from typing import List, Optional

from qgis.PyQt.QtWidgets import QDockWidget

from .compat import BOTTOM_DOCK_WIDGET_AREA, LEFT_DOCK_WIDGET_AREA, RIGHT_DOCK_WIDGET_AREA


class DockArranger:
    """Rearranges and renames native QGIS dock widgets, reversibly."""

    def __init__(self, window):
        self.window = window
        self.renamed_docks: dict = {}

    def arrange(self):
        """Rearrange dock widgets: Contents on the left; Catalog, Geoprocessing,
        Symbology, and Identify Results stacked on the right; Log Messages at
        the bottom (kept hidden -- it also feeds the Notifications dock)."""
        contents = self.find_dock(
            ["layers", "layer tree", "legend", "toc"],
            exclude=["styling", "style", "symbology"],
        )
        catalog = self.find_dock(["browser"])
        geoprocessing = self.find_dock(["processing"])
        symbology = self.find_dock(["styling", "style", "symbology"])
        # Promoted in place of a custom Attributes pane -- QGIS's native
        # Identify Results dock is a ready-made, selection/click-driven
        # feature inspector with zero edit-buffer-conflict risk.
        identify_results = self.find_dock(["identify results"])

        if contents is not None:
            self.rename_dock(contents, "Contents")
            contents.setVisible(True)
            self.window.addDockWidget(LEFT_DOCK_WIDGET_AREA, contents)

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
            dock.setVisible(True)
            self.window.addDockWidget(RIGHT_DOCK_WIDGET_AREA, dock)

            if right_anchor is None:
                right_anchor = dock
            else:
                self.window.tabifyDockWidget(right_anchor, dock)

        if right_anchor is not None:
            right_anchor.raise_()

        log_messages = self.find_dock(["log messages"])
        if log_messages is not None:
            self.rename_dock(log_messages, "Log Messages")
            self.window.addDockWidget(BOTTOM_DOCK_WIDGET_AREA, log_messages)
            log_messages.setVisible(False)

    def find_dock(self, tokens: List[str], exclude: Optional[List[str]] = None) -> Optional[QDockWidget]:
        """Return the first dock whose name/title matches any *tokens* but none of *exclude*."""
        exclude = exclude or []
        docks = self.window.findChildren(QDockWidget)

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
        """Restore original dock widget titles."""
        for dock, title in self.renamed_docks.values():
            dock.setWindowTitle(title)
        self.renamed_docks = {}
