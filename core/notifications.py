"""A lightweight Notifications dock, approximating ArcGIS Pro's bell icon.

Deliberately does not reimplement QGIS's own Log Messages panel or its
status-bar task-progress widget -- both already exist natively (Log
Messages is promoted into the layout by docks.py). This just aggregates
Warning/Critical log messages and task lifecycle events into one compact,
on-demand list, toggled by a bell-style button on the tab toolbar.
"""

import logging

from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QDockWidget, QListWidget

from .compat import BOTTOM_DOCK_WIDGET_AREA, QGIS_CRITICAL, QGIS_WARNING
from .constants import OBJECT_PREFIX
from .reversible import ConnectionTracker
from .toolbars import standard_icon

logger = logging.getLogger(__name__)

_RELEVANT_LOG_LEVELS = (QGIS_WARNING, QGIS_CRITICAL)
_MAX_ENTRIES = 200
_BASE_LABEL = "Notifications"


class NotificationsDock:
    """Creates/tears down the Notifications dock and its bell toggle, reversibly."""

    def __init__(self, window, toolbars):
        self.window = window
        self.toolbars = toolbars
        self.dock = None
        self.list_widget = None
        self.toggle_action = None
        self._connections = ConnectionTracker()
        self._unread = 0

    def apply(self):
        """Dock/signal setup is idempotent (once per apply-restore cycle),
        but re-attaching the bell action to the tab toolbar happens on every
        call -- a re-apply without an intervening restore rebuilds the tab
        toolbar from scratch (see ToolbarBuilder.remove_workspace_toolbars),
        which would otherwise silently drop the bell button even though the
        dock itself is still alive."""
        if self.dock is None:
            self.dock = QDockWidget(_BASE_LABEL, self.window)
            self.dock.setObjectName(f"{OBJECT_PREFIX}NotificationsDock")
            self.list_widget = QListWidget(self.dock)
            self.dock.setWidget(self.list_widget)
            self.window.addDockWidget(BOTTOM_DOCK_WIDGET_AREA, self.dock)
            self.dock.setVisible(False)

            self.toggle_action = self.dock.toggleViewAction()
            self.toggle_action.setText(_BASE_LABEL)
            self.toggle_action.setIcon(standard_icon("SP_MessageBoxInformation"))
            self.toggle_action.toggled.connect(self._on_visibility_toggled)

            # QgsMessageLog.logMessage() and QgsTask's lifecycle signals are
            # documented/used by QGIS's own built-in log panel and task-
            # progress UI as safe to connect GUI-updating slots to directly
            # (QGIS marshals delivery appropriately) -- this mirrors that
            # same usage pattern. Connected only in this one-time-setup
            # branch, not on every apply() call, to avoid double-connecting
            # (and therefore double-logging every event) on a re-apply.
            try:
                self._connections.connect(QgsApplication.messageLog().messageReceived, self._on_log_message)
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not connect to QgsMessageLog")
            try:
                self._connections.connect(QgsApplication.taskManager().taskAdded, self._on_task_added)
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not connect to QgsTaskManager")

        self._attach_toggle_action()

    def _attach_toggle_action(self):
        toolbar = self.toolbars.tab_toolbar
        if self.toggle_action is None or toolbar is None:
            return
        if self.toggle_action not in toolbar.actions():
            toolbar.addAction(self.toggle_action)

    def restore(self):
        """Safe to call even if apply() never ran or only partially completed."""
        self._connections.disconnect_all()

        if self.toggle_action is not None and self.toolbars.tab_toolbar is not None:
            self.toolbars.tab_toolbar.removeAction(self.toggle_action)
        self.toggle_action = None

        if self.dock is not None:
            self.window.removeDockWidget(self.dock)
            self.dock.deleteLater()
        self.dock = None
        self.list_widget = None
        self._unread = 0

    # -- signal handlers ----------------------------------------------------

    def _on_log_message(self, message, tag, level):
        if level not in _RELEVANT_LOG_LEVELS:
            return
        self._add_entry(f"[{tag}] {message}")

    def _on_task_added(self, task_id):
        # QgsTaskManager.taskAdded emits the task's integer id, not the
        # QgsTask object itself -- confirmed the hard way: connecting
        # task_id.taskCompleted directly raised AttributeError('int' object
        # has no attribute 'taskCompleted') the first time a task (e.g.
        # loading a raster) actually ran. Look the real task up by id.
        task = QgsApplication.taskManager().task(task_id)
        if task is None:
            return
        description = self._task_description(task)
        self._add_entry(f"Task started: {description}")
        self._connections.connect(
            task.taskCompleted, lambda t=task: self._add_entry(f"Task completed: {self._task_description(t)}")
        )
        self._connections.connect(
            task.taskTerminated, lambda t=task: self._add_entry(f"Task failed: {self._task_description(t)}")
        )

    @staticmethod
    def _task_description(task) -> str:
        try:
            return task.description()
        except Exception:
            return "task"

    def _on_visibility_toggled(self, visible: bool):
        if visible:
            self._unread = 0
            self._update_badge()

    # -- internals ------------------------------------------------------------

    def _add_entry(self, text: str):
        if self.list_widget is None:
            return
        try:
            self.list_widget.addItem(text)
            while self.list_widget.count() > _MAX_ENTRIES:
                self.list_widget.takeItem(0)
        except RuntimeError:
            return  # underlying widget already deleted

        if self.dock is not None and not self.dock.isVisible():
            self._unread += 1
            self._update_badge()

    def _update_badge(self):
        if self.toggle_action is None:
            return
        if self._unread:
            self.toggle_action.setText(f"{_BASE_LABEL} ({self._unread})")
        else:
            self.toggle_action.setText(_BASE_LABEL)
