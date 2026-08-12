# Manual QA Checklist

This plugin has no local QGIS install available in its development
environment, so nothing in `core/` has ever been executed against real
QGIS APIs from this repo's own tooling. `python -m py_compile` and
`python -m pyflakes` pass on every file, `python -m pytest tests/` passes
against the fake-`qgis`-module harness in `tests/`, and every new PyQGIS
class/method name is checked against QGIS documentation or source where
possible — but none of that is a substitute for running the plugin in a
real QGIS session. The 0.4.0 release is a pointed reminder why: three
features that passed every one of those static checks (shortcut remap,
segment snapping, the Find button) turned out to be silently inert, each
because of a call-shape mistake that only running the code and checking
its *result* — not just the absence of an exception — could have caught.
Run through this checklist there before trusting a release.

## Before you start

- [ ] Install into a QGIS 3.28+ profile (ideally a spare/test profile —
      Settings ▸ User Profiles — so this doesn't touch your main setup).
- [ ] Optionally run `python -m pytest tests/` first, outside QGIS, as a
      fast smoke check — it only exercises what the fake `qgis` module
      models, so a pass here is not a substitute for anything below.
- [ ] Open QGIS's **Log Messages** panel (View ▸ Panels ▸ Log Messages —
      this plugin also arranges it at the bottom of the layout, hidden by
      default, once applied) and watch it throughout, filtered to the
      **"ArcGIS-like Workspace"** tab/tag if the panel supports filtering.
      As of 0.4.0 this plugin's own `logger.warning(...)`/
      `logger.exception(...)` calls are bridged there — previously they
      only ever reached the Python Console, which is how the 0.4.0 inert-
      feature bugs shipped unnoticed despite already having logging calls
      at the right places. Keep the Python Console open too (Plugins ▸
      Python Console) for any uncaught exception that occurs outside a
      `logger.exception(...)` call.

## Core workspace (regression check against 0.1.0 behavior)

- [ ] **Apply ArcGIS-like Workspace** — tab toolbar and ribbon toolbar
      appear; Contents/Catalog/Geoprocessing/Symbology docks are
      arranged and renamed **on the very first click** (Browser in
      particular starts tabbed with Layers in a stock install and was
      the one that needed a second Apply before 0.4.1 — see
      `DockArranger._move_dock` if it regresses); stylesheet is applied;
      default QGIS toolbars are hidden. **Also confirm the Digitizing,
      Advanced Digitizing, Snapping, and Label toolbars stay visible** —
      as of 0.4.0 Apply no longer hides them (the ribbon's Edit group
      doesn't cover their capability; see `core/constants.py`).
- [ ] **Restore Previous QGIS Workspace** — toolbars removed, dock
      titles reverted, stylesheet reverted, original window
      geometry/state restored.
- [ ] **Reset to Default QGIS Workspace** — first, manually hide a
      couple of QGIS's default toolbars (e.g. Layer, Digitizing) and
      Apply, so your "prior layout" has some hidden toolbars. Click
      Reset: confirm this plugin's toolbars/stylesheet are removed
      *and* the manually-hidden default-visible toolbars (Layer, etc.)
      come back too (unlike Restore, which would have left them
      hidden). **Then also confirm the toolbars QGIS itself hides by
      default — Advanced Digitizing, Digitizing, Snapping, Label,
      Database, Web, Raster, Vector, Annotations, Plugins, Help, Mesh/
      Shape Digitizing — end up hidden after Reset, even if you'd
      manually shown one of them first.** Before 0.4.1, Reset forced
      every known toolbar visible regardless of QGIS's real defaults —
      confirm this doesn't regress. Confirm the Contents and Catalog/
      Browser panels are visible afterward.

## New features (exercise each once after Apply)

- [ ] **Dock attribute tables** — open any layer's attribute table;
      confirm it opens docked, not as a separate floating window. If it
      still floats, the `DOCK_ATTRIBUTE_TABLE_KEY` /
      `DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY` guesses in
      `settings_toggles.py` need correcting for your QGIS version (see
      the comments there for how to find the real key via the Python
      console). Both a pre-3.44-style and a 3.44+-style key are written;
      only one will matter on any given install.
- [ ] **Snapping defaults** — Project ▸ Snapping Options; confirm
      snapping is enabled with a ~12px tolerance, **and confirm both
      vertex and segment snapping are actually active** (hover the
      cursor near the middle of an edge, not just on a vertex, and
      confirm it snaps too). 0.3.0 had a wrong `Qgis.SnappingType` enum
      spelling that silently left segment snapping off even though
      Snapping Options looked correctly configured — this is a direct
      regression check for that fix.
- [ ] **Labeling toggle** — right-click a vector layer in Contents;
      confirm QGIS's **real, native** context menu appears (export,
      duplicate, set CRS, zoom to layer, and every other entry you'd
      normally see) with a single extra **"Toggle Labels"** entry added
      to it, and that it actually works. As of 0.4.0 this is added via
      `QgisInterface.addCustomActionForLayerType()`, which appends to the
      native menu rather than replacing it — if any native entry is
      missing, that's a regression, not expected behavior.
