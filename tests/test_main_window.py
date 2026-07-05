"""MainWindow smoke + status-bar behavior.

The constructor kicks off a background WMI device query; we patch it out so
the window builds without hardware. Runs headless via the offscreen Qt
platform set in conftest.
"""

import pytest

from ui.main_window import MainWindow

pytestmark = pytest.mark.usefixtures("qapp")


@pytest.fixture
def window(monkeypatch):
    # Neutralize the constructor's initial background device load (real WMI).
    monkeypatch.setattr(MainWindow, "_refresh_devices", lambda self, *a, **k: None)
    win = MainWindow(config={})
    yield win
    win.close()


def test_main_window_constructs_headlessly(window):
    assert window.windowTitle() == "DeviceGuard"


def test_status_dot_tooltip_explains_monitoring(window):
    # The steady green dot's meaning lives in its tooltip.
    assert "Monitoring active" in window._status_dot.toolTip()


def test_status_label_defaults_to_monitoring(window):
    assert window._status_label.text() == "Monitoring active"


def test_status_label_tracks_connect_and_disconnect(window):
    window._on_device_event({"event_type": "connect", "device_name": "Pulsar eS HE 70"})
    assert window._status_label.text() == "Connected: Pulsar eS HE 70"

    window._on_device_event({"event_type": "disconnect", "device_name": "Pulsar eS HE 70"})
    assert window._status_label.text() == "Disconnected: Pulsar eS HE 70"


def test_status_label_handles_missing_name(window):
    window._on_device_event({"event_type": "connect"})
    assert window._status_label.text() == "Connected: Unknown device"


# ── Devices search + view-in-history (Tier B) ──

_DEVICES = [
    {"name": "Pulsar eS HE 70", "device_id": "HID\\A", "pnp_class": "HIDClass",
     "manufacturer": "Pulsar"},
    {"name": "ROG Gaming Display", "device_id": "USB\\B", "pnp_class": "USBDevice",
     "manufacturer": "WinUsb Device"},
]


def test_search_filters_the_table_and_count(window):
    window._on_devices_loaded(list(_DEVICES))
    assert window._device_table.rowCount() == 2
    assert window._device_count_label.text() == "2 devices"

    window._search_box.setText("pulsar")
    window._render_device_table()
    assert window._device_table.rowCount() == 1
    assert window._device_count_label.text() == "1 of 2 devices"


def test_clearing_search_restores_full_list(window):
    window._on_devices_loaded(list(_DEVICES))
    window._search_box.setText("pulsar")
    window._render_device_table()
    window._search_box.setText("")
    window._render_device_table()
    assert window._device_table.rowCount() == 2
    assert window._device_count_label.text() == "2 devices"


def test_view_in_history_switches_tab_and_prefills_search(window):
    window._view_device_in_history("Pulsar eS HE 70")
    assert window._stack.currentIndex() == 1  # History page
    assert window._history_view._search_box.text() == "Pulsar eS HE 70"
