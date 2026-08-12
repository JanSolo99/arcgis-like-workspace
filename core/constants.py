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


class Keys:
    """Named QSettings keys (relative to SETTINGS_PREFIX unless noted)."""

    HAS_SAVED_STATE = "hasSavedState"
    WINDOW_STATE = "windowState"
    WINDOW_GEOMETRY = "windowGeometry"
    DOCK_ATTRIBUTE_TABLE_ORIGINAL = "dockAttributeTableOriginal"


# Standard QGIS toolbar object names that Apply may hide. Only toolbars
# whose object names are in this known-default set are hidden -- plugin and
# third-party toolbars are always left untouched.
#
# Deliberately EXCLUDED: mDigitizeToolBar, mAdvancedDigitizeToolBar,
# mSnappingToolBar, mLabelToolBar (see QGIS_EDITING_TOOLBAR_NAMES below).
# The replacement ribbon/tab "Edit" group only exposes five actions (toggle
# editing, save edits, add feature, vertex tool, delete selected) -- nowhere
# near the editing capability those native toolbars provide, and
# mSnappingToolBar is the only UI for adjusting snapping settings at all.
# Apply hiding them would strip capability the preset does not replace.
# Reset to Default QGIS Workspace has different needs -- see
# QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES -- and does look at these too.
QGIS_DEFAULT_TOOLBAR_NAMES: set = {
    "mFileToolBar",
    "mLayerToolBar",
    "mMapNavToolBar",
    "mAttributesToolBar",
    "mVectorToolBar",
    "mRasterToolBar",
    "mWebToolBar",
    "mDatabaseToolBar",
    "mHelpToolBar",
    "mPluginToolBar",
    "mSelectionToolBar",
    "mProjectToolBar",
    "mAnnotationToolBar",
    "mDataStreamingToolBar",
    "mShapeDigitizeToolBar",
    "mMeshDigitizingToolBar",
}

# The editing-related toolbars Apply deliberately leaves alone (see the
# comment above) -- kept as a separate set because Reset to Default QGIS
# Workspace has a different job than Apply: it isn't trying to preserve
# whatever editing setup you had, it's trying to reproduce a stock QGIS
# install, and these ARE part of that stock state (see below).
QGIS_EDITING_TOOLBAR_NAMES: set = {
    "mDigitizeToolBar",
    "mAdvancedDigitizeToolBar",
    "mSnappingToolBar",
    "mLabelToolBar",
}

# Toolbars actually visible by default in a stock QGIS install -- confirmed
# against a real QGIS 4 session's View > Toolbars checkboxes (2026-08-12).
# Every other toolbar in QGIS_DEFAULT_TOOLBAR_NAMES/QGIS_EDITING_TOOLBAR_NAMES
# is HIDDEN by default. This matters specifically for "Reset to Default QGIS
# Workspace": showing every toolbar this plugin knows about is not QGIS's
# default, it's toolbar soup -- Reset needs to know which ones QGIS itself
# would leave hidden, not just which ones exist.
QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES: set = {
    "mAttributesToolBar",
    "mLayerToolBar",
    "mMapNavToolBar",
    "mProjectToolBar",
    "mSelectionToolBar",
}
