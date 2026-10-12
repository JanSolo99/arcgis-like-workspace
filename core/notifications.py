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
from .toolbars import theme_icon

logger = logging.getLogger(__name__)

_RELEVANT_LOG_LEVELS = (QGIS_WARNING, QGIS_CRITICAL)
_MAX_ENTRIES = 200
_BASE_LABEL = "Notifications"
#: QGIS's own Log Messages icon -- the closest native match to Pro's bell.
_ICON_NAME = "/mMessageLog.svg"
_BADGE_ICON_SIZE = 32


def _badge_icon(base_icon, count: int):
    """Return *base_icon* with a red unread-count badge painted on its
    top-right corner, or None if painting isn't possible (e.g. no GUI)."""
    try:
        from qgis.PyQt.QtCore import QRectF, Qt
        from qgis.PyQt.QtGui import QColor, QIcon, QPainter

        pixmap = base_icon.pixmap(_BADGE_ICON_SIZE, _BADGE_ICON_SIZE)
        painter = QPainter(pixmap)
        try:
            hints = getattr(QPainter, "RenderHint", QPainter)
            painter.setRenderHint(hints.Antialiasing)
            text = "99+" if count > 99 else str(count)
            diameter = _BADGE_ICON_SIZE * 0.6
            width = max(diameter, diameter * 0.45 * len(text))
            rect = QRectF(_BADGE_ICON_SIZE - width, 0, width, diameter)
            painter.setPen(getattr(getattr(Qt, "PenStyle", Qt), "NoPen"))
            painter.setBrush(QColor("#d83b01"))
            painter.drawRoundedRect(rect, diameter / 2, diameter / 2)
            font = painter.font()
            font.setBold(True)
            font.setPixelSize(round(diameter * 0.7))
            painter.setFont(font)
            painter.setPen(QColor("#ffffff"))
            align = getattr(getattr(Qt, "AlignmentFlag", Qt), "AlignCenter")
            painter.drawText(rect, align, text)
        finally:
            painter.end()
        return QIcon(pixmap)
    except Exception:
        logger.debug("ArcGIS-like Workspace: could not paint the notifications badge", exc_info=True)
        return None


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
        self._base_icon = None

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
            self._base_icon = theme_icon(_ICON_NAME, "SP_MessageBoxInformation")
            self.toggle_action.setIcon(self._base_icon)
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
        self._base_icon = None

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
        # Deliberately NOT routed through self._connections (ConnectionTracker):
        # that tracker exists for the two singleton connections above, whose
        # emitters (QgsMessageLog, QgsTaskManager) outlive this dock and so
        # need an explicit disconnect in restore(). A per-task connection is
        # the opposite case -- the task is short-lived and its signals die
        # with it, so tracking it there would only ever grow the list, never
        # shrink it, across a long session running many tasks. Connecting
        # directly lets Qt drop the connection itself once the QgsTask C++
        # object is destroyed, no bookkeeping required.
        #
        # The description is captured as a plain string *now*, not read off
        # `task` inside the callback, so the lambda closes over `desc`
        # instead of `task` -- nothing here keeps the QgsTask wrapper alive
        # after the task finishes and QgsTaskManager releases it.
        desc = self._task_description(task)
        self._add_entry(f"Task started: {desc}")
        task.taskCompleted.connect(lambda: self._add_entry(f"Task completed: {desc}"))
        task.taskTerminated.connect(lambda: self._add_entry(f"Task failed: {desc}"))

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
        """Paint the unread count onto the icon, like Pro's bell. If painting
        isn't possible, fall back to a "Notifications (N)" text badge."""
        if self.toggle_action is None:
            return
        tooltip = f"{self._unread} unread notification(s)" if self._unread else _BASE_LABEL
        self.toggle_action.setToolTip(tooltip)
        if not self._unread:
            self.toggle_action.setText(_BASE_LABEL)
            if self._base_icon is not None:
                self.toggle_action.setIcon(self._base_icon)
            return
        icon = _badge_icon(self._base_icon, self._unread) if self._base_icon is not None else None
        if icon is not None:
            self.toggle_action.setIcon(icon)
            self.toggle_action.setText(_BASE_LABEL)
        else:
            self.toggle_action.setText(f"{_BASE_LABEL} ({self._unread})")
