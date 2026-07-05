"""Friendly, human-readable labels for raw Windows PnP class names.

Windows reports device classes as terse internal identifiers ("HIDClass",
"MEDIA", "USBDevice"). These are meaningful to advanced users but opaque to
everyone else, so the overview table shows a friendly label and keeps the raw
class in the cell's tooltip. The detail panel still shows the raw value.
"""

# Ordered substring checks — first match wins. Mirrors the grouping used by
# ui.device_icons so a row's icon and label stay consistent.
_RULES = [
    (("diskdrive", "usbstor", "wpd", "volume", "disk"), "Storage"),
    (("monitor", "display"), "Display"),
    (("mouse",), "Mouse"),
    (("keyboard",), "Keyboard"),
    (("hid",), "Input"),
    (("audio", "media", "sound"), "Audio"),
    (("bluetooth",), "Bluetooth"),
    (("net",), "Network"),
    (("image", "camera"), "Camera"),
    (("printer",), "Printer"),
    (("usb",), "USB"),
]


def friendly_class(pnp_class: str | None) -> str:
    """Map a raw PnP class to a friendly label.

    Unknown classes are returned unchanged (better to show the real class than
    a misleading generic), and a blank class becomes 'Device'.
    """
    raw = (pnp_class or "").strip()
    if not raw:
        return "Device"
    lowered = raw.lower()
    for needles, label in _RULES:
        if any(n in lowered for n in needles):
            return label
    return raw
