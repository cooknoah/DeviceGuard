"""Friendly device-name resolution.

Windows often labels devices generically ("HID Keyboard Device"). Two better
sources exist:

1. The bus-reported device description — the product string the device
   itself reports over USB (DEVPKEY_Device_BusReportedDeviceDesc), queried
   locally via cfgmgr32. This is usually the real marketing name.
2. The public usb.ids database (bundled at assets/usb.ids), mapping the
   USB vendor/product IDs embedded in every device ID to names.
"""

import ctypes
import re
import threading
from ctypes import wintypes

from core.paths import resource_path

_VIDPID_RE = re.compile(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", re.IGNORECASE)

# ── Bus-reported device description (cfgmgr32) ──


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _DEVPROPKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_ulong)]


# DEVPKEY_Device_BusReportedDeviceDesc = {540b947e-8b40-45bc-a8a2-6a0b894cbda2}, 4
_BUS_REPORTED_DESC = _DEVPROPKEY(
    _GUID(
        0x540B947E, 0x8B40, 0x45BC,
        (ctypes.c_ubyte * 8)(0xA8, 0xA2, 0x6A, 0x0B, 0x89, 0x4C, 0xBD, 0xA2),
    ),
    4,
)

_CR_SUCCESS = 0
_DEVPROP_TYPE_STRING = 0x12

_cfgmgr = ctypes.windll.cfgmgr32

_bus_name_cache: dict[str, str | None] = {}
_bus_cache_lock = threading.Lock()


def bus_reported_name(instance_id: str) -> str | None:
    """The product string the device itself reports (e.g. the real model
    name), or None if unavailable. Cheap (~ms); results are cached."""
    with _bus_cache_lock:
        if instance_id in _bus_name_cache:
            return _bus_name_cache[instance_id]

    name: str | None = None
    try:
        devinst = ctypes.c_uint32(0)
        ret = _cfgmgr.CM_Locate_DevNodeW(
            ctypes.byref(devinst), ctypes.c_wchar_p(instance_id), 0
        )
        if ret == _CR_SUCCESS:
            prop_type = ctypes.c_ulong(0)
            buf = ctypes.create_unicode_buffer(512)
            size = ctypes.c_ulong(ctypes.sizeof(buf))
            ret = _cfgmgr.CM_Get_DevNode_PropertyW(
                devinst,
                ctypes.byref(_BUS_REPORTED_DESC),
                ctypes.byref(prop_type),
                ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)),
                ctypes.byref(size),
                0,
            )
            if ret == _CR_SUCCESS and prop_type.value == _DEVPROP_TYPE_STRING:
                value = buf.value.strip()
                if value:
                    name = value
    except Exception:
        name = None

    with _bus_cache_lock:
        _bus_name_cache[instance_id] = name
    return name


# ── usb.ids vendor/product database ──

_usb_ids: dict[str, tuple[str, dict[str, str]]] | None = None
_usb_ids_lock = threading.Lock()


def _load_usb_ids() -> dict[str, tuple[str, dict[str, str]]]:
    """Parse assets/usb.ids into {vid: (vendor, {pid: product})}."""
    global _usb_ids
    with _usb_ids_lock:
        if _usb_ids is not None:
            return _usb_ids
        db: dict[str, tuple[str, dict[str, str]]] = {}
        path = resource_path("assets", "usb.ids")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                vendor_id = None
                for line in f:
                    if line.startswith("#") or not line.rstrip():
                        continue
                    # Device class section ends the vendor list.
                    if line.startswith("C "):
                        break
                    if line.startswith("\t\t"):
                        continue
                    if line.startswith("\t"):
                        if vendor_id is not None:
                            pid, _, product = line.strip().partition("  ")
                            if product:
                                db[vendor_id][1][pid.lower()] = product.strip()
                        continue
                    vid, _, vendor = line.rstrip("\n").partition("  ")
                    vid = vid.strip().lower()
                    if len(vid) == 4 and vendor:
                        vendor_id = vid
                        db[vid] = (vendor.strip(), {})
                    else:
                        vendor_id = None
        except OSError:
            pass
        _usb_ids = db
        return db


def usb_ids_lookup(device_id: str) -> tuple[str | None, str | None]:
    """(vendor, product) from the bundled usb.ids for a device ID, or Nones."""
    m = _VIDPID_RE.search(device_id or "")
    if not m:
        return None, None
    db = _load_usb_ids()
    entry = db.get(m.group(1).lower())
    if not entry:
        return None, None
    vendor, products = entry
    return vendor, products.get(m.group(2).lower())


# ── Combined resolution ──


def resolve_name(devices: list[dict], is_generic) -> str | None:
    """Best human name for a group of interface records of one physical
    device, consulting bus-reported strings and usb.ids. None if nothing
    better than the existing (generic) names was found."""
    # The device's own product string, from any interface.
    for d in devices:
        dev_id = d.get("device_id") or ""
        if not dev_id:
            continue
        reported = bus_reported_name(dev_id)
        if reported and not is_generic(reported):
            return reported

    # usb.ids fallback.
    for d in devices:
        vendor, product = usb_ids_lookup(d.get("device_id") or "")
        if product:
            return f"{vendor} {product}" if vendor else product
        if vendor:
            # Vendor known but product unlisted — qualify the generic name.
            base = d.get("name") or "Device"
            return f"{vendor} {base}"
    return None
