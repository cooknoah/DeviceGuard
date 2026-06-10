import json
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.json"

_DEFAULTS = {
    "launch_at_startup": True,
    "notify_on_connect": True,
    "notify_on_disconnect": True,
    "auto_scan_usb": True,
    "yara_scan_depth": 2,
    "custom_rules_dir": "rules/custom",
    "defender_scan_enabled": True,
    "enable_yara_scan": True,
    "enable_driver_check": True,
    "scan_max_file_mb": 50,
    "scan_timeout_sec": 120,
    "yara_rules_paths": ["rules/default", "rules/custom"],
}


def load_config() -> dict:
    """Read config.json and return its contents as a dict.
    Returns defaults if the file is missing or malformed."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        # Merge with defaults so new keys are always present
        merged = {**_DEFAULTS, **config}
        return merged
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)


def save_config(config: dict) -> None:
    """Write the config dict back to config.json."""
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")
