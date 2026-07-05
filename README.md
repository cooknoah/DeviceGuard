# DeviceGuard

[![tests](https://github.com/cooknoah/DeviceGuard/actions/workflows/tests.yml/badge.svg)](https://github.com/cooknoah/DeviceGuard/actions/workflows/tests.yml)

A dark, modern Windows device monitor with real-time USB/PnP tracking, toast notifications, and security scanning.

## Features

- Real-time USB/PnP device connection and disconnection monitoring (WMI)
- Windows toast notifications on device events and threats
- Windows Defender scan of removable drives on connect
- YARA rule-based file scanning (bundled default rules + user rules in `rules/custom/`)
- Unsigned driver detection for non-storage devices
- Live device view with friendly names (bus-reported strings + usb.ids) and per-device scan status
- Full connection history with filtering and CSV export
- System tray integration and optional run-at-startup
- One-click installer (Inno Setup)

## Requirements

- Windows 10 or Windows 11
- Python 3.13 (not 3.14 — yara-python has no cp314 wheels yet)

## Running from source

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Building

```
python build.py          # frozen onedir app at dist/DeviceGuard/
iscc installer\setup.iss # Windows installer (requires Inno Setup 6)
```

Installed builds keep user data (config, event database, custom YARA rules) in `%LOCALAPPDATA%\DeviceGuard`.
