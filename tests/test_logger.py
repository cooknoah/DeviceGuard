"""logger.log_event / get_events / export_csv against the real SQLite store."""

import csv

import pytest

from core import logger

pytestmark = pytest.mark.usefixtures("clean_log")


def test_log_and_read_back():
    logger.log_event("connect", device_name="Kbd", device_id="USB\\VID_1")
    events = logger.get_events()
    assert len(events) == 1
    row = events[0]
    assert row["event_type"] == "connect"
    assert row["device_name"] == "Kbd"
    assert row["device_id"] == "USB\\VID_1"
    assert row["timestamp"]  # populated with an ISO string


def test_events_returned_newest_first():
    logger.log_event("connect", device_name="first")
    logger.log_event("connect", device_name="second")
    logger.log_event("disconnect", device_name="third")
    names = [e["device_name"] for e in logger.get_events()]
    assert names == ["third", "second", "first"]


def test_event_type_filter():
    logger.log_event("connect", device_name="c1")
    logger.log_event("disconnect", device_name="d1")
    logger.log_event("connect", device_name="c2")

    connects = logger.get_events(event_type_filter="connect")
    assert {e["device_name"] for e in connects} == {"c1", "c2"}
    assert all(e["event_type"] == "connect" for e in connects)


def test_limit_caps_row_count():
    for i in range(5):
        logger.log_event("connect", device_name=f"d{i}")
    assert len(logger.get_events(limit=2)) == 2


def test_optional_fields_stored():
    logger.log_event(
        "connect",
        device_name="Signed Dev",
        driver_signed=1,
        scan_result="clean",
    )
    row = logger.get_events()[0]
    assert row["driver_signed"] == 1
    assert row["scan_result"] == "clean"
    assert row["manufacturer"] is None  # unset optional stays NULL


def test_export_csv_populated(tmp_path):
    logger.log_event("connect", device_name="Alpha")
    logger.log_event("disconnect", device_name="Beta")

    out = tmp_path / "events.csv"
    logger.export_csv(str(out))

    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 2
    # export is ascending (oldest first), unlike get_events
    assert [r["device_name"] for r in rows] == ["Alpha", "Beta"]


def test_export_csv_empty_writes_header_only(tmp_path):
    out = tmp_path / "empty.csv"
    logger.export_csv(str(out))

    reader = csv.reader(out.read_text(encoding="utf-8").splitlines())
    header = next(reader)
    assert "device_name" in header and "scan_result" in header
    assert next(reader, None) is None  # no data rows
