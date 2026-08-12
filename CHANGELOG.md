# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.1] - 2026-08-12

Two bugs found the same way the 0.4.0 ones should have been caught in the
first place: actually running the plugin in real QGIS and comparing what
happened against what was claimed. Both reported directly by a user testing
0.4.0.

### Fixed

- **First Apply sometimes didn't move a dock (e.g. Browser) into position --
  a second Apply click was needed.** `DockArranger.arrange()` called
  `dock.setVisible(True)` before `addDockWidget()`, and moving a dock that's
  already part of a tab group (Browser starts tabbed with Layers in a stock
  QGIS install) doesn't always cleanly detach with `addDockWidget()` alone.
  `core/docks.py` now explicitly `removeDockWidget()`s a dock before
  re-adding it to its target area, and repositions before showing rather
  than after, for every dock this plugin touches.
- **"Reset to Default QGIS Workspace" didn't actually match QGIS's
  defaults.** It forced every toolbar this plugin knows about visible --
  but a real QGIS install only shows five by default (Attributes, Manage
  Layers, Map Navigation, Project, Selection); everything else (Advanced
  Digitizing, Digitizing, Snapping, Label, Database, Web, Raster, Vector,
  Annotations, Plugins, Help, Mesh Digitizing, Shape Digitizing) is hidden
  out of the box. Confirmed against a real QGIS 4 session's View > Toolbars
  checkboxes. `core/constants.py` gains
  `QGIS_DEFAULT_VISIBLE_TOOLBAR_NAMES` (the five) and
  `QGIS_EDITING_TOOLBAR_NAMES` (the four Apply deliberately leaves alone,
  which Reset still needs to know about); `ToolbarBuilder.show_default_toolbars()`
  now shows the true-default five and hides every other known toolbar,
  instead of showing all of them.

## [0.4.0] - 2026-08-12

A multi-lens review of the 0.3.0 code (no real QGIS install involved, just
close reading against QGIS/Qt source and docs) found that three of the
"working" 0.2.0/0.3.0 features were actually silently inert -- wrong API
call shapes that never raised, so nothing in manual testing could have
caught them without knowing to check the *result*, not just the absence of
a crash. That is also why `experimental` goes back to `True` below: this
release is large enough, and was field-tested little enough, that calling
it stable again would repeat the same mistake.

### Fixed

- **Shortcut remap was inert.** `QgsShortcutsManager.setKeySequence()`
  takes the new key sequence as a plain `str`, not a `QKeySequence` --
  the old code passed a `QKeySequence` object and never checked the
  method's boolean return value, so a declined or mistyped call wasn't
  distinguished from a real success. `Del`/`Ctrl+B` never actually got
  rebound, and "Apply ArcGIS-like Shortcuts" reported a generic "no
  shortcuts changed" message that reads as a normal no-op case (one of
  the two curated entries legitimately *is* a no-op on stock installs --
  see `core/shortcuts.py`'s module docstring), making the failure easy to
  miss. Fixed by passing the plain string and checking the return value;
  verified against
  https://qgis.org/pyqgis/master/gui/QgsShortcutsManager.html.
- **Segment snapping was never actually enabled.** The snapping-type flags
  passed to `QgsSnappingConfig.setTypeFlag()` used the wrong enum spelling,
  so the project's snapping config silently kept whatever type flag it
  already had -- vertex snapping typically still worked (it was often
  already the default), masking that segment snapping was never being
  turned on. Fixed by resolving `Qgis.SnappingType.Vertex` /
  `Qgis.SnappingType.Segment` (with a `QgsSnappingConfig.VertexFlag` /
  `.SegmentFlag` fallback) via the existing compat-candidate helper in
  `core/settings_toggles.py`; verified against
  https://qgis.org/pyqgis/master/core/Qgis.html and
  `src/core/qgis.h` on https://github.com/qgis/QGIS.
- **The "Find" button did nothing.** It called `QgsGui.locatorWidget()`,
  which has never existed on `QgsGui` at any supported QGIS version --
  the locator widget lives on the main window, not the `QgsGui`
  singleton, and isn't exposed via `QgisInterface` either. Fixed in
  `core/locator_filter.py` by locating the native `QgsLocatorWidget` with
  `iface.mainWindow().findChild(QgsLocatorWidget)`, the same pattern
  already used elsewhere in this plugin for native chrome that has no
  interface accessor; verified `QgsGui` has no such method against
  https://qgis.org/pyqgis/master/gui/QgsGui.html.
- **Cross-session Restore after a crash never ran.** `FeatureRegistry`
  tracked an internal "was this applied" gate and skipped every
  `restore_fn` for features not in it -- but a fresh plugin instance
  (new QGIS process) always starts with an empty gate, regardless of what
  was actually applied and left dangling by a crashed or force-closed
  prior session. `unload()`'s only recovery path (checking
  `HAS_SAVED_STATE` and calling `restore_layout()`) was therefore
  defeated by the very registry it depends on. The gate is removed;
  `restore_all()` now walks every registered feature every time, relying
  on each feature's `restore()` already being required to be a safe
  no-op against never-applied or partial state. See `core/reversible.py`.
- **Dock-attribute-table original could be clobbered on re-apply.**
  A crash between Apply and Restore left the docked-attribute-table
  setting at `True` with no recovery record; the next Apply (in a new
  session) would have read that leaked `True` back as "the original
  value" and happily restored to it later. Both the legacy and 3.44+
  keys in `core/settings_toggles.py` now guard the original-value write
  with `if not settings.contains(original_key)`, so it is only ever
  captured once.
