"""Tests for core/docks.py's DockArranger.

The scenario restore_titles() specifically guards against (see its own
docstring): a native QGIS dock this plugin doesn't own the lifetime of can
already be destroyed (its underlying C++ object gone) by the time Restore
runs -- e.g. the Processing dock disappears if that plugin is disabled
mid-session. setWindowTitle() on a deleted dock raises RuntimeError; that
must not abort the loop and strand every *other* dock's title un-restored,
and renamed_docks must still end up cleared either way (otherwise a single
bad entry keeps failing, or keeps getting silently skipped, on every
subsequent Restore).
"""

from arcgis_like_workspace.core.docks import DockArranger
from qgis.PyQt.QtWidgets import QDockWidget

from tests.helpers import FakeMainWindow


class _ExplodingDock(QDockWidget):
    """A dock whose underlying C++ object is already gone -- setWindowTitle()
    raises RuntimeError, matching real PyQt/sip's behavior for a deleted
    QObject."""

    def setWindowTitle(self, title: str):
        raise RuntimeError("wrapped C++ object of type QDockWidget has been deleted")


def test_restore_titles_survives_one_dock_raising_and_restores_the_rest():
    window = FakeMainWindow()
    arranger = DockArranger(window)
    good_dock = QDockWidget("Contents")
    bad_dock = _ExplodingDock("Catalog")

    arranger.renamed_docks = {
        "good": (good_dock, "Layers"),
        "bad": (bad_dock, "Browser"),
    }

    arranger.restore_titles()  # must not raise

    assert good_dock.windowTitle() == "Layers"
    assert arranger.renamed_docks == {}


def test_restore_titles_clears_renamed_docks_even_if_every_dock_raises():
    window = FakeMainWindow()
    arranger = DockArranger(window)
    arranger.renamed_docks = {
        "a": (_ExplodingDock("A"), "Original A"),
        "b": (_ExplodingDock("B"), "Original B"),
    }

    arranger.restore_titles()  # must not raise

    assert arranger.renamed_docks == {}


def test_restore_titles_is_a_safe_no_op_when_nothing_was_renamed():
    window = FakeMainWindow()
    arranger = DockArranger(window)

    arranger.restore_titles()

    assert arranger.renamed_docks == {}


def test_rename_dock_saves_the_original_title_only_once():
    window = FakeMainWindow()
    arranger = DockArranger(window)
    dock = QDockWidget("Layers")
    dock.setObjectName("mLayerTreeDock")

    arranger.rename_dock(dock, "Contents")
    dock.setWindowTitle("something else entirely")  # simulate external interference
    arranger.rename_dock(dock, "Contents")  # a second arrange() call

    assert dock.windowTitle() == "Contents"
    # The saved original must still be the true original ("Layers"), not
    # whatever the title happened to be on the second rename_dock() call.
    assert arranger.renamed_docks[dock.objectName()] == (dock, "Layers")


def test_find_dock_matches_tokens_and_respects_exclude():
    window = FakeMainWindow()
    layers_dock = QDockWidget("Layers")
    layers_dock.setObjectName("mLayerTreeDock")
    styling_dock = QDockWidget("Layer Styling")
    styling_dock.setObjectName("mLayerStylingDock")
    window.addDockWidget(None, layers_dock)
    window.addDockWidget(None, styling_dock)

    arranger = DockArranger(window)
    found = arranger.find_dock(
        ["layers", "layer tree", "legend", "toc"], exclude=["styling", "style", "symbology"]
    )

    assert found is layers_dock


def test_find_dock_returns_none_when_nothing_matches():
    window = FakeMainWindow()
    arranger = DockArranger(window)

    assert arranger.find_dock(["nonexistent"]) is None
