"""Fake qgis.PyQt.QtWidgets -- just the widget classes core/*.py touches.

None of these are real Qt widgets: no C++ object, no event loop, no
parent-child ownership/deletion semantics beyond a `deleteLater()` flag
tests can assert on. They exist to let core/*.py's *control flow* run
end-to-end in plain CPython.
"""

from typing import List, Optional

from .QtCore import FakeSignal
from .QtGui import QIcon


class _AutoAttrMeta(type):
    """Metaclass that turns any class-attribute access (including ones not
    explicitly defined) into a stable per-name sentinel value.

    Used for QStyle.StandardPixmap and QToolButton's ToolButtonPopupMode
    group: real Qt exposes dozens of SP_* standard-pixmap names and this
    plugin only ever needs a handful, resolved dynamically by name (see
    toolbars.standard_icon()). Rather than hand-enumerate every SP_* used
    across core/*.py (and silently going stale if a call site adds one),
    any attribute access resolves to a distinct, stable placeholder.
    """

    def __getattr__(cls, name):
        return f"<{cls.__name__}.{name}>"


class _StandardPixmap(metaclass=_AutoAttrMeta):
    pass


class QStyle(metaclass=_AutoAttrMeta):
    StandardPixmap = _StandardPixmap


class _StyleInstance:
    def standardIcon(self, pixmap) -> QIcon:
        return QIcon(pixmap)


class QApplication:
    """Only the bits toolbars.standard_icon()/icon_for_action() touch --
    QApplication.style().standardIcon(pixmap)."""

    @staticmethod
    def style() -> _StyleInstance:
        return _StyleInstance()


class QAction:
    """Accepts both real-Qt constructor shapes used across core/*.py:
    QAction(text, parent) and QAction(icon, text, parent)."""

    def __init__(self, *args):
        if len(args) == 2:
            first, parent = args
            if isinstance(first, QIcon):
                icon, text = first, ""
            else:
                icon, text = QIcon(), first
        elif len(args) == 3:
            icon, text, parent = args
        else:
            raise TypeError(f"QAction(...) unsupported arguments: {args!r}")

        self._icon = icon
        self._text = text
        self._parent = parent
        self._checkable = False
        self._checked = False
        self._enabled = True
        self._visible = True
        self._tooltip = ""
        self._shortcut = None
        self.triggered = FakeSignal()
        self.toggled = FakeSignal()
        self.deleted = False

    def setText(self, text: str):
        self._text = text

    def text(self) -> str:
        return self._text

    def setIcon(self, icon: QIcon):
        self._icon = icon

    def icon(self) -> QIcon:
        return self._icon

    def setCheckable(self, checkable: bool):
        self._checkable = checkable

    def isCheckable(self) -> bool:
        return self._checkable

    def setChecked(self, checked: bool):
        self._checked = checked

    def isChecked(self) -> bool:
        return self._checked

    def setEnabled(self, enabled: bool):
        self._enabled = enabled

    def isEnabled(self) -> bool:
        return self._enabled

    def setVisible(self, visible: bool):
        self._visible = visible

    def isVisible(self) -> bool:
        return self._visible

    def setToolTip(self, tooltip: str):
        self._tooltip = tooltip

    def toolTip(self) -> str:
        return self._tooltip

    def setShortcut(self, sequence):
        # Real QAction.setShortcut()/shortcut() always deal in QKeySequence
        # -- wrap here so a caller (e.g. FakeShortcutsManager.setKeySequence,
        # which receives a plain str per the real setKeySequence() contract)
        # can hand in either a str or a QKeySequence and get back a
        # QKeySequence from shortcut() either way, matching real Qt.
        from .QtGui import QKeySequence

        self._shortcut = sequence if isinstance(sequence, QKeySequence) else QKeySequence(sequence)

    def shortcut(self):
        from .QtGui import QKeySequence

        if self._shortcut is None:
            return QKeySequence("")
        return self._shortcut

    def trigger(self):
        self.triggered.emit(False)

    def deleteLater(self):
        self.deleted = True

    def __repr__(self):
        return f"QAction({self._text!r})"


class QWidget:
    """Base stand-in; only used as a findChildren() type filter."""


class QLabel:
    def __init__(self, text: str = "", parent=None):
        self._text = text
        self._parent = parent
        self._object_name = ""
        self._visible = True

    def setObjectName(self, name: str):
        self._object_name = name

    def objectName(self) -> str:
        return self._object_name

    def setVisible(self, visible: bool):
        self._visible = visible

    def isVisible(self) -> bool:
        return self._visible

    def text(self) -> str:
        return self._text


class QMenu:
    def __init__(self, parent=None):
        self._parent = parent
        self._actions: List[QAction] = []

    def addAction(self, action: QAction):
        self._actions.append(action)

    def addSeparator(self) -> QAction:
        separator = QAction("", self)
        self._actions.append(separator)
        return separator

    def actions(self) -> List[QAction]:
        return list(self._actions)


