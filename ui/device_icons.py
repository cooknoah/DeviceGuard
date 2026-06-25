"""Theme-consistent device-class icons drawn with QPainter.

No icon assets ship with the app, so each class glyph is drawn from simple
geometry at load time and cached as a QIcon. Drawing (rather than relying on
emoji or a symbol font) keeps the icons crisp, monochrome, and identical on
every machine regardless of installed fonts.

Public API: ``icon_for_class(pnp_class)`` returns a cached QIcon tinted to the
theme's muted color; unknown classes fall back to a generic chip.
"""

from functools import lru_cache

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

# Drawn on a square canvas, then scaled by Qt to the table's icon size.
_CANVAS = 32
_STROKE = QColor("#94a3b8")  # MUTED — matches ui/styles.py


def _classify(pnp_class: str | None) -> str:
    """Map a Windows PnP class name to one of our icon kinds."""
    c = (pnp_class or "").lower()
    if "disk" in c or "usbstor" in c or "wpd" in c or "volume" in c:
        return "storage"
    if "monitor" in c or "display" in c:
        return "monitor"
    if "mouse" in c:
        return "mouse"
    if "keyboard" in c or "hid" in c:
        return "hid"
    if "audio" in c or "media" in c or "sound" in c:
        return "audio"
    if "net" in c:
        return "network"
    if "bluetooth" in c:
        return "bluetooth"
    if "usb" in c:
        return "usb"
    return "generic"


def _new_painter(pm: QPixmap) -> QPainter:
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(_STROKE)
    pen.setWidthF(2.0)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    return p


def _draw_storage(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(6, 8, 20, 16), 3, 3)
    p.drawLine(QPointF(6, 16), QPointF(26, 16))
    p.drawRect(QRectF(10, 19, 8, 3))


def _draw_monitor(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5, 7, 22, 14), 2, 2)
    p.drawLine(QPointF(12, 25), QPointF(20, 25))
    p.drawLine(QPointF(16, 21), QPointF(16, 25))


def _draw_hid(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5, 10, 22, 12), 2, 2)
    for x in (9, 13, 17, 21):
        p.drawPoint(QPointF(x, 14))
    p.drawLine(QPointF(11, 18), QPointF(21, 18))


def _draw_mouse(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(10, 6, 12, 20), 6, 6)
    p.drawLine(QPointF(16, 7), QPointF(16, 14))


def _draw_audio(p: QPainter) -> None:
    speaker = QPolygonF([
        QPointF(7, 13), QPointF(12, 13), QPointF(17, 8),
        QPointF(17, 24), QPointF(12, 19), QPointF(7, 19),
    ])
    p.drawPolygon(speaker)
    p.drawArc(QRectF(18, 11, 6, 10), -60 * 16, 120 * 16)


def _draw_network(p: QPainter) -> None:
    top = QPointF(16, 8)
    left = QPointF(9, 23)
    right = QPointF(23, 23)
    p.drawLine(top, left)
    p.drawLine(top, right)
    p.drawLine(left, right)
    for c in (top, left, right):
        p.drawEllipse(c, 2.4, 2.4)


def _draw_bluetooth(p: QPainter) -> None:
    # Classic Bluetooth knot as a single polyline.
    p.drawPolyline(QPolygonF([
        QPointF(11, 11), QPointF(21, 21), QPointF(16, 25),
        QPointF(16, 7), QPointF(21, 11), QPointF(11, 21),
    ]))


def _draw_usb(p: QPainter) -> None:
    p.drawLine(QPointF(16, 6), QPointF(16, 24))
    p.drawEllipse(QPointF(16, 25), 2.2, 2.2)
    p.drawPolygon(QPolygonF([
        QPointF(16, 6), QPointF(13, 10), QPointF(19, 10),
    ]))
    p.drawLine(QPointF(16, 14), QPointF(10, 18))
    p.drawEllipse(QPointF(9, 18), 2.0, 2.0)
    p.drawLine(QPointF(16, 12), QPointF(22, 16))
    p.drawRect(QRectF(20, 14, 4, 4))


def _draw_generic(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(8, 8, 16, 16), 2, 2)
    for off in (12, 16, 20):
        p.drawLine(QPointF(off, 4), QPointF(off, 8))
        p.drawLine(QPointF(off, 24), QPointF(off, 28))
        p.drawLine(QPointF(4, off), QPointF(8, off))
        p.drawLine(QPointF(24, off), QPointF(28, off))


_DRAWERS = {
    "storage": _draw_storage,
    "monitor": _draw_monitor,
    "hid": _draw_hid,
    "mouse": _draw_mouse,
    "audio": _draw_audio,
    "network": _draw_network,
    "bluetooth": _draw_bluetooth,
    "usb": _draw_usb,
    "generic": _draw_generic,
}


@lru_cache(maxsize=None)
def _icon_for_kind(kind: str) -> QIcon:
    pm = QPixmap(_CANVAS, _CANVAS)
    pm.fill(Qt.GlobalColor.transparent)
    p = _new_painter(pm)
    _DRAWERS.get(kind, _draw_generic)(p)
    p.end()
    return QIcon(pm)


def icon_for_class(pnp_class: str | None) -> QIcon:
    """Return a cached QIcon for a device's PnP class."""
    return _icon_for_kind(_classify(pnp_class))
