"""Qt5/Qt6 and QGIS 3/4 compatibility helpers.

Centralizes the runtime enum lookups needed to support both Qt bindings and
both QGIS major versions without relying on compatibility aliases that may
be removed in a future release.
"""

from typing import Any, List, Sequence, Tuple

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


def qgis_enum_candidates(candidates: Sequence[Tuple[Any, str]]) -> Any:
    """Return the first resolvable value from an ordered list of enum spellings.

    Some QGIS enums (e.g. snapping types, tolerance units) have moved container
    *and* changed shape across the 3.28-4.x range this plugin supports -- more
    than the flat-vs-nested move that qgis_enum() above handles. A single
    (container, enum_group) pair isn't enough to describe "try Qgis.MapToolUnit,
    and if that container attribute doesn't even exist yet, fall back to
    QgsTolerance.UnitType". This is for that case.

    Each candidate is a (container, dotted_attr_path) pair, e.g.
    ``(Qgis, "SnappingType.Vertex")``, resolved via successive getattr() calls
    starting from container. A candidate whose container is None (e.g. a class
    only importable on some QGIS versions) is skipped rather than erroring.

    Returns the first candidate that resolves. Raises AttributeError, with
    every attempted spelling listed, if none do -- callers should wrap the
    call in the same try/except-log pattern used for every other native-API
    call in this plugin, so a future QGIS rename degrades to a logged failure
    for that one feature rather than an unload-blocking crash.
    """
    attempted: List[str] = []
    for container, attr_path in candidates:
        if container is None:
            continue
        value = container
        try:
            for attr in attr_path.split("."):
                value = getattr(value, attr)
        except AttributeError:
            container_name = getattr(container, "__name__", repr(container))
            attempted.append(f"{container_name}.{attr_path}")
            continue
        return value
    raise AttributeError(
        "ArcGIS-like Workspace: no candidate enum spelling resolved (tried: "
        + ", ".join(attempted)
        + ")"
    )


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
