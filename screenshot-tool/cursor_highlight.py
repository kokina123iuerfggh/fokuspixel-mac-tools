"""Leuchtkreis um den Mauszeiger, damit Zuschauer ihn besser sehen. Innen leicht vergrößert."""
from PySide6.QtCore import QPointF, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

import screengrab

MIN_RADIUS = 14
MAX_RADIUS = 150
DEFAULT_RADIUS = 30
SIZE = MAX_RADIUS * 2 + 16  # Das Fenster hat immer die Größe des größten Kreises, nur der Kreis darin wächst
RING_WIDTH = 3

PRESETS = [("Klein", 20), ("Mittel", 30), ("Groß", 55), ("Sehr groß", 90)]
MAGNIFY_PRESETS = [("Aus", 1.0), ("Leicht (1,5×)", 1.5), ("Mittel (2×)", 2.0), ("Stark (3×)", 3.0)]
DEFAULT_MAGNIFY = 1.5
CAPTURE_INTERVAL = 33  # Millisekunden zwischen zwei Aufnahmen des Bereichs unter dem Zeiger


class CursorHighlight(QWidget):
    def __init__(self, radius=DEFAULT_RADIUS, magnify=DEFAULT_MAGNIFY):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.resize(SIZE, SIZE)
        self.radius = DEFAULT_RADIUS
        self.magnify = DEFAULT_MAGNIFY
        self.set_radius(radius)
        self.set_magnify(magnify)
        self._pressed = False
        self._frame = None
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._follow)
        self._capture_timer = QTimer(self)
        self._capture_timer.setInterval(CAPTURE_INTERVAL)
        self._capture_timer.timeout.connect(self._capture)

    def set_radius(self, radius):
        self.radius = int(min(MAX_RADIUS, max(MIN_RADIUS, radius)))
        self.update()
        return self.radius

    def change_radius(self, delta):
        return self.set_radius(self.radius + delta)

    def set_magnify(self, factor):
        self.magnify = float(max(1.0, min(4.0, factor)))
        if self.magnify <= 1.0:
            self._frame = None
        if self.isVisible():
            self._sync_capture_timer()
        self.update()
        return self.magnify

    def set_pressed(self, pressed):
        self._pressed = pressed
        self.update()

    def set_frame(self, image):
        """Bild des Bereichs unter dem Zeiger, das vergrößert im Kreis erscheint (None: nichts)."""
        self._frame = image
        self.update()

    def start(self):
        self._follow()
        self.show()
        self.raise_()
        self._timer.start()
        self._sync_capture_timer()

    def stop(self):
        self._timer.stop()
        self._capture_timer.stop()
        self._frame = None
        self.hide()

    def _sync_capture_timer(self):
        if self.magnify > 1.0 and screengrab.available():
            self._capture_timer.start()
        else:
            self._capture_timer.stop()
            self._frame = None

    def _follow(self):
        pos = QCursor.pos()
        self.move(pos.x() - SIZE // 2, pos.y() - SIZE // 2)

    def _capture(self):
        pos = QCursor.pos()
        side = max(4, int(round(2 * self.radius / self.magnify)))
        rect = QRect(pos.x() - side // 2, pos.y() - side // 2, side, side)
        self.set_frame(screengrab.capture_below(self, rect))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        center = SIZE / 2
        circle = QRectF(center - self.radius, center - self.radius, self.radius * 2, self.radius * 2)
        if self._frame is not None and not self._frame.isNull():
            clip = QPainterPath()
            clip.addEllipse(circle)
            painter.save()
            painter.setClipPath(clip)
            painter.drawImage(circle, self._frame)
            painter.restore()
        ring = QColor(255, 59, 48, 235) if self._pressed else QColor(31, 68, 255, 235)
        painter.setBrush(Qt.BrushStyle.NoBrush)  # innen bleibt der Bildschirm sichtbar
        painter.setPen(QPen(ring, RING_WIDTH))
        painter.drawEllipse(QPointF(center, center), self.radius, self.radius)
