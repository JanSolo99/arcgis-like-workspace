"""ArcGIS-like Workspace — a reversible workspace preset for QGIS.

Applies an ArcGIS Pro-inspired layout using native QGIS toolbars, dock
widgets, and Qt stylesheets.  All changes are reversible via the Restore
action or by disabling the plugin.

Supports QGIS 3.28+ on both Qt 5 and Qt 6.
"""

import logging

from qgis.PyQt.QtCore import QSize, Qt, QSettings
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QLabel,
    QDockWidget,
    QMenu,
    QMessageBox,
    QStyle,
    QToolBar,
    QToolButton,
)
from qgis.core import Qgis
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)
MENU_NAME = "&ArcGIS-like Workspace"
OBJECT_PREFIX = "arcgisLikeWorkspace"
SETTINGS_PREFIX = "arcgis_like_workspace"
STYLE_MARKER = "/* arcgis-like-workspace-style */"


def _qt_enum(legacy_name: str, enum_group: str) -> Any:
    """Return a Qt 5 or Qt 6 enum value without relying on compatibility aliases."""
    legacy_value = getattr(Qt, legacy_name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(getattr(Qt, enum_group), legacy_name)


def _widget_enum(widget_class: type, legacy_name: str, enum_group: str) -> Any:
    """Return a Qt 5 or Qt 6 widget enum value."""
    legacy_value = getattr(widget_class, legacy_name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(getattr(widget_class, enum_group), legacy_name)


TOOL_BUTTON_TEXT_UNDER_ICON = _qt_enum("ToolButtonTextUnderIcon", "ToolButtonStyle")
TOOL_BUTTON_TEXT_BESIDE_ICON = _qt_enum("ToolButtonTextBesideIcon", "ToolButtonStyle")
TOP_TOOLBAR_AREA = _qt_enum("TopToolBarArea", "ToolBarArea")
LEFT_DOCK_WIDGET_AREA = _qt_enum("LeftDockWidgetArea", "DockWidgetArea")
RIGHT_DOCK_WIDGET_AREA = _qt_enum("RightDockWidgetArea", "DockWidgetArea")
INSTANT_POPUP = _widget_enum(QToolButton, "InstantPopup", "ToolButtonPopupMode")


def _qgis_message_level(name: str) -> Any:
    """Return a QGIS 3 or QGIS 4 message level."""
    legacy_value = getattr(Qgis, name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(Qgis.MessageLevel, name)


QGIS_INFO = _qgis_message_level("Info")
QGIS_WARNING = _qgis_message_level("Warning")

# ── standard QGIS toolbar object names that this plugin may hide ──────────
_QGIS_DEFAULT_TOOLBAR_NAMES: set = {
    "mFileToolBar",
    "mLayerToolBar",
    "mMapNavToolBar",
    "mAttributesToolBar",
    "mDigitizeToolBar",
    "mAdvancedDigitizeToolBar",
    "mLabelToolBar",
    "mVectorToolBar",
    "mRasterToolBar",
    "mWebToolBar",
    "mDatabaseToolBar",
    "mHelpToolBar",
    "mPluginToolBar",
    "mSelectionToolBar",
    "mSnappingToolBar",
    "mProjectToolBar",
    "mAnnotationToolBar",
    "mDataStreamingToolBar",
    "mShapeDigitizeToolBar",
    "mMeshDigitizingToolBar",
}

ARC_STYLE = """
/* arcgis-like-workspace-style */
QToolBar#arcgisLikeWorkspaceTabsToolbar {
    background: #f4f6f8;
    border-bottom: 1px solid #c9d2dc;
    padding: 2px 6px;
    spacing: 4px;
}

QToolBar#arcgisLikeWorkspaceRibbonToolbar {
    background: #ffffff;
    border-top: 1px solid #edf0f3;
    border-bottom: 1px solid #bbc7d4;
    padding: 5px 8px;
    spacing: 3px;
}

QToolBar#arcgisLikeWorkspaceTabsToolbar QToolButton,
QToolBar#arcgisLikeWorkspaceRibbonToolbar QToolButton {
    border: 1px solid transparent;
    border-radius: 3px;
    min-width: 68px;
    padding: 4px 6px;
}

QToolBar#arcgisLikeWorkspaceTabsToolbar QToolButton {
    min-width: 76px;
    padding: 4px 10px;
}

QToolBar#arcgisLikeWorkspaceTabsToolbar QToolButton:hover,
QToolBar#arcgisLikeWorkspaceRibbonToolbar QToolButton:hover {
    background: #e7f0fa;
    border-color: #8eb4dc;
}

QLabel#arcgisLikeWorkspaceGroupLabel {
    color: #3e4b57;
    font-weight: 600;
    padding: 0 8px 0 10px;
}

QDockWidget::title {
    background: #eef2f6;
    border-bottom: 1px solid #c9d2dc;
    padding: 4px 6px;
}
"""


class ArcGISLikeWorkspacePlugin:
    """A reversible ArcGIS Pro-inspired workspace preset for QGIS.

    Creates a ribbon-style toolbar layout with tabbed menus reminiscent of
    ArcGIS Pro while using only native QGIS actions and Qt widgets.  Docks
    are rearranged into a Contents pane (left) and stacked Catalog /
    Geoprocessing / Symbology panes (right).
    """

    def __init__(self, iface):
        self.iface = iface
        self.window = iface.mainWindow()
        self.settings: QSettings = QSettings()
        self.apply_action: Optional[QAction] = None
        self.restore_action: Optional[QAction] = None
        self.about_action: Optional[QAction] = None
        self.menu_actions: List[QAction] = []
        self.created_toolbars: List[QToolBar] = []
        self.renamed_docks: dict = {}
        self.previous_stylesheet: Optional[str] = None

    def initGui(self):
        """Create menu entries and toolbar icon — called by QGIS on load."""
        self.apply_action = self._make_plugin_action(
            "Apply ArcGIS-like Workspace",
            self.apply_layout,
            "SP_DesktopIcon",
        )
        self.restore_action = self._make_plugin_action(
            "Restore Previous QGIS Workspace",
            self.restore_layout,
            "SP_BrowserReload",
        )
        self.about_action = self._make_plugin_action(
            "About This Workspace",
            self.show_about,
            "SP_MessageBoxInformation",
        )

        self.menu_actions = [
            self.apply_action,
            self.restore_action,
            self.about_action,
        ]

        for action in self.menu_actions:
            self.iface.addPluginToMenu(MENU_NAME, action)

        self.iface.addToolBarIcon(self.apply_action)

    def unload(self):
        """Remove menu entries, toolbar icon, and restore workspace — called by QGIS on unload."""
        for action in self.menu_actions:
            self.iface.removePluginMenu(MENU_NAME, action)

        if self.apply_action is not None:
            self.iface.removeToolBarIcon(self.apply_action)

        has_saved_state = self.settings.value(self._key("hasSavedState"), False, type=bool)
        if has_saved_state:
            self.restore_layout()
        else:
            self._remove_workspace_toolbars()
            self._restore_dock_titles()
            self._restore_stylesheet()

    def apply_layout(self):
        """Apply the ArcGIS-like workspace: save current state, create ribbon + tab toolbars,
        rearrange dock widgets, and apply the ArcGIS-inspired stylesheet."""
        self._save_original_window_state_once()
        self._remove_workspace_toolbars()
        self._hide_default_toolbars()
        self._create_tab_toolbar()
        self._create_ribbon_toolbar()
        self._arrange_docks()
        self._apply_stylesheet()
        self._notify("Applied the ArcGIS-like workspace preset.")

    def restore_layout(self):
        """Remove workspace toolbars, restore dock titles, remove the stylesheet,
        and restore the original main-window geometry and state."""
        self._remove_workspace_toolbars()
        self._restore_dock_titles()
        self._restore_stylesheet()

        restored = False
        state = self.settings.value(self._key("windowState"))
        geometry = self.settings.value(self._key("windowGeometry"))

        if geometry is not None:
            restored = bool(self.window.restoreGeometry(geometry)) or restored
        if state is not None:
            restored = bool(self.window.restoreState(state)) or restored

        self.settings.remove(SETTINGS_PREFIX)

        if restored:
            self._notify("Restored the previous QGIS workspace.")
        else:
            self._notify(
                "No saved workspace was found. QGIS kept the current layout.",
                QGIS_WARNING,
            )

    def show_about(self):
        """Display an informational About dialog."""
        QMessageBox.information(
            self.window,
            "ArcGIS-like Workspace",
            (
                "This plugin applies an ArcGIS Pro-inspired workspace preset "
                "using native QGIS actions, toolbars, docks, and Qt styling.\n\n"
                "It is a reversible layout and styling layer. It does not copy "
                "Esri icons, branding, or proprietary ArcGIS UI code."
            ),
        )

    def _create_tab_toolbar(self):
        """Build the tab-style toolbar with drop-down menus for each functional area."""
        toolbar = self._new_toolbar("Arc Layout: Tabs", "TabsToolbar", QSize(22, 22))

        tabs = [
            (
                "Project",
                "actionNewProject",
                [
                    ("actionNewProject", "New Project"),
                    ("actionOpenProject", "Open Project"),
                    ("actionSaveProject", "Save Project"),
                    ("actionSaveProjectAs", "Save Project As"),
                    "-",
                    ("actionCreatePrintLayout", "New Layout"),
                    ("actionShowLayoutManager", "Layout Manager"),
                    ("actionProjectProperties", "Project Properties"),
                ],
            ),
            (
                "Map",
                "actionPan",
                [
                    ("actionPan", "Pan"),
                    ("actionZoomIn", "Zoom In"),
                    ("actionZoomOut", "Zoom Out"),
                    ("actionZoomFullExtent", "Full Extent"),
                    ("actionZoomLast", "Previous Extent"),
                    ("actionZoomNext", "Next Extent"),
                    "-",
                    ("actionIdentify", "Identify"),
                    ("actionMeasure", "Measure"),
                    ("actionMeasureArea", "Measure Area"),
                ],
            ),
            (
                "Insert",
                "actionAddOgrLayer",
                [
                    ("actionAddOgrLayer", "Add Vector Layer"),
                    ("actionAddRasterLayer", "Add Raster Layer"),
                    ("actionAddPgLayer", "Add PostGIS Layer"),
                    ("actionAddWmsLayer", "Add WMS/WMTS Layer"),
                    ("actionAddXyzLayer", "Add XYZ Layer"),
                    ("actionAddVectorTileLayer", "Add Vector Tile Layer"),
                    ("actionAddPointCloudLayer", "Add Point Cloud Layer"),
                    "-",
                    ("actionNewVectorLayer", "New Vector Layer"),
                ],
            ),
            (
                "Edit",
                "actionToggleEditing",
                [
                    ("actionToggleEditing", "Toggle Editing"),
                    ("actionSaveEdits", "Save Edits"),
                    ("actionAddFeature", "Add Feature"),
                    ("actionVertexToolActiveLayer", "Vertex Tool"),
                    ("actionMoveFeature", "Move Feature"),
                    "-",
                    ("actionCutFeatures", "Cut Features"),
                    ("actionCopyFeatures", "Copy Features"),
                    ("actionPasteFeatures", "Paste Features"),
                    ("actionDeleteSelected", "Delete Selected"),
                ],
            ),
            (
                "Analysis",
                "actionOpenFieldCalculator",
                [
                    ("actionOpenFieldCalculator", "Field Calculator"),
                    ("actionOpenStatisticalSummary", "Statistics"),
                    ("actionOpenTable", "Attribute Table"),
                    "-",
                    ("actionShowPythonDialog", "Python Console"),
                    ("actionManagePlugins", "Plugin Manager"),
                ],
            ),
            (
                "View",
                "actionToggleFullScreen",
                [
                    ("actionShowBookmarks", "Bookmarks"),
                    ("actionNewBookmark", "New Bookmark"),
                    ("actionMapTips", "Map Tips"),
                    ("actionToggleFullScreen", "Full Screen"),
                    "-",
                    ("actionLayerProperties", "Layer Properties"),
                    ("actionOptions", "Options"),
                ],
            ),
        ]

        for label, icon_action, action_specs in tabs:
            toolbar.addWidget(self._make_menu_button(label, icon_action, action_specs))

        self._add_restore_button(toolbar)

    def _create_ribbon_toolbar(self):
        """Build the ribbon-style toolbar with icon+label groups for each functional area."""
        toolbar = self._new_toolbar("Arc Layout: Ribbon", "RibbonToolbar", QSize(26, 26))
        toolbar.setToolButtonStyle(TOOL_BUTTON_TEXT_UNDER_ICON)

        self._add_action_group(
            toolbar,
            "Project",
            [
                "actionNewProject",
                "actionOpenProject",
                "actionSaveProject",
                "actionCreatePrintLayout",
            ],
        )
        self._add_action_group(
            toolbar,
            "Map",
            [
                "actionPan",
                "actionZoomIn",
                "actionZoomOut",
                "actionZoomFullExtent",
                "actionIdentify",
                "actionMeasure",
            ],
        )
        self._add_action_group(
            toolbar,
            "Layers",
            [
                "actionAddOgrLayer",
                "actionAddRasterLayer",
                "actionAddWmsLayer",
                "actionLayerProperties",
                "actionOpenTable",
            ],
        )
        self._add_action_group(
            toolbar,
            "Edit",
            [
                "actionToggleEditing",
                "actionSaveEdits",
                "actionAddFeature",
                "actionVertexToolActiveLayer",
                "actionDeleteSelected",
            ],
        )
        self._add_action_group(
            toolbar,
            "Selection",
            [
                "actionSelectRectangle",
                "actionSelectPolygon",
                "actionSelectFreehand",
                "actionSelectRadius",
                "actionZoomToSelected",
            ],
        )
        self._add_action_group(
            toolbar,
            "Analysis",
            [
                "actionOpenFieldCalculator",
                "actionOpenStatisticalSummary",
                "actionShowPythonDialog",
            ],
        )

    def _add_action_group(self, toolbar: QToolBar, label: str, action_names: List[str]):
        """Append a labelled group of native QGIS actions to *toolbar*."""
        actions = [self._native_action(name) for name in action_names]
        actions = [action for action in actions if action is not None]
        if not actions:
            return

        if toolbar.actions():
            toolbar.addSeparator()

        group_label = QLabel(label, self.window)
        group_label.setObjectName(f"{OBJECT_PREFIX}GroupLabel")
        toolbar.addWidget(group_label)

        for action in actions:
            toolbar.addAction(action)

    def _arrange_docks(self):
        """Rearrange dock widgets: Contents on the left; Catalog, Geoprocessing,
        and Symbology stacked on the right."""
        contents = self._find_dock(
            ["layers", "layer tree", "legend", "toc"],
            exclude=["styling", "style", "symbology"],
        )
        catalog = self._find_dock(["browser"])
        geoprocessing = self._find_dock(["processing"])
        symbology = self._find_dock(["styling", "style", "symbology"])

        if contents is not None:
            self._rename_dock(contents, "Contents")
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
            self._rename_dock(dock, title)
            dock.setVisible(True)
            self.window.addDockWidget(RIGHT_DOCK_WIDGET_AREA, dock)

            if right_anchor is None:
                right_anchor = dock
            else:
                self.window.tabifyDockWidget(right_anchor, dock)

        if right_anchor is not None:
            right_anchor.raise_()

    def _find_dock(self, tokens: List[str], exclude: Optional[List[str]] = None) -> Optional[QDockWidget]:
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

    def _rename_dock(self, dock: QDockWidget, title: str):
        """Rename *dock* to *title*, saving the original title for later restore."""
        key = dock.objectName() or str(id(dock))
        if key not in self.renamed_docks:
            self.renamed_docks[key] = (dock, dock.windowTitle())
        dock.setWindowTitle(title)

    def _restore_dock_titles(self):
        """Restore original dock widget titles."""
        for dock, title in self.renamed_docks.values():
            dock.setWindowTitle(title)
        self.renamed_docks = {}

    def _save_original_window_state_once(self):
        """Save the current main-window state and geometry (idempotent)."""
        has_saved_state = self.settings.value(self._key("hasSavedState"), False, type=bool)
        if has_saved_state:
            return

        self.settings.setValue(self._key("windowState"), self.window.saveState())
        self.settings.setValue(self._key("windowGeometry"), self.window.saveGeometry())
        self.settings.setValue(self._key("hasSavedState"), True)

    def _hide_default_toolbars(self):
        """Hide well-known QGIS default toolbars.

        Only toolbars whose object names are in the known QGIS-default set
        are hidden — plugin and third-party toolbars are left untouched.
        """
        for toolbar in self.window.findChildren(QToolBar):
            name = toolbar.objectName()
            if name.startswith(OBJECT_PREFIX):
                continue
            if name in _QGIS_DEFAULT_TOOLBAR_NAMES:
                toolbar.setVisible(False)

    def _new_toolbar(self, title: str, suffix: str, icon_size: QSize) -> QToolBar:
        """Create and register a new, non-movable toolbar."""
        toolbar = QToolBar(title, self.window)
        toolbar.setObjectName(f"{OBJECT_PREFIX}{suffix}")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(icon_size)
        toolbar.setToolButtonStyle(TOOL_BUTTON_TEXT_UNDER_ICON)
        self.window.addToolBar(TOP_TOOLBAR_AREA, toolbar)
        self.created_toolbars.append(toolbar)
        return toolbar

    def _remove_workspace_toolbars(self):
        """Remove and schedule deletion of all toolbars created by this plugin."""
        for toolbar in self.created_toolbars:
            self.window.removeToolBar(toolbar)
            toolbar.deleteLater()
        self.created_toolbars = []

        for toolbar in self.window.findChildren(QToolBar):
            if toolbar.objectName().startswith(OBJECT_PREFIX):
                self.window.removeToolBar(toolbar)
                toolbar.deleteLater()

    def _make_menu_button(self, label: str, icon_action_name: str, action_specs: list) -> QToolButton:
        """Build a drop-down menu button labelled *label* whose menu is populated
        from the native QGIS actions listed in *action_specs*."""
        button = QToolButton(self.window)
        button.setText(label)
        button.setPopupMode(INSTANT_POPUP)
        button.setToolButtonStyle(TOOL_BUTTON_TEXT_BESIDE_ICON)
        button.setIcon(self._icon_for_action(icon_action_name))

        menu = QMenu(button)
        for spec in action_specs:
            if spec == "-":
                menu.addSeparator()
                continue

            action_name, fallback_text = spec
            action = self._native_action(action_name)
            if action is not None:
                menu.addAction(action)
            else:
                unavailable = QAction(f"{fallback_text} (unavailable)", menu)
                unavailable.setEnabled(False)
                menu.addAction(unavailable)

        button.setMenu(menu)
        return button

    def _add_restore_button(self, toolbar: QToolBar):
        """Append a separator and a Restore button to *toolbar*."""
        toolbar.addSeparator()
        button = QToolButton(self.window)
        button.setText("Restore")
        button.setToolButtonStyle(TOOL_BUTTON_TEXT_BESIDE_ICON)
        button.setIcon(self._standard_icon("SP_BrowserReload"))
        button.clicked.connect(self.restore_layout)
        toolbar.addWidget(button)

    def _make_plugin_action(self, text: str, callback: Callable, standard_icon_name: str) -> QAction:
        """Create a QAction wired to *callback* for use in the plugin menu."""
        action = QAction(
            self._standard_icon(standard_icon_name),
            text,
            self.window,
        )
        action.triggered.connect(callback)
        return action

    def _native_action(self, name: str) -> Optional[QAction]:
        """Return a QGIS native action by its iface attribute name.

        Returns ``None`` when the action does not exist or cannot be
        instantiated (e.g. the corresponding provider is not loaded).
        """
        action_factory = getattr(self.iface, name, None)
        if action_factory is None:
            logger.debug("iface.%s not found", name)
            return None

        try:
            action = action_factory()
        except Exception:
            logger.debug("iface.%s() raised an exception", name, exc_info=True)
            return None

        if isinstance(action, QAction):
            return action

        logger.debug("iface.%s() returned %r, not a QAction", name, type(action))
        return None

    def _icon_for_action(self, name: str):
        """Return the icon of a native action, or a fallback standard icon."""
        action = self._native_action(name)
        if action is not None and not action.icon().isNull():
            return action.icon()
        return self._standard_icon("SP_FileDialogDetailedView")

    def _standard_icon(self, name: str):
        """Look up standard pixmaps in both Qt 5 and Qt 6 bindings."""
        standard_pixmaps = getattr(QStyle, "StandardPixmap", None)
        standard_pixmap = getattr(standard_pixmaps, name, None)
        if standard_pixmap is None:
            standard_pixmap = getattr(QStyle, name, None)
        if standard_pixmap is None:
            fallback_name = "SP_FileIcon"
            standard_pixmap = getattr(standard_pixmaps, fallback_name, None)
            if standard_pixmap is None:
                standard_pixmap = getattr(QStyle, fallback_name)
        return QApplication.style().standardIcon(standard_pixmap)

    def _apply_stylesheet(self):
        """Append the ArcGIS-like Qt stylesheet to the main window."""
        if self.previous_stylesheet is None:
            self.previous_stylesheet = self.window.styleSheet()

        current = self.window.styleSheet()
        if STYLE_MARKER not in current:
            self.window.setStyleSheet(f"{current}\n{ARC_STYLE}")

    def _restore_stylesheet(self):
        """Remove the workspace stylesheet, restoring the previously saved one."""
        if self.previous_stylesheet is not None:
            self.window.setStyleSheet(self.previous_stylesheet)
            self.previous_stylesheet = None
            return

        current: str = self.window.styleSheet()
        marker_index: int = current.find(STYLE_MARKER)
        if marker_index < 0:
            return  # stylesheet was already removed or never applied
        self.window.setStyleSheet(current[:marker_index].rstrip())

    def _notify(self, message: str, level=QGIS_INFO):
        """Show a message-bar notification; fall back to a dialog on error."""
        try:
            self.iface.messageBar().pushMessage(
                "ArcGIS-like Workspace",
                message,
                level=level,
                duration=4,
            )
        except Exception:
            QMessageBox.information(self.window, "ArcGIS-like Workspace", message)

    def _key(self, name):
        return f"{SETTINGS_PREFIX}/{name}"
