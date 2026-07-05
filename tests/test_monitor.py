"""Pure device-selection helpers in core.monitor.

Only the WMI/COM-free logic (is_generic_name, pick_best_device) is exercised;
the live query paths need real hardware and are out of scope.
"""

from core import device_names, monitor


# ── is_generic_name ──

def test_generic_names_detected():
    assert monitor.is_generic_name("USB Input Device")
    assert monitor.is_generic_name("HID-compliant mouse")
    assert monitor.is_generic_name("USB Composite Device")


def test_real_names_not_generic():
    assert not monitor.is_generic_name("Logitech G502 Mouse")
    assert not monitor.is_generic_name("SanDisk Ultra")


def test_none_name_is_not_generic():
    assert not monitor.is_generic_name(None)


# ── pick_best_device ──

def test_picks_descriptive_name_over_generic():
    devs = [
        {"name": "USB Input Device", "device_id": "a"},
        {"name": "Logitech G502", "device_id": "b"},
    ]
    assert monitor.pick_best_device(devs)["name"] == "Logitech G502"


def test_falls_back_to_first_named_when_all_generic(monkeypatch):
    # No better name available → keep the first generic entry as-is.
    monkeypatch.setattr(device_names, "resolve_name", lambda devs, is_generic: None)
    devs = [
        {"name": "USB Composite Device", "device_id": "a"},
        {"name": "HID-compliant mouse", "device_id": "b"},
    ]
    assert monitor.pick_best_device(devs)["name"] == "USB Composite Device"


def test_uses_resolved_name_when_all_generic(monkeypatch):
    monkeypatch.setattr(device_names, "resolve_name", lambda devs, is_generic: "Corsair K70")
    devs = [{"name": "USB Input Device", "device_id": "a"}]
    best = monitor.pick_best_device(devs)
    assert best["name"] == "Corsair K70"
    # original device_id is preserved through the resolution merge
    assert best["device_id"] == "a"


def test_empty_group_returns_empty_dict():
    assert monitor.pick_best_device([]) == {}


def test_entry_without_name_is_skipped(monkeypatch):
    monkeypatch.setattr(device_names, "resolve_name", lambda devs, is_generic: None)
    devs = [
        {"name": None, "device_id": "a"},
        {"name": "Kingston DataTraveler", "device_id": "b"},
    ]
    assert monitor.pick_best_device(devs)["name"] == "Kingston DataTraveler"
