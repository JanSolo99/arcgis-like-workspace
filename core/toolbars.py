"""Tab-style and ribbon-style toolbars built from native QGIS actions."""

import logging
from typing import Callable, List, Optional

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QLabel,
    QMenu,
    QStyle,
    QToolBar,
    QToolButton,
)

from .compat import (
    INSTANT_POPUP,
    TOOL_BUTTON_TEXT_BESIDE_ICON,
    TOOL_BUTTON_TEXT_UNDER_ICON,
    TOP_TOOLBAR_AREA,
)
from .constants import (
    OBJECT_PREFIX,
    QGIS_DEFAULT_TOOLBAR_NAMES,
    QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES,
    QGIS_EDITING_TOOLBAR_NAMES,
)

logger = logging.getLogger(__name__)


def native_action(iface, name: str) -> Optional[QAction]:
    """Return a QGIS native action by its iface attribute name.

    Returns ``None`` when the action does not exist or cannot be
    instantiated (e.g. the corresponding provider is not loaded).
    """
    action_factory = getattr(iface, name, None)
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


def standard_icon(name: str):
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


def icon_for_action(iface, name: str):
    """Return the icon of a native action, or a fallback standard icon."""
    action = native_action(iface, name)
    if action is not None and not action.icon().isNull():
        return action.icon()
    return standard_icon("SP_FileDialogDetailedView")


class ActionGroup:
    """A labelled group of toolbar widgets, retained so callers can later
    show/hide it (e.g. for contextual visibility based on layer type)."""

    def __init__(
        self,
        label: str,
        label_widget: QLabel,
        toolbar: QToolBar,
        actions: List[QAction],
        separator: Optional[QAction] = None,
    ):
        self.label = label
        self.label_widget = label_widget
        self.toolbar = toolbar
        self.actions = actions
        #: This group's own leading separator, or None for the first group
        #: in the toolbar (nothing precedes it to separate from). Unlike the
        #: native action QActions in `actions`, this QAction is created by
        #: and belongs solely to this group -- it is never shared with
        #: another toolbar or menu -- so toggling its widget's visibility
        #: here cannot hide it anywhere else. Tracking it keeps contiguous
        #: hidden groups (e.g. Edit + Selection) from leaving orphaned
        #: separators behind: each group takes its own leading separator
        #: with it, and only the boundary separator of the next *visible*
        #: group remains on screen.
        self.separator = separator

    def set_visible(self, visible: bool):
        # Toggle visibility of this toolbar's *widget* for each action, not
        # the shared QAction itself -- the same native QAction instance
        # (e.g. iface.actionPan()) is also referenced by the tab toolbar's
        # dropdown menus and by QGIS's own (hidden) menus, so calling
        # action.setVisible() here would hide it everywhere it's used.
        self.label_widget.setVisible(visible)
        for action in self.actions:
            widget = self.toolbar.widgetForAction(action)
            if widget is not None:
                widget.setVisible(visible)
        if self.separator is not None:
            separator_widget = self.toolbar.widgetForAction(self.separator)
            if separator_widget is not None:
                separator_widget.setVisible(visible)


