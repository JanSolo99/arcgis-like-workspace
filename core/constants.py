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

    #: Absolute (not relative to SETTINGS_PREFIX) -- see SHORTCUTS_SETTINGS_PREFIX.
    SHORTCUTS_HAS_SAVED_STATE = f"{SHORTCUTS_SETTINGS_PREFIX}/hasSavedState"


# Standard QGIS toolbar object names that this plugin may hide. Only toolbars
# whose object names are in this known-default set are hidden -- plugin and
# third-party toolbars are always left untouched.
QGIS_DEFAULT_TOOLBAR_NAMES: set = {
    "mFileToolBar",
    "mLayerToolBar",
    "mMapNavToolBar",
    "mAttributesToolBar",
    "mDigitizeToolBar",
    "mAdvancedDigitizeToolBar",
    "mLabelToolBar",
    "mVectorToolBar",
    "mRasterToolBar",
    "mWebToolBar",
    "mDatabaseToolBar",
    "mHelpToolBar",
    "mPluginToolBar",
    "mSelectionToolBar",
    "mSnappingToolBar",
    "mProjectToolBar",
    "mAnnotationToolBar",
    "mDataStreamingToolBar",
    "mShapeDigitizeToolBar",
    "mMeshDigitizingToolBar",
}
