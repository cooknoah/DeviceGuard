"""Windows toast notifications via winotify."""

from pathlib import Path

from winotify import Notification, audio

_ASSETS = Path(__file__).parent.parent / "assets"
_ICON_PATH = str(_ASSETS.resolve() / "icon.ico")
_APP_ID = "DeviceGuard"


def notify_connect(device_name: str | None) -> None:
    """Show a toast notification for a device connection."""
    name = device_name or "Unknown device"
    try:
        toast = Notification(
            app_id=_APP_ID,
            title="Device Connected",
            msg=name,
            icon=_ICON_PATH,
            duration="short",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as exc:
        print(f"[Notifier] Toast failed: {exc}")


def notify_disconnect(device_name: str | None) -> None:
    """Show a toast notification for a device disconnection."""
    name = device_name or "Unknown device"
    try:
        toast = Notification(
            app_id=_APP_ID,
            title="Device Disconnected",
            msg=name,
            icon=_ICON_PATH,
            duration="short",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as exc:
        print(f"[Notifier] Toast failed: {exc}")


def notify_threat(device_name: str | None, details: str) -> None:
    """Show an alert toast when a threat is detected."""
    name = device_name or "Unknown device"
    try:
        toast = Notification(
            app_id=_APP_ID,
            title="Threat Detected",
            msg=f"{name}: {details}",
            icon=_ICON_PATH,
            duration="long",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as exc:
        print(f"[Notifier] Toast failed: {exc}")
