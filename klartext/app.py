#!/usr/bin/env python3
"""Klartext: Taste halten, sprechen, loslassen. Der aufgeräumte Text erscheint dort, wo du schreibst."""
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
)

from audio import Recorder
from engine import Transcriber, paste_text
from history import History
from hotkey import PushToTalk, resolve_key
from overlay import BLUE, GREEN, ORANGE, RED, StatusPill
from pipeline import finalize
from resources import resource_path
from settings import APP_NAME, Settings, load_api_key, save_api_key, support_dir

KEY_NAMES = {
    "alt_r": "Rechte Option",
    "alt_l": "Linke Option",
    "cmd_r": "Rechte Befehlstaste",
    "ctrl_r": "Rechte Control-Taste",
}
LANGUAGES = [("Deutsch", "de"), ("Englisch", "en"), ("Automatisch erkennen", "auto"), ("Französisch", "fr"), ("Spanisch", "es")]
CLEANUPS = [
    ("Aus (nur Wörterbuch und Kürzel)", "aus"),
    ("Regeln (komplett lokal)", "regeln"),
    ("Claude (nur der Text wird gesendet)", "claude"),
]
STYLES = [("Neutral", "neutral"), ("Locker", "locker"), ("Formell", "formell")]
MODELS = [
    ("tiny (sehr schnell, ungenau)", "tiny"),
    ("base", "base"),
    ("small (empfohlen)", "small"),
    ("medium (genauer, langsamer)", "medium"),
    ("large-v3 (am genauesten, langsam)", "large-v3"),
]


class Controller(QObject):
    """Verbindet Taste, Aufnahme, Erkennung, Aufräumen und Einfügen."""

    start_requested = Signal()
    stop_requested = Signal()
    model_ready = Signal()
    text_ready = Signal(str, str)
    failed = Signal(str)

    def __init__(self, settings, history, pill):
        super().__init__()
        self.settings = settings
        self.history = history
        self.pill = pill
        self.recorder = Recorder()
        self.transcriber = Transcriber(settings["model"])
        self.ready = False
        self.recording = False
        self.start_requested.connect(self._start)
        self.stop_requested.connect(self._stop)
        self.model_ready.connect(self._on_ready)
        self.text_ready.connect(self._insert)
        self.failed.connect(self._on_failed)

    def load_model(self, name=None):
        if name and name != self.transcriber.model_name:
            self.transcriber = Transcriber(name)
        self.ready = False
        self.pill.show_state("Lade Spracherkennung …", BLUE)
        threading.Thread(target=self._load, args=(self.transcriber,), daemon=True).start()

    def _load(self, transcriber):
        try:
            transcriber.load()
        except Exception as error:  # Download oder Speicher: dem Benutzer melden
            self.failed.emit(f"Modell nicht geladen: {error}")
            return
        if transcriber is self.transcriber:
            self.model_ready.emit()

    def _on_ready(self):
        self.ready = True
        self.pill.show_state("Klartext ist bereit", GREEN, 1500)

    def _start(self):
        if not self.ready:
            self.pill.show_state("Spracherkennung lädt noch …", ORANGE, 1800)
            return
        try:
            self.recorder.start()
        except Exception as error:
            self.failed.emit(f"Mikrofon nicht verfügbar: {error}")
            return
        self.recording = True
        self.pill.show_state("Ich höre zu …", RED)

    def _stop(self):
        if not self.recording:
            return
        self.recording = False
        audio = self.recorder.stop()
        self.pill.show_state("Wird aufgeräumt …", BLUE)
        threading.Thread(target=self._work, args=(audio,), daemon=True).start()

    def _work(self, audio):
        try:
            settings = self.settings
            raw = self.transcriber.transcribe(audio, settings["language"], settings.dictionary_words())
            text = finalize(
                raw,
                settings["language"],
                settings["cleanup"],
                settings["style"],
                settings["dictionary"],
                settings["snippets"],
                load_api_key(),
            )
            self.text_ready.emit(text, raw)
        except Exception as error:
            self.failed.emit(f"Fehler: {error}")

    def _insert(self, text, raw):
        if not text:
            self.pill.show_state("Nichts erkannt", ORANGE, 1500)
            return
        paste_text(text)
        self.history.add(text, raw)
        self.pill.show_state("Eingefügt", GREEN, 1000)

    def _on_failed(self, message):
        print(message, file=sys.stderr)
        self.pill.show_state(message[:90], RED, 5000)


