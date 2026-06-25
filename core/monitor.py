import threading
import time
from typing import Callable

import pythoncom
import wmi as wmi_module

from core import device_names

# Names that identify a generic interface rather than the actual product.
_GENERIC_KEYWORDS = (
    "USB Input Device",
    "USB Composite Device",
    "HID-compliant",
    "USB Root Hub",
    "XINPUT compatible",
    "HID-conformant",
    "USB Mass Storage Device",
    "HID Keyboard Device",
    "HID Mouse Device",
    "USB Audio Device",
    "USB Serial Device",
    "Bluetooth Device (",
)

# Device ID prefixes for externally-attached buses.
_EXTERNAL_PREFIXES = ("USB\\", "USBSTOR\\", "HID\\", "BTHENUM\\", "BTHLE\\", "WPD\\")


def is_generic_name(name: str | None) -> bool:
    name = name or ""
    return any(kw.lower() in name.lower() for kw in _GENERIC_KEYWORDS)


def pick_best_device(devices: list[dict]) -> dict:
    """Pick the most descriptive entry from a group of interface records.

    If every entry has a generic Windows label, try to resolve the real
    product name (bus-reported device string, then usb.ids)."""
    best = None
    for d in devices:
        if d.get("name") and not is_generic_name(d["name"]):
            best = d
            break
    if best is None:
        for d in devices:
            if d.get("name"):
                best = d
                break
    if best is None:
        best = devices[0] if devices else {}

    if is_generic_name(best.get("name")):
        resolved = device_names.resolve_name(devices, is_generic_name)
        if resolved:
            best = {**best, "name": resolved}
    return best


# Cache of the last full Win32_PnPEntity snapshot — the query takes
# seconds, so UI filter/category changes reuse it instead of re-querying.
_cache_lock = threading.Lock()
_cached_devices: list[dict] | None = None
_cache_time: float = 0.0


def _query_devices() -> list[dict]:
    """Full Win32_PnPEntity enumeration. Slow (seconds); background threads only."""
    pythoncom.CoInitialize()
    try:
        c = wmi_module.WMI()
        devices = []
        for dev in c.Win32_PnPEntity():
            devices.append({
                "name": dev.Name,
                "device_id": dev.DeviceID,
                "pnp_class": dev.PNPClass or "",
                "manufacturer": dev.Manufacturer,
                "status": dev.Status,
            })
        return devices
    except Exception as exc:
        print(f"[DeviceMonitor] device query error: {exc}")
        return []
    finally:
        pythoncom.CoUninitialize()


def cache_is_fresh(max_age_sec: float) -> bool:
    """True if a cached snapshot exists and is younger than max_age_sec.

    Lets callers (the UI) decide whether a filter change can be served
    synchronously from cache instead of paying for a background WMI query."""
    with _cache_lock:
        return (
            _cached_devices is not None
            and time.monotonic() - _cache_time < max_age_sec
        )


def get_connected_devices(
    class_filter: str | None = None,
    max_age_sec: float = 0.0,
) -> list[dict]:
    """Currently connected PnP devices, optionally filtered by PNPClass.

    With max_age_sec > 0, a cached snapshot at most that old is reused —
    use this for UI filter switches so they don't pay the multi-second
    WMI query. max_age_sec=0 always re-queries."""
    global _cached_devices, _cache_time
    devices = None
    if max_age_sec > 0:
        with _cache_lock:
            if _cached_devices is not None and time.monotonic() - _cache_time < max_age_sec:
                devices = list(_cached_devices)
    if devices is None:
        devices = _query_devices()
        with _cache_lock:
            _cached_devices = devices
            _cache_time = time.monotonic()
    if class_filter:
        devices = [
            d for d in devices
            if (d.get("pnp_class") or "").lower() == class_filter.lower()
        ]
    return devices


def get_external_devices(max_age_sec: float = 0.0) -> list[dict]:
    """Externally-attached devices, grouped one row per physical device.

    Filters Win32_PnPEntity to external buses (USB, HID, Bluetooth, WPD),
    drops root hubs, and collapses the per-interface entries of composite
    devices by their shared VID&PID, keeping the best-named representative.
    """
    grouped: dict[str, list[dict]] = {}
    for d in get_connected_devices(max_age_sec=max_age_sec):
        dev_id = (d.get("device_id") or "").upper()
        if not dev_id.startswith(_EXTERNAL_PREFIXES):
            continue
        if "ROOT_HUB" in dev_id:
            continue
        if d.get("pnp_class") == "USB" and "hub" in (d.get("name") or "").lower():
            continue
        m = device_names.VIDPID_RE.search(dev_id)
        key = m.group(0).upper() if m else dev_id
        grouped.setdefault(key, []).append(d)

    out = []
    for members in grouped.values():
        best = dict(pick_best_device(members))
        best["interfaces"] = len(members)
        out.append(best)
    return out


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
