"""Qt5/Qt6 and QGIS 3/4 compatibility helpers.

Centralizes the runtime enum lookups needed to support both Qt bindings and
both QGIS major versions without relying on compatibility aliases that may
be removed in a future release.
"""

from typing import Any

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QToolButton
from qgis.core import Qgis


def qt_enum(legacy_name: str, enum_group: str) -> Any:
    """Return a Qt 5 or Qt 6 enum value without relying on compatibility aliases."""
    legacy_value = getattr(Qt, legacy_name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(getattr(Qt, enum_group), legacy_name)


def widget_enum(widget_class: type, legacy_name: str, enum_group: str) -> Any:
    """Return a Qt 5 or Qt 6 widget enum value."""
    legacy_value = getattr(widget_class, legacy_name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(getattr(widget_class, enum_group), legacy_name)


def qgis_message_level(name: str) -> Any:
    """Return a QGIS 3 or QGIS 4 message level."""
    legacy_value = getattr(Qgis, name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(Qgis.MessageLevel, name)


def qgis_enum(container: Any, legacy_name: str, enum_group: str) -> Any:
    """Return a QGIS enum value tolerant of pre/post-refactor enum locations.

    Several QGIS enums (snapping types/units, message levels) moved from a
    flat legacy attribute on their container class into a nested enum group
    during the Qt6/QGIS-4 migration. Mirrors qt_enum()/widget_enum() above.
    """
    legacy_value = getattr(container, legacy_name, None)
    if legacy_value is not None:
        return legacy_value
    return getattr(getattr(container, enum_group), legacy_name)


TOOL_BUTTON_TEXT_UNDER_ICON = qt_enum("ToolButtonTextUnderIcon", "ToolButtonStyle")
TOOL_BUTTON_TEXT_BESIDE_ICON = qt_enum("ToolButtonTextBesideIcon", "ToolButtonStyle")
TOP_TOOLBAR_AREA = qt_enum("TopToolBarArea", "ToolBarArea")
BOTTOM_DOCK_WIDGET_AREA = qt_enum("BottomDockWidgetArea", "DockWidgetArea")
LEFT_DOCK_WIDGET_AREA = qt_enum("LeftDockWidgetArea", "DockWidgetArea")
RIGHT_DOCK_WIDGET_AREA = qt_enum("RightDockWidgetArea", "DockWidgetArea")
INSTANT_POPUP = widget_enum(QToolButton, "InstantPopup", "ToolButtonPopupMode")

QGIS_INFO = qgis_message_level("Info")
QGIS_WARNING = qgis_message_level("Warning")
QGIS_CRITICAL = qgis_message_level("Critical")
