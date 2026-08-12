"""Native QGIS setting toggles layered on top of the workspace layout.

Both toggles flip a behavior that already exists natively in QGIS (just not
as the default) and restore the original value on Restore -- no new UI.
"""

import logging

from qgis.core import Qgis, QgsProject, QgsSnappingConfig, QgsTolerance

from .compat import qgis_enum_candidates
from .constants import Keys

logger = logging.getLogger(__name__)

#: QSettings key controlling whether new attribute tables open docked
#: (Settings > Options > Data Sources > "Open attribute table as docked
#: window"). VERIFIED against QGIS source for 3.28-3.40: this is the literal
#: key QgsAttributeTableDialog reads on construction --
#: `settings.value(QStringLiteral("qgis/dockAttributeTable"), false).toBool()`
#: in src/app/qgsattributetabledialog.cpp, line 288 on release-3_34 and line
#: 286 on release-3_40. NOT valid on QGIS 3.44+, which replaced it with a
#: registered settings entry -- see DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY
#: below. If this key is wrong for the running version, setting it silently
#: no-ops -- it will not raise or corrupt anything, it just won't do
#: anything, which is why both keys below are written unconditionally rather
#: than branched on a detected version.
DOCK_ATTRIBUTE_TABLE_KEY = "qgis/dockAttributeTable"

#: QGIS 3.44 replaced the plain bool above with a registered
#: QgsSettingsEntryBool: `settingsAttributeTableDefaultDocked = new
#: QgsSettingsEntryBool(QStringLiteral("attribute-table-default-docked"),
#: QgsSettingsTree::sTreeAttributeTable, false, ...)` in
#: src/app/qgsattributetabledialog.cpp, line 60 on release-3_44 (also present
#: on master). Tree-registered entries resolve their actual QSettings key by
#: joining the ancestor tree node's own key segment with the entry's key via
#: `QDir::cleanPath(parent->completeKey() + "/" + key)`
#: (src/core/settings/qgssettingsentry.cpp), and are read back through plain
#: QSettings with QgsSettings::NoSection -- no "core/"-style prefix
#: (`section()` returns NoSection in the same file). sTreeAttributeTable
#: itself is `treeRoot()->createChildNode(u"attribute-table"_s)`
#: (src/core/settings/qgssettingstree.h), so the resulting key is
#: "attribute-table/attribute-table-default-docked". This derivation is not
#: read off a running QGIS install, but QGIS's own 3-to-4 profile migration
#: (Qgs3To4Migration::migrateProfile in src/app/qgsversionmigration.cpp)
#: independently corroborates both endpoints in one place: it reads the
#: legacy `"qgis/dockAttributeTable"` bool and, if set, calls
#: `QgsAttributeTableDialog::settingsAttributeTableDefaultDocked->setValue(true)`
#: -- the very entry object constructed above. Same no-op-if-wrong failure
#: mode as the legacy key.
DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY = "attribute-table/attribute-table-default-docked"

#: Own-record key (via self._key()) for DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY's
#: pre-apply value -- the counterpart to Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL
#: (constants.py) for the legacy key. Kept as a plain string here rather than
#: added to constants.Keys so this fix doesn't have to touch a file another
#: agent may be editing in parallel; it is just as much "a named QSettings
#: key" as its sibling, only spelled locally.
_DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL = "dockAttributeTableDockedSettingOriginal"

