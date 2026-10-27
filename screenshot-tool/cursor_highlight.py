"""Leuchtkreis um den Mauszeiger, damit Zuschauer ihn besser sehen."""
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QWidget

MIN_RADIUS = 14
MAX_RADIUS = 150
DEFAULT_RADIUS = 30
SIZE = MAX_RADIUS * 2 + 16  # Das Fenster hat immer die Größe des größten Kreises, nur der Kreis darin wächst

PRESETS = [("Klein", 20), ("Mittel", 30), ("Groß", 55), ("Sehr groß", 90)]


class CursorHighlight(QWidget):
    def __init__(self, radius=DEFAULT_RADIUS):
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
        self.set_radius(radius)
        self._pressed = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._follow)

    def set_radius(self, radius):
        self.radius = int(min(MAX_RADIUS, max(MIN_RADIUS, radius)))
        self.update()
        return self.radius

    def change_radius(self, delta):
        return self.set_radius(self.radius + delta)

    def set_pressed(self, pressed):
        self._pressed = pressed
        self.update()

    def start(self):
        self._follow()
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _follow(self):
        pos = QCursor.pos()
        self.move(pos.x() - SIZE // 2, pos.y() - SIZE // 2)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._pressed:
            fill, ring = QColor(255, 59, 48, 120), QColor(255, 59, 48, 230)
        else:
            fill, ring = QColor(18, 216, 90, 90), QColor(31, 68, 255, 230)
        painter.setBrush(fill)
        painter.setPen(QPen(ring, 3))
        center = SIZE // 2
        painter.drawEllipse(center - self.radius, center - self.radius, self.radius * 2, self.radius * 2)
