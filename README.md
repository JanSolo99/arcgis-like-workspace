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
  tools, with Edit/Selection groups shown or hidden based on the active
  layer's type (vector vs. raster), mirroring ArcGIS Pro's contextual
  ribbon tabs.
- **Dock arrangement** — "Contents" pane on the left; stacked "Catalog" /
  "Geoprocessing" / "Symbology" / "Identify Results" panes on the right;
  "Log Messages" at the bottom (hidden by default). All native QGIS docks,
  just repositioned and renamed.
- **ArcGIS-inspired stylesheet** — light-gray toolbar backgrounds, subtle
  borders, and compact buttons.

**Behavior**

- **Docked attribute tables** and a **more generous default snapping
  configuration** (vertex + segment, ~12px tolerance) for the current
  project — both flip an existing native QGIS setting rather than adding
  new UI.
- **One-click Labeling toggle** on the Contents right-click menu.
- **Notifications dock** — a bell-style toggle showing an unread count,
  aggregating background task events and warning/critical log messages.
- **Unified locator** — search layers, geoprocessing tools, and bookmarks
  in one query via QGIS's native locator bar (`Ctrl+K`), plus a "Find"
  button that focuses it.
- **Opt-in keyboard shortcut remap** toward ArcGIS Pro conventions, kept
  separate from the main preset and collision-safe (see Usage below).

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
| **About**                                 | **Plugins → ArcGIS-like Workspace → About This Workspace**         |
| **Notifications**                         | Bell button on the tab toolbar (shows an unread count when hidden) |
| **Find (layers, tools, bookmarks)**       | "Find" button on the tab toolbar, or QGIS's native `Ctrl+K`        |
| **Toggle Labels**                         | Right-click a layer in Contents                                    |
| **Apply ArcGIS-like Shortcuts (opt-in)**  | **Plugins → ArcGIS-like Workspace** menu — separate from the main preset, see below |
| **Restore Original Shortcuts**            | **Plugins → ArcGIS-like Workspace** menu                           |

The main workspace preset is automatically restored when the plugin is
disabled or QGIS is closed (provided it was previously applied in that
session). The opt-in shortcut remap has its own explicit Restore action
because it persists directly to QGIS's own settings the moment it's
applied — see the note in `core/shortcuts.py` — but disabling the plugin
will still restore it automatically as a safety net if you forget.

**One exception to "fully reversible":** the Contents right-click menu
switches to this plugin's own reconstructed menu (zoom, rename, remove,
feature count, plus Toggle Labels/Layer Properties while applied) the
first time you click Apply, and stays that way for the rest of the QGIS
session even after Restore — QGIS's `setMenuProvider()` API doesn't
support safely handing the original native menu back. See the note in
`core/layertree_menu.py` for why.

## Compatibility

- **QGIS 3.28 – 4.x**
- **Qt 5 and Qt 6** (uses runtime enum lookup to avoid binding-specific imports)
- The 0.2.0 behavioral features use additional PyQGIS surface beyond 0.1.0's
  toolbar/dock/stylesheet APIs — `QgsLocatorFilter`, `QgsShortcutsManager`,
  `QgsLayerTreeViewMenuProvider`, `QgsTaskManager`, `QgsSnappingConfig` —
  checked against the `qgisMinimumVersion=3.28` floor, but not yet verified
  against a real QGIS install in every point release; see `QA_CHECKLIST.md`.

## License

[MIT](LICENSE)
