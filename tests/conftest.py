"""Shared pytest setup.

Critically, this runs *before* any `core.*` module is imported. `core.paths`
resolves DATA_DIR at import time (dev mode → the project root), and both
`core.config` and `core.logger` capture their file paths from it on import.
Pointing DEVICEGUARD_DATA_DIR at a throwaway temp dir here keeps the suite
from touching the real config.json / data/device_log.db.
"""

import os
import tempfile
from pathlib import Path

import pytest

# Session-wide isolated data dir. Set before core imports; never cleaned up
# aggressively (temp GC handles it) so post-mortem inspection stays possible.
_TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="deviceguard-tests-"))
os.environ["DEVICEGUARD_DATA_DIR"] = str(_TEST_DATA_DIR)


@pytest.fixture
def data_dir() -> Path:
    """The isolated per-session user-data directory (see module docstring)."""
    return _TEST_DATA_DIR


@pytest.fixture
def clean_log():
    """Truncate the logger's table before a test.

    The logger uses a single module-level SQLite connection bound at import,
    so tests share one database; this gives each logger test a clean slate.
    """
    from core import logger

    logger._get_conn().execute("DELETE FROM device_events")
    logger._get_conn().commit()
    yield
    logger._get_conn().execute("DELETE FROM device_events")
    logger._get_conn().commit()
