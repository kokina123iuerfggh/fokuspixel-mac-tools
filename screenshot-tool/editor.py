"""Editor zum Markieren, Umrahmen und Speichern von Screenshots."""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLineF, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from resources import resource_path

MIN_DRAG = 3
MIN_CROP = 8

ACCENT = "#12d85a"  # Grün aus dem Fokus-Pixel-Logo
ACCENT_BLUE = "#1f44ff"  # Blau aus dem Logo
PALETTE = [ACCENT, ACCENT_BLUE, "#ff3b30", "#ff9500", "#ffd60a", "#bf5af2", "#ffffff", "#000000"]

STYLE = f"""
QMainWindow, QWidget#root {{ background: #0a0c11; }}
QFrame#rail, QFrame#topbar {{ background: #12151c; border: 1px solid #232733; border-radius: 16px; }}
QToolButton {{ background: transparent; border: none; border-radius: 12px; padding: 6px; color: #e8e8ea; font-size: 18px; }}
QToolButton:hover {{ background: #1d2230; }}
QToolButton#tool:checked {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT_BLUE}, stop:1 {ACCENT}); }}
QPushButton {{ background: #1a1e29; color: #e8e8ea; border: 1px solid #2a3040; border-radius: 12px; padding: 8px 16px; }}
QPushButton:hover {{ background: #232938; }}
QPushButton#primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT_BLUE}, stop:1 {ACCENT}); color: #ffffff; font-weight: 600; border: none; }}
QSlider::groove:horizontal {{ height: 6px; background: #232733; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT_BLUE}, stop:1 {ACCENT}); border-radius: 3px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
QLabel {{ color: #e8e8ea; }}
QStatusBar {{ color: #8b90a0; }}
"""


def _brand_brush(size):
    """Farbverlauf aus dem Fokus-Pixel-Logo, von Blau nach Grün."""
    gradient = QLinearGradient(2, 2, size - 2, size - 2)
    gradient.setColorAt(0, QColor(ACCENT_BLUE))
    gradient.setColorAt(1, QColor(ACCENT))
    return QBrush(gradient)


