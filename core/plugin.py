"""ArcGIS-like Workspace -- a reversible workspace preset for QGIS.

Applies an ArcGIS Pro-inspired layout using native QGIS toolbars, dock
widgets, and Qt stylesheets, then layers on genuine behavioral parity
features (native-setting toggles, a contextual ribbon, a Labeling toggle
added additively to the layer tree's native Contents menu -- see
layertree_menu.py -- a Notifications dock, a unified locator filter, and
an opt-in keyboard-shortcut remap). All changes are reversible via the
Restore action or by disabling the plugin, and an opt-in "Apply at QGIS
Startup" preference can re-apply the workspace automatically on the next
launch instead of every session starting back at plain QGIS.

Also installs a small logging.Handler (see _QgisMessageLogHandler below)
that bridges this package's stdlib logging -- used throughout by every
feature module's defensive `logger.exception(...)`/`logger.warning(...)`
calls -- into QGIS's own Message Log panel. Without it, QGIS never
surfaces stdlib logging output anywhere: every "log and continue" is
invisible in the running application, which is how failures in inert
features have shipped unnoticed before.

Supports QGIS 3.28+ on both Qt 5 and Qt 6.
"""

import logging
from typing import Callable, List, Optional, Tuple

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QSettings, QTimer
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .compat import QGIS_CRITICAL, QGIS_INFO, QGIS_WARNING
from .constants import Keys, MENU_NAME, SETTINGS_PREFIX
from .contextual_ribbon import ContextualRibbon
from .docks import CATALOG_DOCK, CONTENTS_DOCK, DockArranger
from .layertree_menu import LayerTreeLabelingMenu
from .locator_filter import LocatorFeature
from .notifications import NotificationsDock
from .reversible import FeatureRegistry
from .settings_toggles import SettingsToggles
from .shortcuts import ShortcutRemap
from .stylesheet import StylesheetManager
from .toolbars import ToolbarBuilder, standard_icon

logger = logging.getLogger(__name__)

#: QSettings key for the opt-in "Apply at QGIS Startup" preference.
#: Deliberately a standalone key OUTSIDE constants.SETTINGS_PREFIX (and
#: not registered in constants.Keys, which is relative to that prefix --
#: see constants.py). restore_layout() wipes the whole SETTINGS_PREFIX
#: branch wholesale (`self.settings.remove(SETTINGS_PREFIX)`) every time
#: the workspace is restored; if this preference lived under that prefix,
#: enabling "Apply at QGIS Startup" would silently un-set itself the very
#: first time the user clicked Restore, defeating the point of a startup
#: preference. Same reasoning constants.py documents for
#: SHORTCUTS_SETTINGS_PREFIX.
APPLY_AT_STARTUP_SETTINGS_KEY = "arcgis_like_workspace_prefs/applyAtStartup"


