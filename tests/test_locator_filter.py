"""Tests for core/locator_filter.py's ArcGIS tool-name filter.

QGIS's built-in locator filters already find layers, bookmarks and
algorithms by their QGIS names without a prefix, so this filter must only
emit alias hits the built-ins can't find -- and must read nothing but the
snapshot prepare() took on the main thread.
"""

from arcgis_like_workspace.core.locator_filter import ArcGISWorkspaceLocatorFilter
from qgis.core import FakeAlgorithm, QgsApplication


class _Feedback:
    def isCanceled(self):
        return False


def _search(text):
    locator_filter = ArcGISWorkspaceLocatorFilter(iface=None)
    results = []
    locator_filter.resultFetched.connect(results.append)
    locator_filter.prepare(text, None)
    locator_filter.fetchResults(text, None, _Feedback())
    return [(result.displayString, result.userData["id"]) for result in results]


def _register(*algorithms):
    QgsApplication.processingRegistry()._algorithms = [FakeAlgorithm(*a) for a in algorithms]


def test_esri_name_finds_the_qgis_equivalent():
    _register(("native:difference", "Difference"), ("native:buffer", "Buffer"))

    assert _search("erase") == [("Difference", "native:difference")]


def test_hits_the_builtin_processing_filter_already_shows_are_skipped():
    _register(("native:clip", "Clip"))

    assert _search("clip") == []


def test_id_aliases_do_not_match_every_similarly_named_algorithm():
    _register(
        ("gdal:merge", "Merge"),
        ("native:mergevectorlayers", "Merge vector layers"),
        ("native:mergelines", "Merge lines"),
    )

    assert _search("mosaic") == [("Merge", "gdal:merge")]


def test_fetch_results_only_reads_the_prepare_snapshot():
    locator_filter = ArcGISWorkspaceLocatorFilter(iface=None)
    results = []
    locator_filter.resultFetched.connect(results.append)
    _register(("native:difference", "Difference"))
    locator_filter.prepare("erase", None)
    _register()  # registry changes after prepare()

    locator_filter.fetchResults("erase", None, _Feedback())

    assert [result.displayString for result in results] == ["Difference"]
