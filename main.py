"""DeviceGuard — Phase 1 entry point.

Loads config, starts the device monitor, and logs events to SQLite.
"""

from core.config import load_config
from core import logger
from core.monitor import DeviceMonitor


def on_connect(device_info: dict) -> None:
    print(f"[+] Device connected:  {device_info}")
    logger.log_event(
        event_type="connect",
        device_name=device_info.get("name"),
        device_id=device_info.get("device_id"),
        device_class=device_info.get("pnp_class"),
        manufacturer=device_info.get("manufacturer"),
    )


def on_disconnect(device_info: dict) -> None:
    print(f"[-] Device disconnected: {device_info}")
    logger.log_event(
        event_type="disconnect",
        device_name=device_info.get("name"),
        device_id=device_info.get("device_id"),
        device_class=device_info.get("pnp_class"),
        manufacturer=device_info.get("manufacturer"),
    )


def main() -> None:
    config = load_config()
    print("DeviceGuard starting...")
    print(f"Config: {config}")

    monitor = DeviceMonitor()
    monitor.register_callbacks(on_connect=on_connect, on_disconnect=on_disconnect)
    monitor.start()

    print("Monitoring for device events. Press Enter to exit.")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        monitor.stop()
        print("DeviceGuard stopped.")


if __name__ == "__main__":
    main()
