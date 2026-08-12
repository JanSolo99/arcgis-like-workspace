# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-08-12

### Added

- **Reset to Default QGIS Workspace**: a new button (tab toolbar, next to
  Restore) and plugin-menu action. Unlike Restore, which returns to
  *your* pre-Apply layout (including any of your own toolbars/panels you
  had hidden), Reset undoes this plugin's changes and then forces every
  known QGIS default toolbar and the core Contents/Catalog panels
  visible regardless of your prior layout. Panel *positions* aren't
  replayed — QGIS's true default layout is built once, in its own C++
  startup code, and isn't exposed for a plugin to reconstruct on demand,
  so a fully pixel-perfect factory reset still needs a QGIS restart.
  `ToolbarBuilder.show_default_toolbars()` (mirrors the existing
  `hide_default_toolbars()`) forces default-toolbar visibility;
  `DockArranger.find_dock()` (already used elsewhere) locates and shows
  the Contents/Catalog docks.

### Changed

- `experimental` flipped to `False` — marked stable.

## [0.2.1] - 2026-08-12

### Fixed

- **Crash**: Apply → Restore → Apply again could instantly crash QGIS.
  Root cause: `core/layertree_menu.py` captured QGIS's native
  `QgsLayerTreeView` menu provider, installed a wrapper via
  `setMenuProvider()`, and tried to hand the native one back on Restore.
  `setMenuProvider()` documents that it "takes ownership of the
  instance" (stored in a `std::unique_ptr`) — every call deletes
  whatever provider was installed before, so the "original" reference
  was already dangling by the time Restore tried to reuse it. The actual
  crash (a double-free) only surfaced on the *next* `setMenuProvider()`
  call, i.e. the second Apply. Fixed by never attempting to preserve or
  restore the native provider at all: the Contents right-click menu is
  now built from scratch (via `QgsLayerTreeViewDefaultActions`) and
  installed at most once per QGIS session, with an `active` flag toggled
  on Apply/Restore instead of swapping providers. See the module
  docstring in `core/layertree_menu.py` for the full explanation. One
  unavoidable consequence: the Contents right-click menu no longer
  reverts to QGIS's exact native menu after Restore within the same
  session — see `QA_CHECKLIST.md`.
- Fixed two Bandit security-scan findings (`try`/`except`/`pass` or
  `continue`, rules B110/B112) flagged by plugins.qgis.org's mandatory
  scan on first upload — both were intentional defensive skips, now
  logged before continuing instead of silently swallowed.

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
