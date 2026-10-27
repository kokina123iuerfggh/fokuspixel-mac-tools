#!/usr/bin/env python3
"""Bildschirm-Werkzeug: Screenshots aufnehmen und bearbeiten, Mauszeiger hervorheben, Lupe.

Läuft als Symbol in der Menüleiste.
"""
import argparse
import multiprocessing
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from cursor_highlight import DEFAULT_MAGNIFY, DEFAULT_RADIUS, MAGNIFY_PRESETS, PRESETS, CursorHighlight
from editor import EditorWindow
from magnifier import ZOOMS, MagnifierLens
from resources import resource_path
from single_instance import SingleInstance
from version import app_version

HOTKEY_AREA = "<ctrl>+<alt>+s"
HOTKEY_CURSOR = "<ctrl>+<alt>+m"
HOTKEY_LENS = "<ctrl>+<alt>+l"
WHEEL_STEP = 3  # Pixel Radius pro Mausrad-Rastung


class Bridge(QObject):
    """Reicht Ereignisse aus den pynput-Threads an den Qt-Hauptthread weiter."""

    area_requested = Signal()
    cursor_toggle_requested = Signal()
    lens_toggle_requested = Signal()
    mouse_pressed = Signal(bool)
    mouse_scrolled = Signal(float)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-dir",
        default=str(Path.home() / "Pictures" / "Screenshots"),
        help="Ordner, in den gespeichert wird",
    )
    parser.add_argument("--no-hotkeys", action="store_true", help="Tastenkürzel abschalten")
    return parser.parse_args()


def make_icon():
    icon = QIcon(str(resource_path("assets/tray.png")))
    icon.setIsMask(True)  # macOS färbt das Symbol passend zur hellen oder dunklen Menüleiste ein
    return icon


def capture(area):
    """Gibt das aufgenommene Bild zurück, oder None bei Abbruch."""
    if sys.platform == "darwin":
        fd, name = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        command = ["screencapture", "-x"] + (["-i"] if area else []) + [name]
        subprocess.run(command, check=False)
        pixmap = QPixmap(name)
        os.unlink(name)
        return None if pixmap.isNull() else pixmap
    screen = QGuiApplication.primaryScreen()
    return screen.grabWindow(0) if screen else None


def start_hotkeys(bridge):
    try:
        from pynput import keyboard

        listener = keyboard.GlobalHotKeys(
            {
                HOTKEY_AREA: bridge.area_requested.emit,
                HOTKEY_CURSOR: bridge.cursor_toggle_requested.emit,
                HOTKEY_LENS: bridge.lens_toggle_requested.emit,
            }
        )
        listener.start()
        return listener
    except Exception as error:  # Berechtigung fehlt oder pynput nicht verfügbar
        print(f"Tastenkürzel nicht verfügbar: {error}")
        return None


def start_mouse_watcher(bridge):
    try:
        from pynput import mouse

        listener = mouse.Listener(
            on_click=lambda _x, _y, _button, pressed: bridge.mouse_pressed.emit(pressed),
            on_scroll=lambda _x, _y, _dx, dy: bridge.mouse_scrolled.emit(float(dy)),
        )
        listener.start()
        return listener
    except Exception as error:
        print(f"Klick-Anzeige nicht verfügbar: {error}")
        return None


def selftest():
    """Prüft, ob alle Bausteine in der gebauten App vorhanden sind (ohne Oberfläche)."""
    import PySide6
    import pynput.keyboard
    import pynput.mouse

    print("Selbsttest ok: PySide6", PySide6.__version__, pynput.keyboard.__name__, pynput.mouse.__name__)
    return 0


