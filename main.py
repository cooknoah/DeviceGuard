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
from core.notifier import notify_connect, notify_disconnect, notify_threat
from core.tray import TrayManager
from core.startup import sync_startup
from core.security.scanner import Scanner
from core.security.types import ScanResult, ScanStatus
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


def _pick_best(devices: list[dict]) -> dict:
    """Pick the most descriptive device dict from a burst of interface events."""
    for d in devices:
        name = d.get("name") or ""
        if name and not _is_generic(name):
            return d
    for d in devices:
        if d.get("name"):
            return d
    return devices[0] if devices else {}


_pending_connects: list[dict] = []
_pending_disconnects: list[dict] = []


def _flush_connects(config: dict) -> None:
    global _connect_timer, _last_connect_toast
    with _pending_lock:
        batch = list(_pending_connects)
        _pending_connects.clear()
        _connect_timer = None
    if not batch:
        return
    best = _pick_best(batch)
    name = best.get("name") or "Unknown device"
    logger.log_event(
        event_type="connect",
        device_name=name,
        device_id=best.get("device_id"),
        device_class=best.get("pnp_class"),
        manufacturer=best.get("manufacturer"),
    )
    if _window:
        _window.notify_device_event("connect", best)
    now = time.monotonic()
    if config.get("notify_on_connect", True) and now - _last_connect_toast >= _COOLDOWN_SECS:
        notify_connect(name)
        _last_connect_toast = now


def _flush_disconnects(config: dict) -> None:
    global _disconnect_timer, _last_disconnect_toast
    with _pending_lock:
        batch = list(_pending_disconnects)
        _pending_disconnects.clear()
        _disconnect_timer = None
    if not batch:
        return
    best = _pick_best(batch)
    name = best.get("name") or "Unknown device"
    logger.log_event(
        event_type="disconnect",
        device_name=name,
        device_id=best.get("device_id"),
        device_class=best.get("pnp_class"),
        manufacturer=best.get("manufacturer"),
    )
    if _window:
        _window.notify_device_event("disconnect", best)
    now = time.monotonic()
    if config.get("notify_on_disconnect", True) and now - _last_disconnect_toast >= _COOLDOWN_SECS:
        notify_disconnect(name)
        _last_disconnect_toast = now


# Reference to the main window, set in main()
_window = None
_scanner: Scanner | None = None


def _handle_scan_result(result: ScanResult) -> None:
    """Receive a ScanResult from the security scanner and fan it out."""
    print(f"[Scan] {result.status.value}: {result.summary}")

    # Push interim 'scanning' updates only to the UI; don't log or toast.
    if result.status == ScanStatus.SCANNING:
        if _window:
            _window.notify_scan_result({
                "device_id": result.device_id,
                "device_name": result.device_name,
                "status": result.status.value,
                "summary": result.summary,
                "findings": [],
            })
        return

    # Log scan completions other than SKIPPED (noise).
    if result.status != ScanStatus.SKIPPED:
        driver_signed: int | None = None
        if result.driver_signed is True:
            driver_signed = 1
        elif result.driver_signed is False:
            driver_signed = 0
        logger.log_event(
            event_type="scan",
            device_name=result.device_name,
            device_id=result.device_id,
            driver_signed=driver_signed,
            scan_result=result.to_log_string(),
        )

    # Toast on threats / unsigned drivers.
    if result.status in (ScanStatus.THREATS_FOUND, ScanStatus.UNSIGNED):
        detail = result.findings[0].label if result.findings else result.summary
        notify_threat(result.device_name, detail)

    if _window:
        _window.notify_scan_result({
            "device_id": result.device_id,
            "device_name": result.device_name,
            "status": result.status.value,
            "summary": result.summary,
            "findings": [
                {"source": f.source, "label": f.label, "detail": f.detail}
                for f in result.findings
            ],
        })


def on_connect(device_info: dict, config: dict) -> None:
    """Raw WMI connect event — one per interface of a composite device.
    Scanning sees every raw event; logging/UI/toast are batched in the flush."""
    global _connect_timer
    print(f"[+] Device connected:  {device_info}")
    if _scanner is not None:
        _scanner.scan_device(device_info)
    with _pending_lock:
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
    print(f"[-] Device disconnected: {device_info}")
    with _pending_lock:
        _pending_disconnects.append(device_info)
        if _disconnect_timer is not None:
            _disconnect_timer.cancel()
        _disconnect_timer = threading.Timer(
            _DEBOUNCE_SECS, _flush_disconnects, args=(config,)
        )
        _disconnect_timer.daemon = True
        _disconnect_timer.start()


def main() -> None:
    global _window, _scanner
    config = load_config()
    print("DeviceGuard starting...")

    sync_startup(config)

    # Create Qt app and window (pass live config dict for in-place settings edits)
    app, window = create_app(config=config)
    _window = window

    # Security scanner
    _scanner = Scanner(config=config, on_result=_handle_scan_result)

    # Device monitor
    monitor = DeviceMonitor()
    monitor.register_callbacks(
        on_connect=lambda info: on_connect(info, config),
        on_disconnect=lambda info: on_disconnect(info, config),
    )
    monitor.start()

    # System tray — pystray callbacks run on the tray thread, so they must
    # not touch Qt widgets directly; request_* marshal via queued signals.
    def handle_open():
        window.request_open()

    def handle_settings():
        window.request_settings()

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
    if _scanner is not None:
        _scanner.shutdown()
    print("DeviceGuard stopped.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
