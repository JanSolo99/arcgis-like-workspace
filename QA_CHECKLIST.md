# Manual QA Checklist

This plugin has no automated test suite and this development environment
has no local QGIS install, so nothing in `core/` has been executed against
real QGIS APIs. `python -m py_compile` and `python -m pyflakes` pass on every
file, and every new PyQGIS class/method name was checked against QGIS
documentation where possible, but genuine version-specific API behavior
(exact `QSettings` key names, signal thread affinity, snapping/locator enum
locations) can only be confirmed by running the plugin in a real QGIS
session. Run through this checklist there before trusting a release.

## Before you start

- [ ] Install into a QGIS 3.28+ profile (ideally a spare/test profile —
      Settings ▸ User Profiles — so this doesn't touch your main setup).
- [ ] Open the Python Console (Plugins ▸ Python Console) and watch it
      throughout — it's the only place uncaught exceptions and this
      plugin's `logger.exception(...)` calls will surface.

## Core workspace (regression check against 0.1.0 behavior)

- [ ] **Apply ArcGIS-like Workspace** — tab toolbar and ribbon toolbar
      appear; Contents/Catalog/Geoprocessing/Symbology docks are
      arranged and renamed; stylesheet is applied; default QGIS
      toolbars are hidden.
- [ ] **Restore Previous QGIS Workspace** — toolbars removed, dock
      titles reverted, stylesheet reverted, original window
      geometry/state restored.

## New features (exercise each once after Apply)

- [ ] **Dock attribute tables** — open any layer's attribute table;
      confirm it opens docked, not as a separate floating window. If it
      still floats, the `DOCK_ATTRIBUTE_TABLE_KEY` guess in
      `settings_toggles.py` needs correcting (see the comment there for
      how to find the real key via the Python console).
- [ ] **Snapping defaults** — Project ▸ Snapping Options; confirm
      snapping is enabled with a ~12px vertex+segment tolerance on the
      currently open project.
- [ ] **Labeling toggle** — right-click a vector layer in Contents;
      confirm a reconstructed context menu appears (zoom to layer,
      rename, remove, show feature count, then a separator, "Toggle
      Labels", and "Layer Properties...") and that Toggle Labels and
      Layer Properties actually work. This is a **deliberately
      reconstructed** menu, not QGIS's exact native one — see the
      "Contents right-click menu" note below for why, and don't be
      alarmed that a few native-only entries (export, duplicate, set
      CRS, etc.) aren't present.
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
- [ ] **Locator** — press `Ctrl+K` (or click the "Find" button), type a
      few characters of a loaded layer's name, a Processing algorithm's
      name, and a bookmark's name; confirm results from all three
      appear and that selecting one does the right thing (activates/
      zooms to the layer, opens the algorithm dialog, or zooms to the
      bookmark).
- [ ] **Shortcuts (opt-in)** — separately, run **Apply ArcGIS-like
      Shortcuts**; confirm `Del` deletes the selected feature(s) and
      `Ctrl+B` creates a new bookmark. Run **Restore Original
      Shortcuts**; confirm both revert. Try applying twice in a row
      (should be a safe no-op the second time) and pre-customizing one
      of the two shortcuts yourself before Apply (should be skipped,
      not overwritten).

## Reversibility

- [ ] **Restore** after exercising every feature above — confirm
      everything reverts, not just the original four (toolbars/docks/
      stylesheet/window state).
- [ ] **Re-apply immediately after Restore — Apply → Restore → Apply
      again, right-click a layer in Contents each time.** This exact
      sequence used to instantly crash QGIS (a double-free in
      `QgsLayerTreeView::setMenuProvider()` caused by trying to hand the
      native menu provider back to QGIS on Restore — see the docstring
      at the top of `core/layertree_menu.py`). Confirm no crash, and no
      duplicate docks, menu entries, ribbon groups, notifications-dock
      instances, or locator-filter registrations.
- [ ] **Disable the plugin without clicking Restore first** — confirm
      `unload()` fully reverses the workspace *and* the shortcut remap
      (if it was applied and not manually restored).
- [ ] **Re-enable and Apply again** — confirm no stale state or
      duplicated widgets from the previous cycle.
- [ ] **Reload the plugin several times in a row** (Plugin Reloader
      plugin) without restoring in between — watch the Python console
      for a handler firing multiple times per layer-selection change
      (the signal-leak class the `ConnectionTracker`/re-sync-on-apply
      design in `contextual_ribbon.py` and `notifications.py` is meant
      to prevent).
- [ ] **Close and reopen QGIS** with the workspace applied — confirm a
      clean state on reopen (no leftover plugin toolbars/docks from a
      crashed or force-closed prior session).

## Note: Contents right-click menu (permanent for the session)

QGIS's `setMenuProvider()` API takes ownership of whatever provider it's
given and deletes the previous one — there's no supported way to install
a custom provider and later hand the *original native one* back. Because
of that, once you click **Apply** for the first time in a QGIS session,
the Contents right-click menu switches to this plugin's reconstructed
menu (zoom, rename, remove, feature count, plus Toggle Labels/Layer
Properties while applied) and **stays that way even after Restore**,
until QGIS is restarted. This is an intentional, unavoidable tradeoff to
eliminate the crash above, not a bug — see `core/layertree_menu.py`'s
module docstring for the full explanation.