class QToolButton:
    ToolButtonPopupMode = type("ToolButtonPopupMode", (), {"InstantPopup": "InstantPopup"})
    InstantPopup = "InstantPopup"

    def __init__(self, parent=None):
        self._parent = parent
        self._text = ""
        self._icon = QIcon()
        self._menu: Optional[QMenu] = None
        self._popup_mode = None
        self._style = None
        self._tooltip = ""
        self._default_action: Optional[QAction] = None
        self._auto_raise = False
        self._icon_size = None
        self.clicked = FakeSignal()

    def setDefaultAction(self, action: QAction):
        self._default_action = action

    def defaultAction(self) -> Optional[QAction]:
        return self._default_action

    def setAutoRaise(self, enabled: bool):
        self._auto_raise = enabled

    def setIconSize(self, size):
        self._icon_size = size

    def setText(self, text: str):
        self._text = text

    def text(self) -> str:
        return self._text

    def setIcon(self, icon: QIcon):
        self._icon = icon

    def icon(self) -> QIcon:
        return self._icon

    def setPopupMode(self, mode):
        self._popup_mode = mode

    def setToolButtonStyle(self, style):
        self._style = style

    def setMenu(self, menu: QMenu):
        self._menu = menu

    def menu(self) -> Optional[QMenu]:
        return self._menu

    def setToolTip(self, tooltip: str):
        self._tooltip = tooltip


class _Rect:
    def __init__(self, x: int, y: int):
        self._x, self._y = x, y

    def x(self) -> int:
        return self._x

    def y(self) -> int:
        return self._y


class QToolBar:
    def __init__(self, title: str = "", parent=None):
        self._title = title
        self._parent = parent
        self._object_name = ""
        self._actions: List[QAction] = []
        self._widget_actions: dict = {}  # QAction -> widget, for addWidget()
        self._movable = True
        self._floatable = True
        self._icon_size = None
        self._style = None
        self._visible = True
        #: (x, y) -- set by tests to model where a native toolbar sits.
        self.position = (0, 0)
        self.deleted = False

    def setObjectName(self, name: str):
        self._object_name = name

    def objectName(self) -> str:
        return self._object_name

    def geometry(self):
        return _Rect(*self.position)

    def deleteLater(self):
        self.deleted = True

    def setMovable(self, movable: bool):
        self._movable = movable

    def setFloatable(self, floatable: bool):
        self._floatable = floatable

    def setIconSize(self, size):
        self._icon_size = size

    def iconSize(self):
        return self._icon_size

    def setToolButtonStyle(self, style):
        self._style = style

    def setVisible(self, visible: bool):
        self._visible = visible

    def isVisible(self) -> bool:
        return self._visible

    def addAction(self, action: QAction):
        if action not in self._actions:
            self._actions.append(action)

    def addSeparator(self) -> QAction:
        separator = QAction("", self)
        self._actions.append(separator)
        return separator

    def addWidget(self, widget):
        # Real QToolBar.addWidget() wraps `widget` in an internal QAction
        # and returns it; widgetForAction() maps back the other way. Mirror
        # both directions so ActionGroup.set_visible() (toolbars.py) can
        # round-trip through it.
        action = QAction("", self)
        self._actions.append(action)
        self._widget_actions[action] = widget
        return action

    def actions(self) -> List[QAction]:
        return list(self._actions)

    def removeAction(self, action: QAction):
        if action in self._actions:
            self._actions.remove(action)
        self._widget_actions.pop(action, None)

    def widgetForAction(self, action: QAction):
        return self._widget_actions.get(action)


class QDockWidget:
    def __init__(self, title: str = "", parent=None):
        self._title = title
        self._parent = parent
        self._object_name = ""
        self._widget = None
        self._visible = True
        self._toggle_action: Optional[QAction] = None
        self.deleted = False

    def setObjectName(self, name: str):
        self._object_name = name

    def objectName(self) -> str:
        return self._object_name

    def setWidget(self, widget):
        self._widget = widget

    def widget(self):
        return self._widget

    def setVisible(self, visible: bool):
        self._visible = visible

    def isVisible(self) -> bool:
        return self._visible

    def setWindowTitle(self, title: str):
        self._title = title

    def windowTitle(self) -> str:
        return self._title

    def toggleViewAction(self) -> QAction:
        if self._toggle_action is None:
            self._toggle_action = QAction(self._title, self._parent)
            self._toggle_action.setCheckable(True)
        return self._toggle_action

    def raise_(self):
        pass

    def deleteLater(self):
        self.deleted = True

    def __repr__(self):
        return f"QDockWidget({self._title!r}, objectName={self._object_name!r})"


class QListWidget:
    def __init__(self, parent=None):
        self._parent = parent
        self._items: List[str] = []
        self.deleted = False

    def addItem(self, text: str):
        if self.deleted:
            raise RuntimeError("underlying C++ object has been deleted")
        self._items.append(text)

    def count(self) -> int:
        return len(self._items)

    def takeItem(self, index: int):
        return self._items.pop(index)

    def item(self, index: int):
        return self._items[index]


class QMessageBox:
    @staticmethod
    def information(parent, title: str, text: str):
        pass
