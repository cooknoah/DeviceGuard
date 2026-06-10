"""PyInstaller build script.

Produces a onedir windowed build at dist/DeviceGuard/.
Run from the project root inside the venv:  python build.py
"""

from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).parent

ARGS = [
    "main.py",
    "--name=DeviceGuard",
    "--windowed",
    f"--icon={ROOT / 'assets' / 'icon.ico'}",
    "--noconfirm",
    "--clean",
    # Bundled read-only resources (resolved via core.paths.resource_path).
    f"--add-data={ROOT / 'assets'};assets",
    f"--add-data={ROOT / 'rules' / 'default'};rules/default",
    # COM/WMI and tray backends that PyInstaller's analysis can miss.
    "--hidden-import=wmi",
    "--hidden-import=win32com",
    "--hidden-import=pythoncom",
    "--hidden-import=pystray._win32",
    "--hidden-import=winotify",
]


def main() -> None:
    PyInstaller.__main__.run(ARGS)
    print(f"\nBuild complete: {ROOT / 'dist' / 'DeviceGuard' / 'DeviceGuard.exe'}")


if __name__ == "__main__":
    main()
