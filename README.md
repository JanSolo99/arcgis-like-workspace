# ArcGIS-like Workspace for QGIS

A QGIS plugin that applies an **ArcGIS Pro-inspired workspace preset** —
layout, styling, and genuine behavioral parity — using native QGIS actions,
toolbars, dock widgets, settings, and Qt styling. No Esri assets, branding,
or proprietary UI code.

![QGIS version](https://img.shields.io/badge/QGIS-3.28%2B-brightgreen)

## What It Does

**Layout and styling**

- **Tab toolbar** — drop-down menus grouped by functional area (Project, Map,
  Insert, Edit, Analysis, View), similar to ArcGIS Pro's ribbon tabs.
- **Ribbon toolbar** — icon+label action groups for quick access to common
  tools (including **Add Data**, QGIS's Data Source Manager), with
  Edit/Selection groups shown or hidden based on the active layer's type
  (vector vs. raster), mirroring ArcGIS Pro's contextual ribbon tabs. The
  tab and ribbon toolbars each get their own row at the top of the window.
- **Contextual native toolbars** — QGIS's Digitizing and Snapping toolbars
  appear only while the active vector layer is being edited, and the
  Labeling toolbar only while a vector layer is active, the way Pro only
  surfaces editing tools in context.
- **Dock arrangement** — "Contents" pane on the left; stacked "Catalog" /
  "Geoprocessing" / "Symbology" / "Identify Results" panes on the right;
  "Log Messages" at the bottom (hidden by default). All native QGIS docks,
  just repositioned and renamed.
- **ArcGIS-inspired stylesheet** — flat ribbon, subtle borders, and
  accent-tinted hover, with colors taken from your current Qt palette so it
  stays readable in dark themes too.

**Behavior**

- **Docked attribute tables** and a **more generous default snapping
  configuration** (vertex + segment, ~12px tolerance) for the current
  project — both flip an existing native QGIS setting rather than adding
  new UI.
- **One-click Labeling toggle** on the Contents right-click menu, added
  additively via QGIS's supported `addCustomActionForLayerType()` API —
  the rest of the native menu (export, duplicate, set CRS, etc.) is
  untouched.
- **Notifications dock** — a toggle whose icon carries a painted unread-count badge,
  aggregating background task events and warning/critical log messages.
- **ArcGIS tool names in search** — QGIS's native locator bar (`Ctrl+K`)
  already finds layers, bookmarks, and geoprocessing tools; this adds
  ArcGIS Pro tool names as aliases for their QGIS Processing equivalent
  (e.g. typing "Erase" finds Difference), plus a "Find" button that focuses
  the locator bar — see Usage below.
- **Opt-in keyboard shortcut remap** toward ArcGIS Pro conventions, kept
  separate from the main preset and collision-safe (see Usage below).
- **Apply at QGIS Startup** — an opt-in checkable menu option that
  re-applies the workspace preset automatically once QGIS finishes
  starting up, instead of every session beginning at plain QGIS (see
  Usage below).

**Reversibility**

- **Fully reversible** — one-click restore returns QGIS to its previous layout,
  dock positions, settings, and stylesheet. Disabling the plugin reverses
  everything automatically, including the shortcut remap if it was never
  manually restored.

## Terminology

This plugin relabels a few native QGIS panels to their ArcGIS Pro names
(Layers → **Contents**, Browser → **Catalog**, Processing → **Geoprocessing**,
Layer Styling → **Symbology**) since the underlying panels already do the
same job. It does **not** change QGIS's underlying project model to match
ArcGIS Pro's: a QGIS **Project** is still one map canvas plus separate print
layouts, not ArcGIS Pro's container of multiple named **Maps** and layouts in
a single `.aprx`. If you're coming from ArcGIS Pro, expect the panel names
and many workflows to feel familiar — expect the project/map structure
itself to still be QGIS's.

## Installation

1. Copy the `arcgis_like_workspace` folder into your QGIS plugin directory:
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS.
3. Enable the plugin via **Plugins → Manage and Install Plugins → Installed**.

## Usage

| Action                                   | Where to find it                                                  |
|-------------------------------------------|--------------------------------------------------------------------|
| **Apply ArcGIS-like Workspace**           | Toolbar icon or **Plugins → ArcGIS-like Workspace** menu           |
| **Restore Previous QGIS Workspace**       | "Restore" button on the tab toolbar, or the plugin menu            |
| **Reset to Default QGIS Workspace**       | "Reset to Default" button on the tab toolbar, or the plugin menu — a stronger reset than Restore, see below |
| **About**                                 | **Plugins → ArcGIS-like Workspace → About This Workspace**         |
| **Notifications**                         | Notifications button on the tab toolbar (paints an unread count on its icon while hidden) |
| **Find (layers, tools, bookmarks, ArcGIS tool names)** | "Find" button on the tab toolbar, or QGIS's native `Ctrl+K` |
| **Toggle Labels**                         | Right-click a layer in Contents                                    |
| **Apply ArcGIS-like Shortcuts (opt-in)**  | **Plugins → ArcGIS-like Workspace** menu — separate from the main preset, see below |
| **Restore Original Shortcuts**            | **Plugins → ArcGIS-like Workspace** menu                           |
| **Apply at QGIS Startup (opt-in)**        | Checkable entry in **Plugins → ArcGIS-like Workspace** menu — see below |

The main workspace preset is automatically restored when the plugin is
disabled or QGIS is closed (provided it was previously applied in that
session). The opt-in shortcut remap has its own explicit Restore action
because it persists directly to QGIS's own settings the moment it's
applied — see the note in `core/shortcuts.py` — but disabling the plugin
will still restore it automatically as a safety net if you forget.

**ArcGIS tool-name aliases in Find:** typing an Esri Processing-tool name
into Find/`Ctrl+K` also matches its QGIS equivalent, labelled "Geoprocessing
Tool (ArcGIS: …)" in the results — e.g. "Erase" finds Difference, "Spatial
Join" finds Join Attributes by Location, "Feature to Point" finds Centroids,
and "Calculate Field" finds Field Calculator. The full curated list is
`ESRI_TOOL_ALIASES` in `core/locator_filter.py`; it's a hand-picked,
non-exhaustive set, not a full ArcGIS-to-QGIS tool mapping.

**Apply at QGIS Startup:** check this once and the workspace preset applies
itself automatically the next time (and every time after that) QGIS
finishes starting up, instead of needing a manual Apply click every
session. It's stored outside the settings branch an ordinary Restore
wipes, so restoring the workspace mid-session doesn't silently un-check
it — uncheck it yourself, from the same menu, to turn auto-apply back off.

**Restore vs. Reset to Default:** Restore returns QGIS to *your* layout
as it was right before you clicked Apply — if you'd already hidden some
toolbars yourself, Restore brings back that same customized state.
**Reset to Default QGIS Workspace** goes further: it undoes this
plugin's changes the same way Restore does, then additionally resets
every known QGIS toolbar to its true stock-install visibility (most of
them — Digitizing, Snapping, Database, Raster, Vector, and a dozen
others — are hidden in a default QGIS install; only Attributes, Manage
Layers, Map Navigation, Project, and Selection are shown out of the
box) and shows the core Contents/Catalog panels, regardless of what
your layout looked like before. Panel *positions* aren't part of this
— QGIS's exact default layout is hardcoded at application startup and
isn't something a plugin can replay on demand, so a pixel-perfect
factory reset still needs a QGIS restart.

The Contents right-click menu itself is QGIS's real, native menu, untouched
— this plugin only adds one "Toggle Labels" entry to it (via
`QgisInterface.addCustomActionForLayerType()`) and removes exactly that
entry on Restore. Earlier releases (0.2.1–0.3.0) carried a caveat here
about the menu staying "reconstructed" after Restore; that was a symptom
of an unsafe `setMenuProvider()`-based approach that has since been
replaced entirely — see `CHANGELOG.md`'s 0.4.0 entry and the module
docstring in `core/layertree_menu.py`.

## Compatibility

- **QGIS 3.28 – 4.x**
- **Qt 5 and Qt 6** (uses runtime enum lookup to avoid binding-specific imports)
- The 0.2.0+ behavioral features use additional PyQGIS surface beyond
  0.1.0's toolbar/dock/stylesheet APIs — `QgsLocatorFilter`,
  `QgsShortcutsManager`, `QgisInterface.addCustomActionForLayerType()`,
  `QgsTaskManager`, `QgsSnappingConfig` — checked against the
  `qgisMinimumVersion=3.28` floor and, where version-sensitive, resolved at
  runtime via the compat-candidate helpers in `core/compat.py` rather than
  a single hardcoded spelling. Still not verified against a real QGIS
  install in every point release; see `QA_CHECKLIST.md`.

## Development / Testing

`tests/` contains a pytest harness built around a fake `qgis` module, so
the plugin's core logic can be exercised without a real QGIS install:

```
python -m pytest tests/
```

It's a unit-level safety net, not a substitute for `QA_CHECKLIST.md` — it
can't catch a wrong PyQGIS call shape that the fakes don't model (exactly
the class of bug behind three of the fixes in the 0.4.0 changelog entry).
Run it before every release alongside `python -m py_compile` and
`python -m pyflakes` on every changed file. `tests/` itself is excluded
from packaged plugin zips (`.gitattributes`, `git archive`).

## License

[MIT](LICENSE)
