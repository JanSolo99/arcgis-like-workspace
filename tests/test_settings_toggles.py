"""Tests for core/settings_toggles.py's dock-attribute-table toggle.

The scenario this guards against, straight from settings_toggles.py's own
comment on _apply_dock_attribute_table_key(): a session where apply() ran
but restore() never did (QGIS crashed, or the user just disabled the
plugin without clicking Restore) leaves the real QSettings key sitting at
the plugin's own value (True) with no restore having happened. A *new*
SettingsToggles instance (self._applied starts False again -- that flag
doesn't survive the crash) then calls apply() again: without the
contains() guard, it would read the already-True value and record it as
"the original", permanently losing the user's real original setting.
"""

from arcgis_like_workspace.core.constants import Keys
from arcgis_like_workspace.core.settings_toggles import (
    DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY,
    DOCK_ATTRIBUTE_TABLE_KEY,
    SettingsToggles,
    _DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL,
)
from qgis.PyQt.QtCore import QSettings

from tests.helpers import key_fn

_PREFIX = "arcgis_like_workspace"


def _make_toggles(settings) -> SettingsToggles:
    return SettingsToggles(settings, key_fn(_PREFIX))


def test_apply_saves_the_original_value_once():
    settings = QSettings()
    toggles = _make_toggles(settings)

    toggles.apply()

    assert settings.value(DOCK_ATTRIBUTE_TABLE_KEY) is True
    assert settings.value(DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY) is True
    assert settings.value(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)) is False
    assert (
        settings.value(key_fn(_PREFIX)(_DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL))
        is False
    )


def test_second_apply_on_the_same_instance_is_a_no_op_by_the_applied_flag():
    """The ordinary, same-session case: SettingsToggles.apply() is
    idempotent via self._applied, so calling it again is simply a no-op
    (nothing re-reads or re-writes anything)."""
    settings = QSettings()
    toggles = _make_toggles(settings)

    toggles.apply()
    original_before = settings.value(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL))

    toggles.apply()  # same instance, self._applied is already True

    assert settings.value(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)) == original_before


def test_apply_after_a_crashed_session_does_not_clobber_the_real_original():
    """The actual regression case: a FRESH SettingsToggles instance (as if
    QGIS had just restarted after a crash, or the plugin got re-enabled)
    calls apply() while QSettings already holds the plugin's own leaked
    True from a previous apply() whose restore() never ran. The
    contains()-guard on the original-value key must stop this second
    apply from recording that leaked True as "the original".
    """
    settings = QSettings()
    first_session = _make_toggles(settings)
    first_session.apply()

    # Simulate a crash: a brand-new instance, same underlying QSettings,
    # which still has DOCK_ATTRIBUTE_TABLE_KEY/DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY
    # left at True from the previous (never-restored) session.
    second_session = _make_toggles(settings)
    second_session.apply()

    # The recorded "original" must still be the real original (False),
    # not the leaked True this second apply() would have seen if it
    # re-read the live key without the guard.
    assert settings.value(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)) is False
    assert (
        settings.value(key_fn(_PREFIX)(_DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL))
        is False
    )
    assert settings.value(DOCK_ATTRIBUTE_TABLE_KEY) is True
    assert settings.value(DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY) is True


def test_restore_writes_back_the_original_and_removes_the_record():
    settings = QSettings()
    toggles = _make_toggles(settings)
    toggles.apply()

    toggles.restore()

    assert settings.value(DOCK_ATTRIBUTE_TABLE_KEY) is False
    assert settings.value(DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY) is False
    assert not settings.contains(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL))
    assert not settings.contains(
        key_fn(_PREFIX)(_DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_ORIGINAL)
    )


def test_restore_is_a_safe_no_op_when_apply_never_ran():
    settings = QSettings()
    toggles = _make_toggles(settings)

    toggles.restore()  # must not raise, must not fabricate any keys

    assert not settings.contains(DOCK_ATTRIBUTE_TABLE_KEY)
    assert not settings.contains(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL))


def test_apply_restore_round_trip_preserves_a_pre_existing_true_value():
    """If the user already had the setting on (True) before ever using
    this plugin, Restore must put it back to True, not fall back to
    False."""
    settings = QSettings()
    settings.setValue(DOCK_ATTRIBUTE_TABLE_KEY, True)
    settings.setValue(DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY, True)
    toggles = _make_toggles(settings)

    toggles.apply()
    assert settings.value(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL)) is True

    toggles.restore()

    assert settings.value(DOCK_ATTRIBUTE_TABLE_KEY) is True
    assert settings.value(DOCK_ATTRIBUTE_TABLE_DOCKED_SETTING_KEY) is True
    assert not settings.contains(key_fn(_PREFIX)(Keys.DOCK_ATTRIBUTE_TABLE_ORIGINAL))
