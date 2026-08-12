"""Pure-Python stand-in for the 'qgis' package, used only by the test suite.

Provides just enough of qgis.PyQt.{QtCore,QtWidgets,QtGui}, qgis.core, and
qgis.gui for core/*.py to import and run under plain CPython -- no PyQt5,
PyQt6, PyQide, or a real QGIS install required. See tests/conftest.py for
how this is wired into sys.modules before any `core` module is imported,
and each submodule's docstring for the specific documented QGIS/sip
contracts it encodes (rejection of non-str shortcut sequences, taskAdded
emitting an int id, etc.) -- those contracts are the point: a fake that was
too permissive would let the exact bugs the review found pass silently.
"""
