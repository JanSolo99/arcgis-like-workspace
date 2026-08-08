# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-08-08

### Added

- Restructured the plugin into an internal `core/` package (`compat`,
  `constants`, `reversible`, `toolbars`, `docks`, `stylesheet`,
  `settings_toggles`, `layertree_menu`, `contextual_ribbon`,
  `notifications`, `locator_filter`, `shortcuts`, `plugin`) so each
  behavioral-parity feature is independently reviewable and testable.
- `FeatureRegistry` (`core/reversible.py`): isolates each feature's
  apply/restore so one feature's failure can't abort the whole workspace
  toggle or block another feature's cleanup.
- Native-setting toggles: QGIS's "Open attribute table as docked window"
  option, and a more generous default snapping configuration for the
  current project (vertex + segment, 12px tolerance).
- A one-click "Toggle Labels" entry on the Contents (layer tree)
  right-click menu, wrapping the native context menu rather than
  replacing it.
- QGIS's native Identify Results and Log Messages docks are now promoted
  into the arranged layout (Identify Results joins the right-hand tabbed
  stack as a read-only feature inspector; Log Messages moves to the
  bottom, hidden by default).
- Contextual ribbon groups: the Edit/Selection groups on the ribbon
  toolbar now show only when a vector layer is active, mirroring ArcGIS
  Pro's contextual Feature-Layer ribbon tabs.
- A Notifications dock: a bell-style toggle on the tab toolbar showing an
  unread count, aggregating background task lifecycle events and
  Warning/Critical log messages.
- A unified locator filter searching layers, geoprocessing tools, and
  bookmarks in one query via QGIS's native locator bar (`Ctrl+K`), plus a
  "Find" button that focuses it.
- An opt-in, reversible keyboard-shortcut remap toward ArcGIS Pro
  conventions ("Apply ArcGIS-like Shortcuts" / "Restore Original
  Shortcuts"), collision-safe and kept independent of the main workspace
  apply/restore lifecycle since it persists directly to QGIS's own
  settings.

### Notes

- `experimental=True` is kept for this release: several of the new
  toggles mutate native QGIS settings more invasively than the pure
  layout/stylesheet layer in 0.1.0, and there is no automated test
  coverage against a real QGIS install. See `QA_CHECKLIST.md`.

## [0.1.0] - 2026-08-07

### Added

- Initial release: tab-style dropdown toolbar and ribbon-style toolbar
  built from native QGIS actions, dock rearrangement (Contents / Catalog
  / Geoprocessing / Symbology), an ArcGIS-Pro-inspired Qt stylesheet, and
  full reversibility via a Restore action or plugin disable.
