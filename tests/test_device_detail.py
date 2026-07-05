"""DeviceDetailPanel empty state and device/clear transitions."""

import pytest

from ui.device_detail import DeviceDetailPanel

pytestmark = pytest.mark.usefixtures("qapp")


@pytest.fixture
def panel():
    return DeviceDetailPanel()


# isHidden() reflects the explicit visibility flag without needing the panel's
# ancestor chain to be shown (unlike isVisible()), so it's the right check for
# headless widget tests.

def test_starts_in_empty_state(panel):
    assert panel._title.text() == "No device selected"
    assert not panel._empty_hint.isHidden()


def test_showing_device_hides_hint_and_sets_title(panel):
    panel.show_device({"name": "Pulsar eS HE 70", "device_id": "HID\\X",
                        "pnp_class": "HIDClass", "manufacturer": "Pulsar"})
    assert panel._title.text() == "Pulsar eS HE 70"
    assert panel._empty_hint.isHidden()


def test_unknown_device_name_falls_back(panel):
    panel.show_device({"device_id": "HID\\X"})
    assert panel._title.text() == "Unknown Device"


def test_clear_restores_empty_state(panel):
    panel.show_device({"name": "Kbd", "device_id": "HID\\X"})
    panel.clear()
    assert panel._title.text() == "No device selected"
    assert not panel._empty_hint.isHidden()
    assert panel._current_device_id is None


def test_showing_event_hides_hint(panel):
    panel.show_event({"device_name": "Kbd", "device_id": "HID\\X",
                      "event_type": "connect", "timestamp": "2026-07-05T03:50:00+00:00"})
    assert panel._title.text() == "Kbd"
    assert panel._empty_hint.isHidden()
