"""VID/PID parsing, usb.ids lookup, and combined name resolution.

The bus-reported (cfgmgr32) and usb.ids data sources are patched out so the
resolution logic is tested deterministically without real hardware or the
bundled 17k-line usb.ids file.
"""

import pytest

from core import device_names


# ── VID/PID regex ──

def test_vidpid_regex_extracts_groups():
    m = device_names.VIDPID_RE.search("USB\\VID_046D&PID_C52B\\6&abc")
    assert m is not None
    assert m.group(1) == "046D"
    assert m.group(2) == "C52B"


def test_vidpid_regex_is_case_insensitive():
    assert device_names.VIDPID_RE.search("usb\\vid_046d&pid_c52b") is not None


def test_vidpid_regex_no_match():
    assert device_names.VIDPID_RE.search("ACPI\\PNP0501") is None


# ── usb.ids lookup ──

@pytest.fixture
def fake_usb_ids(monkeypatch):
    db = {"046d": ("Logitech, Inc.", {"c52b": "Unifying Receiver"})}
    monkeypatch.setattr(device_names, "_usb_ids", db)
    return db


def test_usb_ids_lookup_hit(fake_usb_ids):
    vendor, product = device_names.usb_ids_lookup("USB\\VID_046D&PID_C52B")
    assert vendor == "Logitech, Inc."
    assert product == "Unifying Receiver"


def test_usb_ids_lookup_known_vendor_unknown_product(fake_usb_ids):
    vendor, product = device_names.usb_ids_lookup("USB\\VID_046D&PID_FFFF")
    assert vendor == "Logitech, Inc."
    assert product is None


def test_usb_ids_lookup_unknown_vendor(fake_usb_ids):
    assert device_names.usb_ids_lookup("USB\\VID_9999&PID_0001") == (None, None)


def test_usb_ids_lookup_no_vidpid(fake_usb_ids):
    assert device_names.usb_ids_lookup("ACPI\\PNP0501") == (None, None)


# ── combined resolution ──

def _generic(name):
    return (name or "") in ("HID Keyboard Device", "USB Input Device")


def test_resolve_prefers_bus_reported_name(monkeypatch, fake_usb_ids):
    monkeypatch.setattr(device_names, "bus_reported_name", lambda _id: "My Fancy Keyboard")
    devs = [{"device_id": "USB\\VID_046D&PID_C52B", "name": "HID Keyboard Device"}]
    assert device_names.resolve_name(devs, _generic) == "My Fancy Keyboard"


def test_resolve_ignores_generic_bus_name_falls_back_to_usb_ids(monkeypatch, fake_usb_ids):
    # Bus-reported string is itself generic → skip it, use usb.ids.
    monkeypatch.setattr(device_names, "bus_reported_name", lambda _id: "USB Input Device")
    devs = [{"device_id": "USB\\VID_046D&PID_C52B", "name": "HID Keyboard Device"}]
    assert device_names.resolve_name(devs, _generic) == "Logitech, Inc. Unifying Receiver"


def test_resolve_vendor_only_qualifies_generic_name(monkeypatch, fake_usb_ids):
    monkeypatch.setattr(device_names, "bus_reported_name", lambda _id: None)
    devs = [{"device_id": "USB\\VID_046D&PID_FFFF", "name": "HID Keyboard Device"}]
    # Product unknown, vendor known → prefix the existing name with the vendor.
    assert device_names.resolve_name(devs, _generic) == "Logitech, Inc. HID Keyboard Device"


def test_resolve_returns_none_when_nothing_better(monkeypatch, fake_usb_ids):
    monkeypatch.setattr(device_names, "bus_reported_name", lambda _id: None)
    devs = [{"device_id": "USB\\VID_9999&PID_0001", "name": "HID Keyboard Device"}]
    assert device_names.resolve_name(devs, _generic) is None
