"""The ArcGIS-Pro-inspired Qt stylesheet and its reversible apply/restore.

Colors are derived from the application palette at apply time instead of
being hard-coded: a fixed light-gray/white scheme rendered unreadable
(light text on a white ribbon) under dark or non-default palettes. The
ArcGIS Pro look comes from the structure -- flat ribbon, subtle borders,
accent-tinted hover -- which works in any palette.
"""

import logging
from typing import Dict

from .constants import OBJECT_PREFIX, STYLE_END_MARKER, STYLE_MARKER

logger = logging.getLogger(__name__)

#: Used when the palette can't be read (e.g. no QApplication yet). The
#: original light scheme.
_FALLBACK_COLORS = {
    "tabs_bg": "#f4f6f8",
    "ribbon_bg": "#ffffff",
    "border": "#c9d2dc",
    "border_soft": "#edf0f3",
    "text": "#1f2a35",
    "label": "#3e4b57",
    "hover_bg": "#e7f0fa",
    "hover_border": "#8eb4dc",
    "dock_title_bg": "#eef2f6",
}


def _mix(first, second, amount: float) -> str:
    """Blend two QColors, *amount* of the way from *first* to *second*."""
    channels = (
        round(a + (b - a) * amount)
        for a, b in (
            (first.red(), second.red()),
            (first.green(), second.green()),
            (first.blue(), second.blue()),
        )
    )
    return "#{:02x}{:02x}{:02x}".format(*channels)


def palette_colors() -> Dict[str, str]:
    """Stylesheet colors derived from the current application palette."""
    try:
        from qgis.PyQt.QtGui import QPalette
        from qgis.PyQt.QtWidgets import QApplication

        roles = getattr(QPalette, "ColorRole", QPalette)
        palette = QApplication.palette()
        window = palette.color(roles.Window)
        base = palette.color(roles.Base)
        text = palette.color(roles.WindowText)
        mid = palette.color(roles.Mid)
        highlight = palette.color(roles.Highlight)
    except Exception:
        logger.debug("ArcGIS-like Workspace: palette unavailable, using fallback colors", exc_info=True)
        return dict(_FALLBACK_COLORS)

    return {
        "tabs_bg": window.name(),
        "ribbon_bg": base.name(),
        "border": _mix(window, mid, 0.6),
        "border_soft": _mix(base, mid, 0.25),
        "text": text.name(),
        "label": _mix(text, window, 0.25),
        "hover_bg": _mix(base, highlight, 0.15),
        "hover_border": _mix(base, highlight, 0.55),
        "dock_title_bg": _mix(window, highlight, 0.06),
    }


def build_stylesheet(colors: Dict[str, str]) -> str:
    return f"""
{STYLE_MARKER}
QToolBar#{OBJECT_PREFIX}TabsToolbar {{
    background: {colors["tabs_bg"]};
    border-bottom: 1px solid {colors["border"]};
    padding: 2px 6px;
    spacing: 4px;
}}

QToolBar#{OBJECT_PREFIX}RibbonToolbar {{
    background: {colors["ribbon_bg"]};
    border-top: 1px solid {colors["border_soft"]};
    border-bottom: 1px solid {colors["border"]};
    padding: 5px 8px;
    spacing: 3px;
}}

QToolBar#{OBJECT_PREFIX}TabsToolbar QToolButton,
QToolBar#{OBJECT_PREFIX}RibbonToolbar QToolButton {{
    color: {colors["text"]};
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 4px 6px;
}}

QToolBar#{OBJECT_PREFIX}TabsToolbar QToolButton {{
    min-width: 76px;
    padding: 4px 10px;
}}

QToolBar#{OBJECT_PREFIX}TabsToolbar QToolButton:hover,
QToolBar#{OBJECT_PREFIX}RibbonToolbar QToolButton:hover,
QToolBar#{OBJECT_PREFIX}RibbonToolbar QToolButton:checked {{
    background: {colors["hover_bg"]};
    border-color: {colors["hover_border"]};
}}

QLabel#{OBJECT_PREFIX}GroupLabel {{
    color: {colors["label"]};
    font-weight: 600;
    padding: 0 8px 0 10px;
}}

QDockWidget::title {{
    background: {colors["dock_title_bg"]};
    border-bottom: 1px solid {colors["border"]};
    padding: 4px 6px;
}}
{STYLE_END_MARKER}
"""


def strip_workspace_style(stylesheet: str) -> str:
    """Remove this plugin's marker-delimited block from *stylesheet*,
    leaving everything before and after it untouched."""
    start = stylesheet.find(STYLE_MARKER)
    if start < 0:
        return stylesheet
    end = stylesheet.find(STYLE_END_MARKER, start)
    if end < 0:
        # Block written by a pre-0.4.2 version, which had no end marker and
        # always appended itself last.
        return stylesheet[:start].rstrip()
    before = stylesheet[:start].rstrip()
    after = stylesheet[end + len(STYLE_END_MARKER):].lstrip("\n")
    return f"{before}\n{after}" if before and after else before or after


class StylesheetManager:
    """Applies and reversibly removes the ArcGIS-like stylesheet on the main window.

    Restore cuts out only this plugin's marker-delimited block instead of
    reinstating a snapshot taken at Apply time, so a stylesheet change made
    by someone else in between (another plugin, a theme switch) survives.
    """

    def __init__(self, window):
        self.window = window

    def apply(self):
        """Append the ArcGIS-like Qt stylesheet to the main window. Re-apply
        replaces the previous block (re-reading the palette) instead of
        stacking a second copy."""
        current = strip_workspace_style(self.window.styleSheet())
        block = build_stylesheet(palette_colors())
        self.window.setStyleSheet(f"{current}\n{block}" if current else block)

    def restore(self):
        """Remove the workspace stylesheet block, if present."""
        current = self.window.styleSheet()
        stripped = strip_workspace_style(current)
        if stripped != current:
            self.window.setStyleSheet(stripped)
