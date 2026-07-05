"""YARA rule collection and graceful-degradation paths.

Tests that don't need yara-python run everywhere; the ones that actually
compile/scan are skipped when the wheel isn't installed.
"""

import pytest

from core.security import yara_scanner
from core.security.types import ScanStatus

requires_yara = pytest.mark.skipif(
    not yara_scanner.is_available(),
    reason="yara-python not installed",
)


# ── rule file collection (no yara needed) ──

def test_collect_rule_files_finds_yar_and_yara(tmp_path):
    (tmp_path / "a.yar").write_text("rule A {condition: true}", encoding="utf-8")
    (tmp_path / "b.yara").write_text("rule B {condition: true}", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

    files = yara_scanner._collect_rule_files([str(tmp_path)])
    names = {f.name for f in files}
    assert names == {"a.yar", "b.yara"}


def test_collect_rule_files_dedupes_same_dir(tmp_path):
    (tmp_path / "a.yar").write_text("rule A {condition: true}", encoding="utf-8")
    files = yara_scanner._collect_rule_files([str(tmp_path), str(tmp_path)])
    assert len(files) == 1


def test_collect_rule_files_skips_missing_dir(tmp_path):
    assert yara_scanner._collect_rule_files([str(tmp_path / "nope")]) == []


# ── graceful degradation ──

def test_scan_missing_path_is_skipped(tmp_path):
    # Whether or not yara is present, a non-existent drive is SKIPPED, not an error.
    result = yara_scanner.scan_drive(str(tmp_path / "ghost"), rule_dirs=[])
    assert result.status == ScanStatus.SKIPPED


@requires_yara
def test_scan_with_no_rules_is_skipped(tmp_path):
    (tmp_path / "file.bin").write_bytes(b"harmless")
    result = yara_scanner.scan_drive(str(tmp_path), rule_dirs=[str(tmp_path / "no_rules")])
    assert result.status == ScanStatus.SKIPPED
    assert "no yara rules" in result.summary


@requires_yara
def test_scan_detects_matching_rule(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "hit.yar").write_text(
        'rule FindMarker { strings: $m = "DEADBEEF_MARKER" condition: $m }',
        encoding="utf-8",
    )
    scan_dir = tmp_path / "drive"
    scan_dir.mkdir()
    (scan_dir / "evil.bin").write_text("....DEADBEEF_MARKER....", encoding="utf-8")

    # Fresh compile: bypass the module cache so this dir's rules are used.
    yara_scanner._compiled_rules = None
    yara_scanner._compile_paths_sig = None
    result = yara_scanner.scan_drive(str(scan_dir), rule_dirs=[str(rules_dir)])

    assert result.status == ScanStatus.THREATS_FOUND
    assert any(f.label == "FindMarker" for f in result.findings)


@requires_yara
def test_scan_clean_dir(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "hit.yar").write_text(
        'rule FindMarker { strings: $m = "DEADBEEF_MARKER" condition: $m }',
        encoding="utf-8",
    )
    scan_dir = tmp_path / "drive"
    scan_dir.mkdir()
    (scan_dir / "ok.bin").write_text("nothing suspicious here", encoding="utf-8")

    yara_scanner._compiled_rules = None
    yara_scanner._compile_paths_sig = None
    result = yara_scanner.scan_drive(str(scan_dir), rule_dirs=[str(rules_dir)])

    assert result.status == ScanStatus.CLEAN