class ToolbarBuilder:
    """Builds and tears down the plugin's tab and ribbon toolbars."""

    def __init__(self, iface, window):
        self.iface = iface
        self.window = window
        self.created_toolbars: List[QToolBar] = []
        #: Populated by create_ribbon_toolbar(); label -> ActionGroup.
        self.action_groups: dict = {}
        #: Set by create_tab_toolbar(); lets other feature modules (e.g. the
        #: Notifications dock's bell toggle) attach their own actions to it.
        self.tab_toolbar: Optional[QToolBar] = None

    def hide_default_toolbars(self):
        """Hide well-known QGIS default toolbars.

        Only toolbars whose object names are in the known QGIS-default set
        are hidden -- plugin and third-party toolbars are left untouched.
        """
        for toolbar in self.window.findChildren(QToolBar):
            name = toolbar.objectName()
            if name.startswith(OBJECT_PREFIX):
                continue
            if name in QGIS_DEFAULT_TOOLBAR_NAMES:
                toolbar.setVisible(False)

    def show_default_toolbars(self):
        """Reset every known QGIS toolbar to its TRUE stock-install
        visibility, regardless of its current state: the handful that
        QGIS itself shows by default (QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES)
        are shown, everything else this plugin knows about -- including
        the editing toolbars Apply deliberately leaves alone -- is
        hidden, because that's what a stock QGIS install actually looks
        like. Forcing every KNOWN toolbar visible (the previous
        behavior) is not a default reset, it's toolbar soup: QGIS itself
        keeps most of them hidden out of the box.

        Used by "Reset to Default QGIS Workspace", which is a stronger
        reset than plain Restore -- it doesn't just undo this plugin's
        hiding, it also overrides whatever toolbar visibility you had
        *before* ever using this plugin.
        """
        known = QGIS_DEFAULT_TOOLBAR_NAMES | QGIS_EDITING_TOOLBAR_NAMES
        for toolbar in self.window.findChildren(QToolBar):
            name = toolbar.objectName()
            if name in known:
                toolbar.setVisible(name in QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES)

    def create_tab_toolbar(self, restore_callback: Callable, reset_callback: Callable) -> QToolBar:
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

        self._add_restore_button(toolbar, restore_callback, reset_callback)
        self.tab_toolbar = toolbar
        return toolbar

    def create_ribbon_toolbar(self) -> QToolBar:
        """Build the ribbon-style toolbar with icon+label groups for each functional area."""
        toolbar = self._new_toolbar("Arc Layout: Ribbon", "RibbonToolbar", QSize(26, 26))
        toolbar.setToolButtonStyle(TOOL_BUTTON_TEXT_UNDER_ICON)
        self.action_groups = {}

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
        return toolbar

    def remove_workspace_toolbars(self):
        """Remove and schedule deletion of all toolbars created by this plugin."""
        for toolbar in self.created_toolbars:
            self.window.removeToolBar(toolbar)
            toolbar.deleteLater()
        self.created_toolbars = []
        self.action_groups = {}
        self.tab_toolbar = None

        for toolbar in self.window.findChildren(QToolBar):
            if toolbar.objectName().startswith(OBJECT_PREFIX):
                self.window.removeToolBar(toolbar)
                toolbar.deleteLater()

    def _add_action_group(self, toolbar: QToolBar, label: str, action_names: List[str]):
        """Append a labelled group of native QGIS actions to *toolbar*."""
        actions = [native_action(self.iface, name) for name in action_names]
        actions = [action for action in actions if action is not None]
        if not actions:
            return

        # addSeparator() returns the QAction it just created -- capture it
        # so ActionGroup can hide/show this group's leading separator along
        # with its label and action widgets (see ActionGroup.separator).
        separator = toolbar.addSeparator() if toolbar.actions() else None

        group_label = QLabel(label, self.window)
        group_label.setObjectName(f"{OBJECT_PREFIX}GroupLabel")
        toolbar.addWidget(group_label)

        for action in actions:
            toolbar.addAction(action)

        self.action_groups[label] = ActionGroup(label, group_label, toolbar, actions, separator)

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

    def _make_menu_button(self, label: str, icon_action_name: str, action_specs: list) -> QToolButton:
        """Build a drop-down menu button labelled *label* whose menu is populated
        from the native QGIS actions listed in *action_specs*."""
        button = QToolButton(self.window)
        button.setText(label)
        button.setPopupMode(INSTANT_POPUP)
        button.setToolButtonStyle(TOOL_BUTTON_TEXT_BESIDE_ICON)
        button.setIcon(icon_for_action(self.iface, icon_action_name))

        menu = QMenu(button)
        for spec in action_specs:
            if spec == "-":
                menu.addSeparator()
                continue

            action_name, fallback_text = spec
            action = native_action(self.iface, action_name)
            if action is not None:
                menu.addAction(action)
            else:
                unavailable = QAction(f"{fallback_text} (unavailable)", menu)
                unavailable.setEnabled(False)
                menu.addAction(unavailable)

        button.setMenu(menu)
        return button

    def _add_restore_button(self, toolbar: QToolBar, restore_callback: Callable, reset_callback: Callable):
        """Append a separator, a Restore button, and a Reset-to-Default button to *toolbar*."""
        toolbar.addSeparator()

        restore_button = QToolButton(self.window)
        restore_button.setText("Restore")
        restore_button.setToolButtonStyle(TOOL_BUTTON_TEXT_BESIDE_ICON)
        restore_button.setIcon(standard_icon("SP_BrowserReload"))
        restore_button.clicked.connect(restore_callback)
        toolbar.addWidget(restore_button)

        reset_button = QToolButton(self.window)
        reset_button.setText("Reset to Default")
        reset_button.setToolButtonStyle(TOOL_BUTTON_TEXT_BESIDE_ICON)
        reset_button.setIcon(standard_icon("SP_DialogResetButton"))
        reset_button.setToolTip(
            "Undo this workspace and force QGIS's default toolbars/panels visible -- "
            "a stronger reset than Restore, which only returns to your prior layout."
        )
        reset_button.clicked.connect(reset_callback)
        toolbar.addWidget(reset_button)
