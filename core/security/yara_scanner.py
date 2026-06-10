"""YARA rule-based file scanning. Degrades gracefully when yara-python is unavailable."""

import os
import threading
import time
from pathlib import Path

from core.security.types import ScanFinding, ScanResult, ScanStatus

try:
    import yara  # type: ignore[import-not-found]
    _YARA_AVAILABLE = True
    _YARA_IMPORT_ERROR: str | None = None
except Exception as _exc:  # ImportError or runtime DLL load failure
    yara = None  # type: ignore[assignment]
    _YARA_AVAILABLE = False
    _YARA_IMPORT_ERROR = str(_exc)


_PROJECT_ROOT = Path(__file__).parent.parent.parent

_compiled_rules = None
_compile_lock = threading.Lock()
_compile_paths_sig: tuple[str, ...] | None = None


def is_available() -> bool:
    return _YARA_AVAILABLE


def import_error() -> str | None:
    return _YARA_IMPORT_ERROR


def _collect_rule_files(rule_dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for d in rule_dirs:
        p = Path(d)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        if p.exists():
            files.extend(sorted(p.glob("*.yar")))
            files.extend(sorted(p.glob("*.yara")))
    return files


def _ensure_compiled(rule_dirs: list[str]):
    """Compile (and cache) YARA rules from the given directories."""
    global _compiled_rules, _compile_paths_sig
    files = _collect_rule_files(rule_dirs)
    sig = tuple(str(f) for f in files)
    with _compile_lock:
        if _compiled_rules is not None and _compile_paths_sig == sig:
            return _compiled_rules
        if not files:
            _compiled_rules = None
            _compile_paths_sig = sig
            return None
        filepaths = {f"r{i}": str(p) for i, p in enumerate(files)}
        _compiled_rules = yara.compile(filepaths=filepaths)
        _compile_paths_sig = sig
        return _compiled_rules


def scan_drive(
    drive_path: str | Path,
    rule_dirs: list[str],
    max_file_mb: int = 50,
    max_depth: int = 2,
    timeout_sec: int = 120,
) -> ScanResult:
    """Walk `drive_path` up to `max_depth` levels, YARA-scanning files under the size cap.

    `max_depth` of 0 means only files in the root; 1 includes one subdirectory level, etc.
    Stops early if `timeout_sec` is exceeded. Designed for background-thread use.
    """
    if not _YARA_AVAILABLE:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.SKIPPED,
            summary=f"yara unavailable: {_YARA_IMPORT_ERROR}",
        )

    root = Path(drive_path)
    if not root.exists():
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.SKIPPED,
            summary=f"path not accessible: {drive_path}",
        )

    try:
        rules = _ensure_compiled(rule_dirs)
    except Exception as exc:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.ERROR,
            summary=f"yara compile failed: {exc}",
        )
    if rules is None:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.SKIPPED,
            summary="no yara rules found",
        )

    max_bytes = max_file_mb * 1024 * 1024
    root_depth = len(root.parts)
    deadline = time.monotonic() + timeout_sec
    findings: list[ScanFinding] = []
    files_scanned = 0
    timed_out = False

    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if time.monotonic() > deadline:
                timed_out = True
                break

            depth = len(Path(dirpath).parts) - root_depth
            if depth > max_depth:
                dirnames[:] = []
                continue

            for fname in filenames:
                if time.monotonic() > deadline:
                    timed_out = True
                    break
                fp = Path(dirpath) / fname
                try:
                    size = fp.stat().st_size
                except OSError:
                    continue
                if size > max_bytes or size == 0:
                    continue
                try:
                    matches = rules.match(str(fp), timeout=10)
                except Exception:
                    continue
                files_scanned += 1
                for m in matches:
                    findings.append(ScanFinding(
                        source="yara",
                        label=str(m.rule),
                        detail=str(fp),
                    ))
            if timed_out:
                break
    except Exception as exc:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.ERROR,
            summary=f"yara scan failed: {exc}",
        )

    if findings:
        return ScanResult(
            device_id=None,
            device_name=None,
            status=ScanStatus.THREATS_FOUND,
            findings=findings,
            summary=f"yara: {len(findings)} match(es) in {files_scanned} file(s)",
        )
    suffix = " (timed out)" if timed_out else ""
    return ScanResult(
        device_id=None,
        device_name=None,
        status=ScanStatus.CLEAN,
        summary=f"yara: clean ({files_scanned} files scanned){suffix}",
    )
