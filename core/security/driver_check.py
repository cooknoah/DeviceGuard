"""Unsigned driver detection via Win32_PnPSignedDriver."""

import pythoncom
import wmi as wmi_module

from core.security.types import ScanFinding, ScanResult, ScanStatus


def check_device_driver(device_id: str | None, device_name: str | None) -> ScanResult:
    """Return a ScanResult indicating whether the device's driver is signed.

    Designed to be called from a background thread — initializes COM itself.
    Returns ScanStatus.SKIPPED when device_id is missing or no driver row is found.
    """
    if not device_id:
        return ScanResult(
            device_id=device_id,
            device_name=device_name,
            status=ScanStatus.SKIPPED,
            summary="no device id",
        )

    pythoncom.CoInitialize()
    try:
        c = wmi_module.WMI()
        # DeviceID may contain backslashes; WMI's WQL needs them escaped.
        escaped = device_id.replace("\\", "\\\\").replace("'", "\\'")
        rows = c.query(
            f"SELECT DeviceName, IsSigned, Signer "
            f"FROM Win32_PnPSignedDriver WHERE DeviceID='{escaped}'"
        )
        if not rows:
            return ScanResult(
                device_id=device_id,
                device_name=device_name,
                status=ScanStatus.SKIPPED,
                summary="no driver record",
            )

        row = rows[0]
        is_signed = bool(getattr(row, "IsSigned", False))
        signer = getattr(row, "Signer", None) or "unknown"
        drv_name = getattr(row, "DeviceName", None) or device_name or "driver"

        if is_signed:
            return ScanResult(
                device_id=device_id,
                device_name=device_name,
                status=ScanStatus.CLEAN,
                summary=f"signed by {signer}",
                driver_signed=True,
            )

        finding = ScanFinding(
            source="driver",
            label=drv_name,
            detail=f"unsigned (signer: {signer})",
        )
        return ScanResult(
            device_id=device_id,
            device_name=device_name,
            status=ScanStatus.UNSIGNED,
            findings=[finding],
            summary=f"unsigned driver: {drv_name}",
            driver_signed=False,
        )
    except Exception as exc:
        return ScanResult(
            device_id=device_id,
            device_name=device_name,
            status=ScanStatus.ERROR,
            summary=f"driver query failed: {exc}",
        )
    finally:
        pythoncom.CoUninitialize()