class _QgisMessageLogHandler(logging.Handler):
    """Bridges stdlib logging records into QGIS's Message Log panel.

    QGIS does not install any handler on the root logger or on this
    package's logger -- stdlib `logging` and QGIS's own C++-side message
    log are two separate systems that nothing connects by default. This
    handler is the connection: attached to the package logger in
    initGui() (see ArcGISLikeWorkspacePlugin.initGui()) and removed in
    unload(), it forwards WARNING-and-above records to
    QgsApplication.messageLog().logMessage(), verified via
    https://qgis.org/pyqgis/master/core/QgsMessageLog.html --
    `logMessage(message, tag='', level=Qgis.MessageLevel.Warning, ...)`.
    """

    def __init__(self, level=logging.WARNING):
        super().__init__(level=level)
        # Default Formatter() renders bare "%(message)s" -- since many
        # `logger.exception(...)` calls across this package already prefix
        # their own message with "ArcGIS-like Workspace: ...", the tag
        # passed to logMessage() below covers the plugin identity, so this
        # only adds the originating module and level, useful for telling
        # apart which feature module logged an entry once several show up
        # in the same QGIS Message Log tag. Formatter.format() appends any
        # exception traceback (record.exc_info, set by logger.exception())
        # after the format string regardless of its content, so tracebacks
        # still come through in full.
        self.setFormatter(logging.Formatter("%(name)s [%(levelname)s] %(message)s"))

    def emit(self, record: logging.LogRecord):
        # A logging handler must never raise out of emit() -- the stdlib
        # docs are explicit that exceptions here should not propagate.
        # Guarded with the standard self.handleError() escape hatch
        # (a no-op unless logging.raiseExceptions is set and stderr is
        # available) rather than a bare except, so a broken handler still
        # fails the documented, safe way instead of silently swallowing
        # everything including bugs in this handler itself.
        try:
            message = self.format(record)
            level = QGIS_CRITICAL if record.levelno >= logging.ERROR else QGIS_WARNING
            QgsApplication.messageLog().logMessage(message, "ArcGIS-like Workspace", level)
        except Exception:
            self.handleError(record)


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
        self.reset_action: Optional[QAction] = None
        self.about_action: Optional[QAction] = None
        self.apply_shortcuts_action: Optional[QAction] = None
        self.restore_shortcuts_action: Optional[QAction] = None
        self.apply_at_startup_action: Optional[QAction] = None
        self.menu_actions: List[QAction] = []

        #: Set only while a one-shot handler is wired to auto-apply the
        #: workspace once QGIS finishes starting up (see
        #: _connect_startup_apply()/_on_initialization_completed()); a
        #: (signal, slot) pair so unload() can disconnect it if it never
        #: fired. None otherwise.
        self._startup_connection: Optional[Tuple[object, Callable]] = None

        #: The stdlib-logging-to-QGIS-message-log bridge (see
        #: _QgisMessageLogHandler above), attached to _plugin_logger in
        #: initGui() and removed in unload(). Both None until initGui()
        #: runs.
        self._log_handler: Optional[_QgisMessageLogHandler] = None
        self._plugin_logger: Optional[logging.Logger] = None

    def initGui(self):
        """Create menu entries and toolbar icon -- called by QGIS on load."""
        self._attach_log_handler()

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
        self.reset_action = self._make_plugin_action(
            "Reset to Default QGIS Workspace",
            self.reset_to_default_workspace,
            "SP_DialogResetButton",
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

        self.apply_at_startup_action = QAction(
            standard_icon("SP_DialogYesButton"),
            "Apply at QGIS Startup",
            self.window,
        )
        self.apply_at_startup_action.setCheckable(True)
        self.apply_at_startup_action.setChecked(
            self.settings.value(APPLY_AT_STARTUP_SETTINGS_KEY, False, type=bool)
        )
        self.apply_at_startup_action.toggled.connect(self._set_apply_at_startup)

        self.menu_actions = [
            self.apply_action,
            self.restore_action,
            self.reset_action,
            self.about_action,
            self.apply_shortcuts_action,
            self.restore_shortcuts_action,
            self.apply_at_startup_action,
        ]

        for action in self.menu_actions:
            self.iface.addPluginToMenu(MENU_NAME, action)

        self.iface.addToolBarIcon(self.apply_action)

        if self.apply_at_startup_action.isChecked():
            self._connect_startup_apply()

    def unload(self):
        """Remove menu entries, toolbar icon, and restore workspace -- called by QGIS on unload."""
        for action in self.menu_actions:
            self.iface.removePluginMenu(MENU_NAME, action)

        if self.apply_action is not None:
            self.iface.removeToolBarIcon(self.apply_action)

        # The menu/toolbar calls above only detach these QActions from
        # their menus/toolbars -- they stay alive, parented to the main
        # window (long-lived), with a live `triggered`/`toggled`
        # connection back into this plugin instance's bound methods. Left
        # that way, each one pins the whole dead plugin instance in memory
        # across a Plugin Reloader cycle (the same hazard locator_filter.py
        # documents for its find_action). deleteLater() breaks that.
        for action in self.menu_actions:
            if action is not None:
                action.deleteLater()
        self.menu_actions = []

        if self._startup_connection is not None:
            signal, slot = self._startup_connection
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                # Already disconnected (it fired and self-disconnected --
                # see _on_initialization_completed()), or the underlying
                # C++ object is already gone -- safe to ignore either way.
                pass
            self._startup_connection = None

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

        self._detach_log_handler()

    def apply_layout(self):
        """Apply the ArcGIS-like workspace: save current state, create ribbon + tab toolbars,
        rearrange dock widgets, and apply the ArcGIS-inspired stylesheet."""
        self._save_original_window_state_once()
        self.toolbars.remove_workspace_toolbars(keep_anchor=True)
        self.toolbars.hide_default_toolbars()
        self.toolbars.create_tab_toolbar(self.restore_layout, self.reset_to_default_workspace)
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

    def reset_to_default_workspace(self):
        """A stronger reset than Restore.

        Restore only returns QGIS to whatever *your* layout looked like
        right before you clicked Apply -- if that layout already had
        toolbars hidden or panels tucked away for your own reasons,
        Restore faithfully brings that back too. This action goes
        further: after undoing everything this plugin's Apply did, it
        also resets every known QGIS toolbar to its TRUE stock-install
        visibility (most of them are hidden by default -- forcing all of
        them on would be toolbar soup, not a default reset) and ensures
        the core Contents/Catalog panels are visible, regardless of what
        your prior layout had.

        QGIS's exact default panel *positions* are hardcoded in its own
        C++ startup code and aren't exposed to plugins to replay on
        demand, so this covers visibility, not pixel-perfect positioning
        -- a full factory-default layout still requires restarting QGIS.
        """
        self.restore_layout()
        self.toolbars.show_default_toolbars()

        contents = self.docks.find_named_dock(CONTENTS_DOCK)
        if contents is not None:
            contents.setVisible(True)

        catalog = self.docks.find_named_dock(CATALOG_DOCK)
        if catalog is not None:
            catalog.setVisible(True)

        self._notify(
            "Reset toolbar visibility and core panels to QGIS defaults. Restart QGIS "
            "for a full reset of default panel positions."
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
                "It is a reversible layer on top of native QGIS behavior -- "
                "Restore returns to your prior layout, or Reset to Default QGIS "
                "Workspace goes further and forces QGIS's own default toolbars/"
                "panels visible. It does not copy Esri icons, branding, or "
                "proprietary ArcGIS UI code, and it does not change QGIS's "
                "underlying project model.\n\n"
                "Check \"Apply at QGIS Startup\" in this menu to have the "
                "workspace re-applied automatically the next time QGIS launches, "
                "instead of applying it by hand every session."
            ),
        )

    def _connect_startup_apply(self):
        """Wire a one-shot handler that applies the workspace once QGIS
        finishes its own startup sequence.

        Only ever called from initGui() when "Apply at QGIS Startup" is
        already checked (persisted from a previous session). If initGui()
        instead runs mid-session -- the user enabling this plugin by hand
        via the Plugin Manager well after QGIS's own startup already
        completed -- iface.initializationCompleted already fired earlier
        in this process and connecting to it now is a safe no-op: Qt
        signals never replay a past emission to a newly-connected slot, so
        the handler below simply never runs and the workspace is not
        auto-applied. That is exactly the desired behavior (the user can
        still click Apply by hand) and needs no extra mid-session
        detection code -- it falls out of ordinary Qt signal semantics.
        """
        signal = getattr(self.iface, "initializationCompleted", None)
        if signal is not None:
            try:
                signal.connect(self._on_initialization_completed)
            except Exception:
                logger.exception(
                    "ArcGIS-like Workspace: could not connect to iface.initializationCompleted"
                )
            else:
                self._startup_connection = (signal, self._on_initialization_completed)
                return

        # Fallback for a hypothetical QGIS build lacking
        # initializationCompleted -- verified present on QgisInterface
        # since at least the release-3_28 branch (this plugin's floor;
        # python/gui/auto_generated/qgisinterface.sip.in on
        # https://github.com/qgis/QGIS), so in practice this branch should
        # be unreachable and exists only per the compat-helper pattern
        # (compat.py) for forward safety. Unlike the signal path above, a
        # bare QTimer.singleShot cannot tell "QGIS is still starting up"
        # apart from "the plugin was just enabled mid-session", and its
        # static form gives no handle to cancel from unload() -- accepted
        # here as a best-effort fallback only, not an equivalent guarantee.
        QTimer.singleShot(0, self.apply_layout)

    def _on_initialization_completed(self):
        """One-shot handler for iface.initializationCompleted -- see
        _connect_startup_apply()."""
        if self._startup_connection is not None:
            signal, slot = self._startup_connection
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
            self._startup_connection = None
        self.apply_layout()

    def _set_apply_at_startup(self, checked: bool):
        """Persist the "Apply at QGIS Startup" preference (toggled handler).

        Deliberately does not connect/disconnect _connect_startup_apply()
        here -- the signal is only ever wired once, from initGui(), for
        the reasons documented there. Toggling this action mid-session
        only affects what happens on the *next* QGIS launch.
        """
        self.settings.setValue(APPLY_AT_STARTUP_SETTINGS_KEY, bool(checked))

    def _attach_log_handler(self):
        """Bridge this package's stdlib logging into QGIS's Message Log --
        see _QgisMessageLogHandler and the module docstring."""
        if self._log_handler is not None:
            return
        try:
            # __name__ here is "<install_dir_name>.core.plugin" -- the
            # package containing this core/ subpackage is the first
            # dot-segment. Attaching to that package logger (rather than
            # just this module's own logger) means every feature module's
            # `logging.getLogger(__name__)` -- all children of it -- routes
            # here too, since child loggers propagate to ancestor handlers
            # by default.
            package_name = __name__.rsplit(".", 2)[0]
            self._plugin_logger = logging.getLogger(package_name)
            # A previous plugin instance that never unloaded cleanly (crash,
            # or a reload path that skipped unload()) may have left its own
            # bridge handler on this shared package logger -- remove any
            # stale ones first, or every log line would surface twice in
            # QGIS's Message Log.
            # Matched by class NAME, not isinstance: after a plugin reload
            # this module is re-imported, so a stale handler is an instance
            # of the previous import's class object, which isinstance
            # against the current class would miss.
            for handler in list(self._plugin_logger.handlers):
                if type(handler).__name__ == "_QgisMessageLogHandler":
                    self._plugin_logger.removeHandler(handler)
            self._log_handler = _QgisMessageLogHandler(logging.WARNING)
            self._plugin_logger.addHandler(self._log_handler)
        except Exception:
            # Must never block initGui() -- worst case, logging just stays
            # invisible in QGIS the way it always has.
            logger.exception("ArcGIS-like Workspace: could not attach the QGIS message-log bridge")
            self._log_handler = None
            self._plugin_logger = None

    def _detach_log_handler(self):
        if self._log_handler is not None and self._plugin_logger is not None:
            try:
                self._plugin_logger.removeHandler(self._log_handler)
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not detach the QGIS message-log bridge")
        self._log_handler = None
        self._plugin_logger = None

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