#: Ordered enum-spelling candidates for QGIS's snapping-type flags and
#: tolerance units, resolved via compat.qgis_enum_candidates(). Every
#: candidate here is a spelling actually observed in QGIS's own source or
#: generated Python bindings -- none are guesses:
#:
#: * Qgis.SnappingType.Vertex/.Segment: the current, documented home since
#:   QGIS 3.26 (present on the 3.28 floor: `enum class SnappingType` nested
#:   in Qgis, src/core/qgis.h) through master/4.x (same declaration, still
#:   present). QgsSnappingConfig.setTypeFlag()/typeFlag() take/return exactly
#:   this type across the same range (src/core/qgssnappingconfig.h).
#: * QgsSnappingConfig.VertexFlag/.SegmentFlag: a legacy compat alias, listed
#:   only as a defensive fallback -- confirmed present (monkey-patched onto
#:   QgsSnappingConfig, equal to Qgis.SnappingType.Vertex/.Segment) in the
#:   generated python/core/auto_additions/qgis.py on both release-3_28 and
#:   release-3_40, so it does not extend coverage beyond the primary spelling
#:   above, but costs nothing to keep as a second attempt.
#: * Qgis.MapToolUnit.Pixels: the tolerance-units enum's home since QGIS
#:   3.32 (`enum class MapToolUnit`, src/core/qgis.h), unchanged through
#:   master. Does not exist before 3.32.
#: * QgsTolerance.UnitType.Pixels: QgsTolerance's own nested UnitType enum,
#:   native (not an alias) on the 3.28 floor
#:   (python/core/auto_generated/qgstolerance.sip.in on release-3_28: `enum
#:   UnitType { LayerUnits, Pixels, ProjectUnits }`), and kept working from
#:   3.32 onward via a monkey-patched alias, `QgsTolerance.UnitType =
#:   Qgis.MapToolUnit` (python/core/auto_additions/qgis.py on release-3_40).
#:   Listed second because Qgis.MapToolUnit is the permanent, current home,
#:   but this spelling alone actually covers the whole 3.28-4.x range.
_SNAPPING_VERTEX_CANDIDATES = (
    (Qgis, "SnappingType.Vertex"),
    (QgsSnappingConfig, "VertexFlag"),
)
_SNAPPING_SEGMENT_CANDIDATES = (
    (Qgis, "SnappingType.Segment"),
    (QgsSnappingConfig, "SegmentFlag"),
)
_TOLERANCE_PIXELS_CANDIDATES = (
    (Qgis, "MapToolUnit.Pixels"),
    (QgsTolerance, "UnitType.Pixels"),
)


class SettingsToggles:
    """Dock-attribute-tables and default-snapping toggles, reversibly."""

    def __init__(self, settings, key_fn):
        self.settings = settings
        self._key = key_fn
        self._original_snapping_config = None
        self._applied = False

    def apply(self):
        """Idempotent: calling apply() again before restore() is a no-op."""
        if self._applied:
            return
        self._apply_dock_attribute_table()
        self._apply_snapping_defaults()
        self._applied = True

    def restore(self):
        """Safe to call even if apply() never ran or only partially completed."""
        self._restore_dock_attribute_table()
        self._restore_snapping_defaults()
        self._applied = False

    # -- Dock attribute tables --------------------------------------------
    #
    # Both the legacy (3.28-3.40) and current (3.44+) keys are applied and
    # restored unconditionally, each with its own saved-original -- see the
    # module docstring block above for why. Whichever key the running QGIS
    # version doesn't actually read is a harmless no-op write.

    def _apply_dock_attribute_table(self):
        self._apply_dock_attribute_table_key(
            DOCK_ATTRIBUTE_TABLE_KEY, self._key(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)
        )
        self._apply_dock_attribute_table_key(
            DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY,
            self._key(_DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL),
        )

    def _apply_dock_attribute_table_key(self, key, original_key):
        # Guarded so a re-apply after a crashed/killed session (apply() ran,
        # restore() never did) can't record the plugin's own leaked True as
        # "original" -- mirrors ShortcutRemap.apply()'s guard in shortcuts.py.
        if not self.settings.contains(original_key):
            original = self.settings.value(key, False, type=bool)
            self.settings.setValue(original_key, original)
        self.settings.setValue(key, True)

    def _restore_dock_attribute_table(self):
        self._restore_dock_attribute_table_key(
            DOCK_ATTRIBUTE_TABLE_KEY, self._key(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)
        )
        self._restore_dock_attribute_table_key(
            DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY,
            self._key(_DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL),
        )

    def _restore_dock_attribute_table_key(self, key, original_key):
        if not self.settings.contains(original_key):
            return
        original = self.settings.value(original_key, False, type=bool)
        self.settings.setValue(key, original)
        self.settings.remove(original_key)

    # -- Snapping defaults (current project only, not persisted) ----------

    def _apply_snapping_defaults(self):
        project = QgsProject.instance()
        self._original_snapping_config = project.snappingConfig()

        config = project.snappingConfig()
        try:
            config.setEnabled(True)
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not enable snapping")
        try:
            config.setTolerance(12)
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not set snapping tolerance")
        try:
            config.setUnits(qgis_enum_candidates(_TOLERANCE_PIXELS_CANDIDATES))
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not set snapping units")
        try:
            vertex = qgis_enum_candidates(_SNAPPING_VERTEX_CANDIDATES)
            segment = qgis_enum_candidates(_SNAPPING_SEGMENT_CANDIDATES)
            config.setTypeFlag(vertex | segment)
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not set snapping type")

        project.setSnappingConfig(config)

    def _restore_snapping_defaults(self):
        if self._original_snapping_config is None:
            return
        try:
            QgsProject.instance().setSnappingConfig(self._original_snapping_config)
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not restore snapping config")
        finally:
            self._original_snapping_config = None
