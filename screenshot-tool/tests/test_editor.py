"""Test des Editors ohne Bildschirm: QT_QPA_PLATFORM=offscreen python -m unittest"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QPoint, QPointF, QRect
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QGraphicsItem

from cursor_highlight import MAX_RADIUS, MIN_RADIUS, SIZE, CursorHighlight
from editor import Canvas, EditorWindow
from magnifier import DIAMETER, MagnifierLens
from single_instance import SingleInstance

app = QApplication.instance() or QApplication([])


def white_pixmap(width=200, height=120):
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("white"))
    return pixmap


def draw(canvas, tool, start, end):
    canvas.tool = tool
    canvas.begin(QPointF(*start))
    canvas.drag(QPointF(*end))
    canvas.end(QPointF(*end))


class CanvasTest(unittest.TestCase):
    def test_rect_draws_frame_and_undo_removes_it(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        draw(canvas, "rect", (20, 20), (100, 80))
        self.assertEqual(canvas.annotation_count(), 1)

        image = canvas.render_image()
        self.assertEqual(image.size().width(), 200)
        self.assertEqual(image.pixelColor(20, 50), QColor("#ff0000"))
        self.assertEqual(image.pixelColor(60, 50), QColor("white"))

        canvas.undo()
        self.assertEqual(canvas.annotation_count(), 0)
        self.assertEqual(canvas.render_image().pixelColor(20, 50), QColor("white"))

    def test_all_shape_tools_add_an_annotation(self):
        canvas = Canvas(white_pixmap())
        for tool in ("rect", "ellipse", "arrow", "line", "pen", "marker"):
            draw(canvas, tool, (10, 10), (90, 70))
        self.assertEqual(canvas.annotation_count(), 6)

    def test_click_without_drag_adds_nothing(self):
        canvas = Canvas(white_pixmap())
        draw(canvas, "rect", (30, 30), (31, 31))
        self.assertEqual(canvas.annotation_count(), 0)

    def test_marker_is_translucent(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        draw(canvas, "marker", (10, 60), (190, 60))
        pixel = canvas.render_image().pixelColor(100, 60)
        self.assertEqual(pixel.red(), 255)
        self.assertGreater(pixel.green(), 60)

    def test_text_is_added(self):
        canvas = Canvas(white_pixmap(300, 100))
        canvas.add_text(QPointF(10, 10), "Hallo")
        self.assertEqual(canvas.annotation_count(), 1)
        image = canvas.render_image()
        non_white = any(
            image.pixelColor(x, y) != QColor("white")
            for x in range(10, 120)
            for y in range(10, 50)
        )
        self.assertTrue(non_white)


class NewToolsTest(unittest.TestCase):
    def test_redo_restores_undone_item(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        draw(canvas, "rect", (20, 20), (100, 80))
        canvas.undo()
        self.assertEqual(canvas.annotation_count(), 0)
        canvas.redo()
        self.assertEqual(canvas.annotation_count(), 1)
        self.assertEqual(canvas.render_image().pixelColor(20, 50), QColor("#ff0000"))

    def test_new_drawing_clears_redo(self):
        canvas = Canvas(white_pixmap())
        draw(canvas, "rect", (20, 20), (100, 80))
        canvas.undo()
        draw(canvas, "line", (10, 10), (50, 50))
        canvas.redo()
        self.assertEqual(canvas.annotation_count(), 1)

    def test_arrow_head_is_filled(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        canvas.width = 8
        draw(canvas, "arrow", (20, 60), (150, 60))
        image = canvas.render_image()
        # Kurz hinter der Pfeilspitze, neben der Mittellinie, ist die Spitze ausgefüllt
        self.assertEqual(image.pixelColor(140, 64), QColor("#ff0000"))

    def test_badges_are_numbered_in_order(self):
        canvas = Canvas(white_pixmap())
        canvas.tool = "badge"
        for x in (30, 80, 130):
            canvas.begin(QPointF(x, 60))
            canvas.end(QPointF(x, 60))
        numbers = [e[1].number for e in canvas._history if e[0] == "item"]
        self.assertEqual(numbers, [1, 2, 3])

    def test_pixelate_changes_pixels_into_blocks(self):
        pixmap = QPixmap(100, 100)
        image = QImage(100, 100, QImage.Format.Format_ARGB32)
        for x in range(100):
            for y in range(100):
                image.setPixelColor(x, y, QColor("black") if (x + y) % 2 else QColor("white"))
        pixmap = QPixmap.fromImage(image)
        canvas = Canvas(pixmap)
        canvas.width = 5
        draw(canvas, "pixelate", (10, 10), (90, 90))
        self.assertEqual(canvas.annotation_count(), 1)
        out = canvas.render_image()
        self.assertEqual(out.pixelColor(40, 40), out.pixelColor(41, 40))
        self.assertNotEqual(out.pixelColor(40, 40), QColor("white"))

    def test_crop_shrinks_output_and_undo_restores_it(self):
        canvas = Canvas(white_pixmap(200, 120))
        draw(canvas, "crop", (10, 10), (110, 70))
        image = canvas.render_image()
        self.assertEqual((image.width(), image.height()), (100, 60))
        canvas.undo()
        image = canvas.render_image()
        self.assertEqual((image.width(), image.height()), (200, 120))
        canvas.redo()
        self.assertEqual(canvas.render_image().width(), 100)

    def test_delete_selected_is_undoable(self):
        canvas = Canvas(white_pixmap())
        draw(canvas, "rect", (20, 20), (100, 80))
        item = canvas._history[0][1]
        item.setSelected(True)
        canvas.delete_selected()
        self.assertEqual(canvas.annotation_count(), 0)
        canvas.undo()
        self.assertEqual(canvas.annotation_count(), 1)


class ResourceTest(unittest.TestCase):
    def test_logo_files_load(self):
        from resources import resource_path

        for name in ("assets/icon.png", "assets/tray.png"):
            self.assertFalse(QPixmap(str(resource_path(name))).isNull(), name)

    def test_editor_window_shows_logo(self):
        window = EditorWindow(white_pixmap(), "/tmp")
        from PySide6.QtWidgets import QLabel

        logo = window.findChild(QLabel, "logo")
        self.assertIsNotNone(logo)
        self.assertFalse(logo.pixmap().isNull())


class RestyleTest(unittest.TestCase):
    def test_width_change_applies_to_the_selected_drawing(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        canvas.width = 4
        draw(canvas, "rect", (40, 40), (100, 80))
        self.assertEqual(canvas.render_image().pixelColor(34, 60), QColor("white"))
        canvas.restyle_selected(width=20)
        self.assertEqual(canvas.render_image().pixelColor(34, 60), QColor("#ff0000"))

    def test_color_change_applies_to_the_selected_drawing(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        draw(canvas, "rect", (40, 40), (100, 80))
        canvas.restyle_selected(color=QColor("#0000ff"))
        self.assertEqual(canvas.render_image().pixelColor(40, 60), QColor("#0000ff"))

    def test_only_the_newest_drawing_is_changed(self):
        canvas = Canvas(white_pixmap())
        canvas.color = QColor("#ff0000")
        canvas.width = 4
        draw(canvas, "rect", (40, 20), (60, 40))
        draw(canvas, "rect", (40, 70), (60, 100))
        canvas.restyle_selected(width=20)
        image = canvas.render_image()
        self.assertEqual(image.pixelColor(34, 30), QColor("white"))
        self.assertEqual(image.pixelColor(34, 85), QColor("#ff0000"))

    def test_arrow_head_grows_with_the_width(self):
        canvas = Canvas(white_pixmap(300, 120))
        canvas.width = 4
        draw(canvas, "arrow", (20, 60), (250, 60))
        item = canvas._history[0][1]
        small = item.path().boundingRect().height()
        canvas.restyle_selected(width=20)
        self.assertGreater(item.path().boundingRect().height(), small)

    def test_text_and_badge_follow_width_and_color(self):
        canvas = Canvas(white_pixmap())
        canvas.add_text(QPointF(10, 10), "Hallo")
        text = canvas._history[0][1]
        size = text.font().pointSize()
        canvas.restyle_selected(width=30, color=QColor("#00ff00"))
        self.assertGreater(text.font().pointSize(), size)
        self.assertEqual(text.defaultTextColor(), QColor("#00ff00"))
        canvas.add_badge(QPointF(100, 60))
        badge = canvas._history[1][1]
        canvas.restyle_selected(width=10)
        self.assertEqual(badge.diameter, 50)

    def test_render_keeps_the_selection(self):
        canvas = Canvas(white_pixmap())
        draw(canvas, "rect", (40, 40), (100, 80))
        canvas.render_image()
        self.assertEqual(len(canvas._scene.selectedItems()), 1)

    def test_preview_dot_shows_the_chosen_color(self):
        window = EditorWindow(white_pixmap(), "/tmp")
        window.set_color(QColor("#0000ff"))
        window.slider.setValue(30)
        image = window.preview.grab().toImage()
        self.assertEqual(image.pixelColor(17, 17), QColor("#0000ff"))


class CursorHighlightTest(unittest.TestCase):
    def test_radius_is_clamped(self):
        highlight = CursorHighlight(30)
        self.assertEqual(highlight.change_radius(10), 40)
        self.assertEqual(highlight.set_radius(1000), MAX_RADIUS)
        self.assertEqual(highlight.set_radius(-5), MIN_RADIUS)

    def test_circle_grows_with_the_radius(self):
        highlight = CursorHighlight(20)
        center = SIZE // 2
        self.assertEqual(highlight.grab().toImage().pixelColor(center + 60, center).alpha(), 0)
        highlight.set_radius(100)
        self.assertGreater(highlight.grab().toImage().pixelColor(center + 60, center).alpha(), 0)


class MagnifierTest(unittest.TestCase):
    def test_frame_is_drawn_inside_the_circle_only(self):
        lens = MagnifierLens(3.0)
        frame = QPixmap(100, 100)
        frame.fill(QColor("#ff0000"))
        lens.set_frame(frame)
        image = lens.grab().toImage()
        middle = DIAMETER // 2
        self.assertEqual(image.pixelColor(middle + 20, middle + 20), QColor("#ff0000"))
        self.assertEqual(image.pixelColor(1, 1).alpha(), 0)

    def test_position_flips_at_the_screen_edges(self):
        lens = MagnifierLens()
        screen = QRect(0, 0, 1920, 1080)
        self.assertEqual(lens.lens_position(QPoint(500, 600), screen), (570, 310))
        x, _ = lens.lens_position(QPoint(1900, 600), screen)
        self.assertLess(x, 1900)
        _, y = lens.lens_position(QPoint(500, 50), screen)
        self.assertGreater(y, 50)

    def test_lens_never_overlaps_the_captured_area(self):
        lens = MagnifierLens(2.0)
        screen = QRect(0, 0, 1920, 1080)
        side = int(DIAMETER / lens.zoom)
        for cursor in (QPoint(10, 10), QPoint(1910, 10), QPoint(960, 540), QPoint(1910, 1070)):
            x, y = lens.lens_position(cursor, screen)
            captured = QRect(cursor.x() - side // 2, cursor.y() - side // 2, side, side)
            self.assertFalse(QRect(x, y, DIAMETER, DIAMETER).intersects(captured), cursor)


class StartupSafetyTest(unittest.TestCase):
    def test_second_instance_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = SingleInstance("demo", folder), SingleInstance("demo", folder)
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())

    def test_freeze_support_runs_before_main(self):
        source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
        entry = source.split('if __name__ == "__main__":')[1]
        self.assertLess(entry.index("multiprocessing.freeze_support()"), entry.index("main()"))


class ReviewFixesTest(unittest.TestCase):
    """Regressionstests für Fehler aus der Code-Prüfung."""

    def test_pen_loop_that_ends_at_its_start_is_kept(self):
        canvas = Canvas(white_pixmap())
        canvas.tool = "pen"
        canvas.begin(QPointF(50, 50))
        for point in ((120, 50), (120, 100), (50, 100), (51, 51)):
            canvas.drag(QPointF(*point))
        canvas.end(QPointF(51, 51))
        self.assertEqual(canvas.annotation_count(), 1)

    def test_pen_click_without_movement_is_discarded(self):
        canvas = Canvas(white_pixmap())
        draw(canvas, "pen", (50, 50), (51, 50))
        self.assertEqual(canvas.annotation_count(), 0)

    def test_pixelated_area_cannot_be_moved_or_selected(self):
        canvas = Canvas(white_pixmap())
        draw(canvas, "pixelate", (10, 10), (90, 90))
        item = canvas._history[0][1]
        flags = item.flags()
        self.assertFalse(flags & QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.assertFalse(flags & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.assertFalse(item.isSelected())

    def test_badge_numbers_stay_unique_after_deleting_one(self):
        canvas = Canvas(white_pixmap())
        for x in (30, 80, 130):
            canvas.add_badge(QPointF(x, 60))
        middle = canvas._history[1][1]
        canvas._scene.clearSelection()
        middle.setSelected(True)
        canvas.delete_selected()
        canvas.add_badge(QPointF(180, 60))
        numbers = sorted(e[1].number for e in canvas._history if e[0] == "item" and e[1].scene() is not None)
        self.assertEqual(numbers, [1, 3, 4])


class SaveTest(unittest.TestCase):
    def test_save_writes_png_with_annotation(self):
        with tempfile.TemporaryDirectory() as folder:
            window = EditorWindow(white_pixmap(), folder)
            window.canvas.color = QColor("#0000ff")
            draw(window.canvas, "ellipse", (20, 20), (180, 100))
            window.save()
            files = list(Path(folder).glob("Screenshot *.png"))
            self.assertEqual(len(files), 1)
            image = QImage(str(files[0]))
            self.assertEqual((image.width(), image.height()), (200, 120))
            self.assertTrue(
                any(
                    image.pixelColor(x, 60) == QColor("#0000ff")
                    for x in range(15, 30)
                )
            )


if __name__ == "__main__":
    unittest.main()
