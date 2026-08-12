"""Adds a single "Toggle Labels" entry to the layer tree's native Contents
right-click context menu for vector layers.

REPLACES A setMenuProvider()-BASED APPROACH (read before touching this
file): an earlier version of this module captured the layer tree view's
native menu provider via `view.menuProvider()`, replaced it with
`view.setMenuProvider()` wrapping a self-built menu, and attempted to give
the native one back on restore() by calling `setMenuProvider()` a second
time with the captured reference.

That was unsafe and caused a real QGIS crash. QGIS's own docs for
`setMenuProvider()` state it "Takes ownership of the instance" -- the view
stores the provider in a `std::unique_ptr`, and *every* call deletes
whatever provider was installed before. The first `setMenuProvider()` call
(in the old apply()) deleted QGIS's native provider, so the captured
"original" reference was already dangling from that point on. restore()
then handed that dangling pointer back to `setMenuProvider()` -- this
didn't raise, but it corrupted the view's internal state. The *second*
Apply's `setMenuProvider()` call then deleted "whatever is currently
installed" as part of replacing it, which was that already-dangling
pointer: a double-free, exactly the kind of bug that crashes the whole
process instead of raising a catchable Python exception (Apply -> Restore
-> Apply again -> crash). It also permanently degraded the Contents menu
to a hand-rebuilt subset of QGIS's real one for the rest of the session,
since there was never a way to recover the original provider once
replaced. See git history for the full forensics.

The fix: this module never touches the menu provider at all.
`QgisInterface.addCustomActionForLayerType()` /
`removeCustomActionForLayerType()` are QGIS's long-standing supported API
for adding/removing layer-tree context-menu entries *additively*, without
owning or replacing anything QGIS or any other plugin installed. The
native menu is left completely untouched; this module only ever adds one
QAction to it, and removes exactly that QAction on restore() -- safe to
cycle apply/restore/apply indefinitely. Verified against
https://qgis.org/pyqgis/master/gui/QgisInterface.html (current signature)
and the release-3_28 branch's python/gui/auto_generated/qgisinterface.sip.in
on https://github.com/qgis/QGIS (the 3.28 signature); see
_resolve_vector_layer_type() below for how the `type` argument's spelling
is bridged across that range.
"""

import logging

from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QAction

from .compat import qgis_enum_candidates

logger = logging.getLogger(__name__)

try:
    # QgsMapLayerType is only importable on QGIS < 3.30 -- see the
    # candidates list below. Guarded so this module still loads on
    # versions where it no longer exists.
    from qgis.core import QgsMapLayerType
except ImportError:
    QgsMapLayerType = None

#: addCustomActionForLayerType()'s `type` argument changed container across
#: the 3.28-4.x range this plugin supports -- the same kind of move
#: settings_toggles.py's snapping-type candidates handle (see compat.py's
#: qgis_enum_candidates() docstring). Every candidate below is a spelling
#: actually observed in QGIS's own source or generated bindings:
#:
#: * Qgis.LayerType.Vector: the current, documented home since QGIS 3.30
#:   (`enum class LayerType` nested in Qgis, src/core/qgis.h, whose own
#:   docstring reads "Prior to 3.30 this was available as
#:   QgsMapLayerType"), unchanged through master/4.x.
#:   QgisInterface.addCustomActionForLayerType() takes exactly this type
#:   on master (python/gui/auto_generated/qgisinterface.sip.in).
#: * QgsMapLayerType.VectorLayer: the pre-3.30 standalone enum (declared
#:   in src/core/qgis.h, and the addCustomActionForLayerType() parameter
#:   type in python/gui/auto_generated/qgisinterface.sip.in on the
#:   release-3_28 branch -- this plugin's floor). Fully removed by
#:   master/4.x, which is exactly why the import above is guarded with
#:   try/except ImportError; qgis_enum_candidates() skips a None
#:   container automatically, so this candidate is simply unreachable
#:   there rather than an error.
_VECTOR_LAYER_TYPE_CANDIDATES = (
    (Qgis, "LayerType.Vector"),
    (QgsMapLayerType, "VectorLayer"),
)


def _resolve_vector_layer_type():
    """Return the running QGIS version's spelling of "vector layer type"."""
    return qgis_enum_candidates(_VECTOR_LAYER_TYPE_CANDIDATES)


class LayerTreeLabelingMenu:
    """Adds/removes a single "Toggle Labels" action on the layer tree's
    native Contents context menu for vector layers, via
    QgisInterface.addCustomActionForLayerType()/removeCustomActionForLayerType()
    -- see module docstring for why this replaced a setMenuProvider()-based
    approach.

    One action serves every vector layer (registered with allLayers=True)
    rather than a checkable action reflecting one particular layer's
    state, which would be misleading for a menu entry that can be invoked
    on any layer: triggering it reads
    iface.layerTreeView().currentLayer() -- the layer the context menu
    was opened on -- flips its labelsEnabled(), and triggers a repaint.
    """

    def __init__(self, iface):
        self.iface = iface
        self._action = None

    def apply(self):
        """Idempotent, and safe to call repeatedly across apply/restore
        cycles: only registers the action if it is not already
        registered (self._action is None)."""
        if self._action is not None:
            return

        view = self.iface.layerTreeView()
        if view is None:
            logger.warning(
                "ArcGIS-like Workspace: no layer tree view available, skipping the Toggle Labels menu entry"
            )
            return

        try:
            layer_type = _resolve_vector_layer_type()
        except AttributeError:
            logger.exception(
                "ArcGIS-like Workspace: could not resolve a vector-layer type for the layer-tree menu"
            )
            return

        action = QAction("Toggle Labels", self.iface.mainWindow())
        action.triggered.connect(self._toggle_labels)

        try:
            # menu="" -- add only to the layer tree's own context menu; a
            # non-empty `menu` argument would additionally create/append to
            # a top-level main-window menu of that name, which is not
            # wanted here.
            self.iface.addCustomActionForLayerType(action, "", layer_type, True)
        except Exception:
            logger.exception(
                "ArcGIS-like Workspace: could not register the Toggle Labels layer-tree action"
            )
            action.deleteLater()
            return

        self._action = action

    def restore(self):
        """Safe to call even if apply() never registered an action, and
        safe to call twice in a row."""
        if self._action is None:
            return

        try:
            self.iface.removeCustomActionForLayerType(self._action)
        except Exception:
            logger.exception(
                "ArcGIS-like Workspace: could not deregister the Toggle Labels layer-tree action"
            )

        # Parented to iface.mainWindow() (long-lived), not to anything this
        # plugin destroys on restore -- same hazard documented for the
        # locator's find_action (locator_filter.py): without an explicit
        # deleteLater() this would be orphaned with a live triggered
        # connection for the rest of the QGIS session.
        self._action.deleteLater()
        self._action = None

    def _toggle_labels(self, checked=False):
        view = self.iface.layerTreeView()
        layer = view.currentLayer() if view is not None else None
        if layer is None or not hasattr(layer, "labelsEnabled") or not hasattr(layer, "setLabelsEnabled"):
            return
        try:
            layer.setLabelsEnabled(not layer.labelsEnabled())
            layer.triggerRepaint()
        except Exception:
            logger.exception("ArcGIS-like Workspace: failed to toggle labels for %r", layer)
