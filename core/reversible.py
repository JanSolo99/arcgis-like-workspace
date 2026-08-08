"""Shared reversibility helpers used by every feature module in this plugin.

Every feature added here (native-setting toggles, the layer-tree menu
wrapper, the notifications dock, the locator filter, the shortcut remap)
must satisfy this checklist:

1. Original state captured once, before first mutation; re-apply is a no-op.
2. Apply-apply (no restore in between) produces the same end state as one
   apply -- no duplicate docks/menu entries/registrations.
3. Every persisted QSettings key lives under SETTINGS_PREFIX/ (see
   constants.py) unless deliberately excluded and documented why (the
   shortcut remap is the one deliberate exception -- see shortcuts.py).
4. Every signal.connect() has a paired disconnect() reachable from
   unload(), via ConnectionTracker below -- don't rely on Qt/PyQt's
   deferred deleteLater() auto-disconnect for signals owned by long-lived
   QGIS singletons (iface.currentLayerChanged, QgsApplication.taskManager(),
   QgsMessageLog) that outlive plugin-created widgets.
5. Every created widget/dock/action is tracked and explicitly removed.
6. Every QGIS extension-point registration (locator filter, menu provider,
   shortcut entries) has a matching deregistration, guarded against
   double-registration.
7. unload() must work cleanly whether or not apply() ever ran, and if
   called twice.
"""

import logging
from typing import Callable, List, NamedTuple

logger = logging.getLogger(__name__)


class _Connection(NamedTuple):
    signal: object
    slot: Callable


class ConnectionTracker:
    """Tracks Qt signal/slot connections so they can all be torn down at once."""

    def __init__(self):
        self._connections: List[_Connection] = []

    def connect(self, signal, slot: Callable):
        signal.connect(slot)
        self._connections.append(_Connection(signal, slot))

    def disconnect_all(self):
        for connection in self._connections:
            try:
                connection.signal.disconnect(connection.slot)
            except (TypeError, RuntimeError):
                # Already disconnected, or the underlying C++ object is
                # already gone -- safe to ignore either way.
                pass
        self._connections = []


class _Feature(NamedTuple):
    name: str
    apply_fn: Callable[[], None]
    restore_fn: Callable[[], None]


class FeatureRegistry:
    """Applies/restores a set of independent features, isolating failures.

    One feature's exception during apply_all()/restore_all() is logged and
    skipped rather than aborting the whole workspace toggle -- a locator
    registration failure can't prevent toolbars/docks/style from applying,
    and a notifications-dock teardown failure can't block the rest of
    Restore from running.
    """

    def __init__(self):
        self._features: List[_Feature] = []
        self._applied: List[str] = []

    def register(self, name: str, apply_fn: Callable[[], None], restore_fn: Callable[[], None]):
        self._features.append(_Feature(name, apply_fn, restore_fn))

    def apply_all(self):
        for feature in self._features:
            # Marked applied BEFORE calling apply_fn, not after: if apply_fn
            # raises partway through (e.g. after creating a dock but before
            # finishing signal wiring), restore_fn must still run during
            # restore_all() to clean up whatever partial state exists.
            # Every restore_fn must therefore be safe to call against
            # no-op/partial state (checking `if self.dock is not None`, etc).
            self._applied.append(feature.name)
            try:
                feature.apply_fn()
            except Exception:
                logger.exception("ArcGIS-like Workspace: '%s' failed to apply", feature.name)

    def restore_all(self):
        for feature in reversed(self._features):
            if feature.name not in self._applied:
                continue
            try:
                feature.restore_fn()
            except Exception:
                logger.exception("ArcGIS-like Workspace: '%s' failed to restore", feature.name)
        self._applied = []
