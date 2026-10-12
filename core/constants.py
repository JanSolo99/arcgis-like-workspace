"""Shared constants: menu/object naming, settings keys, and known toolbar names."""

MENU_NAME = "&ArcGIS-like Workspace"
OBJECT_PREFIX = "arcgisLikeWorkspace"

#: QSettings branch wiped wholesale by restore_layout(). Anything stored under
#: here is undone the moment the workspace is restored. Settings that must
#: survive an ordinary workspace restore (e.g. the opt-in shortcut remap,
#: which has its own independent apply/restore lifecycle) must NOT live here
#: -- see SHORTCUTS_SETTINGS_PREFIX below.
SETTINGS_PREFIX = "arcgis_like_workspace"

#: Separate top-level settings branch for the opt-in keyboard-shortcut remap.
#: Deliberately outside SETTINGS_PREFIX so that restoring the main workspace
#: preset does not wipe the record of a user's original shortcuts -- that
#: record must remain recoverable via "Restore Original Shortcuts" even if
#: QGIS crashed before the main workspace was ever restored.
SHORTCUTS_SETTINGS_PREFIX = "arcgis_like_workspace_shortcuts"

STYLE_MARKER = "/* arcgis-like-workspace-style */"
#: Closes the block STYLE_MARKER opens, so Restore can cut out exactly this
#: plugin's rules and leave anything appended after them (e.g. by another
#: plugin) in place.
STYLE_END_MARKER = "/* /arcgis-like-workspace-style */"


class Keys:
    """Named QSettings keys (relative to SETTINGS_PREFIX unless noted)."""

    HAS_SAVED_STATE = "hasSavedState"
    WINDOW_STATE = "windowState"
    WINDOW_GEOMETRY = "windowGeometry"
    DOCK_ATTRIBUTE_TABLE_ORIGINAL = "dockAttributeTableOriginal"


# Standard QGIS toolbar object names that Apply hides. Only toolbars whose
# object names are in this known-default set are hidden -- plugin and
# third-party toolbars are always left untouched. Names are the union of
# what QGIS 3.28-3.40 and 4.x use (checked against a fresh QGIS 4.2 profile,
# 2026-09-27); a name missing from the running version is simply never
# matched.
#
# The editing-related toolbars are NOT in this set -- see
# QGIS_CONTEXTUAL_TOOLBAR_NAMES below, which shows/hides them based on the
# active layer instead of hiding them outright.
QGIS_DEFAULT_TOOLBAR_NAMES: set = {
    "mFileToolBar",
    "mLayerToolBar",
    "mMapNavToolBar",
    "mAttributesToolBar",
    "mVectorToolBar",
    "mRasterToolBar",
    "mWebToolBar",
    "mDatabaseToolBar",
    "mDataSourceManagerToolBar",
    "mHelpToolBar",
    "mPluginToolBar",
    "mSelectionToolBar",
    "mProjectToolBar",
    "mAnnotationToolBar",
    "mAnnotationsToolBar",
    "mDataStreamingToolBar",
    "mShapeDigitizeToolBar",
    "mMeshToolBar",
    "mMeshDigitizingToolBar",
    "mGpsToolBar",
}

# Native toolbars whose visibility follows the active layer while the
# workspace is applied, the way ArcGIS Pro only surfaces editing and
# labeling tools in context (see contextual_ribbon.py). The ribbon's own
# Edit group exposes only five actions -- nowhere near what these provide,
# and mSnappingToolBar is the main snapping UI -- so they are shown when
# relevant rather than hidden for good.
#
#: Shown only while the active layer is a vector layer in edit mode.
QGIS_EDITING_CONTEXT_TOOLBAR_NAMES: tuple = ("mDigitizeToolBar", "mSnappingToolBar")
#: Shown whenever the active layer is a vector layer.
QGIS_VECTOR_CONTEXT_TOOLBAR_NAMES: tuple = ("mLabelToolBar",)
QGIS_CONTEXTUAL_TOOLBAR_NAMES: set = set(QGIS_EDITING_CONTEXT_TOOLBAR_NAMES) | set(
    QGIS_VECTOR_CONTEXT_TOOLBAR_NAMES
)

# Every editing-related toolbar, for Reset to Default QGIS Workspace, which
# has a different job than Apply: it reproduces a stock QGIS install, and
# these ARE part of that stock state.
QGIS_EDITING_TOOLBAR_NAMES: set = QGIS_CONTEXTUAL_TOOLBAR_NAMES | {"mAdvancedDigitizeToolBar"}

# Toolbars visible by default in a stock QGIS install -- read off a fresh
# QGIS 4.2 profile (2026-09-27). Every other toolbar in
# QGIS_DEFAULT_TOOLBAR_NAMES/QGIS_EDITING_TOOLBAR_NAMES is HIDDEN by default.
# This matters specifically for "Reset to Default QGIS Workspace": showing
# every toolbar this plugin knows about is not QGIS's default, it's toolbar
# soup -- Reset needs to know which ones QGIS itself would leave hidden.
QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES: set = {
    "mFileToolBar",
    "mDataSourceManagerToolBar",
    "mDigitizeToolBar",
    "mMapNavToolBar",
    "mAttributesToolBar",
    "mSelectionToolBar",
    "mLabelToolBar",
    "mVectorToolBar",
    "mWebToolBar",
    "mPluginToolBar",
    "mHelpToolBar",
}