def tool_icon(key):
    """Symbol eines Werkzeugs: im Farbverlauf, und weiß auf dem Verlaufs-Hintergrund, wenn gewählt."""
    icon = QIcon()
    icon.addPixmap(_draw_tool(key, False), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_draw_tool(key, True), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def _draw_tool(key, active):
    size = 28
    scale = 2  # doppelte Auflösung, damit die Symbole auf Retina-Bildschirmen scharf sind
    pixmap = QPixmap(size * scale, size * scale)
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    brush = QBrush(QColor("#ffffff")) if active else _brand_brush(size)
    pen = QPen(brush, 2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    def dot(x, y, radius):
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        p.drawEllipse(QPointF(x, y), radius, radius)
        p.restore()

    def label(text, pixel_size, color=None):
        font = QFont("Helvetica")
        font.setBold(True)
        font.setPixelSize(pixel_size)
        p.setFont(font)
        if color is not None:
            p.setPen(color)
        p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)

    def undo_shape():
        path = QPainterPath(QPointF(20, 21))
        path.cubicTo(25, 12, 15, 6, 9, 10)
        p.drawPath(path)
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        p.drawPolygon(QPolygonF([QPointF(4, 10.5), QPointF(10.5, 4.5), QPointF(12, 14)]))
        p.restore()

    if key == "select":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        p.drawPolygon(
            QPolygonF(
                [QPointF(7, 4), QPointF(7, 22), QPointF(11.5, 18), QPointF(14.5, 24.5), QPointF(17.5, 23), QPointF(14.5, 16.8), QPointF(20.5, 16.5)]
            )
        )
    elif key == "arrow":
        path = QPainterPath(QPointF(5, 22))
        path.cubicTo(8, 11, 14, 8, 20, 8)
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        p.drawPolygon(QPolygonF([QPointF(25, 8), QPointF(18, 3.5), QPointF(18, 12.5)]))
    elif key == "line":
        p.drawLine(QPointF(7, 21), QPointF(21, 7))
        dot(7, 21, 2.6)
        dot(21, 7, 2.6)
    elif key == "rect":
        p.drawRoundedRect(QRectF(5, 7, 18, 14), 4, 4)
        dot(5, 7, 2.3)
        dot(23, 21, 2.3)
    elif key == "ellipse":
        p.drawEllipse(QPointF(13.5, 14), 9, 8)
        dot(22.5, 14, 2.3)
    elif key == "pen":
        path = QPainterPath(QPointF(4, 19))
        path.cubicTo(8, 8, 12, 8, 14, 14)
        path.cubicTo(16, 20, 19, 20, 24, 9)
        p.drawPath(path)
    elif key == "marker":
        p.save()
        p.setOpacity(0.55)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        p.drawRoundedRect(QRectF(4, 8, 20, 10), 3, 3)
        p.restore()
        p.drawLine(QPointF(5, 23), QPointF(23, 23))
    elif key == "text":
        label("Aa", 15)  # der Stift trägt den Farbverlauf, daher hat auch die Schrift ihn
    elif key == "pixelate":
        levels = [[1.0, 0.55, 1.0], [0.55, 1.0, 0.35], [1.0, 0.35, 0.7]]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        for row in range(3):
            for col in range(3):
                p.setOpacity(levels[row][col])
                p.drawRoundedRect(QRectF(4.5 + col * 6.6, 4.5 + row * 6.6, 5.4, 5.4), 1.3, 1.3)
        p.setOpacity(1)
    elif key == "badge":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        p.drawEllipse(QPointF(14, 14), 10, 10)
        label("1", 14, QColor("#10131a") if active else QColor("#ffffff"))
    elif key == "crop":
        p.drawLine(9, 4, 9, 19)
        p.drawLine(9, 19, 24, 19)
        p.drawLine(4, 9, 19, 9)
        p.drawLine(19, 9, 19, 24)
        dot(14, 14, 1.8)
    elif key == "undo":
        undo_shape()
    elif key == "redo":
        p.translate(size, 0)
        p.scale(-1, 1)
        undo_shape()
    p.end()
    return pixmap


class Badge(QGraphicsItem):
    """Runde Markierung mit Nummer."""

    def __init__(self, number, color, diameter):
        super().__init__()
        self.number = number
        self.color = QColor(color)
        self.diameter = diameter

    def boundingRect(self):
        d = self.diameter
        return QRectF(-d / 2, -d / 2, d, d)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawEllipse(self.boundingRect())
        font = QFont("Helvetica")
        font.setBold(True)
        font.setPixelSize(int(self.diameter * 0.55))
        painter.setFont(font)
        painter.setPen(QColor("#1a1a1a") if self.color.lightness() > 150 else QColor("#ffffff"))
        painter.drawText(self.boundingRect(), Qt.AlignmentFlag.AlignCenter, str(self.number))


class Canvas(QGraphicsView):
    """Zeichenfläche: das Bild als Hintergrund, Markierungen als eigene Elemente."""

    changed = Signal()

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap = pixmap
        self._bounds = QRectF(pixmap.rect())
        self._background = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(self._bounds)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.tool = "arrow"
        self.color = QColor(ACCENT)
        self.width = 8

        # Einträge: ("item", item) | ("delete", item) | ("crop", altes_rect, neues_rect)
        self._history = []
        self._redo = []
        self._current = None
        self._active_tool = None
        self._start = QPointF()
        self._path = None

    def set_tool(self, key):
        self.tool = key
        cursor = Qt.CursorShape.ArrowCursor if key == "select" else Qt.CursorShape.CrossCursor
        self.viewport().setCursor(cursor)

    # --- Zeichnen -------------------------------------------------------

    def _make_pen(self):
        color = QColor(self.color)
        width = float(self.width)
        if self.tool == "marker":
            color.setAlpha(110)
            width = max(14.0, width * 4)
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _arrow_path(self, start, end, width=None):
        width = self.width if width is None else width
        path = QPainterPath(start)
        length = QLineF(start, end).length()
        if length < 1:
            path.lineTo(end)
            return path
        head = min(max(18.0, width * 3.5), length)
        base = QLineF(end, start)
        base.setLength(head * 0.75)
        path.lineTo(base.p2())
        points = []
        for delta in (25, -25):
            side = QLineF(end, start)
            side.setLength(head)
            side.setAngle(side.angle() + delta)
            points.append(side.p2())
        path.moveTo(end)
        path.lineTo(points[0])
        path.lineTo(points[1])
        path.closeSubpath()
        return path

    def begin(self, pos):
        self._scene.clearSelection()
        self._start = pos
        self._active_tool = self.tool
        tool = self.tool

        if tool == "text":
            text, ok = QInputDialog.getText(self, "Text", "Text eingeben:")
            if ok and text.strip():
                self.add_text(pos, text)
            self._active_tool = None
            return
        if tool == "badge":
            self.add_badge(pos)
            self._active_tool = None
            return

        pen = self._make_pen()
        if tool in ("pen", "marker"):
            self._path = QPainterPath(pos)
            item = QGraphicsPathItem(self._path)
        elif tool in ("rect", "pixelate", "crop"):
            item = QGraphicsRectItem(QRectF(pos, pos))
        elif tool == "ellipse":
            item = QGraphicsEllipseItem(QRectF(pos, pos))
        elif tool == "line":
            item = QGraphicsLineItem(QLineF(pos, pos))
        elif tool == "arrow":
            item = QGraphicsPathItem()
            item.setBrush(QBrush(pen.color()))
        else:
            return
        if tool in ("pixelate", "crop"):
            pen = QPen(QColor("#ffffff"), 2)
            pen.setStyle(Qt.PenStyle.DashLine)
        item.setPen(pen)
        self._scene.addItem(item)
        self._current = item

    def drag(self, pos):
        item = self._current
        if item is None:
            return
        tool = self._active_tool
        if tool in ("pen", "marker"):
            self._path.lineTo(pos)
            item.setPath(self._path)
        elif tool in ("rect", "ellipse", "pixelate", "crop"):
            item.setRect(QRectF(self._start, pos).normalized())
        elif tool == "line":
            item.setLine(QLineF(self._start, pos))
        elif tool == "arrow":
            item.setPath(self._arrow_path(self._start, pos))
            item.setData(0, (QPointF(self._start), QPointF(pos)))

    def end(self, pos):
        item = self._current
        if item is None:
            return
        tool = self._active_tool
        self.drag(pos)
        self._current = None
        if tool in ("pen", "marker"):
            # Ein Kreis endet, wo er begann. Deshalb zählt die Ausdehnung des Strichs, nicht der Abstand.
            size = self._path.boundingRect()
            too_small = max(size.width(), size.height()) < MIN_DRAG
        else:
            too_small = (pos - self._start).manhattanLength() < MIN_DRAG
        if tool in ("pixelate", "crop"):
            self._scene.removeItem(item)
            if not too_small:
                rect = QRectF(self._start, pos).normalized()
                if tool == "pixelate":
                    self._apply_pixelate(rect)
                else:
                    self._apply_crop(rect)
            return
        if too_small:
            self._scene.removeItem(item)
            return
        self._finish(item)

    def _finish(self, item):
        self._scene.clearSelection()
        if not isinstance(item, QGraphicsPixmapItem):  # Verpixelung darf nicht verschoben werden
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            # Das frisch gezeichnete Element bleibt ausgewählt, damit Farbe und Stärke es noch ändern
            item.setSelected(True)
        self._push(("item", item))

    def _push(self, entry):
        self._history.append(entry)
        self._redo.clear()
        self.changed.emit()

    def add_text(self, pos, text):
        item = QGraphicsTextItem(text)
        font = QFont()
        font.setPointSize(max(14, int(self.width) * 3 + 8))
        font.setBold(True)
        item.setFont(font)
        item.setDefaultTextColor(self.color)
        item.setPos(pos)
        self._scene.addItem(item)
        self._finish(item)

    def add_badge(self, pos):
        number = 1 + max(
            (
                entry[1].number
                for entry in self._history
                if entry[0] == "item" and isinstance(entry[1], Badge) and entry[1].scene() is not None
            ),
            default=0,
        )
        badge = Badge(number, self.color, max(28, int(self.width) * 5))
        badge.setPos(pos)
        self._scene.addItem(badge)
        self._finish(badge)

    def _apply_pixelate(self, rect):
        area = rect.intersected(self._bounds).toRect()
        if area.width() < 2 or area.height() < 2:
            return
        region = self._pixmap.copy(area)
        block = max(6, int(self.width) * 2)
        w, h = region.width(), region.height()
        small = region.scaled(
            max(1, w // block),
            max(1, h // block),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        mosaic = small.scaled(
            w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation
        )
        item = QGraphicsPixmapItem(mosaic)
        item.setPos(QPointF(area.topLeft()))
        self._scene.addItem(item)
        self._finish(item)

    def _apply_crop(self, rect):
        area = QRectF(rect.intersected(self._bounds).toRect())
        if area.width() < MIN_CROP or area.height() < MIN_CROP:
            return
        old = self._scene.sceneRect()
        self._set_crop(area)
        self._push(("crop", old, area))

    def _set_crop(self, rect):
        area = rect.toRect()
        self._background.setPixmap(self._pixmap.copy(area))
        self._background.setPos(QPointF(area.topLeft()))
        self._scene.setSceneRect(QRectF(area))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # --- Verlauf --------------------------------------------------------

    def restyle_selected(self, color=None, width=None):
        """Wendet neue Farbe und/oder Stärke auf die ausgewählten Markierungen an."""
        changed = False
        for item in self._scene.selectedItems():
            if isinstance(item, Badge):
                if color is not None:
                    item.color = QColor(color)
                if width is not None:
                    item.prepareGeometryChange()
                    item.diameter = max(28, int(width) * 5)
                item.update()
            elif isinstance(item, QGraphicsTextItem):
                if color is not None:
                    item.setDefaultTextColor(QColor(color))
                if width is not None:
                    font = item.font()
                    font.setPointSize(max(14, int(width) * 3 + 8))
                    item.setFont(font)
            elif isinstance(item, QGraphicsPixmapItem) or not hasattr(item, "pen"):
                continue
            else:
                pen = QPen(item.pen())
                translucent = pen.color().alpha() < 255  # Textmarker
                if color is not None:
                    new_color = QColor(color)
                    new_color.setAlpha(pen.color().alpha())
                    pen.setColor(new_color)
                    if item.brush().style() != Qt.BrushStyle.NoBrush:
                        item.setBrush(QBrush(new_color))  # gefüllte Pfeilspitze
                if width is not None:
                    pen.setWidthF(max(14.0, width * 4.0) if translucent else float(width))
                    ends = item.data(0)
                    if isinstance(ends, tuple):
                        item.setPath(self._arrow_path(ends[0], ends[1], width))
                item.setPen(pen)
            changed = True
        if changed:
            self.changed.emit()

    def undo(self):
        if not self._history:
            return
        entry = self._history.pop()
        kind = entry[0]
        if kind == "item":
            self._scene.removeItem(entry[1])
        elif kind == "delete":
            self._scene.addItem(entry[1])
        elif kind == "crop":
            self._set_crop(entry[1])
        self._redo.append(entry)
        self.changed.emit()

    def redo(self):
        if not self._redo:
            return
        entry = self._redo.pop()
        kind = entry[0]
        if kind == "item":
            self._scene.addItem(entry[1])
        elif kind == "delete":
            self._scene.removeItem(entry[1])
        elif kind == "crop":
            self._set_crop(entry[2])
        self._history.append(entry)
        self.changed.emit()

    def delete_selected(self):
        for item in self._scene.selectedItems():
            self._scene.removeItem(item)
            self._push(("delete", item))

    def annotation_count(self):
        return sum(
            1 for entry in self._history if entry[0] == "item" and entry[1].scene() is not None
        )

    def render_image(self):
        selected = self._scene.selectedItems()
        self._scene.clearSelection()
        rect = self._scene.sceneRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
        for item in selected:
            item.setSelected(True)
        return image

    # --- Maus -----------------------------------------------------------

    def mousePressEvent(self, event):
        if self.tool == "select":
            super().mousePressEvent(event)
        elif event.button() == Qt.MouseButton.LeftButton:
            self.begin(self.mapToScene(event.position().toPoint()))

    def mouseMoveEvent(self, event):
        if self.tool == "select":
            super().mouseMoveEvent(event)
        elif self._current is not None:
            self.drag(self.mapToScene(event.position().toPoint()))

    def mouseReleaseEvent(self, event):
        if self.tool == "select":
            super().mouseReleaseEvent(event)
        elif event.button() == Qt.MouseButton.LeftButton:
            self.end(self.mapToScene(event.position().toPoint()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class StrokePreview(QWidget):
    """Kleiner Punkt, der zeigt, wie dick und in welcher Farbe die nächste Linie wird."""

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.setFixedSize(34, 34)
        self.setToolTip("Vorschau von Farbe und Stärke")

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.canvas.color)
        diameter = min(30.0, max(3.0, self.canvas.width * 0.75))
        painter.drawEllipse(QPointF(self.rect().center()), diameter / 2, diameter / 2)


class EditorWindow(QMainWindow):
    # (Schlüssel, Name, Taste)
    TOOLS = [
        ("select", "Auswählen", "V"),
        ("arrow", "Pfeil", "A"),
        ("line", "Linie", "L"),
        ("rect", "Rahmen", "R"),
        ("ellipse", "Kreis", "E"),
        ("pen", "Stift", "P"),
        ("marker", "Textmarker", "M"),
        ("text", "Text", "T"),
        ("badge", "Nummer", "N"),
        ("pixelate", "Verpixeln", "X"),
        ("crop", "Zuschneiden", "C"),
    ]
    GROUPS = [
        ["select"],
        ["arrow", "line", "rect", "ellipse"],
        ["pen", "marker"],
        ["text", "badge"],
        ["pixelate", "crop"],
    ]

    def __init__(self, pixmap, save_dir):
        super().__init__()
        self.setWindowTitle("Screenshot bearbeiten")
        self.setStyleSheet(STYLE)
        self.setWindowIcon(QIcon(str(resource_path("assets/icon.png"))))
        self.save_dir = Path(save_dir)
        self.canvas = Canvas(pixmap)
        self.canvas.setFrameShape(QFrame.Shape.NoFrame)
        self.canvas.setStyleSheet("background: #0a0c11; border: none;")
        self.canvas.set_tool(self.canvas.tool)

        root = QWidget()
        root.setObjectName("root")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(12)
        layout.addWidget(self._build_rail())
        column = QVBoxLayout()
        column.setSpacing(12)
        column.addWidget(self._build_topbar())
        column.addWidget(self.canvas, 1)
        layout.addLayout(column, 1)
        self.setCentralWidget(root)

        self._bind(QKeySequence.StandardKey.Undo, self.canvas.undo)
        self._bind(QKeySequence.StandardKey.Redo, self.canvas.redo)
        self._bind(QKeySequence.StandardKey.Copy, self.copy_to_clipboard)
        self._bind(QKeySequence.StandardKey.Save, self.save)
        self._bind(QKeySequence.StandardKey.SaveAs, self.save_as)
        self._bind(QKeySequence("Backspace"), self.canvas.delete_selected)
        self._bind(QKeySequence("Delete"), self.canvas.delete_selected)
        for key, _name, letter in self.TOOLS:
            self._bind(QKeySequence(letter), lambda k=key: self.set_tool(k))

        self.resize(min(pixmap.width() + 120, 1500), min(pixmap.height() + 170, 950))

    def _bind(self, sequence, slot):
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(slot)

    def _icon_button(self, icon_key, tooltip, slot):
        button = QToolButton()
        button.setIcon(tool_icon(icon_key))
        button.setIconSize(QSize(26, 26))
        button.setFixedSize(46, 46)
        button.setToolTip(tooltip)
        button.clicked.connect(lambda _checked=False: slot())
        return button

    def _build_rail(self):
        """Senkrechte Werkzeugleiste links, nach Aufgaben gruppiert."""
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(66)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(9, 10, 9, 10)
        layout.setSpacing(4)
        names = {key: (name, letter) for key, name, letter in self.TOOLS}
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self.tool_buttons = {}
        for index, group in enumerate(self.GROUPS):
            if index:
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet("background: #232733; border: none;")
                layout.addSpacing(4)
                layout.addWidget(line)
                layout.addSpacing(4)
            for key in group:
                name, letter = names[key]
                button = QToolButton()
                button.setObjectName("tool")
                button.setCheckable(True)
                button.setIcon(tool_icon(key))
                button.setIconSize(QSize(26, 26))
                button.setFixedSize(46, 46)
                button.setToolTip(f"{name} ({letter})")
                button.clicked.connect(lambda _checked=False, k=key: self.set_tool(k))
                self._tool_group.addButton(button)
                self.tool_buttons[key] = button
                layout.addWidget(button)
                if key == self.canvas.tool:
                    button.setChecked(True)
        layout.addStretch(1)
        layout.addWidget(self._icon_button("undo", "Rückgängig (⌘Z)", self.canvas.undo))
        layout.addWidget(self._icon_button("redo", "Wiederholen (⇧⌘Z)", self.canvas.redo))
        return rail

    def _build_topbar(self):
        """Obere Leiste: Logo, Farben, Stärke und die Knöpfe zum Beenden."""
        bar = QFrame()
        bar.setObjectName("topbar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(8)

        logo = QLabel()
        logo.setObjectName("logo")
        logo_pixmap = QPixmap(str(resource_path("assets/icon.png")))
        if not logo_pixmap.isNull():
            logo.setPixmap(logo_pixmap.scaledToHeight(38, Qt.TransformationMode.SmoothTransformation))
        row.addWidget(logo)
        row.addSpacing(10)

        self._swatch_group = QButtonGroup(self)
        self._swatch_group.setExclusive(True)
        self.swatches = []
        for color in PALETTE:
            swatch = QToolButton()
            swatch.setCheckable(True)
            swatch.setFixedSize(26, 26)
            swatch.setToolTip(color)
            swatch.setStyleSheet(
                f"QToolButton {{ background: {color}; border: 2px solid #12151c; border-radius: 8px; padding: 0; }}"
                "QToolButton:hover { border: 2px solid #8b90a0; }"
                "QToolButton:checked { border: 2px solid #ffffff; }"
            )
            swatch.clicked.connect(lambda _checked=False, c=color: self.set_color(QColor(c)))
            self._swatch_group.addButton(swatch)
            self.swatches.append(swatch)
            row.addWidget(swatch)
            if QColor(color) == self.canvas.color:
                swatch.setChecked(True)
        custom = QToolButton()
        custom.setText("+")
        custom.setToolTip("Eigene Farbe")
        custom.clicked.connect(self._choose_color)
        row.addWidget(custom)

        row.addSpacing(14)
        minus = QToolButton()
        minus.setText("−")
        minus.setToolTip("Dünner")
        plus = QToolButton()
        plus.setText("+")
        plus.setToolTip("Dicker")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 40)
        self.slider.setValue(self.canvas.width)
        self.slider.setFixedWidth(130)
        self.slider.setToolTip("Stärke: gilt für die nächste Zeichnung und für die markierte")
        self.slider.valueChanged.connect(self._set_width)
        minus.clicked.connect(lambda _checked=False: self.slider.setValue(self.slider.value() - 1))
        plus.clicked.connect(lambda _checked=False: self.slider.setValue(self.slider.value() + 1))
        self.width_label = QLabel(str(self.canvas.width))
        self.width_label.setMinimumWidth(22)
        self.preview = StrokePreview(self.canvas)
        for widget in (minus, self.slider, plus, self.width_label, self.preview):
            row.addWidget(widget)

        row.addStretch(1)
        close = QPushButton("Schließen")
        close.setToolTip("Ohne Speichern schließen")
        close.clicked.connect(self.close)
        copy = QPushButton("Kopieren")
        copy.setToolTip("In die Zwischenablage (⌘C)")
        copy.clicked.connect(self.copy_to_clipboard)
        save = QPushButton("Speichern")
        save.setObjectName("primary")
        save.setToolTip("Als PNG speichern (⌘S)")
        save.clicked.connect(self.save)
        for button in (close, copy, save):
            row.addWidget(button)
        return bar

    def set_tool(self, key):
        self.canvas.set_tool(key)
        self.tool_buttons[key].setChecked(True)

    def set_color(self, color):
        self.canvas.color = QColor(color)
        self.canvas.restyle_selected(color=color)
        self.preview.update()

    def _set_width(self, value):
        self.canvas.width = value
        self.width_label.setText(str(value))
        self.canvas.restyle_selected(width=value)
        self.preview.update()

    def _choose_color(self):
        color = QColorDialog.getColor(self.canvas.color, self, "Farbe wählen")
        if not color.isValid():
            return
        self.set_color(color)
        self._swatch_group.setExclusive(False)
        for swatch in self.swatches:
            swatch.setChecked(False)
        self._swatch_group.setExclusive(True)

    def copy_to_clipboard(self):
        QApplication.clipboard().setImage(self.canvas.render_image())
        self.statusBar().showMessage("In die Zwischenablage kopiert", 3000)

    def save(self):
        name = datetime.now().strftime("Screenshot %Y-%m-%d %H.%M.%S.png")
        self._write(self.save_dir / name)

    def save_as(self):
        start = str(self.save_dir / datetime.now().strftime("Screenshot %Y-%m-%d %H.%M.%S.png"))
        path, _ = QFileDialog.getSaveFileName(self, "Speichern unter", start, "PNG (*.png)")
        if path:
            self._write(Path(path))

    def _write(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.canvas.render_image().save(str(path)):
            self.statusBar().showMessage(f"Gespeichert: {path}", 6000)
        else:
            QMessageBox.warning(self, "Fehler", f"Konnte nicht speichern:\n{path}")
