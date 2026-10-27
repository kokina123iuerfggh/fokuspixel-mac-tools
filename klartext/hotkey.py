"""Tastenlogik: gedrückt halten zum Sprechen, kurzes Antippen für Freihand-Modus, frei wählbare Taste."""
import time

DEFAULT_KEY = "alt_r"

# Vorschläge im Menü: (Name der Taste bei pynput, Anzeigename)
PRESET_KEYS = [
    ("alt_r", "Rechte Option"),
    ("alt", "Linke Option"),
    ("cmd_r", "Rechte Befehlstaste"),
    ("ctrl_r", "Rechte Control-Taste"),
    ("shift_r", "Rechte Umschalttaste"),
    ("f6", "F6"),
    ("f8", "F8"),
    ("f9", "F9"),
]
DISPLAY_NAMES = dict(PRESET_KEYS)
DISPLAY_NAMES.update({"cmd": "Linke Befehlstaste", "ctrl": "Linke Control-Taste", "shift": "Linke Umschalttaste"})

# pynput nennt die linken Tasten ohne Zusatz. Ältere Einstellungen mit „_l“ werden umgewandelt.
ALIASES = {"alt_l": "alt", "cmd_l": "cmd", "ctrl_l": "ctrl", "shift_l": "shift"}

# Diese Tasten braucht man beim Schreiben. Als Aufnahme-Taste würden sie ständig stören.
UNSUITABLE = {
    "enter", "space", "tab", "backspace", "delete", "esc", "up", "down", "left", "right",
    "home", "end", "page_up", "page_down", "caps_lock", "insert",
}

# So lange nach dem Einfügen werden Tastendrücke ignoriert: Das Einfügen drückt selbst Cmd+V,
# und das darf keine Aufnahme starten, wenn die Befehlstaste die Aufnahme-Taste ist.
PASTE_MUTE_SECONDS = 0.5


def normalise_key_name(name):
    if not isinstance(name, str):
        return ""
    return ALIASES.get(name, name)


def key_name(key):
    """Name einer pynput-Taste. Buchstaben und Zahlen haben keinen Namen, dafür gibt es None."""
    return getattr(key, "name", None)


def is_suitable_key(name):
    name = normalise_key_name(name)
    return bool(name) and name not in UNSUITABLE


def is_known_key(name):
    """Kennt pynput die Taste? Ohne pynput (zum Beispiel in Tests) wird nicht geprüft."""
    name = normalise_key_name(name)
    if not name:
        return False
    try:
        from pynput import keyboard
    except Exception:
        return True
    return hasattr(keyboard.Key, name)


def is_valid_key(name):
    return is_suitable_key(name) and is_known_key(name)


def display_name(name):
    name = normalise_key_name(name)
    if not name:
        return "Keine"
    return DISPLAY_NAMES.get(name, name.upper().replace("_", " "))


class PushToTalk:
    """idle -> holding (Taste unten) -> idle, oder bei kurzem Antippen handsfree bis zum nächsten Druck."""

    def __init__(self, on_start, on_stop, tap_seconds=0.3, clock=time.monotonic):
        self.on_start = on_start
        self.on_stop = on_stop
        self.tap_seconds = tap_seconds
        self.clock = clock
        self.state = "idle"
        self._pressed_at = 0.0

    def press(self):
        if self.state == "handsfree":
            self.state = "idle"
            self.on_stop()
        elif self.state == "idle":
            self.state = "holding"
            self._pressed_at = self.clock()
            self.on_start()
        # "holding": Tastenwiederholung des Systems, ignorieren

    def release(self):
        if self.state != "holding":
            return
        if self.clock() - self._pressed_at < self.tap_seconds:
            self.state = "handsfree"
        else:
            self.state = "idle"
            self.on_stop()

    def cancel(self):
        """Beendet eine laufende Aufnahme, zum Beispiel wenn die Taste gewechselt wird."""
        was_active = self.state != "idle"
        self.state = "idle"
        if was_active:
            self.on_stop()

    def reset(self):
        """Setzt den Zustand zurück, ohne on_stop aufzurufen (die Aufnahme hatte gar nicht begonnen)."""
        self.state = "idle"


class KeyBinding:
    """Verbindet die gewählte Taste mit der Aufnahmelogik. Die Taste lässt sich zur Laufzeit ändern."""

    def __init__(self, talk, key=DEFAULT_KEY, clock=time.monotonic):
        self.talk = talk
        self.key = normalise_key_name(key)
        self.clock = clock
        self._capture = None
        self._capture_token = 0
        self._muted_until = 0.0

    @property
    def capturing(self):
        return self._capture is not None

    def set_key(self, name):
        self.talk.cancel()
        self.key = normalise_key_name(name)

    def mute(self, seconds=PASTE_MUTE_SECONDS):
        """Ignoriert Tastendrücke kurz, zum Beispiel während die App selbst Cmd+V drückt."""
        self._muted_until = self.clock() + seconds

    def capture_next(self, callback):
        """Der nächste Tastendruck wird nicht zum Aufnehmen genutzt, sondern an callback(name) gemeldet.

        Gibt eine Nummer zurück, mit der sich genau diese Erfassung wieder abbrechen lässt.
        """
        self._capture = callback
        self._capture_token += 1
        return self._capture_token

    def cancel_capture(self, token=None):
        """Bricht die Erfassung ab. Mit Nummer nur dann, wenn es noch dieselbe Erfassung ist."""
        if self._capture is None:
            return False
        if token is not None and token != self._capture_token:
            return False
        self._capture = None
        return True

    def press(self, name):
        if self._capture is not None:
            callback, self._capture = self._capture, None
            callback(normalise_key_name(name) or None)
            return
        if self.clock() < self._muted_until:
            return
        if name and normalise_key_name(name) == self.key:
            self.talk.press()

    def release(self, name):
        if self.clock() < self._muted_until:
            return
        if name and normalise_key_name(name) == self.key:
            self.talk.release()