- [ ] **Identify Results / Log Messages docks** — confirm both appear
      renamed and repositioned (Identify Results tabbed on the right;
      Log Messages at the bottom, hidden until opened via View ▸
      Panels).
- [ ] **Contextual ribbon** — select a vector layer: Edit/Selection
      ribbon groups appear. Select a raster layer (or no layer): they
      disappear. Switch back and forth a few times.
- [ ] **Notifications dock** — trigger a warning (e.g. an invalid
      expression in the Field Calculator) and run a background task
      (e.g. a Processing algorithm); confirm entries appear and the bell
      button's label shows an unread count while the dock is hidden,
      clearing when opened.
- [ ] **Locator — basic search** — press `Ctrl+K` (or click the "Find"
      button — see below), type a few characters of a loaded layer's
      name, a Processing algorithm's name, and a bookmark's name;
      confirm results from all three appear and that selecting one does
      the right thing (activates/zooms to the layer, opens the algorithm
      dialog, or zooms to the bookmark).
- [ ] **Locator — CRS-correct layer zoom** — load or reproject a layer
      into a CRS different from the project's CRS, search for it via the
      locator, and select the result. Confirm it zooms to the layer's
      actual extent, not somewhere nonsensical — 0.3.0 fed the layer's
      own-CRS extent straight to the canvas without transforming it;
      0.4.0 uses `iface.zoomToActiveLayer()` instead.
- [ ] **Locator — ArcGIS tool-name aliases** — type an Esri tool name
      that has no literal match in QGIS's own algorithm names, e.g.
      `erase`, `spatial join`, or `feature to point`. Confirm the
      corresponding QGIS algorithm (Difference, Join Attributes by
      Location, Centroids) appears, labelled "Geoprocessing Tool
      (ArcGIS: …)". See `ESRI_TOOL_ALIASES` in `core/locator_filter.py`
      for the full list.
- [ ] **Find button** — click the "Find" button on the tab toolbar (not
      `Ctrl+K` this time); confirm it actually opens/focuses the native
      locator bar. This button was **silently inert in 0.3.0** — it
      called a `QgsGui` method that has never existed on any QGIS
      version, so clicking it did nothing and raised nothing. 0.4.0
      finds the native `QgsLocatorWidget` via `findChild()` instead;
      this is a direct regression check for that fix.
