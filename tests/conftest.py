"""Pytest bootstrap for the ArcGIS-like Workspace plugin's test suite.

Two path/import tricks make it possible to unit-test core/*.py without a
running QGIS + PyQt install:

1. tests/fake_qgis/ is a pure-Python stand-in for the third-party 'qgis'
   package (qgis.PyQt.{QtCore,QtWidgets,QtGui}, qgis.core, qgis.gui) --
   see tests/fake_qgis/qgis/__init__.py for what it covers and why. Its
   directory is inserted at the FRONT of sys.path, and 'qgis' is imported
   here, in conftest.py, before pytest collects any test_*.py module --
   collection is what triggers `from tests.helpers import ...`, which in
   turn imports core/*.py modules, so 'qgis' must already resolve to our
   fake in sys.modules by then. Import order matters: if any core module
   imported qgis.* before this file ran, it would either fail (no real
   qgis installed) or bind to a different 'qgis' than the one instantiated
   below, silently splitting the fake's state in two.

2. The repository root's PARENT directory is added to sys.path so
   `import arcgis_like_workspace.core.<module>` resolves the same way it
   would for an installed QGIS plugin (the installed plugins directory is
   the parent of the plugin's own folder, and QGIS imports plugins as
   `<plugin_dir_name>.something`). This also exercises core/__init__.py's
   real import chain (-> .plugin -> every feature module), which is a
   useful smoke test in its own right: if the fake qgis package is missing
   a symbol any core module needs at import time, collection fails loudly
   here rather than only when some deeply-nested feature is finally
   exercised.
"""

import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parent  # .../arcgis_like_workspace
_PACKAGE_PARENT = _REPO_ROOT.parent  # .../outputs (arcgis_like_workspace's own parent)
_FAKE_QGIS_DIR = _TESTS_DIR / "fake_qgis"

for path in (str(_FAKE_QGIS_DIR), str(_PACKAGE_PARENT), str(_TESTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

# Import the fake 'qgis' package now, ahead of any test module import, so
# it lands in sys.modules before core/*.py's `from qgis....` imports run.
import qgis  # noqa: E402  (import must follow the sys.path setup above)
import qgis.core  # noqa: E402,F401
import qgis.gui  # noqa: E402,F401
import qgis.PyQt.QtCore  # noqa: E402,F401
import qgis.PyQt.QtGui  # noqa: E402,F401
import qgis.PyQt.QtWidgets  # noqa: E402,F401

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def reset_qgis_fakes():
    """Give every test a clean slate: fresh QgsApplication singletons
    (message log / task manager), a fresh QgsProject, and no shortcuts
    manager installed on QgsGui. Without this, tests would leak state
    into each other via the class-level singletons tests/fake_qgis/qgis/
    core.py and gui.py use to mirror QGIS's real app-wide singletons.
    """
    qgis.core.reset_singletons()
    qgis.gui.QgsGui._manager = None
    yield
    qgis.core.reset_singletons()
    qgis.gui.QgsGui._manager = None
