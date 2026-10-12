"""Tests for core/stylesheet.py: Restore removes exactly this plugin's
marker-delimited block, and re-apply never stacks a second copy."""

from arcgis_like_workspace.core.constants import STYLE_END_MARKER, STYLE_MARKER
from arcgis_like_workspace.core.stylesheet import StylesheetManager, strip_workspace_style

from tests.helpers import FakeMainWindow


def test_restore_keeps_rules_added_by_someone_else_after_apply():
    window = FakeMainWindow()
    window.setStyleSheet("QWidget { color: red; }")
    manager = StylesheetManager(window)

    manager.apply()
    window.setStyleSheet(window.styleSheet() + "\nQLabel { color: blue; }")  # another plugin
    manager.restore()

    assert window.styleSheet() == "QWidget { color: red; }\nQLabel { color: blue; }"


def test_reapply_replaces_the_block_instead_of_stacking_it():
    window = FakeMainWindow()
    manager = StylesheetManager(window)

    manager.apply()
    manager.apply()

    assert window.styleSheet().count(STYLE_MARKER) == 1
    assert window.styleSheet().count(STYLE_END_MARKER) == 1


def test_restore_without_apply_is_a_no_op():
    window = FakeMainWindow()
    window.setStyleSheet("QWidget { color: red; }")

    StylesheetManager(window).restore()

    assert window.styleSheet() == "QWidget { color: red; }"


def test_strip_handles_a_legacy_block_without_end_marker():
    legacy = f"QWidget {{ color: red; }}\n{STYLE_MARKER}\nQToolBar {{ }}"

    assert strip_workspace_style(legacy) == "QWidget { color: red; }"
