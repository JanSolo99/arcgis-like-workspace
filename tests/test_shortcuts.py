"""Tests for core/shortcuts.py -- ShortcutRemap.

The bug this guards against: QgsShortcutsManager.setKeySequence(action,
sequence) only accepts *sequence* as a plain str (verified against
https://qgis.org/pyqgis/master/gui/QgsShortcutsManager.html --
`setKeySequence(action: Optional[QAction], sequence: Optional[str]) -> bool`).
Passing a QKeySequence instead raises TypeError at the sip boundary, which
is exactly the documented contract that made an earlier version of this
feature inert. tests/helpers.FakeShortcutsManager enforces that same
str-only contract, so apply()/restore() succeeding here is a real
regression test for it -- a fake that accepted any type would let that bug
back in silently.
"""

from arcgis_like_workspace.core.shortcuts import (
    _HAS_SAVED_STATE_KEY,
    _ORIGINAL_KEY_PREFIX,
    ShortcutRemap,
)
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import QSettings

from tests.helpers import FakeIface, FakeShortcutsManager, make_action


def _original_key(action_name: str) -> str:
    return f"{_ORIGINAL_KEY_PREFIX}/{action_name}"


def test_apply_succeeds_with_a_manager_that_rejects_non_str_sequences():
    """This is the regression test: FakeShortcutsManager.setKeySequence
    raises TypeError for anything but a str, mirroring the real sip
    contract. If shortcuts.py ever regressed to passing a QKeySequence
    (or the target's QKeySequence object) instead of the plain
    sequence_str, this would raise instead of returning cleanly."""
    action = make_action("Delete Selected Features")
    manager = FakeShortcutsManager()
    manager.set_default(action, "Backspace")  # current == default, != target "Del"
    QgsGui._manager = manager

    iface = FakeIface({"actionDeleteSelected": action})
    settings = QSettings()
    remap = ShortcutRemap(iface, settings)

    count = remap.apply()

    assert count == 1
    assert action.shortcut().toString() == "Del"
    assert manager.set_calls == [(action, "Del")]
    assert settings.value(_original_key("actionDeleteSelected")) == "Backspace"
    assert settings.value(_HAS_SAVED_STATE_KEY) is True


def test_apply_is_idempotent_when_already_applied():
    """current == target is treated as an already-applied no-op -- no
    setKeySequence call, no settings write for that entry."""
    action = make_action()
    manager = FakeShortcutsManager()
    manager.set_default(action, "Backspace")  # default is irrelevant here
    action.setShortcut("Del")  # already at the target value
    QgsGui._manager = manager

    iface = FakeIface({"actionDeleteSelected": action})
    settings = QSettings()
    remap = ShortcutRemap(iface, settings)

    count = remap.apply()

    assert count == 0
    assert manager.set_calls == []
    assert not settings.contains(_original_key("actionDeleteSelected"))


def test_apply_skips_an_already_customized_shortcut():
    """current != default -> the user changed this shortcut themselves;
    apply() must never overwrite it."""
    action = make_action()
    manager = FakeShortcutsManager()
    manager.set_default(action, "Ctrl+D")
    action.setShortcut("Ctrl+Shift+D")  # user's own customization
    QgsGui._manager = manager

    iface = FakeIface({"actionDeleteSelected": action})
    settings = QSettings()
    remap = ShortcutRemap(iface, settings)

    count = remap.apply()

    assert count == 0
    assert manager.set_calls == []
    assert not settings.contains(_original_key("actionDeleteSelected"))
    assert action.shortcut().toString() == "Ctrl+Shift+D"  # untouched


def test_apply_skips_when_target_sequence_is_bound_elsewhere():
    """current == default (eligible), but the target sequence is already
    in use by a different action -- must skip rather than create a
    collision."""
    action = make_action()
    other_action = make_action("Some Other Action")
    manager = FakeShortcutsManager()
    manager.set_default(action, "")  # current == default == "" (unset)
    manager.register_action(other_action, "Del")  # target already bound here
    QgsGui._manager = manager

    iface = FakeIface({"actionDeleteSelected": action})
    settings = QSettings()
    remap = ShortcutRemap(iface, settings)

    count = remap.apply()

    assert count == 0
    assert manager.set_calls == []
    assert not settings.contains(_original_key("actionDeleteSelected"))
    assert action.shortcut().toString() == ""


def test_restore_keeps_the_record_when_setkeysequence_fails_and_only_removes_it_on_success():
    action1 = make_action("Delete Selected Features")
    action2 = make_action("New Bookmark")
    manager = FakeShortcutsManager()
    manager.set_default(action1, "Backspace")
    manager.set_default(action2, "Ctrl+Shift+B")
    QgsGui._manager = manager

    iface = FakeIface(
        {"actionDeleteSelected": action1, "actionNewBookmark": action2}
    )
    settings = QSettings()
    remap = ShortcutRemap(iface, settings)

    applied = remap.apply()
    assert applied == 2
    assert settings.contains(_original_key("actionDeleteSelected"))
    assert settings.contains(_original_key("actionNewBookmark"))

    # Now make restoring action1's shortcut fail (simulating QGIS declining
    # the change) while action2 restores normally.
    manager.decline_next(action1)

    restored = remap.restore()

    assert restored == 1
    # action1's recovery record must survive a failed restore -- it would
    # otherwise be silently lost while the remap stayed applied.
    assert settings.contains(_original_key("actionDeleteSelected"))
    assert settings.value(_original_key("actionDeleteSelected")) == "Backspace"
    assert action1.shortcut().toString() == "Del"  # unchanged -- still remapped

    # action2's record is gone because its restore succeeded.
    assert not settings.contains(_original_key("actionNewBookmark"))
    assert action2.shortcut().toString() == "Ctrl+Shift+B"

    # Still "has saved state" -- action1 is still pending recovery.
    assert settings.value(_HAS_SAVED_STATE_KEY) is True

    # A later retry (e.g. from unload()'s safety net) succeeds once the
    # manager stops declining, and clears the remaining record.
    manager.stop_declining(action1)
    restored_again = remap.restore()
    assert restored_again == 1
    assert not settings.contains(_original_key("actionDeleteSelected"))
    assert action1.shortcut().toString() == "Backspace"
    assert settings.value(_HAS_SAVED_STATE_KEY) is False


def test_restore_is_a_safe_no_op_when_apply_never_ran():
    action = make_action()
    manager = FakeShortcutsManager()
    manager.set_default(action, "Backspace")
    QgsGui._manager = manager

    iface = FakeIface({"actionDeleteSelected": action})
    settings = QSettings()
    remap = ShortcutRemap(iface, settings)

    count = remap.restore()

    assert count == 0
    assert manager.set_calls == []
