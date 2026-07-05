"""config.load_config / save_config behavior."""

import json

import pytest

from core import config


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """Redirect config I/O to an isolated file per test."""
    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "_CONFIG_PATH", path)
    return path


def test_missing_file_returns_defaults(config_file):
    assert not config_file.exists()
    cfg = config.load_config()
    assert cfg == config._DEFAULTS


def test_defaults_are_a_copy_not_shared_state(config_file):
    cfg = config.load_config()
    cfg["auto_scan_usb"] = "mutated"
    # Mutating the returned dict must not corrupt the module defaults.
    assert config._DEFAULTS["auto_scan_usb"] is True


def test_malformed_json_returns_defaults(config_file):
    config_file.write_text("{ this is not valid json ", encoding="utf-8")
    assert config.load_config() == config._DEFAULTS


def test_partial_config_merges_with_defaults(config_file):
    config_file.write_text(json.dumps({"auto_scan_usb": False}), encoding="utf-8")
    cfg = config.load_config()
    assert cfg["auto_scan_usb"] is False          # user value wins
    assert cfg["yara_scan_depth"] == 2            # missing key filled from defaults
    assert set(cfg) == set(config._DEFAULTS)


def test_unknown_keys_are_preserved(config_file):
    config_file.write_text(json.dumps({"future_key": 42}), encoding="utf-8")
    assert config.load_config()["future_key"] == 42


def test_save_then_load_round_trips(config_file):
    cfg = config.load_config()
    cfg["scan_timeout_sec"] = 999
    config.save_config(cfg)

    assert config_file.exists()
    reloaded = config.load_config()
    assert reloaded["scan_timeout_sec"] == 999


def test_saved_file_is_readable_json(config_file):
    config.save_config({"a": 1, "b": "two"})
    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk == {"a": 1, "b": "two"}
