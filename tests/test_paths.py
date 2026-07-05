"""Path resolution and the DEVICEGUARD_DATA_DIR override."""

from pathlib import Path

from core import paths


def test_data_dir_honors_env_override(data_dir):
    # conftest sets DEVICEGUARD_DATA_DIR before core import.
    assert paths.DATA_DIR == data_dir


def test_user_path_lands_under_data_dir(data_dir):
    p = paths.user_path("config.json")
    assert p == data_dir / "config.json"
    assert p.parent == data_dir


def test_user_path_joins_multiple_parts(data_dir):
    assert paths.user_path("data", "device_log.db") == data_dir / "data" / "device_log.db"


def test_resource_path_uses_bundle_dir():
    # Dev mode: bundled resources resolve under the project root.
    p = paths.resource_path("assets", "usb.ids")
    assert p == paths.BUNDLE_DIR / "assets" / "usb.ids"
    assert isinstance(p, Path)


def test_data_dir_created():
    assert paths.DATA_DIR.is_dir()
