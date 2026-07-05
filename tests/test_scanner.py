"""Scanner orchestration.

The OS-facing collaborators (Defender, YARA, driver check, drive enumeration)
are stubbed so the orchestration logic — dispatch, config gating, driver-check
dedup/noise-suppression, storage-scan status aggregation, and new-drive
claiming — is exercised deterministically without hardware or a thread pool.
"""

import pytest

from core.security import defender, driver_check, scanner as scanner_mod, yara_scanner
from core.security.scanner import Scanner, _is_storage
from core.security.types import ScanFinding, ScanResult, ScanStatus


def _result(status, findings=None, summary="", **kw):
    return ScanResult(
        device_id=kw.get("device_id", "dev"),
        device_name=kw.get("device_name", "Dev"),
        status=status,
        findings=findings or [],
        summary=summary,
        driver_signed=kw.get("driver_signed"),
    )


class SyncExecutor:
    """Runs submitted work inline so dispatch is synchronous in tests."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

    def shutdown(self, *a, **k):
        pass


@pytest.fixture
def make_scanner(monkeypatch):
    """Factory: build a Scanner with an empty drive baseline, a synchronous
    executor, and an emit-capturing callback. Returns (scanner, emits)."""
    monkeypatch.setattr(scanner_mod, "_list_removable_drives", lambda: set())

    def _factory(config=None):
        emits = []
        sc = Scanner(config=config or {}, on_result=emits.append)
        sc._executor.shutdown(wait=False)
        sc._executor = SyncExecutor()
        return sc, emits

    return _factory


def _finals(emits):
    """Emits that aren't interim SCANNING progress updates."""
    return [e for e in emits if e.status != ScanStatus.SCANNING]


# ── _is_storage classification ──

@pytest.mark.parametrize("info,expected", [
    ({"pnp_class": "DiskDrive", "device_id": "IDE\\X"}, True),
    ({"pnp_class": "WPD", "device_id": "WPD\\X"}, True),
    ({"pnp_class": "USB", "device_id": "USBSTOR\\DISK&VEN"}, True),   # usb + storage hint
    ({"pnp_class": "USB", "device_id": "USB\\VID_046D&PID_C52B"}, False),  # usb, no hint
    ({"pnp_class": "HIDClass", "device_id": "USBSTOR\\X"}, True),     # hint in id wins
    ({"pnp_class": "Keyboard", "device_id": "HID\\X"}, False),
    ({}, False),
])
def test_is_storage(info, expected):
    assert _is_storage(info) is expected


# ── scan_device dispatch + config gating ──

def test_storage_device_dispatches_storage_scan(make_scanner):
    sc, _ = make_scanner({"auto_scan_usb": True})
    calls = []
    sc._run_storage_scan = lambda info: calls.append(info)
    sc.scan_device({"pnp_class": "DiskDrive", "device_id": "IDE\\X"})
    assert len(calls) == 1


def test_storage_scan_skipped_when_auto_scan_off(make_scanner):
    sc, _ = make_scanner({"auto_scan_usb": False})
    calls = []
    sc._run_storage_scan = lambda info: calls.append(info)
    sc.scan_device({"pnp_class": "DiskDrive", "device_id": "IDE\\X"})
    assert calls == []


def test_nonstorage_device_dispatches_driver_check(make_scanner):
    sc, _ = make_scanner({"enable_driver_check": True})
    calls = []
    sc._run_driver_check = lambda info: calls.append(info)
    sc.scan_device({"pnp_class": "Keyboard", "device_id": "HID\\X"})
    assert len(calls) == 1


def test_driver_check_skipped_when_disabled(make_scanner):
    sc, _ = make_scanner({"enable_driver_check": False})
    calls = []
    sc._run_driver_check = lambda info: calls.append(info)
    sc.scan_device({"pnp_class": "Keyboard", "device_id": "HID\\X"})
    assert calls == []


# ── _run_driver_check: dedup, noise suppression, errors ──

def test_driver_check_emits_unsigned(make_scanner, monkeypatch):
    sc, emits = make_scanner()
    monkeypatch.setattr(
        driver_check, "check_device_driver",
        lambda did, name: _result(ScanStatus.UNSIGNED, summary="unsigned!"),
    )
    sc._run_driver_check({"device_id": "HID\\X", "name": "Kbd"})
    assert [e.status for e in emits] == [ScanStatus.UNSIGNED]


