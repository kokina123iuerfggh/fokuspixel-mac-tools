"""Spracherkennung (lokal mit faster-whisper) und Einfügen des Textes."""
import subprocess
import threading
import time

from audio import MIN_SECONDS, SAMPLE_RATE


def _use_thread_locks():
    """Die Fortschrittsanzeige beim Modell-Download soll keine Prozess-Sperren anlegen.

    Diese starten auf dem Mac in einer gepackten App einen Hilfsprozess, und der ruft die App erneut auf.
    """
    try:
        from tqdm import tqdm

        tqdm.set_lock(threading.RLock())
    except ImportError:
        pass


class Transcriber:
    def __init__(self, model_name):
        self.model_name = model_name
        self.model = None

    def load(self):
        _use_thread_locks()
        from faster_whisper import WhisperModel

        self.model = WhisperModel(self.model_name, device="auto", compute_type="int8")

    def transcribe(self, audio, language, hints=None):
        if audio.size < SAMPLE_RATE * MIN_SECONDS:
            return ""
        segments, _info = self.model.transcribe(
            audio,
            language=None if language in (None, "", "auto") else language,
            vad_filter=True,
            beam_size=5,
            initial_prompt=", ".join(hints) if hints else None,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


def paste_text(text):
    """Fügt Text mit Cmd+V ein und stellt die vorherige Zwischenablage (nur Text) kurz danach wieder her."""
    from pynput import keyboard

    previous = subprocess.run(["pbpaste"], capture_output=True, check=False).stdout
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    time.sleep(0.05)
    controller = keyboard.Controller()
    controller.press(keyboard.Key.cmd)
    controller.press("v")
    controller.release("v")
    controller.release(keyboard.Key.cmd)
    if previous:
        threading.Timer(
            0.6, lambda: subprocess.run(["pbcopy"], input=previous, check=False)
        ).start()
