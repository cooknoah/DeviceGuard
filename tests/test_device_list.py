"""ConnectedDevicesTable: friendly class labels and the Security placeholder."""

import pytest

from ui.device_list import ConnectedDevicesTable, _scan_cell

pytestmark = pytest.mark.usefixtures("qapp")


def test_scan_cell_placeholder_has_explanatory_tooltip():
    item = _scan_cell(None)
    assert item.text() == "—"
    assert "No security scan" in item.toolTip()


def test_scan_cell_shows_badge_for_a_result():
    item = _scan_cell({"status": "clean", "summary": "yara: clean"})
    assert "Clean" in item.text()
    assert item.toolTip() == "yara: clean"


def test_class_column_shows_friendly_label_with_raw_tooltip():
    table = ConnectedDevicesTable()
    table.load_devices([
        {"name": "Pulsar eS HE 70", "device_id": "HID\\X",
         "pnp_class": "HIDClass", "manufacturer": "Pulsar"},
    ])
    class_item = table.item(0, 1)
    assert class_item.text() == "Input"          # friendly label shown
    assert class_item.toolTip() == "HIDClass"    # raw class preserved on hover


def test_name_column_keeps_full_name_in_tooltip():
    table = ConnectedDevicesTable()
    table.load_devices([
        {"name": "A Very Long Device Name That Truncates", "device_id": "USB\\X",
         "pnp_class": "USBDevice", "manufacturer": "Acme"},
    ])
    assert table.item(0, 0).toolTip() == "A Very Long Device Name That Truncates"
