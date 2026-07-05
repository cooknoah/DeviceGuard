"""Frozen-aware path resolution.

Dev runs keep everything in the project root. Frozen (PyInstaller) builds
read bundled resources from the install directory and write user data
(config.json, data/, rules/custom) to %LOCALAPPDATA%\\DeviceGuard.
"""

import os
import sys
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))

if IS_FROZEN:
    # Bundled, read-only resources (onedir: the _internal directory).
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    DATA_DIR = (
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        / "DeviceGuard"
    )
else:
    BUNDLE_DIR = Path(__file__).parent.parent
    DATA_DIR = BUNDLE_DIR

# Explicit override (portable installs, tests) wins over the defaults above.
_DATA_DIR_OVERRIDE = os.environ.get("DEVICEGUARD_DATA_DIR")
if _DATA_DIR_OVERRIDE:
    DATA_DIR = Path(_DATA_DIR_OVERRIDE)

DATA_DIR.mkdir(parents=True, exist_ok=True)


def resource_path(*parts: str) -> Path:
    """Path to a read-only bundled resource (assets, default YARA rules)."""
    return BUNDLE_DIR.joinpath(*parts)


def user_path(*parts: str) -> Path:
    """Path under the writable per-user data directory."""
    return DATA_DIR.joinpath(*parts)
