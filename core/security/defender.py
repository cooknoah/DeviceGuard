"""Windows Defender (MpCmdRun.exe) custom-path scan wrapper."""

import os
import re
import subprocess
import winreg
from pathlib import Path

from core.security.types import ScanFinding, ScanResult, ScanStatus


_MPCMDRUN_CACHE: Path | None = None


def _locate_mpcmdrun() -> Path | None:
    """Find MpCmdRun.exe. Caches the result. Returns None if unavailable."""
    global _MPCMDRUN_CACHE
    if _MPCMDRUN_CACHE is not None:
        return _MPCMDRUN_CACHE if _MPCMDRUN_CACHE.exists() else None

    candidates: list[Path] = []

    # 1. Registry: HKLM\SOFTWARE\Microsoft\Windows Defender\InstallLocation
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows Defender",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
            if install_loc:
                candidates.append(Path(install_loc) / "MpCmdRun.exe")
    except OSError:
        pass

    # 2. Standard install paths.
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    candidates.append(Path(program_files) / "Windows Defender" / "MpCmdRun.exe")
    # Platform-specific Defender (newer versions live under Platform\<version>\)
    platform_root = Path(program_data) / "Microsoft" / "Windows Defender" / "Platform"
    if platform_root.exists():
        try:
            versions = sorted(
                (p for p in platform_root.iterdir() if p.is_dir()),
                reverse=True,
            )
            for v in versions:
                candidates.append(v / "MpCmdRun.exe")
        except OSError:
            pass

    for c in candidates:
        if c.exists():
            _MPCMDRUN_CACHE = c
            return c
    return None


# Threat lines in MpCmdRun output look like:
#   Threat                  : Trojan:Win32/Wacatac.B!ml
# or
#   List of threats: ... Trojan:Win32/...
_THREAT_LINE = re.compile(r"^\s*(?:Threat|List of threats)\s*:\s*(.+?)\s*$", re.IGNORECASE)


def scan_path(
    target: str | Path,
    timeout_sec: int = 120,
) -> ScanResult:
    """Run a Defender custom-path scan on `target`. Blocks until done or timeout.

    Returns a ScanResult; callers should run this from a background thread.
    """
    target_path = str(target)
    mpcmd = _locate_mpcmdrun()
    if mpcmd is None:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.SKIPPED,
            summary="MpCmdRun.exe not found",
        )

    cmd = [str(mpcmd), "-Scan", "-ScanType", "3", "-File", target_path, "-DisableRemediation"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.ERROR,
            summary=f"defender scan timed out after {timeout_sec}s",
        )
    except OSError as exc:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.ERROR,
            summary=f"defender launch failed: {exc}",
        )

    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    findings: list[ScanFinding] = []
    for line in output.splitlines():
        m = _THREAT_LINE.match(line)
        if m:
            findings.append(ScanFinding(source="defender", label=m.group(1).strip()))

    # MpCmdRun exit codes: 0 = no malware, 2 = malware found, others = error.
    rc = proc.returncode
    if rc == 0 and not findings:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.CLEAN,
            summary=f"defender: clean ({target_path})",
        )
    if rc == 2 or findings:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.THREATS_FOUND,
            findings=findings or [ScanFinding(source="defender", label="threat detected")],
            summary=f"defender flagged {len(findings) or 1} item(s)",
        )

    snippet = output.strip().splitlines()[-1] if output.strip() else f"exit {rc}"
    return ScanResult(
        device_id=None,
        device_name=None,
        status=ScanStatus.ERROR,
        summary=f"defender error (rc={rc}): {snippet[:200]}",
    )
