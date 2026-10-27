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
QMainWindow, QWidget#root {{ background: #0e0f11; }}
QFrame#panel {{ background: #17181b; border: 1px solid #2a2b30; border-radius: 16px; }}
QToolButton {{ background: transparent; border: none; border-radius: 8px; padding: 5px; color: #e8e8ea; font-size: 18px; }}
QToolButton:hover {{ background: #26272c; }}
QToolButton:checked {{ background: {ACCENT}; }}
QPushButton {{ background: #222327; color: #e8e8ea; border: 1px solid #2f3036; border-radius: 10px; padding: 7px 16px; }}
QPushButton:hover {{ background: #2c2d33; }}
QPushButton#primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT_BLUE}, stop:1 {ACCENT}); color: #ffffff; font-weight: 600; border: none; }}
QSlider::groove:horizontal {{ height: 3px; background: #3a3b41; border-radius: 1px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }}
QLabel {{ color: #e8e8ea; }}
QStatusBar {{ color: #9a9ba1; }}
"""


def tool_icon(key):
    """Zeichnet das Symbol eines Werkzeugs, hell im Normalzustand und dunkel, wenn gewählt."""
    icon = QIcon()
    for color, state in (("#e8e8ea", QIcon.State.Off), ("#1a1a1a", QIcon.State.On)):
        icon.addPixmap(_draw_tool(key, QColor(color)), QIcon.Mode.Normal, state)
    return icon


def _draw_tool(key, color):
    size = 28
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color, 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    full = QRectF(0, 0, size, size)
    if key == "select":
        p.setBrush(color)
        p.drawPolygon(
            QPolygonF([QPointF(8, 5), QPointF(8, 22), QPointF(12.5, 17.5), QPointF(16, 24), QPointF(18.5, 22.8), QPointF(15, 16.5), QPointF(21, 16)])
        )
    elif key == "arrow":
        p.drawLine(6, 22, 19, 9)
        p.setBrush(color)
        p.drawPolygon(QPolygonF([QPointF(23, 5), QPointF(13.5, 8), QPointF(20, 14.5)]))
    elif key == "line":
        p.drawLine(6, 22, 22, 6)
    elif key == "rect":
        p.drawRect(5, 8, 18, 13)
    elif key == "ellipse":
        p.drawEllipse(4, 6, 20, 16)
    elif key == "pen":
        p.drawLine(6, 22, 20, 8)
        p.drawLine(17, 5, 23, 11)
    elif key == "marker":
        p.drawLine(8, 17, 17, 8)
        p.drawLine(8, 17, 6, 22)
        p.drawLine(6, 22, 11, 20)
        p.drawLine(15, 24, 23, 24)
    elif key == "text":
        font = QFont("Helvetica")
        font.setBold(True)
        font.setPixelSize(20)
        p.setFont(font)
        p.drawText(full, Qt.AlignmentFlag.AlignCenter, "T")
    elif key == "pixelate":
        for row in range(3):
            for col in range(3):
                if (row + col) % 2 == 0:
                    p.fillRect(QRectF(5 + col * 6, 5 + row * 6, 6, 6), color)
    elif key == "badge":
        p.drawEllipse(4, 4, 20, 20)
        font = QFont("Helvetica")
        font.setBold(True)
        font.setPixelSize(13)
        p.setFont(font)
        p.drawText(full, Qt.AlignmentFlag.AlignCenter, "1")
    elif key == "crop":
        p.drawLine(9, 4, 9, 19)
        p.drawLine(9, 19, 24, 19)
        p.drawLine(4, 9, 19, 9)
        p.drawLine(19, 9, 19, 24)
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

    def _arrow_path(self, start, end):
        path = QPainterPath(start)
        length = QLineF(start, end).length()
        if length < 1:
            path.lineTo(end)
            return path
        head = min(max(18.0, self.width * 3.5), length)
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

    def end(self, pos):
        item = self._current
        if item is None:
            return
        tool = self._active_tool
        self.drag(pos)
        self._current = None
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
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
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
        number = 1 + sum(
            1
            for entry in self._history
            if entry[0] == "item" and isinstance(entry[1], Badge) and entry[1].scene() is not None
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
        self._scene.clearSelection()
        rect = self._scene.sceneRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
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


class EditorWindow(QMainWindow):
    TOOLS = [
        ("select", "Auswählen"),
        ("arrow", "Pfeil"),
        ("line", "Linie"),
        ("rect", "Rahmen"),
        ("ellipse", "Kreis"),
        ("pen", "Stift"),
        ("marker", "Textmarker"),
        ("text", "Text"),
        ("pixelate", "Verpixeln"),
        ("badge", "Nummer"),
        ("crop", "Zuschneiden"),
    ]

    def __init__(self, pixmap, save_dir):
        super().__init__()
        self.setWindowTitle("Screenshot bearbeiten")
        self.setStyleSheet(STYLE)
        self.setWindowIcon(QIcon(str(resource_path("assets/icon.png"))))
        self.save_dir = Path(save_dir)
        self.canvas = Canvas(pixmap)
        self.canvas.setFrameShape(QFrame.Shape.NoFrame)
        self.canvas.setStyleSheet("background: #0e0f11; border: none;")
        self.canvas.set_tool(self.canvas.tool)

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self._build_panel())
        self.setCentralWidget(root)

        self._bind(QKeySequence.StandardKey.Undo, self.canvas.undo)
        self._bind(QKeySequence.StandardKey.Redo, self.canvas.redo)
        self._bind(QKeySequence.StandardKey.Copy, self.copy_to_clipboard)
        self._bind(QKeySequence.StandardKey.Save, self.save)
        self._bind(QKeySequence.StandardKey.SaveAs, self.save_as)
        self._bind(QKeySequence("Backspace"), self.canvas.delete_selected)
        self._bind(QKeySequence("Delete"), self.canvas.delete_selected)

        self.resize(min(pixmap.width() + 60, 1500), min(pixmap.height() + 200, 950))

    def _bind(self, sequence, slot):
        shortcut = QShortcut(QKeySequence(sequence), self)
        shortcut.activated.connect(slot)

    def _build_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        row = QHBoxLayout()
        row.setSpacing(4)
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self.tool_buttons = {}
        for key, label in self.TOOLS:
            button = QToolButton()
            button.setCheckable(True)
            button.setToolTip(label)
            button.setIcon(tool_icon(key))
            button.setIconSize(QSize(26, 26))
            button.clicked.connect(lambda _checked=False, k=key: self.set_tool(k))
            self._tool_group.addButton(button)
            self.tool_buttons[key] = button
            row.addWidget(button)
            if key == self.canvas.tool:
                button.setChecked(True)

        row.addSpacing(12)
        self._swatch_group = QButtonGroup(self)
        self._swatch_group.setExclusive(True)
        self.swatches = []
        for color in PALETTE:
            swatch = QToolButton()
            swatch.setCheckable(True)
            swatch.setFixedSize(24, 24)
            swatch.setToolTip(color)
            swatch.setStyleSheet(
                f"QToolButton {{ background: {color}; border: 2px solid #17181b; border-radius: 12px; padding: 0; }}"
                "QToolButton:hover { border: 2px solid #9a9ba1; }"
                "QToolButton:checked { border: 2px solid #e8e8ea; }"
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

        row.addSpacing(12)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 40)
        self.slider.setValue(self.canvas.width)
        self.slider.setFixedWidth(110)
        self.slider.valueChanged.connect(self._set_width)
        self.width_label = QLabel(str(self.canvas.width))
        self.width_label.setMinimumWidth(22)
        row.addWidget(self.slider)
        row.addWidget(self.width_label)

        row.addStretch(1)
        for text, slot, tip in (("↶", self.canvas.undo, "Rückgängig"), ("↷", self.canvas.redo, "Wiederholen")):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(lambda _checked=False, s=slot: s())
            row.addWidget(button)
        outer.addLayout(row)

        bottom = QHBoxLayout()
        logo = QLabel()
        logo.setObjectName("logo")
        logo_pixmap = QPixmap(str(resource_path("assets/logo.png")))
        if not logo_pixmap.isNull():
            logo.setPixmap(
                logo_pixmap.scaledToHeight(52, Qt.TransformationMode.SmoothTransformation)
            )
        bottom.addWidget(logo)
        bottom.addStretch(1)
        discard = QPushButton("Verwerfen")
        discard.clicked.connect(self.close)
        copy = QPushButton("Kopieren")
        copy.clicked.connect(self.copy_to_clipboard)
        save = QPushButton("Sichern")
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        for button in (discard, copy, save):
            bottom.addWidget(button)
        outer.addLayout(bottom)
        return panel

    def set_tool(self, key):
        self.canvas.set_tool(key)
        self.tool_buttons[key].setChecked(True)

    def set_color(self, color):
        self.canvas.color = QColor(color)

    def _set_width(self, value):
        self.canvas.width = value
        self.width_label.setText(str(value))

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