- [ ] **Shortcuts (opt-in)** — separately, run **Apply ArcGIS-like
      Shortcuts**; confirm `Del` deletes the selected feature(s) and
      `Ctrl+B` creates a new bookmark. **These were silently inert in
      0.3.0** — `setKeySequence()` was called with a `QKeySequence`
      object instead of the plain string it actually requires, so the
      action reported no error while never rebinding anything; this is a
      direct regression check for that fix. Run **Restore Original
      Shortcuts**; confirm both revert. Try applying twice in a row
      (should be a safe no-op the second time) and pre-customizing one
      of the two shortcuts yourself before Apply (should be skipped,
      not overwritten).
- [ ] **Apply at QGIS Startup** — check this menu entry, then fully
      restart QGIS (not just reload the plugin). Confirm the workspace
      preset applies itself automatically once QGIS finishes starting,
      with no manual Apply click needed. Uncheck it, restart QGIS again,
      and confirm it does *not* auto-apply this time.

## Reversibility

- [ ] **Restore** after exercising every feature above — confirm
      everything reverts, not just the original four (toolbars/docks/
      stylesheet/window state).
- [ ] **Re-apply immediately after Restore — Apply → Restore → Apply
      again, right-click a layer in Contents each time.** This exact
      sequence used to instantly crash QGIS in 0.2.0 (a double-free in
      `QgsLayerTreeView::setMenuProvider()`, fixed in 0.2.1) and, after
      that fix, could still leave a stale post-crash state unrecovered
      in a fresh session (fixed in 0.4.0 — see `CHANGELOG.md` for both).
      Confirm no crash, and no duplicate docks, menu entries, ribbon
      groups, notifications-dock instances, or locator-filter
      registrations — and confirm the Contents right-click menu still
      shows exactly one "Toggle Labels" entry, not two.
- [ ] **Crash recovery across sessions** — Apply the workspace, then
      force-quit QGIS (kill the process; don't click Restore or close it
      normally) to simulate a crash. Reopen QGIS with the same profile,
      then disable this plugin from the Plugin Manager *without* clicking
      Apply first. Confirm `unload()` detects the leftover saved state
      from the killed session and actually restores it — toolbars/docks/
      stylesheet/window geometry all back to normal. 0.3.0's
      `FeatureRegistry` tracked an in-memory "was this applied" gate that
      a fresh process's empty registry always failed, silently skipping
      every `restore_fn` in exactly this scenario; fixed in 0.4.0.
- [ ] **Dock-attribute-table original survives a crash-then-reapply** —
      repeat the crash simulation above (Apply, force-quit, reopen), but
      this time click **Apply** again in the new session instead of
      disabling the plugin, then **Restore**. Confirm "Open attribute
      table as docked window" ends up back at its true pre-plugin
      original, not stuck on `True`. 0.3.0 could record the plugin's own
      leaked `True` from the killed session as the "original" the next
      time Apply ran, permanently losing the real original; 0.4.0 guards
      that write so it only ever happens once.
- [ ] **A dead dock during Restore** — with the workspace applied,
      disable another plugin that owns one of the arranged docks (e.g.
      the core Processing plugin) via the Plugin Manager, then click
      Restore. Confirm no error aborts the process and every *other*
      dock's title still restores correctly, even though one dock's
      underlying object is now gone.
- [ ] **Disable the plugin without clicking Restore first** — confirm
      `unload()` fully reverses the workspace *and* the shortcut remap
      (if it was applied and not manually restored).
- [ ] **Re-enable and Apply again** — confirm no stale state or
      duplicated widgets from the previous cycle.
- [ ] **Reload the plugin several times in a row** (Plugin Reloader
      plugin) without restoring in between — watch the Log Messages
      panel (tag "ArcGIS-like Workspace") and Python console for a
      handler firing multiple times per layer-selection change (the
      signal-leak class the `ConnectionTracker`/re-sync-on-apply design
      in `contextual_ribbon.py` and `notifications.py` is meant to
      prevent).
- [ ] **Close and reopen QGIS** with the workspace applied — confirm a
      clean state on reopen (no leftover plugin toolbars/docks from a
      crashed or force-closed prior session).
