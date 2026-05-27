r"""Manage Windows startup registry entry (HKCU\Software\Microsoft\Windows\CurrentVersion\Run)."""

import sys
import winreg

_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "DeviceGuard"


def _get_exe_path() -> str:
    """Return the path to use for the startup command.
    When frozen (PyInstaller), use the exe. Otherwise use python + main.py."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" "{sys.argv[0]}"'


def enable_startup() -> None:
    """Add DeviceGuard to the current user's startup programs."""
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _get_exe_path())


def disable_startup() -> None:
    """Remove DeviceGuard from the current user's startup programs."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _APP_NAME)
    except FileNotFoundError:
        pass


def is_startup_enabled() -> bool:
    """Check whether DeviceGuard is currently in the startup registry."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_READ
        ) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except FileNotFoundError:
        return False


def sync_startup(config: dict) -> None:
    """Enable or disable startup based on the config dict's launch_at_startup flag."""
    if config.get("launch_at_startup", False):
        enable_startup()
    else:
        disable_startup()
