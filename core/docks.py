"""Dock widget rearrangement: Contents (left), Catalog/Geoprocessing/Symbology (right, tabbed)."""

from typing import List, Optional

from qgis.PyQt.QtWidgets import QDockWidget

from .compat import LEFT_DOCK_WIDGET_AREA, RIGHT_DOCK_WIDGET_AREA


class DockArranger:
    """Rearranges and renames native QGIS dock widgets, reversibly."""

    def __init__(self, window):
        self.window = window
        self.renamed_docks: dict = {}

    def arrange(self):
        """Rearrange dock widgets: Contents on the left; Catalog, Geoprocessing,
        and Symbology stacked on the right."""
        contents = self.find_dock(
            ["layers", "layer tree", "legend", "toc"],
            exclude=["styling", "style", "symbology"],
        )
        catalog = self.find_dock(["browser"])
        geoprocessing = self.find_dock(["processing"])
        symbology = self.find_dock(["styling", "style", "symbology"])

        if contents is not None:
            self.rename_dock(contents, "Contents")
            contents.setVisible(True)
            self.window.addDockWidget(LEFT_DOCK_WIDGET_AREA, contents)

        right_anchor = None
        for dock, title in [
            (catalog, "Catalog"),
            (geoprocessing, "Geoprocessing"),
            (symbology, "Symbology"),
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
