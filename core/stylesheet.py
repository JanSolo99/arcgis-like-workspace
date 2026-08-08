"""The ArcGIS-Pro-inspired Qt stylesheet and its reversible apply/restore."""

from typing import Optional

from .constants import OBJECT_PREFIX, STYLE_MARKER

ARC_STYLE = f"""
{STYLE_MARKER}
QToolBar#{OBJECT_PREFIX}TabsToolbar {{
    background: #f4f6f8;
    border-bottom: 1px solid #c9d2dc;
    padding: 2px 6px;
    spacing: 4px;
}}

QToolBar#{OBJECT_PREFIX}RibbonToolbar {{
    background: #ffffff;
    border-top: 1px solid #edf0f3;
    border-bottom: 1px solid #bbc7d4;
    padding: 5px 8px;
    spacing: 3px;
}}

QToolBar#{OBJECT_PREFIX}TabsToolbar QToolButton,
QToolBar#{OBJECT_PREFIX}RibbonToolbar QToolButton {{
    border: 1px solid transparent;
    border-radius: 3px;
    min-width: 68px;
    padding: 4px 6px;
}}

QToolBar#{OBJECT_PREFIX}TabsToolbar QToolButton {{
    min-width: 76px;
    padding: 4px 10px;
}}

QToolBar#{OBJECT_PREFIX}TabsToolbar QToolButton:hover,
QToolBar#{OBJECT_PREFIX}RibbonToolbar QToolButton:hover {{
    background: #e7f0fa;
    border-color: #8eb4dc;
}}

QLabel#{OBJECT_PREFIX}GroupLabel {{
    color: #3e4b57;
    font-weight: 600;
    padding: 0 8px 0 10px;
}}

QDockWidget::title {{
    background: #eef2f6;
    border-bottom: 1px solid #c9d2dc;
    padding: 4px 6px;
}}
"""


class StylesheetManager:
    """Applies and reversibly removes the ArcGIS-like stylesheet on the main window."""

    def __init__(self, window):
        self.window = window
        self.previous_stylesheet: Optional[str] = None

    def apply(self):
        """Append the ArcGIS-like Qt stylesheet to the main window (idempotent)."""
        if self.previous_stylesheet is None:
            self.previous_stylesheet = self.window.styleSheet()

        current = self.window.styleSheet()
        if STYLE_MARKER not in current:
            self.window.setStyleSheet(f"{current}\n{ARC_STYLE}")

    def restore(self):
        """Remove the workspace stylesheet, restoring the previously saved one."""
        if self.previous_stylesheet is not None:
            self.window.setStyleSheet(self.previous_stylesheet)
            self.previous_stylesheet = None
            return

        current: str = self.window.styleSheet()
        marker_index: int = current.find(STYLE_MARKER)
        if marker_index < 0:
            return  # stylesheet was already removed or never applied
        self.window.setStyleSheet(current[:marker_index].rstrip())
