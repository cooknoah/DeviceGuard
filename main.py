"""DeviceGuard — entry point.

Loads config, starts the device monitor, tray icon, toast notifications,
and PyQt6 main window.
"""

import sys
import time
import threading

from core.config import load_config
from core import logger
from core.monitor import DeviceMonitor
from core.notifier import notify_connect, notify_disconnect
from core.tray import TrayManager
from core.startup import sync_startup
from ui.app import create_app

# ── Notification debounce + cooldown ──
_DEBOUNCE_SECS = 0.8
_COOLDOWN_SECS = 5.0

_pending_lock = threading.Lock()
_connect_timer: threading.Timer | None = None
_disconnect_timer: threading.Timer | None = None
_last_connect_toast: float = 0.0
_last_disconnect_toast: float = 0.0

_GENERIC_KEYWORDS = [
    "USB Input Device",
    "USB Composite Device",
    "HID-compliant",
    "USB Root Hub",
    "XINPUT compatible",
    "HID-conformant",
]


def _is_generic(name: str) -> bool:
    for kw in _GENERIC_KEYWORDS:
        if kw.lower() in name.lower():
            return True
    return False


def _pick_best_name(devices: list[dict]) -> str:
    for d in devices:
        name = d.get("name") or ""
        if name and not _is_generic(name):
            return name
    for d in devices:
        if d.get("name"):
            return d["name"]
    return "Unknown device"


_pending_connects: list[dict] = []
_pending_disconnects: list[dict] = []


def _flush_connects(config: dict) -> None:
    global _connect_timer, _last_connect_toast
    with _pending_lock:
        batch = list(_pending_connects)
        _pending_connects.clear()
        _connect_timer = None
    if batch and config.get("notify_on_connect", True):
        name = _pick_best_name(batch)
        notify_connect(name)
        _last_connect_toast = time.monotonic()


def _flush_disconnects(config: dict) -> None:
    global _disconnect_timer, _last_disconnect_toast
    with _pending_lock:
        batch = list(_pending_disconnects)
        _pending_disconnects.clear()
        _disconnect_timer = None
    if batch and config.get("notify_on_disconnect", True):
        name = _pick_best_name(batch)
        notify_disconnect(name)
        _last_disconnect_toast = time.monotonic()


# Reference to the main window, set in main()
_window = None


def on_connect(device_info: dict, config: dict) -> None:
    global _connect_timer
    name = device_info.get("name")
    print(f"[+] Device connected:  {device_info}")
    logger.log_event(
        event_type="connect",
        device_name=name,
        device_id=device_info.get("device_id"),
        device_class=device_info.get("pnp_class"),
        manufacturer=device_info.get("manufacturer"),
    )
    if _window:
        _window.notify_device_event("connect", device_info)
    with _pending_lock:
        now = time.monotonic()
        if now - _last_connect_toast < _COOLDOWN_SECS:
            return
        _pending_connects.append(device_info)
        if _connect_timer is not None:
            _connect_timer.cancel()
        _connect_timer = threading.Timer(
            _DEBOUNCE_SECS, _flush_connects, args=(config,)
        )
        _connect_timer.daemon = True
        _connect_timer.start()


def on_disconnect(device_info: dict, config: dict) -> None:
    global _disconnect_timer
    name = device_info.get("name")
    print(f"[-] Device disconnected: {device_info}")
    logger.log_event(
        event_type="disconnect",
        device_name=name,
        device_id=device_info.get("device_id"),
        device_class=device_info.get("pnp_class"),
        manufacturer=device_info.get("manufacturer"),
    )
    if _window:
        _window.notify_device_event("disconnect", device_info)
    with _pending_lock:
        now = time.monotonic()
        if now - _last_disconnect_toast < _COOLDOWN_SECS:
            return
        _pending_disconnects.append(device_info)
        if _disconnect_timer is not None:
            _disconnect_timer.cancel()
        _disconnect_timer = threading.Timer(
            _DEBOUNCE_SECS, _flush_disconnects, args=(config,)
        )
        _disconnect_timer.daemon = True
        _disconnect_timer.start()


def main() -> None:
    global _window
    config = load_config()
    print("DeviceGuard starting...")

    sync_startup(config)

    # Create Qt app and window
    app, window = create_app()
    _window = window

    # Device monitor
    monitor = DeviceMonitor()
    monitor.register_callbacks(
        on_connect=lambda info: on_connect(info, config),
        on_disconnect=lambda info: on_disconnect(info, config),
    )
    monitor.start()

    # System tray
    def handle_open():
        window.show()
        window.raise_()
        window.activateWindow()

    def handle_settings():
        window.show()
        window.raise_()
        window.open_settings()

    def handle_exit():
        print("[Tray] Exit clicked")
        monitor.stop()
        app.quit()

    tray = TrayManager(
        on_open=handle_open,
        on_settings=handle_settings,
        on_exit=handle_exit,
    )
    tray.start()

    # Show window on launch
    window.show()

    print("DeviceGuard running.")

    exit_code = app.exec()
    monitor.stop()
    tray.stop()
    print("DeviceGuard stopped.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
