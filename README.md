# ArcGIS-like Workspace for QGIS

A QGIS plugin that applies an **ArcGIS Pro-inspired workspace preset** using
native QGIS actions, toolbars, dock widgets, and Qt styling — no Esri assets,
branding, or proprietary UI code.

![QGIS version](https://img.shields.io/badge/QGIS-3.28%2B-brightgreen)

## What It Does

- **Tab toolbar** — drop-down menus grouped by functional area (Project, Map,
  Insert, Edit, Analysis, View), similar to ArcGIS Pro's ribbon tabs.
- **Ribbon toolbar** — icon+label action groups for quick access to common
  tools.
- **Dock arrangement** — "Contents" pane on the left, and stacked "Catalog" /
  "Geoprocessing" / "Symbology" panes on the right.
- **ArcGIS-inspired stylesheet** — light-gray toolbar backgrounds, subtle
  borders, and compact buttons.
- **Fully reversible** — one-click restore returns QGIS to its previous layout,
  dock positions, and stylesheet.

## Installation

1. Copy the `arcgis_like_workspace` folder into your QGIS plugin directory:
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS.
3. Enable the plugin via **Plugins → Manage and Install Plugins → Installed**.

## Usage

| Action                              | Where to find it                                                |
|-------------------------------------|------------------------------------------------------------------|
| **Apply ArcGIS-like Workspace**     | Toolbar icon or **Plugins → ArcGIS-like Workspace** menu         |
| **Restore Previous QGIS Workspace** | "Restore" button on the tab toolbar, or the plugin menu          |
| **About**                           | **Plugins → ArcGIS-like Workspace → About This Workspace**       |

The workspace is also automatically restored when the plugin is disabled or
QGIS is closed (provided the workspace was previously applied in that session).

## Compatibility

- **QGIS 3.28 – 4.x**
- **Qt 5 and Qt 6** (uses runtime enum lookup to avoid binding-specific imports)

## License

[MIT](LICENSE)
