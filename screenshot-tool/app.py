#!/usr/bin/env python3
"""Bildschirm-Werkzeug: Screenshots aufnehmen und bearbeiten, Mauszeiger hervorheben.

Läuft als Symbol in der Menüleiste.
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from cursor_highlight import CursorHighlight
from editor import EditorWindow
from resources import resource_path

HOTKEY_AREA = "<ctrl>+<alt>+s"
HOTKEY_CURSOR = "<ctrl>+<alt>+m"


class Bridge(QObject):
    """Reicht Ereignisse aus den pynput-Threads an den Qt-Hauptthread weiter."""

    area_requested = Signal()
    cursor_toggle_requested = Signal()
    mouse_pressed = Signal(bool)


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
    return QIcon(str(resource_path("assets/logo.png")))


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
            on_click=lambda _x, _y, _button, pressed: bridge.mouse_pressed.emit(pressed)
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

    print("Selbsttest ok: PySide6", PySide6.__version__)
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = parse_args()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        sys.exit("Kein Menüleistensymbol möglich.")

    bridge = Bridge()
    highlight = CursorHighlight()
    editors = []

    def open_capture(area):
        pixmap = capture(area)
        if pixmap is None:
            return
        window = EditorWindow(pixmap, args.save_dir)
        editors.append(window)
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

    menu = QMenu()
    area_action = QAction(f"Bereich aufnehmen ({HOTKEY_AREA})", menu)
    area_action.triggered.connect(lambda: request(True))
    full_action = QAction("Ganzen Bildschirm aufnehmen", menu)
    full_action.triggered.connect(lambda: request(False))
    cursor_action = QAction(f"Mauszeiger hervorheben ({HOTKEY_CURSOR})", menu, checkable=True)
    cursor_action.triggered.connect(lambda _checked: toggle_cursor())
    folder_action = QAction("Screenshot-Ordner öffnen", menu)
    folder_action.triggered.connect(lambda: subprocess.run(["open", args.save_dir], check=False))
    quit_action = QAction("Beenden", menu)
    quit_action.triggered.connect(app.quit)
    for action in (area_action, full_action, cursor_action, folder_action):
        menu.addAction(action)
    menu.addSeparator()
    menu.addAction(quit_action)

    tray = QSystemTrayIcon(make_icon())
    tray.setToolTip("Bildschirm-Werkzeug")
    tray.setContextMenu(menu)
    tray.show()

    bridge.area_requested.connect(lambda: request(True))
    bridge.cursor_toggle_requested.connect(toggle_cursor)
    bridge.mouse_pressed.connect(highlight.set_pressed)

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
    main()
