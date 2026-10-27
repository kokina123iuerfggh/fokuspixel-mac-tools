"""Kleine schwebende Statusanzeige am unteren Bildschirmrand."""
from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

GREEN = "#12d85a"
BLUE = "#1f44ff"
RED = "#ff3b30"
ORANGE = "#ff9500"

HEIGHT = 40
BOTTOM_MARGIN = 90


class StatusPill(QWidget):
    def __init__(self):
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
        font = QFont()
        font.setPixelSize(14)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        self._text = ""
        self._color = QColor(GREEN)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_state(self, text, color=GREEN, milliseconds=0):
        """Zeigt eine Meldung. Mit milliseconds > 0 verschwindet sie danach von selbst."""
        self._text = text
        self._color = QColor(color)
        width = QFontMetrics(self.font()).horizontalAdvance(text) + 64
        self.resize(width, HEIGHT)
        screen = QGuiApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(area.center().x() - width // 2, area.bottom() - BOTTOM_MARGIN)
        self.show()
        self.update()
        if milliseconds:
            self._hide_timer.start(milliseconds)
        else:
            self._hide_timer.stop()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(23, 24, 27, 238))
        painter.setPen(QPen(QColor("#2a2b30"), 1.5))
        painter.drawRoundedRect(rect, HEIGHT / 2, HEIGHT / 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawEllipse(QRectF(16, HEIGHT / 2 - 6, 12, 12))
        painter.setPen(QColor("#e8e8ea"))
        painter.drawText(
            QRectF(38, 0, self.width() - 48, HEIGHT),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )
