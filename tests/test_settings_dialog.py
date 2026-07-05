"""SettingsDialog config plumbing.

Verifies the load side (widgets initialize from the config dict) and the save
side (the *same* live dict is mutated in place so the running scanner applies
changes without restart, and save_config persists it). Runs headlessly via the
offscreen Qt platform set in conftest.
"""

import pytest

from ui import settings_dialog
from ui.settings_dialog import SettingsDialog

pytestmark = pytest.mark.usefixtures("qapp")


# The ten config keys the dialog exposes, and the widget attribute that owns
# each. Checkboxes use isChecked(); spin boxes use value().
CHECKBOX_KEYS = {
    "launch_at_startup": "_cb_startup",
    "notify_on_connect": "_cb_notify_connect",
    "notify_on_disconnect": "_cb_notify_disconnect",
    "auto_scan_usb": "_cb_auto_scan",
    "defender_scan_enabled": "_cb_defender",
    "enable_yara_scan": "_cb_yara",
    "enable_driver_check": "_cb_driver",
}
SPINBOX_KEYS = {
    "yara_scan_depth": "_sp_depth",
    "scan_max_file_mb": "_sp_max_mb",
    "scan_timeout_sec": "_sp_timeout",
}


@pytest.fixture(autouse=True)
def _no_disk_writes(monkeypatch):
    """Capture save_config so tests never touch config.json; returns the list
    of dicts it was called with."""
    saved = []
    monkeypatch.setattr(settings_dialog, "save_config", lambda cfg: saved.append(cfg))
    return saved


def _full_config():
    return {
        "launch_at_startup": True,
        "notify_on_connect": True,
        "notify_on_disconnect": True,
        "auto_scan_usb": True,
        "defender_scan_enabled": True,
        "enable_yara_scan": True,
        "enable_driver_check": True,
        "yara_scan_depth": 2,
        "scan_max_file_mb": 50,
        "scan_timeout_sec": 120,
    }


# ── load side ──

def test_checkboxes_load_from_config():
    cfg = _full_config()
    # Flip every boolean off so we're not just matching the True defaults.
    for key in CHECKBOX_KEYS:
        cfg[key] = False
    dlg = SettingsDialog(live_config=cfg)
    for key, attr in CHECKBOX_KEYS.items():
        assert getattr(dlg, attr).isChecked() is False, key


def test_spinboxes_load_from_config():
    cfg = _full_config()
    cfg.update(yara_scan_depth=5, scan_max_file_mb=200, scan_timeout_sec=300)
    dlg = SettingsDialog(live_config=cfg)
    assert dlg._sp_depth.value() == 5
    assert dlg._sp_max_mb.value() == 200
    assert dlg._sp_timeout.value() == 300


def test_missing_keys_fall_back_to_widget_defaults():
    # Empty config → the .get(key, default) fallbacks in __init__ apply.
    dlg = SettingsDialog(live_config={})
    for attr in CHECKBOX_KEYS.values():
        assert getattr(dlg, attr).isChecked() is True   # all default True
    assert dlg._sp_depth.value() == 2
    assert dlg._sp_max_mb.value() == 50
    assert dlg._sp_timeout.value() == 120


# ── save side ──

def test_save_mutates_the_same_live_dict(_no_disk_writes):
    cfg = _full_config()
    dlg = SettingsDialog(live_config=cfg)

    dlg._cb_notify_connect.setChecked(False)
    dlg._sp_timeout.setValue(600)
    dlg._save()

    # Identity: the running scanner holds this very dict, so it sees the change.
    assert cfg["notify_on_connect"] is False
    assert cfg["scan_timeout_sec"] == 600
    # save_config received that same object.
    assert _no_disk_writes and _no_disk_writes[0] is cfg


def test_save_writes_every_managed_key():
    cfg = _full_config()
    dlg = SettingsDialog(live_config=cfg)

    # Drive each widget to a distinct, non-default value.
    for attr in CHECKBOX_KEYS.values():
        getattr(dlg, attr).setChecked(False)
    dlg._sp_depth.setValue(7)
    dlg._sp_max_mb.setValue(1024)
    dlg._sp_timeout.setValue(999)
    dlg._save()

    for key in CHECKBOX_KEYS:
        assert cfg[key] is False, key
    assert cfg["yara_scan_depth"] == 7
    assert cfg["scan_max_file_mb"] == 1024
    assert cfg["scan_timeout_sec"] == 999


def test_save_preserves_keys_the_dialog_does_not_manage():
    # Advanced keys aren't exposed in the UI; a save must not drop them.
    cfg = _full_config()
    cfg["custom_rules_dir"] = "rules/custom"
    cfg["yara_rules_paths"] = ["rules/default", "rules/custom"]
    dlg = SettingsDialog(live_config=cfg)
    dlg._save()
    assert cfg["custom_rules_dir"] == "rules/custom"
    assert cfg["yara_rules_paths"] == ["rules/default", "rules/custom"]


def test_round_trip_load_edit_save():
    cfg = _full_config()
    dlg = SettingsDialog(live_config=cfg)
    # Toggle every checkbox from its loaded state and bump each spinbox.
    for attr in CHECKBOX_KEYS.values():
        w = getattr(dlg, attr)
        w.setChecked(not w.isChecked())
    dlg._sp_depth.setValue(dlg._sp_depth.value() + 1)
    dlg._save()

    for key in CHECKBOX_KEYS:
        assert cfg[key] is False   # all started True, toggled to False
    assert cfg["yara_scan_depth"] == 3


# ── live_config = None path ──

def test_none_live_config_loads_via_load_config(monkeypatch):
    source = _full_config()
    source["scan_max_file_mb"] = 321
    monkeypatch.setattr(settings_dialog, "load_config", lambda: dict(source))
    dlg = SettingsDialog(live_config=None)
    assert dlg._sp_max_mb.value() == 321


def test_spinbox_ranges_clamp_out_of_bounds_config():
    # Defensive: a wildly out-of-range persisted value is clamped by the widget,
    # not crashed on.
    cfg = _full_config()
    cfg["scan_timeout_sec"] = 10_000  # spinbox max is 3600
    dlg = SettingsDialog(live_config=cfg)
    assert dlg._sp_timeout.value() == 3600