@pytest.mark.parametrize("status", [ScanStatus.CLEAN, ScanStatus.SKIPPED])
def test_driver_check_suppresses_clean_and_skipped(make_scanner, monkeypatch, status):
    sc, emits = make_scanner()
    monkeypatch.setattr(driver_check, "check_device_driver",
                        lambda did, name: _result(status))
    sc._run_driver_check({"device_id": "HID\\X", "name": "Kbd"})
    assert emits == []  # noise: not surfaced


def test_driver_check_dedupes_per_device_id(make_scanner, monkeypatch):
    sc, emits = make_scanner()
    calls = []
    monkeypatch.setattr(
        driver_check, "check_device_driver",
        lambda did, name: calls.append(did) or _result(ScanStatus.UNSIGNED),
    )
    info = {"device_id": "HID\\X", "name": "Kbd"}
    sc._run_driver_check(info)
    sc._run_driver_check(info)  # same id → skipped before the check runs
    assert calls == ["HID\\X"]
    assert len(emits) == 1


def test_driver_check_no_device_id_is_noop(make_scanner, monkeypatch):
    sc, emits = make_scanner()
    called = []
    monkeypatch.setattr(driver_check, "check_device_driver",
                        lambda did, name: called.append(1) or _result(ScanStatus.UNSIGNED))
    sc._run_driver_check({"device_id": None, "name": "Kbd"})
    assert called == [] and emits == []


def test_driver_check_crash_emits_error(make_scanner, monkeypatch):
    sc, emits = make_scanner()

    def boom(did, name):
        raise RuntimeError("wmi exploded")

    monkeypatch.setattr(driver_check, "check_device_driver", boom)
    sc._run_driver_check({"device_id": "HID\\X", "name": "Kbd"})
    assert len(emits) == 1
    assert emits[0].status == ScanStatus.ERROR
    assert "wmi exploded" in emits[0].summary


# ── _run_storage_scan: aggregation precedence ──

def _stub_scans(monkeypatch, defender_res, yara_res):
    monkeypatch.setattr(defender, "scan_path", lambda path, timeout_sec=120: defender_res)
    monkeypatch.setattr(yara_scanner, "scan_drive", lambda drive, **kw: yara_res)


def _storage_config():
    return {"defender_scan_enabled": True, "enable_yara_scan": True}


def test_storage_both_clean_aggregates_clean(make_scanner, monkeypatch):
    sc, emits = make_scanner(_storage_config())
    sc._claim_new_drive = lambda: "E:\\"
    _stub_scans(monkeypatch, _result(ScanStatus.CLEAN, summary="def ok"),
                _result(ScanStatus.CLEAN, summary="yara ok"))
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    finals = _finals(emits)
    assert len(finals) == 1
    assert finals[0].status == ScanStatus.CLEAN
    assert "E:\\" in finals[0].summary


def test_storage_threats_win_over_everything(make_scanner, monkeypatch):
    sc, emits = make_scanner(_storage_config())
    sc._claim_new_drive = lambda: "E:\\"
    threat = _result(ScanStatus.THREATS_FOUND,
                     findings=[ScanFinding("defender", "Trojan:X")], summary="bad")
    _stub_scans(monkeypatch, _result(ScanStatus.ERROR, summary="def err"), threat)
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    final = _finals(emits)[0]
    assert final.status == ScanStatus.THREATS_FOUND
    assert any(f.label == "Trojan:X" for f in final.findings)


def test_storage_error_beats_clean(make_scanner, monkeypatch):
    sc, emits = make_scanner(_storage_config())
    sc._claim_new_drive = lambda: "E:\\"
    _stub_scans(monkeypatch, _result(ScanStatus.ERROR, summary="def err"),
                _result(ScanStatus.CLEAN, summary="yara ok"))
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    assert _finals(emits)[0].status == ScanStatus.ERROR


def test_storage_all_skipped_aggregates_skipped(make_scanner, monkeypatch):
    sc, emits = make_scanner(_storage_config())
    sc._claim_new_drive = lambda: "E:\\"
    _stub_scans(monkeypatch, _result(ScanStatus.SKIPPED), _result(ScanStatus.SKIPPED))
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    assert _finals(emits)[0].status == ScanStatus.SKIPPED


