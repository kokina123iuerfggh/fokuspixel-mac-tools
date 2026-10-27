"""Lupe: ein rundes Fenster neben dem Mauszeiger zeigt die Umgebung des Zeigers vergrößert."""
from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

DIAMETER = 220
GAP = 70  # Abstand der Lupe zum Zeiger, so liegt sie nie im aufgenommenen Bereich
ZOOMS = [("2×", 2.0), ("3×", 3.0), ("4×", 4.0)]


class MagnifierLens(QWidget):
    def __init__(self, zoom=3.0):
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
        self.resize(DIAMETER, DIAMETER)
        self.zoom = zoom
        self._frame = None
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def set_zoom(self, zoom):
        self.zoom = float(zoom)

    def start(self):
        self._tick()
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def set_frame(self, pixmap):
        self._frame = pixmap
        self.update()

    def lens_position(self, cursor, screen_rect):
        """Oben rechts vom Zeiger; am Bildschirmrand klappt die Lupe auf die andere Seite."""
        x = cursor.x() + GAP
        y = cursor.y() - GAP - DIAMETER
        if x + DIAMETER > screen_rect.right():
            x = cursor.x() - GAP - DIAMETER
        if y < screen_rect.top():
            y = cursor.y() + GAP
        return int(x), int(y)

    def _tick(self):
        cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.geometry()
        side = max(8, int(DIAMETER / self.zoom))
        left = cursor.x() - side // 2 - area.x()
        top = cursor.y() - side // 2 - area.y()
        self.set_frame(screen.grabWindow(0, left, top, side, side))
        self.move(*self.lens_position(cursor, area))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        circle = QRectF(3, 3, DIAMETER - 6, DIAMETER - 6)
        clip = QPainterPath()
        clip.addEllipse(circle)
        painter.save()
        painter.setClipPath(clip)
        painter.fillRect(self.rect(), QColor(20, 20, 22))
        if self._frame is not None and not self._frame.isNull():
            painter.drawPixmap(circle.toRect(), self._frame)
        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(31, 68, 255, 235), 4))
        painter.drawEllipse(circle)
        # kleines Fadenkreuz in der Mitte zeigt die Stelle unter dem Zeiger
        center = QPointF(DIAMETER / 2, DIAMETER / 2)
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
        painter.drawLine(center + QPointF(-8, 0), center + QPointF(8, 0))
        painter.drawLine(center + QPointF(0, -8), center + QPointF(0, 8))
