"""Single source of truth for presenting ScanStatus values in the UI.

Every surface that renders a scan status (detail badge, history Event
column, status bar, threat filters) maps through this module, so adding
or renaming a ScanStatus value is a one-file change here.

`ScanStatus` is a str-enum, so these dicts work with either enum members
or the raw strings stored in scan-info dicts and log rows.
"""

from core.security.types import ScanStatus

STATUS_COLORS: dict[str, str] = {
    ScanStatus.CLEAN: "#4ade80",
    ScanStatus.SCANNING: "#38bdf8",
    ScanStatus.THREATS_FOUND: "#f87171",
    ScanStatus.UNSIGNED: "#fbbf24",
    ScanStatus.ERROR: "#94a3b8",
    ScanStatus.SKIPPED: "#94a3b8",
}

# Detail-panel badge text.
BADGE_LABELS: dict[str, str] = {
    ScanStatus.CLEAN: "Clean",
    ScanStatus.SCANNING: "Scanning…",
    ScanStatus.THREATS_FOUND: "Threats Found",
    ScanStatus.UNSIGNED: "Unsigned Driver",
    ScanStatus.ERROR: "Scan Error",
    ScanStatus.SKIPPED: "Scan Skipped",
}

# History "Event" column text (alongside Connected/Disconnected rows).
EVENT_LABELS: dict[str, str] = {
    ScanStatus.CLEAN: "Scan Clean",
    ScanStatus.SCANNING: "Scanning",
    ScanStatus.THREATS_FOUND: "Threats Found",
    ScanStatus.UNSIGNED: "Unsigned Driver",
    ScanStatus.ERROR: "Scan Error",
    ScanStatus.SKIPPED: "Scan Skipped",
}

# Status-bar message templates ({name}/{summary} placeholders).
STATUS_MESSAGES: dict[str, str] = {
    ScanStatus.SCANNING: "Scanning {name}: {summary}",
    ScanStatus.THREATS_FOUND: "Threats found on {name}: {summary}",
    ScanStatus.UNSIGNED: "Unsigned driver: {name}",
    ScanStatus.CLEAN: "Scan clean: {name}",
    ScanStatus.ERROR: "Scan error ({name}): {summary}",
}

# Statuses that warrant alerting the user (red rows, Threats Only filter).
ALERT_STATUSES = (ScanStatus.THREATS_FOUND, ScanStatus.UNSIGNED, ScanStatus.ERROR)


def status_of_log_string(scan_result: str | None) -> ScanStatus | None:
    """Recover the ScanStatus a logger scan_result string was built from
    (to_log_string() prefixes the row with the status value)."""
    s = scan_result or ""
    for status in ScanStatus:
        if s.startswith(status.value):
            return status
    return None


def is_alert_result(scan_result: str | None) -> bool:
    """True if a logged scan_result string represents an alerting status."""
    return status_of_log_string(scan_result) in ALERT_STATUSES