def test_storage_findings_merged_from_both_scans(make_scanner, monkeypatch):
    sc, emits = make_scanner(_storage_config())
    sc._claim_new_drive = lambda: "E:\\"
    _stub_scans(
        monkeypatch,
        _result(ScanStatus.THREATS_FOUND, findings=[ScanFinding("defender", "D1")]),
        _result(ScanStatus.THREATS_FOUND, findings=[ScanFinding("yara", "Y1")]),
    )
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    labels = {f.label for f in _finals(emits)[0].findings}
    assert labels == {"D1", "Y1"}


def test_storage_no_new_drive_emits_only_scanning(make_scanner, monkeypatch):
    sc, emits = make_scanner(_storage_config())
    sc._claim_new_drive = lambda: None
    called = []
    monkeypatch.setattr(defender, "scan_path",
                        lambda *a, **k: called.append("def") or _result(ScanStatus.CLEAN))
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    assert called == []            # scans never ran
    assert _finals(emits) == []    # only the interim SCANNING update was emitted
    assert emits and emits[0].status == ScanStatus.SCANNING


def test_storage_respects_disabled_scans(make_scanner, monkeypatch):
    sc, emits = make_scanner({"defender_scan_enabled": False, "enable_yara_scan": False})
    sc._claim_new_drive = lambda: "E:\\"
    called = []
    monkeypatch.setattr(defender, "scan_path", lambda *a, **k: called.append("d"))
    monkeypatch.setattr(yara_scanner, "scan_drive", lambda *a, **k: called.append("y"))
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    assert called == []            # neither engine invoked
    assert _finals(emits) == []    # no statuses → no aggregate emitted


def test_storage_only_defender_when_yara_disabled(make_scanner, monkeypatch):
    sc, emits = make_scanner({"defender_scan_enabled": True, "enable_yara_scan": False})
    sc._claim_new_drive = lambda: "E:\\"
    monkeypatch.setattr(defender, "scan_path",
                        lambda *a, **k: _result(ScanStatus.CLEAN, summary="def ok"))
    called = []
    monkeypatch.setattr(yara_scanner, "scan_drive", lambda *a, **k: called.append("y"))
    sc._run_storage_scan({"device_id": "USBSTOR\\X", "name": "Stick"})
    assert called == []
    assert _finals(emits)[0].status == ScanStatus.CLEAN


# ── _claim_new_drive: baseline bookkeeping ──

def test_claim_returns_new_drive_and_records_it(make_scanner, monkeypatch):
    sc, _ = make_scanner()
    sc._removable_baseline = {"C:\\"}
    monkeypatch.setattr(scanner_mod, "_list_removable_drives", lambda: {"C:\\", "E:\\"})
    monkeypatch.setattr(scanner_mod.Path, "exists", lambda self: True)

    claimed = sc._claim_new_drive(timeout_sec=0)
    assert claimed == "E:\\"
    assert "E:\\" in sc._removable_baseline  # claimed so a concurrent scan won't repeat it


def test_claim_forgets_unplugged_drive(make_scanner, monkeypatch):
    sc, _ = make_scanner()
    sc._removable_baseline = {"F:\\"}                # was present
    monkeypatch.setattr(scanner_mod, "_list_removable_drives", lambda: set())  # now gone
    monkeypatch.setattr(scanner_mod.Path, "exists", lambda self: True)

    assert sc._claim_new_drive(timeout_sec=0) is None
    assert "F:\\" not in sc._removable_baseline     # forgotten, so a re-plug counts as new


def test_claim_times_out_when_nothing_new(make_scanner, monkeypatch):
    sc, _ = make_scanner()
    sc._removable_baseline = {"C:\\"}
    monkeypatch.setattr(scanner_mod, "_list_removable_drives", lambda: {"C:\\"})
    monkeypatch.setattr(scanner_mod.Path, "exists", lambda self: True)
    assert sc._claim_new_drive(timeout_sec=0) is None


def test_claim_ignores_new_drive_that_fails_exists(make_scanner, monkeypatch):
    sc, _ = make_scanner()
    sc._removable_baseline = set()
    monkeypatch.setattr(scanner_mod, "_list_removable_drives", lambda: {"E:\\"})
    monkeypatch.setattr(scanner_mod.Path, "exists", lambda self: False)  # not really mounted
    assert sc._claim_new_drive(timeout_sec=0) is None
    assert "E:\\" not in sc._removable_baseline
