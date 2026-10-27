"""Zeichnet die App-Symbole und die einfarbigen Menüleisten-Symbole beider Apps.

Aufruf im Hauptordner:  python tools/make_icons.py
Schreibt assets/icon.png (App-Symbol) und assets/tray.png (Menüleiste) in klartext/ und screenshot-tool/.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

ROOT = Path(__file__).resolve().parent.parent
WHITE = QColor("#ffffff")


def new_canvas(size):
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    return image, painter


def rounded(rect, radius):
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


# --- App-Symbole (1024 x 1024) ------------------------------------------------


def glyph_klartext(p, gradient):
    """Sprechblase mit Schallwellen: gesprochenes wird zu Text."""
    bubble = rounded(QRectF(232, 262, 560, 380), 120)
    tail = QPainterPath()
    tail.moveTo(330, 620)
    tail.lineTo(330, 782)
    tail.lineTo(500, 630)
    tail.closeSubpath()
    p.fillPath(bubble.united(tail), WHITE)
    for dx, height in ((-176, 96), (-88, 200), (0, 296), (88, 200), (176, 96)):
        bar = rounded(QRectF(512 + dx - 24, 452 - height / 2, 48, height), 24)
        p.fillPath(bar, QBrush(gradient))  # gleicher Verlauf wie der Hintergrund, wirkt wie ausgestanzt


def glyph_screenshot(p, gradient):
    """Ecken eines Bildausschnitts mit einem Zeigerkreis in der Mitte."""
    pen = QPen(WHITE, 56)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    near, far, length = 252, 772, 150
    for x, y, sx, sy in ((near, near, 1, 1), (far, near, -1, 1), (near, far, 1, -1), (far, far, -1, -1)):
        corner = QPainterPath(QPointF(x + sx * length, y))
        corner.lineTo(x, y)
        corner.lineTo(x, y + sy * length)
        p.drawPath(corner)
    p.setPen(QPen(WHITE, 40))
    p.drawEllipse(QPointF(512, 512), 120, 120)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(WHITE)
    p.drawEllipse(QPointF(512, 512), 46, 46)


def app_icon(color_a, color_b, glyph):
    image, p = new_canvas(1024)
    gradient = QLinearGradient(64, 64, 960, 960)
    gradient.setColorAt(0, QColor(color_a))
    gradient.setColorAt(1, QColor(color_b))
    body = rounded(QRectF(64, 64, 896, 896), 200)
    p.fillPath(body, QBrush(gradient))
    gloss = QLinearGradient(0, 64, 0, 560)
    gloss.setColorAt(0, QColor(255, 255, 255, 70))
    gloss.setColorAt(1, QColor(255, 255, 255, 0))
    p.save()
    p.setClipPath(body)
    p.fillRect(QRectF(64, 64, 896, 500), QBrush(gloss))
    p.restore()
    glyph(p, gradient)
    p.end()
    return image


# --- Menüleiste (88 x 88, einfarbig schwarz, macOS färbt es selbst ein) -----------


def tray_klartext():
    image, p = new_canvas(88)
    black = QColor("#000000")
    bubble = rounded(QRectF(6, 10, 76, 50), 16)
    tail = QPainterPath()
    tail.moveTo(20, 54)
    tail.lineTo(20, 78)
    tail.lineTo(42, 56)
    tail.closeSubpath()
    p.fillPath(bubble.united(tail), black)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
    for dx, height in ((-24, 12), (-12, 26), (0, 38), (12, 26), (24, 12)):
        p.fillPath(rounded(QRectF(44 + dx - 3.5, 35 - height / 2, 7, height), 3.5), black)
    p.end()
    return image


def tray_screenshot():
    image, p = new_canvas(88)
    black = QColor("#000000")
    pen = QPen(black, 8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    near, far, length = 14, 74, 22
    for x, y, sx, sy in ((near, near, 1, 1), (far, near, -1, 1), (near, far, 1, -1), (far, far, -1, -1)):
        corner = QPainterPath(QPointF(x + sx * length, y))
        corner.lineTo(x, y)
        corner.lineTo(x, y + sy * length)
        p.drawPath(corner)
    p.setPen(QPen(black, 6))
    p.drawEllipse(QPointF(44, 44), 15, 15)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(black)
    p.drawEllipse(QPointF(44, 44), 5.5, 5.5)
    p.end()
    return image


def main():
    app = QGuiApplication.instance() or QGuiApplication([])
    jobs = {
        "klartext": (app_icon("#1f44ff", "#12d85a", glyph_klartext), tray_klartext()),
        "screenshot-tool": (app_icon("#7a3cff", "#ff7a45", glyph_screenshot), tray_screenshot()),
    }
    for folder, (icon, tray) in jobs.items():
        target = ROOT / folder / "assets"
        target.mkdir(parents=True, exist_ok=True)
        icon.save(str(target / "icon.png"))
        tray.save(str(target / "tray.png"))
        print("geschrieben:", target)
    del app


if __name__ == "__main__":
    main()
