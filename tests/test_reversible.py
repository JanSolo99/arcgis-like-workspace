"""Tests for core/reversible.py -- FeatureRegistry and ConnectionTracker.

The bug this guards against: an earlier version of FeatureRegistry tracked
an `_applied` list and skipped restore_fn for anything not in it. That
looks like a safety check but breaks crash recovery -- a fresh plugin
instance (new process, new FeatureRegistry) has an empty `_applied` list no
matter what QSettings says actually got applied last session. See
core/reversible.py's FeatureRegistry docstring for the full reasoning; the
tests below are the regression tests for exactly that scenario.
"""

from arcgis_like_workspace.core.reversible import ConnectionTracker, FeatureRegistry
from qgis.PyQt.QtCore import FakeSignal


def test_restore_all_runs_every_restore_fn_on_a_fresh_registry():
    """Simulates crash recovery: a brand-new FeatureRegistry (as if QGIS
    had just restarted after a crash) whose restore_fn's are called
    without any apply_all() ever having run against *this* registry
    instance -- QSettings may still hold real state from the previous
    session that needs undoing. There must be no "was this applied" gate
    that skips a restore_fn just because this process never saw apply()
    happen.
    """
    registry = FeatureRegistry()
    restored = []
    registry.register("settings_toggles", lambda: None, lambda: restored.append("settings_toggles"))
    registry.register("notifications", lambda: None, lambda: restored.append("notifications"))
    registry.register("locator", lambda: None, lambda: restored.append("locator"))

    # Deliberately no apply_all() call here -- that's the whole point.
    registry.restore_all()

    assert restored == ["locator", "notifications", "settings_toggles"]  # reverse registration order


def test_restore_all_runs_every_restore_fn_even_called_twice():
    """restore_all() must be safe to call repeatedly (e.g. once from the
    explicit Restore action, again from unload()'s safety net)."""
    registry = FeatureRegistry()
    restored = []
    registry.register("a", lambda: None, lambda: restored.append("a"))

    registry.restore_all()
    registry.restore_all()

    assert restored == ["a", "a"]


def test_apply_all_failure_does_not_prevent_that_features_restore():
    """A feature whose apply_fn raises must still get its restore_fn
    called by a later restore_all() -- FeatureRegistry has no applied-gate
    (see module docstring), so a raise during apply can't strand that
    feature un-restorable."""
    registry = FeatureRegistry()
    restore_calls = []

    def bad_apply():
        raise RuntimeError("boom")

    registry.register("bad", bad_apply, lambda: restore_calls.append("bad"))

    registry.apply_all()  # exception is caught and logged, not raised
    registry.restore_all()

    assert restore_calls == ["bad"]


def test_apply_all_isolates_one_features_failure_from_the_rest():
    """One feature's apply_fn raising must not stop the others from
    applying -- a locator registration failure can't prevent
    toolbars/docks/style from applying (see FeatureRegistry docstring)."""
    registry = FeatureRegistry()
    applied = []

    def bad_apply():
        raise RuntimeError("boom")

    registry.register("bad", bad_apply, lambda: None)
    registry.register("good", lambda: applied.append("good"), lambda: None)

    registry.apply_all()

    assert applied == ["good"]


def test_restore_all_isolates_one_features_failure_from_the_rest():
    """Symmetric with apply_all: one feature's restore_fn raising must not
    stop the others from restoring -- a notifications-dock teardown
    failure can't block the rest of Restore from running."""
    registry = FeatureRegistry()
    restored = []

    def bad_restore():
        raise RuntimeError("boom")

    registry.register("first", lambda: None, lambda: restored.append("first"))
    registry.register("second", lambda: None, bad_restore)

    registry.restore_all()  # restored in reverse order: second (raises), then first

    assert restored == ["first"]


def test_apply_all_calls_every_apply_fn_in_registration_order():
    registry = FeatureRegistry()
    applied = []
    registry.register("a", lambda: applied.append("a"), lambda: None)
    registry.register("b", lambda: applied.append("b"), lambda: None)

    registry.apply_all()

    assert applied == ["a", "b"]


# -- ConnectionTracker -------------------------------------------------------


def test_connection_tracker_disconnect_all_disconnects_every_connection():
    tracker = ConnectionTracker()
    signal_a = FakeSignal()
    signal_b = FakeSignal()
    slot_a_calls = []
    slot_b_calls = []

    tracker.connect(signal_a, lambda: slot_a_calls.append(1))
    tracker.connect(signal_b, lambda: slot_b_calls.append(1))

    tracker.disconnect_all()

    signal_a.emit()
    signal_b.emit()

    assert slot_a_calls == []
    assert slot_b_calls == []


def test_connection_tracker_disconnect_all_survives_already_disconnected_signal():
    """Matches the reversibility contract: disconnect_all() must not raise
    if a connection is already gone (TypeError) or its underlying object
    is already destroyed (RuntimeError) -- both are swallowed."""
    tracker = ConnectionTracker()
    signal = FakeSignal()
    tracker.connect(signal, lambda: None)

    # Simulate the connection already having been torn down some other way.
    signal.slots = []

    tracker.disconnect_all()  # must not raise TypeError

    # Safe to call twice in a row too (unload() calling it again, etc.)
    tracker.disconnect_all()


def test_connection_tracker_clears_its_list_after_disconnect_all():
    tracker = ConnectionTracker()
    signal = FakeSignal()
    tracker.connect(signal, lambda: None)

    tracker.disconnect_all()

    assert tracker._connections == []
