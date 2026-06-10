"""Shared dataclasses for the security scanner subsystem."""

from dataclasses import dataclass, field
from enum import Enum


class ScanStatus(str, Enum):
    SKIPPED = "skipped"
    SCANNING = "scanning"
    CLEAN = "clean"
    THREATS_FOUND = "threats_found"
    UNSIGNED = "unsigned"
    ERROR = "error"


@dataclass
class ScanFinding:
    """A single suspicious item — a YARA match, a Defender hit, or an unsigned driver."""
    source: str  # "yara" | "defender" | "driver"
    label: str   # rule name, threat name, or driver name
    detail: str = ""


@dataclass
class ScanResult:
    """Aggregate result returned by the orchestrator for one device."""
    device_id: str | None
    device_name: str | None
    status: ScanStatus
    findings: list[ScanFinding] = field(default_factory=list)
    summary: str = ""
    driver_signed: bool | None = None

    def to_log_string(self) -> str:
        """Compact representation suitable for the logger's scan_result column."""
        if self.status == ScanStatus.CLEAN:
            return "clean"
        if self.status == ScanStatus.SKIPPED:
            return "skipped"
        if self.status == ScanStatus.ERROR:
            return f"error: {self.summary}" if self.summary else "error"
        parts = [self.status.value]
        if self.findings:
            top = ", ".join(f.label for f in self.findings[:3])
            extra = len(self.findings) - 3
            if extra > 0:
                top += f" (+{extra} more)"
            parts.append(top)
        return " — ".join(parts)
