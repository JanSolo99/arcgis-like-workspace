"""Opt-in keyboard-shortcut remap toward ArcGIS Pro conventions.

Ships as its OWN pair of menu actions ("Apply ArcGIS-like Shortcuts" /
"Restore Original Shortcuts"), independent of the main workspace
apply_layout()/restore_layout() lifecycle and deliberately NOT registered
with FeatureRegistry: QgsShortcutsManager.setKeySequence() persists
straight to QGIS's own settings storage immediately, unlike every other
feature in this plugin, which is only an in-session Qt/QSettings mutation
undone by the ordinary workspace Restore. If QGIS crashes before this
module's own Restore runs, the remap sticks. Keeping it separate and
explicitly opt-in limits that risk to users who deliberately chose it,
without affecting the main workspace preset's reliability either way.
Originals are persisted under constants.SHORTCUTS_SETTINGS_PREFIX -- a
namespace outside SETTINGS_PREFIX, so an ordinary workspace Restore does
not wipe the record needed to undo a shortcut remap.

The curated list below is intentionally short and conservative -- verify
each entry against ArcGIS Pro's official Keyboard Shortcuts reference
before trusting it, since some are a best-effort match rather than a
confirmed one. The collision guards in apply() make it safe to extend
this list speculatively: a wrong or colliding guess is simply skipped,
never applied, and can't corrupt or overwrite anything.
"""

import logging

from qgis.gui import QgsGui
from qgis.PyQt.QtGui import QKeySequence

from .constants import SHORTCUTS_SETTINGS_PREFIX
from .toolbars import native_action

logger = logging.getLogger(__name__)

#: (iface action name, target Qt key-sequence string, human label).
#: "Delete Selected Features" -> Del is a near-universal GIS/CAD convention
#: and matches ArcGIS Pro. "New Bookmark" -> Ctrl+B is a reasonable but
#: less-verified guess -- review before relying on it.
CURATED_SHORTCUTS = [
    ("actionDeleteSelected", "Del", "Delete Selected Features"),
    ("actionNewBookmark", "Ctrl+B", "New Bookmark"),
]

_ORIGINAL_KEY_PREFIX = f"{SHORTCUTS_SETTINGS_PREFIX}/original"
_HAS_SAVED_STATE_KEY = f"{SHORTCUTS_SETTINGS_PREFIX}/hasSavedState"


class ShortcutRemap:
    """Applies/restores the curated ArcGIS-like keyboard shortcut remap."""

    def __init__(self, iface, settings):
        self.iface = iface
        self.settings = settings

    def has_saved_state(self) -> bool:
        return self.settings.value(_HAS_SAVED_STATE_KEY, False, type=bool)

    def apply(self) -> int:
        """Returns the number of shortcuts actually changed."""
        manager = QgsGui.shortcutsManager()
        applied_count = 0

        for action_name, sequence_str, label in CURATED_SHORTCUTS:
            action = native_action(self.iface, action_name)
            if action is None:
                continue

            target = QKeySequence(sequence_str)
            try:
                current = action.shortcut()
                default = manager.defaultKeySequence(action)
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not read shortcut state for '%s'", label)
                continue

            if current == target:
                continue  # already applied -- idempotent no-op
            if current != default:
                # Already customized by the user to something else -- never overwrite.
                logger.info(
                    "ArcGIS-like Workspace: skipping shortcut remap for '%s' (already customized)", label
                )
                continue
            if self._is_bound_elsewhere(manager, action, target):
                logger.info(
                    "ArcGIS-like Workspace: skipping shortcut remap for '%s' ('%s' already in use)",
                    label,
                    sequence_str,
                )
                continue

            original_key = f"{_ORIGINAL_KEY_PREFIX}/{action_name}"
            if not self.settings.contains(original_key):
                self.settings.setValue(original_key, current.toString())

            try:
                manager.setKeySequence(action, target)
                applied_count += 1
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not set shortcut for '%s'", label)

        self.settings.setValue(_HAS_SAVED_STATE_KEY, True)
        return applied_count

    def restore(self) -> int:
        """Returns the number of shortcuts actually restored. Safe to call
        even if apply() never ran or only partially completed."""
        manager = QgsGui.shortcutsManager()
        restored_count = 0

        for action_name, _sequence_str, label in CURATED_SHORTCUTS:
            original_key = f"{_ORIGINAL_KEY_PREFIX}/{action_name}"
            if not self.settings.contains(original_key):
                continue

            original_str = self.settings.value(original_key, "")
            self.settings.remove(original_key)

            action = native_action(self.iface, action_name)
            if action is None:
                continue

            try:
                manager.setKeySequence(action, QKeySequence(original_str))
                restored_count += 1
            except Exception:
                logger.exception("ArcGIS-like Workspace: could not restore shortcut for '%s'", label)

        self.settings.setValue(_HAS_SAVED_STATE_KEY, False)
        return restored_count

    @staticmethod
    def _is_bound_elsewhere(manager, action, sequence: QKeySequence) -> bool:
        if sequence.isEmpty():
            return False
        try:
            actions = manager.listActions()
        except Exception:
            return False
        for other in actions:
            if other is action:
                continue
            try:
                other_sequence = other.shortcut()
            except Exception:
                logger.debug(
                    "ArcGIS-like Workspace: could not read shortcut for action %r while checking collisions",
                    other,
                    exc_info=True,
                )
                continue
            if other_sequence == sequence:
                return True
        return False
