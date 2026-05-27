import threading
import time
from typing import Callable

import pythoncom
import wmi as wmi_module


class DeviceMonitor:
    """Watches for PnP device connection and disconnection events via WMI."""

    def __init__(self):
        self._on_connect: Callable[[dict], None] | None = None
        self._on_disconnect: Callable[[dict], None] | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def register_callbacks(
        self,
        on_connect: Callable[[dict], None] | None = None,
        on_disconnect: Callable[[dict], None] | None = None,
    ) -> None:
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

    def start(self) -> None:
        """Spin up daemon threads that listen for WMI creation/deletion events."""
        self._stop_event.clear()

        self._thread_connect = threading.Thread(
            target=self._watch_events,
            args=("creation",),
            daemon=True,
            name="DeviceMonitor-connect",
        )
        self._thread_disconnect = threading.Thread(
            target=self._watch_events,
            args=("deletion",),
            daemon=True,
            name="DeviceMonitor-disconnect",
        )
        self._thread_connect.start()
        self._thread_disconnect.start()

    def stop(self) -> None:
        """Signal the watcher threads to stop."""
        self._stop_event.set()

    def _watch_events(self, event_kind: str) -> None:
        """Run on a background thread. Subscribes to WMI instance events."""
        pythoncom.CoInitialize()
        try:
            c = wmi_module.WMI()

            if event_kind == "creation":
                watcher = c.Win32_PnPEntity.watch_for("creation", delay_secs=1)
            else:
                watcher = c.Win32_PnPEntity.watch_for("deletion", delay_secs=1)

            while not self._stop_event.is_set():
                try:
                    event = watcher(timeout_ms=1000)
                except wmi_module.x_wmi_timed_out:
                    continue

                device_info = {
                    "name": getattr(event, "Name", None),
                    "device_id": getattr(event, "DeviceID", None),
                    "pnp_class": getattr(event, "PNPClass", None),
                    "manufacturer": getattr(event, "Manufacturer", None),
                }

                if event_kind == "creation" and self._on_connect:
                    try:
                        self._on_connect(device_info)
                    except Exception as exc:
                        print(f"[DeviceMonitor] on_connect callback error: {exc}")
                elif event_kind == "deletion" and self._on_disconnect:
                    try:
                        self._on_disconnect(device_info)
                    except Exception as exc:
                        print(f"[DeviceMonitor] on_disconnect callback error: {exc}")

        except Exception as exc:
            print(f"[DeviceMonitor] WMI watcher ({event_kind}) error: {exc}")
        finally:
            pythoncom.CoUninitialize()