def main():
    if "--version" in sys.argv:
        print(app_version())
        sys.exit(0)
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    instance = SingleInstance("bildschirm-werkzeug")
    if not instance.acquire():
        print("Das Bildschirm-Werkzeug läuft bereits.")
        sys.exit(0)
    args = parse_args()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("Fokus Pixel")
    app.setApplicationName("Bildschirm-Werkzeug")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        sys.exit("Kein Menüleistensymbol möglich.")

    prefs = QSettings()
    bridge = Bridge()
    highlight = CursorHighlight(
        int(prefs.value("radius", DEFAULT_RADIUS)), float(prefs.value("magnify", DEFAULT_MAGNIFY))
    )
    lens = MagnifierLens(float(prefs.value("zoom", 3.0)))
    # Die Lupe nimmt unterhalb des Leuchtkreises auf, damit er nicht mit im Bild ist
    lens.reference_provider = lambda: highlight if highlight.isVisible() else lens
    editors = []

    def open_capture(area):
        pixmap = capture(area)
        if pixmap is None:
            return
        window = EditorWindow(pixmap, args.save_dir)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        editors.append(window)  # Verweis halten, solange das Fenster offen ist
        window.destroyed.connect(lambda _obj=None, w=window: w in editors and editors.remove(w))
        window.show()
        window.raise_()
        window.activateWindow()

    def request(area):
        # Kurz warten, damit das Menü verschwunden ist
        QTimer.singleShot(250, lambda: open_capture(area))

    def toggle_cursor():
        if highlight.isVisible():
            highlight.stop()
        else:
            highlight.start()
        cursor_action.setChecked(highlight.isVisible())

    def toggle_lens():
        if lens.isVisible():
            lens.stop()
        else:
            lens.start()
        lens_action.setChecked(lens.isVisible())

    def set_radius(radius):
        prefs.setValue("radius", highlight.set_radius(radius))

    def set_magnify(factor):
        prefs.setValue("magnify", highlight.set_magnify(factor))

    def set_zoom(zoom):
        lens.set_zoom(zoom)
        prefs.setValue("zoom", zoom)

    def on_scroll(delta):
        # Nur mit gedrückter Optionstaste, damit normales Scrollen unverändert bleibt
        optionsdruck = QGuiApplication.queryKeyboardModifiers() & Qt.KeyboardModifier.AltModifier
        if highlight.isVisible() and optionsdruck:
            prefs.setValue("radius", highlight.change_radius(delta * WHEEL_STEP))

    menu = QMenu()
    area_action = QAction(f"Bereich aufnehmen ({HOTKEY_AREA})", menu)
    area_action.triggered.connect(lambda: request(True))
    full_action = QAction("Ganzen Bildschirm aufnehmen", menu)
    full_action.triggered.connect(lambda: request(False))
    cursor_action = QAction(f"Mauszeiger hervorheben ({HOTKEY_CURSOR})", menu, checkable=True)
    cursor_action.triggered.connect(lambda _checked: toggle_cursor())

    size_menu = QMenu("Größe des Leuchtkreises", menu)
    size_menu.addAction("Mit Optionstaste + Mausrad stufenlos ändern").setEnabled(False)
    size_menu.addSeparator()
    size_group = QActionGroup(size_menu)
    size_actions = []
    for label, radius in PRESETS:
        action = QAction(label, size_menu, checkable=True)
        action.triggered.connect(lambda _c=False, r=radius: set_radius(r))
        size_group.addAction(action)
        size_menu.addAction(action)
        size_actions.append((action, radius))

    magnify_menu = QMenu("Vergrößerung im Leuchtkreis", menu)
    magnify_group = QActionGroup(magnify_menu)
    magnify_actions = []
    for label, factor in MAGNIFY_PRESETS:
        action = QAction(label, magnify_menu, checkable=True)
        action.triggered.connect(lambda _c=False, f=factor: set_magnify(f))
        magnify_group.addAction(action)
        magnify_menu.addAction(action)
        magnify_actions.append((action, factor))

    lens_action = QAction(f"Lupe neben dem Zeiger ({HOTKEY_LENS})", menu, checkable=True)
    lens_action.triggered.connect(lambda _checked: toggle_lens())
    zoom_menu = QMenu("Vergrößerung der Lupe", menu)
    zoom_group = QActionGroup(zoom_menu)
    zoom_actions = []
    for label, zoom in ZOOMS:
        action = QAction(label, zoom_menu, checkable=True)
        action.triggered.connect(lambda _c=False, z=zoom: set_zoom(z))
        zoom_group.addAction(action)
        zoom_menu.addAction(action)
        zoom_actions.append((action, zoom))

    def refresh_checks():
        for action, radius in size_actions:
            action.setChecked(highlight.radius == radius)
        for action, zoom in zoom_actions:
            action.setChecked(lens.zoom == zoom)
        for action, factor in magnify_actions:
            action.setChecked(highlight.magnify == factor)

    folder_action = QAction("Screenshot-Ordner öffnen", menu)
    folder_action.triggered.connect(lambda: subprocess.run(["open", args.save_dir], check=False))
    quit_action = QAction("Beenden", menu)
    quit_action.triggered.connect(app.quit)

    menu.addAction(area_action)
    menu.addAction(full_action)
    menu.addSeparator()
    menu.addAction(cursor_action)
    menu.addMenu(size_menu)
    menu.addMenu(magnify_menu)
    menu.addAction(lens_action)
    menu.addMenu(zoom_menu)
    menu.addSeparator()
    menu.addAction(folder_action)
    menu.addSeparator()
    menu.addAction(f"Bildschirm-Werkzeug {app_version()}").setEnabled(False)
    menu.addAction(quit_action)
    menu.aboutToShow.connect(refresh_checks)

    tray = QSystemTrayIcon(make_icon())
    tray.setToolTip("Bildschirm-Werkzeug")
    tray.setContextMenu(menu)
    tray.show()

    bridge.area_requested.connect(lambda: request(True))
    bridge.cursor_toggle_requested.connect(toggle_cursor)
    bridge.lens_toggle_requested.connect(toggle_lens)
    bridge.mouse_pressed.connect(highlight.set_pressed)
    bridge.mouse_scrolled.connect(on_scroll)

    listeners = []
    if not args.no_hotkeys:
        listeners.append(start_hotkeys(bridge))
    listeners.append(start_mouse_watcher(bridge))

    code = app.exec()
    for listener in listeners:
        if listener:
            listener.stop()
    sys.exit(code)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # in der gepackten App als Erstes, sonst starten Hilfsprozesse neue Kopien
    main()
