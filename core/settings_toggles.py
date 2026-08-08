"""Native QGIS setting toggles layered on top of the workspace layout.

Both toggles flip a behavior that already exists natively in QGIS (just not
as the default) and restore the original value on Restore -- no new UI.
"""

import logging

from qgis.core import Qgis, QgsProject, QgsTolerance

from .compat import qgis_enum
from .constants import Keys

logger = logging.getLogger(__name__)

#: QSettings key controlling whether new attribute tables open docked
#: (Settings > Options > Data Sources > "Open attribute table as docked
#: window" -- confirmed to exist via QGIS docs, but the exact key string
#: below is a best-effort guess, NOT yet verified against a real QGIS
#: install. VERIFY before relying on this: toggle the checkbox in Options,
#: then diff QSettings().allKeys() (or QSettings().value(...)) via the QGIS
#: Python console. If this key is wrong, the toggle silently no-ops --
#: it will not raise or corrupt anything, it just won't do anything.
DOCK_ATTRIBUTE_TABLE_KEY = "qgis/dockAttributeTable"


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

    def _apply_dock_attribute_table(self):
        original = self.settings.value(DOCK_ATTRIBUTE_TABLE_KEY, False, type=bool)
        self.settings.setValue(self._key(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL), original)
        self.settings.setValue(DOCK_ATTRIBUTE_TABLE_KEY, True)

    def _restore_dock_attribute_table(self):
        original_key = self._key(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)
        if not self.settings.contains(original_key):
            return
        original = self.settings.value(original_key, False, type=bool)
        self.settings.setValue(DOCK_ATTRIBUTE_TABLE_KEY, original)
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
            config.setUnits(qgis_enum(QgsTolerance, "Pixels", "UnitType"))
        except Exception:
            logger.exception("ArcGIS-like Workspace: could not set snapping units")
        try:
            vertex = qgis_enum(Qgis, "SnappingTypeVertex", "SnappingType")
            segment = qgis_enum(Qgis, "SnappingTypeSegment", "SnappingType")
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
