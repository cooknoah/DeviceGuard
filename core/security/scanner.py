"""Scanner orchestrator.

For storage devices: waits for a drive letter to appear, then runs Defender + YARA.
For other devices: runs the driver signature check (first time per device_id).
Results are dispatched to a user-supplied callback as ScanResult objects.
"""

import ctypes
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from core.security import defender, driver_check, yara_scanner
from core.security.types import ScanFinding, ScanResult, ScanStatus

ResultCallback = Callable[[ScanResult], None]

# Win32 GetDriveType return values.
_DRIVE_REMOVABLE = 2
_DRIVE_FIXED = 3

_STORAGE_HINTS = ("usbstor", "diskdrive", "wpd")


def _is_storage(device_info: dict) -> bool:
    cls = (device_info.get("pnp_class") or "").lower()
    dev_id = (device_info.get("device_id") or "").lower()
    if cls in ("diskdrive", "wpd", "usb"):
        # Class "USB" is ambiguous — also check the device ID prefix
        if cls == "usb" and not any(h in dev_id for h in _STORAGE_HINTS):
            return False
        return True
    return any(h in dev_id for h in _STORAGE_HINTS)


def _list_drives() -> list[tuple[str, int]]:
    """Return (drive_root, drive_type) for all currently mounted drives."""
    kernel32 = ctypes.windll.kernel32
    mask = kernel32.GetLogicalDrives()
    out = []
    for i, letter in enumerate(string.ascii_uppercase):
        if mask & (1 << i):
            root = f"{letter}:\\"
            dtype = kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
            out.append((root, dtype))
    return out


def _list_removable_drives() -> set[str]:
    return {root for root, dtype in _list_drives() if dtype == _DRIVE_REMOVABLE}


class Scanner:
    """Manages background scan execution for device events."""

    def __init__(
        self,
        config: dict,
        on_result: ResultCallback,
        max_workers: int = 2,
    ):
        self._config = config
        self._on_result = on_result
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="scanner",
        )
        self._driver_checked: set[str] = set()
        self._driver_lock = threading.Lock()
        # Drives already present or claimed by a scan; guarded by _baseline_lock
        # so concurrent storage scans each claim a distinct new drive.
        self._baseline_lock = threading.Lock()
        self._removable_baseline: set[str] = _list_removable_drives()

    def _claim_new_drive(
        self,
        timeout_sec: float = 8.0,
        poll_interval: float = 0.4,
    ) -> str | None:
        """Poll until a removable drive appears that isn't in the baseline,
        atomically claiming it so no other concurrent scan picks it up."""
        deadline = time.monotonic() + timeout_sec
        while True:
            current = _list_removable_drives()
            with self._baseline_lock:
                # Forget unplugged drives so a re-plug is detected as new.
                self._removable_baseline &= current
                for root in current - self._removable_baseline:
                    if Path(root).exists():
                        self._removable_baseline.add(root)
                        return root
            if time.monotonic() >= deadline:
                return None
            time.sleep(poll_interval)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ── Public entry point ──
    def scan_device(self, device_info: dict) -> None:
        """Dispatch a scan for a freshly-connected device. Non-blocking."""
        if _is_storage(device_info):
            if not self._config.get("auto_scan_usb", True):
                return
            self._executor.submit(self._run_storage_scan, device_info)
        else:
            if not self._config.get("enable_driver_check", True):
                return
            self._executor.submit(self._run_driver_check, device_info)

    # ── Driver check (non-storage) ──
    def _run_driver_check(self, device_info: dict) -> None:
        device_id = device_info.get("device_id")
        if not device_id:
            return
        with self._driver_lock:
            if device_id in self._driver_checked:
                return
            self._driver_checked.add(device_id)
        try:
            result = driver_check.check_device_driver(device_id, device_info.get("name"))
        except Exception as exc:
            result = ScanResult(
                device_id=device_id,
                device_name=device_info.get("name"),
                status=ScanStatus.ERROR,
                summary=f"driver check crashed: {exc}",
            )
        # Suppress noise: don't surface clean/skipped driver checks.
        if result.status in (ScanStatus.UNSIGNED, ScanStatus.THREATS_FOUND, ScanStatus.ERROR):
            self._emit(result)

    # ── Storage scan (Defender + YARA) ──
    def _run_storage_scan(self, device_info: dict) -> None:
        device_id = device_info.get("device_id")
        device_name = device_info.get("name")

        # Notify UI that a scan is starting.
        self._emit(ScanResult(
            device_id=device_id,
            device_name=device_name,
            status=ScanStatus.SCANNING,
            summary="waiting for drive to mount",
        ))

        drive_root = self._claim_new_drive()
        if drive_root is None:
            # No new removable drive showed up — probably not a mass-storage device.
            return

        findings: list[ScanFinding] = []
        statuses: list[ScanStatus] = []
        summaries: list[str] = []

        # Defender scan.
        if self._config.get("defender_scan_enabled", True):
            self._emit(ScanResult(
                device_id=device_id,
                device_name=device_name,
                status=ScanStatus.SCANNING,
                summary=f"defender scanning {drive_root}",
            ))
            timeout = int(self._config.get("scan_timeout_sec", 120))
            d_result = defender.scan_path(drive_root, timeout_sec=timeout)
            findings.extend(d_result.findings)
            statuses.append(d_result.status)
            summaries.append(d_result.summary)

        # YARA scan.
        if self._config.get("enable_yara_scan", True):
            self._emit(ScanResult(
                device_id=device_id,
                device_name=device_name,
                status=ScanStatus.SCANNING,
                summary=f"yara scanning {drive_root}",
            ))
            rule_dirs = self._config.get(
                "yara_rules_paths",
                ["rules/default", self._config.get("custom_rules_dir", "rules/custom")],
            )
            y_result = yara_scanner.scan_drive(
                drive_root,
                rule_dirs=rule_dirs,
                max_file_mb=int(self._config.get("scan_max_file_mb", 50)),
                max_depth=int(self._config.get("yara_scan_depth", 2)),
                timeout_sec=int(self._config.get("scan_timeout_sec", 120)),
            )
            findings.extend(y_result.findings)
            statuses.append(y_result.status)
            summaries.append(y_result.summary)

        # Aggregate.
        if not statuses:
            return
        if ScanStatus.THREATS_FOUND in statuses:
            agg = ScanStatus.THREATS_FOUND
        elif ScanStatus.ERROR in statuses:
            agg = ScanStatus.ERROR
        elif all(s == ScanStatus.SKIPPED for s in statuses):
            agg = ScanStatus.SKIPPED
        else:
            agg = ScanStatus.CLEAN

        self._emit(ScanResult(
            device_id=device_id,
            device_name=device_name,
            status=agg,
            findings=findings,
            summary=f"{drive_root} — " + "; ".join(s for s in summaries if s),
        ))

    # ── Internal ──
    def _emit(self, result: ScanResult) -> None:
        try:
            self._on_result(result)
        except Exception as exc:
            print(f"[Scanner] result callback error: {exc}")
