"""Tastenlogik: gedrückt halten zum Sprechen, kurzes Antippen für Freihand-Modus."""
import time


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


def resolve_key(name):
    from pynput import keyboard

    try:
        return getattr(keyboard.Key, name)
    except AttributeError:
        raise ValueError(f"Unbekannte Taste: {name}")
