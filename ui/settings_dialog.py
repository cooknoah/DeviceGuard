"""Settings dialog — toggles for notifications, security scanning, and YARA."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QCheckBox,
    QSpinBox, QPushButton, QLabel, QGroupBox, QDialogButtonBox,
)

from core.config import load_config, save_config
from core.security import yara_scanner


class SettingsDialog(QDialog):
    def __init__(self, parent=None, live_config: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("DeviceGuard Settings")
        self.setMinimumSize(460, 480)

        # If we were given a live dict (shared with the running scanner),
        # mutate it directly so changes apply without restart.
        self._live_config = live_config
        self._config = live_config if live_config is not None else load_config()

        root = QVBoxLayout(self)

        # ── General ──
        gen_box = QGroupBox("General")
        gen_form = QFormLayout(gen_box)
        self._cb_startup = QCheckBox("Launch DeviceGuard at Windows startup")
        self._cb_startup.setChecked(bool(self._config.get("launch_at_startup", True)))
        gen_form.addRow(self._cb_startup)
        root.addWidget(gen_box)

        # ── Notifications ──
        notif_box = QGroupBox("Notifications")
        notif_form = QFormLayout(notif_box)
        self._cb_notify_connect = QCheckBox("Toast on device connect")
        self._cb_notify_connect.setChecked(bool(self._config.get("notify_on_connect", True)))
        notif_form.addRow(self._cb_notify_connect)
        self._cb_notify_disconnect = QCheckBox("Toast on device disconnect")
        self._cb_notify_disconnect.setChecked(bool(self._config.get("notify_on_disconnect", True)))
        notif_form.addRow(self._cb_notify_disconnect)
        root.addWidget(notif_box)

        # ── Security scanning ──
        sec_box = QGroupBox("Security Scanning")
        sec_form = QFormLayout(sec_box)

        self._cb_auto_scan = QCheckBox("Scan USB storage on connect")
        self._cb_auto_scan.setChecked(bool(self._config.get("auto_scan_usb", True)))
        sec_form.addRow(self._cb_auto_scan)

        self._cb_defender = QCheckBox("Run Windows Defender custom scan")
        self._cb_defender.setChecked(bool(self._config.get("defender_scan_enabled", True)))
        sec_form.addRow(self._cb_defender)

        self._cb_yara = QCheckBox("Run YARA rule scan")
        self._cb_yara.setChecked(bool(self._config.get("enable_yara_scan", True)))
        sec_form.addRow(self._cb_yara)
        if not yara_scanner.is_available():
            warn = QLabel(
                f"<i>yara-python unavailable — YARA scans will be skipped.<br>"
                f"({yara_scanner.import_error()})</i>"
            )
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #fbbf24;")
            sec_form.addRow(warn)

        self._cb_driver = QCheckBox("Flag unsigned drivers on new devices")
        self._cb_driver.setChecked(bool(self._config.get("enable_driver_check", True)))
        sec_form.addRow(self._cb_driver)

        self._sp_depth = QSpinBox()
        self._sp_depth.setRange(0, 10)
        self._sp_depth.setValue(int(self._config.get("yara_scan_depth", 2)))
        sec_form.addRow("YARA scan depth:", self._sp_depth)

        self._sp_max_mb = QSpinBox()
        self._sp_max_mb.setRange(1, 4096)
        self._sp_max_mb.setSuffix(" MB")
        self._sp_max_mb.setValue(int(self._config.get("scan_max_file_mb", 50)))
        sec_form.addRow("Max file size:", self._sp_max_mb)

        self._sp_timeout = QSpinBox()
        self._sp_timeout.setRange(10, 3600)
        self._sp_timeout.setSuffix(" s")
        self._sp_timeout.setValue(int(self._config.get("scan_timeout_sec", 120)))
        sec_form.addRow("Scan timeout:", self._sp_timeout)

        root.addWidget(sec_box)

        # ── Buttons ──
        info = QLabel("<i>Changes take effect on next device event. "
                      "Restart DeviceGuard to apply startup changes.</i>")
        info.setWordWrap(True)
        root.addWidget(info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _save(self) -> None:
        self._config["launch_at_startup"] = self._cb_startup.isChecked()
        self._config["notify_on_connect"] = self._cb_notify_connect.isChecked()
        self._config["notify_on_disconnect"] = self._cb_notify_disconnect.isChecked()
        self._config["auto_scan_usb"] = self._cb_auto_scan.isChecked()
        self._config["defender_scan_enabled"] = self._cb_defender.isChecked()
        self._config["enable_yara_scan"] = self._cb_yara.isChecked()
        self._config["enable_driver_check"] = self._cb_driver.isChecked()
        self._config["yara_scan_depth"] = self._sp_depth.value()
        self._config["scan_max_file_mb"] = self._sp_max_mb.value()
        self._config["scan_timeout_sec"] = self._sp_timeout.value()
        save_config(self._config)
        self.accept()
