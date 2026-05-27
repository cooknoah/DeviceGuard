"""System tray icon with right-click menu using pystray."""

import threading
from pathlib import Path
from typing import Callable

from PIL import Image
import pystray

_ASSETS = Path(__file__).parent.parent / "assets"
_ICON_PATH = _ASSETS / "icon.ico"
_ICON_ALERT_PATH = _ASSETS / "icon_alert.ico"


class TrayManager:
    """Manages the system tray icon and its context menu."""

    def __init__(
        self,
        on_open: Callable[[], None] | None = None,
        on_settings: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ):
        self._on_open = on_open
        self._on_settings = on_settings
        self._on_exit = on_exit

        self._icon_image = Image.open(_ICON_PATH)
        self._icon_alert_image = Image.open(_ICON_ALERT_PATH)

        menu = pystray.Menu(
            pystray.MenuItem("Open DeviceGuard", self._handle_open, default=True),
            pystray.MenuItem("Settings", self._handle_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._handle_exit),
        )

        self._icon = pystray.Icon(
            name="DeviceGuard",
            icon=self._icon_image,
            title="DeviceGuard",
            menu=menu,
        )

    def start(self) -> None:
        """Run the tray icon on a daemon thread."""
        thread = threading.Thread(target=self._icon.run, daemon=True, name="TrayIcon")
        thread.start()

    def stop(self) -> None:
        """Remove the tray icon."""
        self._icon.stop()

    def set_alert(self, alert: bool) -> None:
        """Swap the tray icon between normal and alert states."""
        self._icon.icon = self._icon_alert_image if alert else self._icon_image

    def _handle_open(self, icon, item) -> None:
        if self._on_open:
            self._on_open()

    def _handle_settings(self, icon, item) -> None:
        if self._on_settings:
            self._on_settings()

    def _handle_exit(self, icon, item) -> None:
        if self._on_exit:
            self._on_exit()
        self.stop()
