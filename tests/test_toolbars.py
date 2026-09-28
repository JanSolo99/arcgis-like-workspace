"""Tests for core/toolbars.py: toolbar placement and ribbon group visibility.

Placement regression: a bare addToolBar(TOP, ...) appended both plugin
toolbars to the last existing toolbar row, side by side -- in a real QGIS
4.2 session the ribbon was squeezed to 124px behind its overflow chevron,
underneath the still-visible native toolbars. They must each get their own
row, above every native toolbar.
"""

from arcgis_like_workspace.core.constants import OBJECT_PREFIX
from arcgis_like_workspace.core.toolbars import ToolbarBuilder
from qgis.PyQt.QtWidgets import QToolBar

from tests.helpers import FakeIface, FakeMainWindow, make_action


def _native_toolbar(name, position, visible=True):
    toolbar = QToolBar(name)
    toolbar.setObjectName(name)
    toolbar.position = position
    toolbar.setVisible(visible)
    return toolbar


def _apply(builder):
    """Mirror plugin.apply_layout()'s toolbar steps."""
    builder.remove_workspace_toolbars(keep_anchor=True)
    builder.hide_default_toolbars()
    builder.create_tab_toolbar(lambda: None, lambda: None)
    builder.create_ribbon_toolbar()


def _names(window):
    return [[toolbar.objectName() for toolbar in row] for row in window.toolbar_rows]


def _window_with_native_toolbars():
    window = FakeMainWindow()
    window.toolbar_rows = [
        [_native_toolbar("mFileToolBar", (0, 0)), _native_toolbar("mDigitizeToolBar", (250, 0))],
        [_native_toolbar("thirdPartyToolBar", (0, 30))],
    ]
    return window


def test_tabs_and_ribbon_get_their_own_rows_above_native_toolbars():
    window = _window_with_native_toolbars()
    builder = ToolbarBuilder(FakeIface(main_window=window), window)

    _apply(builder)

    assert _names(window) == [
        [f"{OBJECT_PREFIX}TabsToolbar"],
        [f"{OBJECT_PREFIX}RibbonToolbar"],
        ["mFileToolBar", "mDigitizeToolBar"],
        ["thirdPartyToolBar"],
    ]


def test_reapply_rebuilds_the_toolbars_in_the_same_place():
    window = _window_with_native_toolbars()
    builder = ToolbarBuilder(FakeIface(main_window=window), window)

    _apply(builder)
    first = _names(window)
    _apply(builder)  # the anchor (mFileToolBar) is hidden by now

    assert _names(window) == first


def test_placement_without_any_native_toolbar_still_uses_separate_rows():
    window = FakeMainWindow()
    builder = ToolbarBuilder(FakeIface(main_window=window), window)

    _apply(builder)

    assert _names(window) == [[f"{OBJECT_PREFIX}TabsToolbar"], [f"{OBJECT_PREFIX}RibbonToolbar"]]


def test_group_visibility_never_touches_the_shared_native_action():
    pan = make_action("Pan")
    select = make_action("Select")
    window = FakeMainWindow()
    builder = ToolbarBuilder(
        FakeIface({"actionPan": pan, "actionSelectRectangle": select}, main_window=window), window
    )
    builder.create_ribbon_toolbar()

    selection = builder.action_groups["Selection"]
    selection.set_visible(False)

    assert pan.isVisible() and select.isVisible()
    assert selection.separator is not None and not selection.separator.isVisible()
    assert all(not action.isVisible() for action in selection.widget_actions)
    assert all(action.isVisible() for action in builder.action_groups["Map"].widget_actions)

    selection.set_visible(True)
    assert selection.separator.isVisible()
    assert all(action.isVisible() for action in selection.widget_actions)


def test_ribbon_buttons_wrap_the_native_actions():
    pan = make_action("Pan")
    window = FakeMainWindow()
    builder = ToolbarBuilder(FakeIface({"actionPan": pan}, main_window=window), window)
    toolbar = builder.create_ribbon_toolbar()

    widget_action = builder.action_groups["Map"].widget_actions[1]  # [0] is the label
    assert toolbar.widgetForAction(widget_action).defaultAction() is pan


def test_main_window_only_actions_are_resolved_by_object_name():
    data_source_manager = make_action("Data Source Manager")
    window = FakeMainWindow()
    window.named_actions["mActionDataSourceManager"] = data_source_manager
    builder = ToolbarBuilder(FakeIface(main_window=window), window)
    toolbar = builder.create_ribbon_toolbar()

    layers = builder.action_groups["Layers"]
    assert toolbar.widgetForAction(layers.widget_actions[1]).defaultAction() is data_source_manager
