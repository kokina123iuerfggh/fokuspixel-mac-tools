"""Sorgt dafür, dass die App nur einmal läuft. Ein zweiter Start beendet sich sofort.

Das ist die Sicherung gegen eine Kettenreaktion: Startet eine Bibliothek in einer gepackten App
versehentlich neue Kopien der App, würde sich sonst jede Kopie wieder neu starten.
Die Sperre gibt das Betriebssystem automatisch frei, wenn der Prozess endet, auch nach einem Absturz.
"""
import fcntl
import tempfile
from pathlib import Path


class SingleInstance:
    def __init__(self, name, folder=None):
        self.path = Path(folder or tempfile.gettempdir()) / f"{name}.lock"
        self._handle = open(self.path, "w")

    def acquire(self):
        try:
            fcntl.flock(self._handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True