def ask_api_key():
    key, ok = QInputDialog.getText(
        None,
        "Claude-Schlüssel",
        "API-Schlüssel (wird nur auf diesem Mac gespeichert):",
        QLineEdit.EchoMode.Password,
    )
    if ok and key.strip():
        save_api_key(key)
        return True
    return False


def add_choice_menu(menu, title, options, current, on_pick):
    submenu = menu.addMenu(title)
    group = QActionGroup(submenu)
    group.setExclusive(True)
    for label, value in options:
        action = QAction(label, submenu, checkable=True)
        action.setChecked(value == current)
        action.triggered.connect(lambda _checked=False, v=value: on_pick(v))
        group.addAction(action)
        submenu.addAction(action)


def build_menu(menu, controller, settings, history, app):
    menu.clear()
    key = KEY_NAMES.get(settings["key"], settings["key"].upper())
    info = menu.addAction(f"Taste halten: {key}  ·  kurz tippen = Freihand")
    info.setEnabled(False)
    menu.addSeparator()

    def pick_cleanup(value):
        if value == "claude" and not load_api_key() and not ask_api_key():
            QMessageBox.information(None, APP_NAME, "Ohne Schlüssel bleibt es bei den lokalen Regeln.")
            return
        settings["cleanup"] = value

    add_choice_menu(menu, "Aufräumen", CLEANUPS, settings["cleanup"], pick_cleanup)
    add_choice_menu(menu, "Stil (nur mit Claude)", STYLES, settings["style"], lambda v: settings.__setitem__("style", v))
    add_choice_menu(menu, "Sprache", LANGUAGES, settings["language"], lambda v: settings.__setitem__("language", v))

    def pick_model(value):
        settings["model"] = value
        controller.load_model(value)

    add_choice_menu(menu, "Spracherkennung", MODELS, settings["model"], pick_model)

    recent = menu.addMenu("Verlauf")
    entries = history.recent(8)
    if not entries:
        recent.addAction("Noch nichts diktiert").setEnabled(False)
    for entry in entries:
        text = entry["text"]
        label = text if len(text) <= 60 else text[:59] + "…"
        action = recent.addAction(label.replace("&", "&&"))
        action.triggered.connect(lambda _c=False, t=text: copy_text(controller, t))

    menu.addSeparator()
    menu.addAction("Claude-Schlüssel speichern …").triggered.connect(lambda: ask_api_key())
    menu.addAction("Wörterbuch und Kürzel bearbeiten …").triggered.connect(
        lambda: subprocess.run(["open", "-t", str(settings.path)], check=False)
    )
    menu.addSeparator()
    menu.addAction("Beenden").triggered.connect(app.quit)


def copy_text(controller, text):
    QGuiApplication.clipboard().setText(text)
    controller.pill.show_state("In die Zwischenablage kopiert", GREEN, 1200)


def start_listener(controller, settings):
    from pynput import keyboard

    target = resolve_key(settings["key"])
    talk = PushToTalk(
        controller.start_requested.emit, controller.stop_requested.emit, settings["tap_seconds"]
    )
    listener = keyboard.Listener(
        on_press=lambda k: k == target and talk.press(),
        on_release=lambda k: k == target and talk.release(),
    )
    listener.start()
    return listener


def selftest():
    """Prüft, ob alle Bausteine in der gebauten App vorhanden sind (ohne Oberfläche und Mikrofon)."""
    import ctranslate2
    import faster_whisper
    import numpy
    import onnxruntime
    import pynput
    import sounddevice

    print("Selbsttest ok:", faster_whisper.__name__, ctranslate2.__version__, numpy.__version__)
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        sys.exit("Kein Menüleistensymbol möglich.")

    settings = Settings()
    settings.save()
    history = History(support_dir() / "history.json")
    pill = StatusPill()
    controller = Controller(settings, history, pill)

    menu = QMenu()
    menu.aboutToShow.connect(lambda: build_menu(menu, controller, settings, history, app))
    tray = QSystemTrayIcon(QIcon(str(resource_path("assets/logo.png"))))
    tray.setToolTip(APP_NAME)
    tray.setContextMenu(menu)
    tray.show()

    listener = None
    try:
        listener = start_listener(controller, settings)
    except Exception as error:
        controller.failed.emit(f"Taste nicht verfügbar: {error}")
    controller.load_model()

    code = app.exec()
    if listener:
        listener.stop()
    sys.exit(code)


if __name__ == "__main__":
    main()
