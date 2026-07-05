"""Friendly PnP-class label mapping."""

import pytest

from ui.device_labels import friendly_class


@pytest.mark.parametrize("raw,expected", [
    ("HIDClass", "Input"),
    ("MEDIA", "Audio"),
    ("USBDevice", "USB"),
    ("Bluetooth", "Bluetooth"),
    ("DiskDrive", "Storage"),
    ("USBSTOR", "Storage"),
    ("WPD", "Storage"),
    ("Monitor", "Display"),
    ("Mouse", "Mouse"),
    ("Keyboard", "Keyboard"),
    ("Net", "Network"),
])
def test_known_classes_map_to_friendly(raw, expected):
    assert friendly_class(raw) == expected


def test_case_insensitive():
    assert friendly_class("hidclass") == "Input"
    assert friendly_class("bluetooth") == "Bluetooth"


def test_unknown_class_returned_unchanged():
    # Better to show the real class than a misleading generic.
    assert friendly_class("SomeVendorClass") == "SomeVendorClass"


def test_blank_class_becomes_device():
    assert friendly_class("") == "Device"
    assert friendly_class(None) == "Device"
    assert friendly_class("   ") == "Device"


def test_mouse_beats_generic_hid():
    # A mouse is HID too, but the more specific label should win.
    assert friendly_class("Mouse") == "Mouse"
