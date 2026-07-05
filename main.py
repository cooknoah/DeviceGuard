"""DeviceGuard — entry point.

Loads config, starts the device monitor, tray icon, toast notifications,
and PyQt6 main window.
"""

import sys

from core.config import load_config
from core import logger
from core.monitor import DeviceMonitor
from core.event_batch import EventBatch
from core.notifier import notify_connect, notify_disconnect, notify_threat
from core.tray import TrayManager
from core.startup import sync_startup
from core.security.scanner import Scanner
from core.security.types import ScanResult, ScanStatus
from ui.app import create_app


def _emit_device_event(event_type: str, best: dict) -> None:
    """Marshal a flushed device event to the UI, if the window exists yet."""
    if _window:
        _window.notify_device_event(event_type, best)


_connect_batch = EventBatch(
    "connect", "notify_on_connect", notify_connect, on_flush=_emit_device_event
)
_disconnect_batch = EventBatch(
    "disconnect", "notify_on_disconnect", notify_disconnect, on_flush=_emit_device_event
)


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
    print(f"[+] Device connected:  {device_info}")
    if _scanner is not None:
        _scanner.scan_device(device_info)
    _connect_batch.add(device_info, config)


def on_disconnect(device_info: dict, config: dict) -> None:
    print(f"[-] Device disconnected: {device_info}")
    _disconnect_batch.add(device_info, config)


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