- **A dead dock could wedge Restore.** `DockArranger.restore_titles()`
  iterated every renamed dock and called `setWindowTitle()`
  unconditionally; if a dock's underlying QGIS C++ object had already
  been destroyed (e.g. the Processing dock disappearing because that
  plugin was disabled mid-session), the call raised `RuntimeError` and
  aborted the loop, leaving every dock after it un-restored. Now guarded
  per-dock in `core/docks.py` so one dead dock can't strand the rest.
- **Shortcut restore could destroy its own recovery record on failure.**
  `ShortcutRemap.restore()` in `core/shortcuts.py` now only clears a
  shortcut's saved-original QSettings entry once `setKeySequence()`
  actually reports success, instead of clearing it unconditionally --
  a declined restore no longer silently loses the only record of what
  still needs undoing.

### Changed

- **The Contents right-click menu integration was replaced, not patched.**
  The previous approach captured QGIS's native `QgsLayerTreeView` menu
  provider and swapped it out via `setMenuProvider()`, which "takes
  ownership" of whatever provider it's given and deletes the one before
  it -- the root cause of the 0.2.1 double-free crash, and the reason the
  0.2.0-0.3.0 docs carried a "reconstructed menu, permanent for the
  session" caveat. `core/layertree_menu.py` no longer touches the menu
  provider at all: it now uses `QgisInterface.addCustomActionForLayerType()`
  / `removeCustomActionForLayerType()`, QGIS's supported extension point for
  adding layer-tree context-menu entries additively. **The native Contents
  menu is now fully preserved** -- this plugin only ever adds one "Toggle
  Labels" entry to it and removes exactly that entry on Restore. The
  caveat in the README and QA checklist about the menu staying
  "reconstructed" after Restore is gone because the underlying limitation
  is gone; verified against
  https://qgis.org/pyqgis/master/gui/QgisInterface.html and
  `python/gui/auto_generated/qgisinterface.sip.in` on
  https://github.com/qgis/QGIS.
- **Digitizing/snapping/label toolbars are no longer hidden by Apply.**
  `mDigitizeToolBar`, `mAdvancedDigitizeToolBar`, `mSnappingToolBar`, and
  `mLabelToolBar` are excluded from `QGIS_DEFAULT_TOOLBAR_NAMES` in
  `core/constants.py` -- the replacement ribbon "Edit" group only exposes
  five actions, nowhere near the editing capability those native toolbars
  provide, and `mSnappingToolBar` was the only UI for adjusting snapping
  settings at all. Applying the workspace no longer strips editing
  capability it doesn't replace.
- **Plugin logging now surfaces inside QGIS.** A `logging.Handler`
  (`core/plugin.py`) bridges this package's stdlib `logger.exception(...)`
  / `logger.warning(...)` calls into QGIS's own Message Log panel, under
  the tag "ArcGIS-like Workspace", instead of only reaching the Python
  console. This is directly responsive to how the three inert-feature bugs
  above shipped unnoticed: `logger.exception()` calls were already present
  at every one of those call sites, but nothing surfaced them anywhere a
  reviewer or user would look.
- **Plugin-menu actions are now properly deleted on unload.** `unload()`
  in `core/plugin.py` calls `deleteLater()` on every plugin-menu `QAction`
  after detaching it, closing a leak where each action -- still parented
  to the long-lived main window with a live `triggered`/`toggled`
  connection back into the plugin instance -- pinned the whole dead
  plugin instance in memory across a Plugin Reloader cycle.
- **Locator layer-zoom is now CRS-correct.** Selecting a layer result used
  to feed the layer's own-CRS extent straight to
  `mapCanvas().setExtent()`, which produces a nonsense view whenever the
  layer and canvas CRS differ. `core/locator_filter.py` now calls
  `iface.zoomToActiveLayer()`, which performs the on-the-fly transform.
- **Dock-attribute-table key now covers 3.44+ as well as 3.28-3.40.**
  QGIS 3.44 replaced the legacy `qgis/dockAttributeTable` bool with a
  registered settings entry at
  `attribute-table/attribute-table-default-docked`
  (`QgsAttributeTableDialog::settingsAttributeTableDefaultDocked`,
  corroborated by QGIS's own 3-to-4 profile migration code, which reads
  the legacy key and writes it into the new entry). `core/settings_toggles.py`
  now writes and restores both keys unconditionally, each with its own
  saved-original; whichever key a given QGIS version doesn't read is a
  harmless no-op write.

### Added

- **"Apply at QGIS Startup"** -- a checkable entry in the plugin menu.
  When checked, the workspace preset is applied automatically once QGIS
  finishes its own startup sequence (`iface.initializationCompleted`),
  instead of every session starting back at plain QGIS and needing a
  manual Apply. The preference is stored in its own QSettings key,
  deliberately outside the `SETTINGS_PREFIX` branch that an ordinary
  Restore wipes wholesale, so restoring the workspace doesn't silently
  un-check it. See `core/plugin.py` and the README's Usage section.
- **ArcGIS-to-QGIS tool-name aliases in the locator.** Typing an Esri
  Processing-tool name now also matches its QGIS equivalent -- e.g.
  "Erase" finds Difference, "Spatial Join" finds Join Attributes by
  Location, "Dissolve" and "Buffer" match directly. See
  `ESRI_TOOL_ALIASES` in `core/locator_filter.py` for the full curated
  list, and the README's Usage section for examples.
- **`tests/`**: a fake-`qgis`-module pytest harness, so core logic can run
  and be checked outside a real QGIS install. Run with
  `python -m pytest tests/`. See the README's Development section. A
  `.gitattributes` (`tests/ export-ignore`) keeps this out of
  `git archive`-built plugin zips, matching how the plugin has always
  been packaged for plugins.qgis.org.

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
