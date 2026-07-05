"""ScanResult.to_log_string across every ScanStatus."""

from core.security.types import ScanFinding, ScanResult, ScanStatus


def _result(status, findings=None, summary=""):
    return ScanResult(
        device_id="dev",
        device_name="Dev",
        status=status,
        findings=findings or [],
        summary=summary,
    )


def test_clean_is_compact():
    assert _result(ScanStatus.CLEAN, summary="ignored").to_log_string() == "clean"


def test_skipped_is_compact():
    assert _result(ScanStatus.SKIPPED, summary="ignored").to_log_string() == "skipped"


def test_error_with_summary():
    assert _result(ScanStatus.ERROR, summary="disk gone").to_log_string() == "error: disk gone"


def test_error_without_summary():
    assert _result(ScanStatus.ERROR).to_log_string() == "error"


def test_threats_found_lists_finding_labels():
    findings = [
        ScanFinding(source="yara", label="rule_a"),
        ScanFinding(source="defender", label="Trojan:X"),
    ]
    s = _result(ScanStatus.THREATS_FOUND, findings=findings).to_log_string()
    assert s.startswith("threats_found — ")
    assert "rule_a" in s and "Trojan:X" in s


def test_threats_found_truncates_beyond_three():
    findings = [ScanFinding(source="yara", label=f"r{i}") for i in range(5)]
    s = _result(ScanStatus.THREATS_FOUND, findings=findings).to_log_string()
    assert "(+2 more)" in s
    # only the first three labels are spelled out
    assert "r3" not in s and "r4" not in s
    assert "r0" in s and "r2" in s


def test_status_without_findings_is_just_the_status():
    assert _result(ScanStatus.UNSIGNED).to_log_string() == "unsigned"
