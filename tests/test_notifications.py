"""Tests for core/notifications.py's _on_task_added handler.

The bug this guards against (see notifications.py's own comment on
_on_task_added): QgsTaskManager.taskAdded emits the task's integer id, not
the QgsTask object -- confirmed against
https://qgis.org/pyqgis/master/core/QgsTaskManager.html:
`taskAdded(taskId: int)` / `task(id: int) -> QgsTask | None`. An earlier
version connected straight to the emitted value as if it were a QgsTask
and crashed the first time a real task ran
(`AttributeError: 'int' object has no attribute 'taskCompleted'`).
tests/fake_qgis's _FakeTaskManager.taskAdded emits a plain int, exactly
like the real one, so calling _on_task_added with that int is the
regression test.
"""

import gc
import weakref
from types import SimpleNamespace

from arcgis_like_workspace.core.notifications import NotificationsDock
from qgis.core import QgsApplication
from qgis.PyQt.QtWidgets import QDockWidget, QListWidget

from tests.helpers import FakeMainWindow, FakeTask


def _make_dock() -> NotificationsDock:
    """A NotificationsDock with its dock/list widgets set up directly,
    bypassing apply()'s toolbar/signal wiring -- _on_task_added() doesn't
    need any of that."""
    window = FakeMainWindow()
    toolbars = SimpleNamespace(tab_toolbar=None)
    dock = NotificationsDock(window, toolbars)
    dock.dock = QDockWidget("Notifications")
    dock.list_widget = QListWidget(dock.dock)
    dock.toggle_action = dock.dock.toggleViewAction()
    return dock


def test_on_task_added_looks_up_the_task_by_id_and_logs_its_lifecycle():
    dock = _make_dock()
    task = FakeTask("Load raster layer")
    task_id = QgsApplication.taskManager().add_task(task)

    dock._on_task_added(task_id)  # must not raise -- old code: AttributeError

    assert dock.list_widget.count() == 1
    assert dock.list_widget.item(0) == "Task started: Load raster layer"

    task.taskCompleted.emit()
    assert dock.list_widget.item(1) == "Task completed: Load raster layer"

    task.taskTerminated.emit()
    assert dock.list_widget.item(2) == "Task failed: Load raster layer"


def test_on_task_added_with_unknown_id_does_nothing():
    """task(id) -> None (per the documented contract) must be handled,
    not treated as a valid task."""
    dock = _make_dock()

    dock._on_task_added(999)

    assert dock.list_widget.count() == 0


def test_completion_lambdas_close_over_the_description_not_the_task():
    """The description is captured as a plain string *before* the lambdas
    are created, specifically so nothing keeps the QgsTask wrapper alive
    after QgsTaskManager releases it (see notifications.py's comment on
    _on_task_added). Inspecting the connected lambdas' closures directly
    verifies that: the task object itself must not appear in either
    closure."""
    dock = _make_dock()
    task = FakeTask("Reproject layer")
    task_id = QgsApplication.taskManager().add_task(task)

    dock._on_task_added(task_id)

    completed_slot = task.taskCompleted.slots[0]
    terminated_slot = task.taskTerminated.slots[0]

    for slot in (completed_slot, terminated_slot):
        closure_values = [cell.cell_contents for cell in (slot.__closure__ or ())]
        assert task not in closure_values
        assert "Reproject layer" in closure_values


def test_task_is_garbage_collectible_after_the_manager_forgets_it():
    """Belt-and-suspenders companion to the closure-inspection test above:
    once nothing else (test var, fake manager registry) holds a strong
    reference to the task, it must actually be collectible -- proving
    dock._on_task_added() didn't stash the task anywhere else either.
    """
    dock = _make_dock()
    task = FakeTask("Buffer analysis")
    task_id = QgsApplication.taskManager().add_task(task)
    dock._on_task_added(task_id)

    task_ref = weakref.ref(task)
    QgsApplication.taskManager().forget(task_id)
    del task
    gc.collect()

    assert task_ref() is None


def test_task_description_falls_back_to_a_generic_label_when_description_raises():
    class BrokenTask:
        def description(self):
            raise RuntimeError("boom")

    assert NotificationsDock._task_description(BrokenTask()) == "task"
