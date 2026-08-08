"""ArcGIS-like Workspace -- a reversible workspace preset for QGIS.

Applies an ArcGIS Pro-inspired layout using native QGIS toolbars, dock
widgets, and Qt stylesheets, then layers on genuine behavioral parity
features (native-setting toggles, a contextual ribbon, a Labeling toggle, a
Notifications dock, a unified locator filter, and an opt-in keyboard-shortcut
remap). All changes are reversible via the Restore action or by disabling
the plugin.

Supports QGIS 3.28+ on both Qt 5 and Qt 6.
"""

from typing import Callable, List, Optional

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .compat import QGIS_INFO, QGIS_WARNING
from .constants import Keys, MENU_NAME, SETTINGS_PREFIX
from .contextual_ribbon import ContextualRibbon
from .docks import DockArranger
from .layertree_menu import LayerTreeLabelingMenu
from .locator_filter import LocatorFeature
from .notifications import NotificationsDock
from .reversible import FeatureRegistry
from .settings_toggles import SettingsToggles
from .shortcuts import ShortcutRemap
from .stylesheet import StylesheetManager
from .toolbars import ToolbarBuilder, standard_icon


class ArcGISLikeWorkspacePlugin:
    """A reversible ArcGIS Pro-inspired workspace preset for QGIS.

    Orchestrates the layout layer (tab/ribbon toolbars, dock rearrangement,
    stylesheet -- toolbars.py/docks.py/stylesheet.py) and the behavioral
    parity features registered with self.features (settings_toggles.py,
    layertree_menu.py, contextual_ribbon.py, notifications.py,
    locator_filter.py), plus the separately-lifecycled opt-in shortcut
    remap (shortcuts.py). See core/reversible.py for the reversibility
    contract every feature module follows.
    """

    def __init__(self, iface):
        self.iface = iface
        self.window = iface.mainWindow()
        self.settings: QSettings = QSettings()

        self.toolbars = ToolbarBuilder(iface, self.window)
        self.docks = DockArranger(self.window)
        self.stylesheet = StylesheetManager(self.window)

        #: Feature modules (settings toggles, layer-tree menu, notifications,
        #: locator filter) register their apply/restore pair here. Registered
        #: once in __init__; the shortcut remap deliberately is NOT
        #: registered here -- it has its own separate apply/restore actions
        #: and settings namespace, since it must survive an ordinary
        #: workspace restore (see constants.SHORTCUTS_SETTINGS_PREFIX).
        self.features = FeatureRegistry()

        self.settings_toggles = SettingsToggles(self.settings, self._key)
        self.features.register(
            "settings_toggles", self.settings_toggles.apply, self.settings_toggles.restore
        )

        self.layertree_menu = LayerTreeLabelingMenu(iface)
        self.features.register(
            "layertree_menu", self.layertree_menu.apply, self.layertree_menu.restore
        )

        self.contextual_ribbon = ContextualRibbon(iface, self.toolbars)
        self.features.register(
            "contextual_ribbon", self.contextual_ribbon.apply, self.contextual_ribbon.restore
        )

        self.notifications = NotificationsDock(self.window, self.toolbars)
        self.features.register(
            "notifications", self.notifications.apply, self.notifications.restore
        )

        self.locator = LocatorFeature(iface, self.toolbars)
        self.features.register("locator", self.locator.apply, self.locator.restore)

        #: Deliberately separate from self.features -- see module docstring
        #: and shortcuts.ShortcutRemap.
        self.shortcut_remap = ShortcutRemap(iface, self.settings)

        self.apply_action: Optional[QAction] = None
        self.restore_action: Optional[QAction] = None
        self.about_action: Optional[QAction] = None
        self.apply_shortcuts_action: Optional[QAction] = None
        self.restore_shortcuts_action: Optional[QAction] = None
        self.menu_actions: List[QAction] = []

    def initGui(self):
        """Create menu entries and toolbar icon -- called by QGIS on load."""
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
        self.apply_shortcuts_action = self._make_plugin_action(
            "Apply ArcGIS-like Shortcuts (opt-in)",
            self.apply_shortcuts,
            "SP_FileDialogListView",
        )
        self.restore_shortcuts_action = self._make_plugin_action(
            "Restore Original Shortcuts",
            self.restore_shortcuts,
            "SP_BrowserReload",
        )

        self.menu_actions = [
            self.apply_action,
            self.restore_action,
            self.about_action,
            self.apply_shortcuts_action,
            self.restore_shortcuts_action,
        ]

        for action in self.menu_actions:
            self.iface.addPluginToMenu(MENU_NAME, action)

        self.iface.addToolBarIcon(self.apply_action)

    def unload(self):
        """Remove menu entries, toolbar icon, and restore workspace -- called by QGIS on unload."""
        for action in self.menu_actions:
            self.iface.removePluginMenu(MENU_NAME, action)

        if self.apply_action is not None:
            self.iface.removeToolBarIcon(self.apply_action)

        has_saved_state = self.settings.value(self._key(Keys.HAS_SAVED_STATE), False, type=bool)
        if has_saved_state:
            self.restore_layout()
        else:
            self.toolbars.remove_workspace_toolbars()
            self.docks.restore_titles()
            self.stylesheet.restore()

        # Safety net: the shortcut remap has its own explicit Restore action
        # (see shortcuts.ShortcutRemap), but disabling the plugin should
        # still be able to undo it automatically, same as the main
        # workspace above -- otherwise a remap applied in a session where
        # the user forgets to click Restore before disabling the plugin
        # would stick indefinitely.
        if self.shortcut_remap.has_saved_state():
            self.shortcut_remap.restore()

    def apply_layout(self):
        """Apply the ArcGIS-like workspace: save current state, create ribbon + tab toolbars,
        rearrange dock widgets, and apply the ArcGIS-inspired stylesheet."""
        self._save_original_window_state_once()
        self.toolbars.remove_workspace_toolbars()
        self.toolbars.hide_default_toolbars()
        self.toolbars.create_tab_toolbar(self.restore_layout)
        self.toolbars.create_ribbon_toolbar()
        self.docks.arrange()
        self.stylesheet.apply()
        self.features.apply_all()
        self._notify("Applied the ArcGIS-like workspace preset.")

    def restore_layout(self):
        """Remove workspace toolbars, restore dock titles, remove the stylesheet,
        and restore the original main-window geometry and state."""
        self.features.restore_all()
        self.toolbars.remove_workspace_toolbars()
        self.docks.restore_titles()
        self.stylesheet.restore()

        restored = False
        state = self.settings.value(self._key(Keys.WINDOW_STATE))
        geometry = self.settings.value(self._key(Keys.WINDOW_GEOMETRY))

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

    def apply_shortcuts(self):
        """Apply the opt-in, curated ArcGIS-like keyboard shortcut remap.

        Independent of apply_layout() -- see shortcuts.ShortcutRemap for why."""
        count = self.shortcut_remap.apply()
        if count:
            self._notify(f"Applied {count} ArcGIS-like keyboard shortcut(s).")
        else:
            self._notify(
                "No shortcuts were changed (already applied, already customized, or in use elsewhere).",
                QGIS_WARNING,
            )

    def restore_shortcuts(self):
        """Restore the original keyboard shortcuts changed by apply_shortcuts()."""
        count = self.shortcut_remap.restore()
        if count:
            self._notify(f"Restored {count} original keyboard shortcut(s).")
        else:
            self._notify("No ArcGIS-like shortcuts were applied.", QGIS_WARNING)

    def show_about(self):
        """Display an informational About dialog."""
        QMessageBox.information(
            self.window,
            "ArcGIS-like Workspace",
            (
                "This plugin applies an ArcGIS Pro-inspired workspace preset "
                "using native QGIS actions, toolbars, docks, settings, and Qt "
                "styling: layout and stylesheet, plus behavioral touches like a "
                "contextual ribbon, a Labeling toggle, a Notifications dock, a "
                "unified locator, and an opt-in keyboard shortcut remap.\n\n"
                "It is a reversible layer on top of native QGIS behavior. It "
                "does not copy Esri icons, branding, or proprietary ArcGIS UI "
                "code, and it does not change QGIS's underlying project model."
            ),
        )

    def _save_original_window_state_once(self):
        """Save the current main-window state and geometry (idempotent)."""
        has_saved_state = self.settings.value(self._key(Keys.HAS_SAVED_STATE), False, type=bool)
        if has_saved_state:
            return

        self.settings.setValue(self._key(Keys.WINDOW_STATE), self.window.saveState())
        self.settings.setValue(self._key(Keys.WINDOW_GEOMETRY), self.window.saveGeometry())
        self.settings.setValue(self._key(Keys.HAS_SAVED_STATE), True)

    def _make_plugin_action(self, text: str, callback: Callable, standard_icon_name: str) -> QAction:
        """Create a QAction wired to *callback* for use in the plugin menu."""
        action = QAction(
            standard_icon(standard_icon_name),
            text,
            self.window,
        )
        action.triggered.connect(callback)
        return action

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
