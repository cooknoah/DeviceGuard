import csv
import sqlite3
from datetime import datetime, timezone

from core.paths import user_path

_DATA_DIR = user_path("data")
_DB_PATH = _DATA_DIR / "device_log.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS device_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    device_name TEXT,
    device_id TEXT,
    device_class TEXT,
    manufacturer TEXT,
    driver_signed INTEGER,
    scan_result TEXT
);
"""

# Ensure data dir and database exist on import
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
_conn.execute("PRAGMA journal_mode=WAL;")
_conn.execute(_SCHEMA)
_conn.commit()


def _get_conn() -> sqlite3.Connection:
    return _conn


def log_event(
    event_type: str,
    device_name: str | None = None,
    device_id: str | None = None,
    device_class: str | None = None,
    manufacturer: str | None = None,
    driver_signed: int | None = None,
    scan_result: str | None = None,
) -> None:
    """Insert a device event row with the current UTC timestamp."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO device_events
           (timestamp, event_type, device_name, device_id, device_class,
            manufacturer, driver_signed, scan_result)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            event_type,
            device_name,
            device_id,
            device_class,
            manufacturer,
            driver_signed,
            scan_result,
        ),
    )
    conn.commit()


def get_events(
    limit: int = 200, event_type_filter: str | None = None
) -> list[dict]:
    """Return up to *limit* events as dicts, newest first.
    Optionally filter by event_type ('connect' or 'disconnect')."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if event_type_filter:
        cursor.execute(
            "SELECT * FROM device_events WHERE event_type = ? "
            "ORDER BY id DESC LIMIT ?",
            (event_type_filter, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM device_events ORDER BY id DESC LIMIT ?",
            (limit,),
        )

    rows = cursor.fetchall()
    conn.row_factory = None
    return [dict(row) for row in rows]


def export_csv(filepath: str) -> None:
    """Export all events to a CSV file at the given path."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM device_events ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.row_factory = None

    if not rows:
        columns = [
            "id", "timestamp", "event_type", "device_name", "device_id",
            "device_class", "manufacturer", "driver_signed", "scan_result",
        ]
    else:
        columns = rows[0].keys()

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
